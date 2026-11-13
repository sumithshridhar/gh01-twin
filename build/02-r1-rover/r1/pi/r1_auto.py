"""Drive one path by itself: lidar + ground sensor + step sensors -> r1_supervisor -> I/O board, photos at each station.
Starter code, untested on hardware. Added 13 Nov 2026 (ISSUES.md E5: v1 listed a lidar in the parts but had no code
that read it, so R1 could only be driven by hand from the phone).

  python3 r1_auto.py --house 1 --bed 3     the worker has parked it at the start of that path, tag in view

Hardware it reads (bench steps in ISSUES.md; check each driver there before trusting it):
  lidar    RPLIDAR C1 on its USB adapter, mounted LOW at the front (about 15 cm, under the bed tops)
  steps    2 x VL53L1X ToF on I2C, front corners, aimed down at the ground 25 cm ahead
  ground   PMW3901 optical-flow sensor on SPI, under the deck, 8-10 cm above the soil
The loop only talks to `sensors.read()`, so the same loop runs on a laptop with the simulator standing in for the
hardware (tests/test_r1_pi.py: test_auto_loop_with_the_simulator).
"""
import math
import time

from r1_supervisor import Sense, estimate_walls, scan_to_points, Cfg


def read_tag(img, cv2=None):
    """The QR tag on the stake at each bed end says 'H<house>-B<bed>'. Returns its text, or None."""
    if cv2 is None:
        import cv2 as _cv2
        cv2 = _cv2
    txt, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return txt or None


def path_width(pts, cfg=None):
    """Width of the path the lidar sees, wall to wall, or None."""
    w = estimate_walls(pts, cfg or Cfg())
    return round(w.d_left + w.d_right, 3) if w.ok else None


def start_checks(house, bed, tag, width, bath_confirmed_at, now_s, air_c, rh, box_c, battery_wh, plan_wh,
                 sickest_today=None):
    """Every reason not to start this path now (empty = go). The same rules as r1_mission, in one place."""
    from r1_mission import door_ok, may_enter, patrol_gate, start_ok
    why = []
    for g in (start_ok(house, bed, tag, width), door_ok(house.id, bath_confirmed_at, now_s),
              patrol_gate(air_c, rh, box_c, battery_wh, plan_wh), may_enter(house, sickest_today)):
        why += g.why
    return why


def sickest_today(day_log_path, today):
    """The highest risk of any house R1 has been in today, from ~/r1/day.json ({date: [risk, ...]})."""
    import json
    from pathlib import Path
    from r1_mission import RISK
    p = Path(day_log_path)
    seen = json.loads(p.read_text()).get(today, []) if p.exists() else []
    return max(seen, key=lambda r: RISK[r]) if seen else None


def log_visit(day_log_path, today, risk):
    import json
    from pathlib import Path
    p = Path(day_log_path)
    d = json.loads(p.read_text()) if p.exists() else {}
    d.setdefault(today, []).append(risk)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d))


def run_path(link, sensors, sup, capturer=None, phone=None, clock=time.monotonic, sleep=time.sleep, max_s=3600.0):
    """phone: .send(kind, metre, message) and .poll() -> 'resume' | 'skip' | None. Returns the supervisor."""
    link.send("L g")
    if capturer:
        link.send("F 1")                              # rings on for the whole path, not flashed
    t0 = clock()
    try:
        while clock() - t0 < max_s:
            t = clock()
            s = sensors.read(t)
            s.tripped, s.batt_low, s.batt_flat = link.tripped, link.batt_low, link.batt_flat
            cmd = phone.poll() if phone else None
            s.resume, s.skip = cmd == "resume", cmd == "skip"
            if s.resume and link.tripped:
                link.resume()                         # the board accepts it only if RESET was pressed on the rover
            out = sup.step(s)
            for kind, metre, msg in out.events:
                if kind == "photo" and capturer:
                    link.set_drive(0, 0)              # stopped while the cameras take turns
                    capturer.shoot(metre)
                elif kind != "photo" and phone:
                    phone.send(kind, metre, msg)
            link.set_drive(out.left, out.right)
            if out.state == "DONE":
                break
            sleep(max(0.0, 0.1 - (clock() - t)))
    finally:
        link.set_drive(0, 0)
        if capturer:
            link.send("F 0")
    return sup


class HardwareSensors:
    """The real sensors. Libraries: pip install rplidar-roboticia vl53l1x pmw3901 (all untested with R1 so far)."""

    def __init__(self, cfg):
        import threading
        from rplidar import RPLidar
        import VL53L1X
        from pmw3901 import PMW3901
        self.cfg = cfg
        s = cfg.get("sensors", {})
        self.lidar_x = s.get("lidar_x", 0.30)
        self.tof_h, self.tof_d = s.get("tof_height_m", 0.15), s.get("tof_ahead_m", 0.25)
        self.flow_k = s.get("flow_m_per_count", 0.0005)  # measure: push it 1 m by hand, divide by the counts
        self.lidar = RPLidar(cfg.get("lidar_port", "/dev/ttyUSB0"), baudrate=460800)
        self.tofs = []
        # Both VL53L1X start at address 0x29. At boot, hold the right one's XSHUT pin (GPIO 17) low, move the left one
        # to 0x30, then release it (bench test B4 checks this, and the library's call for it, before trusting it).
        for addr in (0x29, 0x30):
            t = VL53L1X.VL53L1X(i2c_bus=1, i2c_address=addr)
            t.open()
            t.start_ranging(1)                        # short range mode: steadier in daylight
            self.tofs.append(t)
        self.flow = PMW3901(spi_port=0, spi_cs_gpio=s.get("flow_cs_gpio", 7))
        self.scan = (None, None)
        self.last_t = None
        threading.Thread(target=self._lidar_loop, daemon=True).start()

    def _lidar_loop(self):
        for scan in self.lidar.iter_scans():          # [(quality, angle_deg clockwise, distance_mm), ...]
            a = [-math.radians(((d + 180) % 360) - 180) for _, d, _ in scan]
            r = [mm / 1000.0 for _, _, mm in scan]
            self.scan = (a, r)

    def step_height(self, t):
        r0 = math.hypot(self.tof_h, self.tof_d)       # flat ground
        r = t.get_distance() / 1000.0
        return (r0 - r) * self.tof_h / r0             # + = something on the ground, - = a hole

    def read(self, t):
        a, r = self.scan
        pts = scan_to_points(a or [], r or [], self.lidar_x)
        dt = 0.1 if self.last_t is None else max(1e-3, t - self.last_t)
        self.last_t = t
        dx, _ = self.flow.get_motion()
        ground_v = dx * self.flow_k / dt
        return Sense(t=t, pts=pts, step_l=self.step_height(self.tofs[0]), step_r=self.step_height(self.tofs[1]),
                     ground_v=ground_v, wheel_v=ground_v)  # wheel_v is replaced below from the wheel pulses


def main():
    import argparse
    import cv2
    from r1_capture import Capturer
    from r1_link import Link, load_config
    from r1_mission import CROPS, House, Progress, bed_wh, photo_every_for
    from r1_supervisor import Supervisor
    ap = argparse.ArgumentParser()
    ap.add_argument("--house", type=int, required=True)
    ap.add_argument("--bed", type=int, required=True)
    ap.add_argument("--risk", default="green", choices=["green", "amber", "red"], help="from the heat-and-dew alarm")
    ap.add_argument("--air-c", type=float, required=True, help="air temperature now (the alarm box shows it)")
    ap.add_argument("--rh", type=float, required=True, help="humidity now, %%")
    args = ap.parse_args()
    cfg = load_config()
    h = next(x for x in cfg["houses"] if x["id"] == args.house)
    house = House(h["id"], h["crop"], h["beds"], h["bed_len_m"], h["path_w_m"], args.risk)
    progress = Progress(f"{__import__('os').path.expanduser('~')}/r1/progress.json")
    start = progress.scanned_to(house.id, args.bed)
    bath = input("Wheel bath + mist done at this door just now? y/n: ").strip().lower() == "y"
    link = Link(cfg)
    sensors = HardwareSensors(cfg)
    time.sleep(1.0)                                   # a few lidar scans
    if start > 0:                                     # carrying on mid-path: no tag here, a person confirms instead
        same = input(f"R1 is still where it stopped (house {house.id}, bed {args.bed}, metre {start:.1f})? y/n: ")
        tag = f"H{house.id}-B{args.bed}" if same.strip().lower() == "y" else None
    else:
        cam = cv2.VideoCapture(cfg.get("front_camera", 12), cv2.CAP_V4L2)
        ok, img = cam.read()
        cam.release()
        tag = read_tag(img) if ok else None
    width = path_width(sensors.read(time.monotonic()).pts)
    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        box_c = int(f.read()) / 1000 - 20             # Pi chip - ~20 C until a box sensor is fitted
    soc_wh = cfg.get("battery_wh", 768) * (0.8 if not link.batt_low else 0.1)
    import datetime
    day_log = f"{__import__('os').path.expanduser('~')}/r1/day.json"
    today = datetime.date.today().isoformat()
    why = start_checks(house, args.bed, tag, width, {house.id: time.time()} if bath else {}, time.time(),
                       args.air_c, args.rh, box_c, soc_wh, bed_wh(house), sickest_today(day_log, today))
    if why:
        link.close()
        raise SystemExit("Not starting:\n  " + "\n  ".join(why))
    log_visit(day_log, today, house.risk)             # it is inside this house now
    link.send("E 1")
    link.set_drive(0, 0)
    prev = [0.0, time.monotonic()]
    raw_read = sensors.read

    def read_with_wheels(t):                          # wheel speed from the board's pulse counts
        s = raw_read(t)
        d = link.distance_m()
        s.wheel_v = (d - prev[0]) / max(1e-3, t - prev[1])
        prev[0], prev[1] = d, t
        return s
    sensors.read = read_with_wheels
    sup = Supervisor(Cfg(photo_every=photo_every_for(house.risk)), path_len=house.bed_len_m - start,
                     label=f"house {house.id} · bed {args.bed}")
    cap = Capturer(cfg, house.id, args.bed, CROPS[house.crop]["cameras"], heights=CROPS[house.crop].get("heights"))

    class Console:                                    # until the phone page sends taps: type r or s + Enter
        def send(self, kind, metre, msg):
            print(f"[{kind}] {msg or metre}" + ("   -> r = Resume, s = Skip this path" if kind == "ask" else ""))

        def poll(self):
            import select
            import sys
            if select.select([sys.stdin], [], [], 0)[0]:
                return {"r": "resume", "s": "skip"}.get(sys.stdin.readline().strip().lower())
            return None
    try:
        sup = run_path(link, sensors, sup, cap, Console())
    finally:
        progress.record(house.id, args.bed, start + sup.dist)
        for a, z in sup.unscanned:
            progress.skip(house.id, args.bed, start + a, start + z, "skipped by a person")
        cap.close()
        link.close()


if __name__ == "__main__":
    main()
