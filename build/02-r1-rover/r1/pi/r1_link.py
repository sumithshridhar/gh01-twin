"""The serial link to the Arduino Mega (r1_io.ino). Starter code, untested on hardware.

Keeps the Mega's 300 ms watchdog fed, parses its status lines, and gives the other scripts one place to send commands.

13 Nov 2026 (firmware v2): reads the battery voltage and the status flags (tripped, RESET latch, battery low/flat,
waiting for neutral, valve time limit, tank dry); sends a stop at once instead of waiting for the next 100 ms resend;
resume() re-enables the drive after a person has pressed RESET on the rover and tapped Resume on the phone.
"""
import threading
import time

FLAG_TRIPPED, FLAG_LATCH, FLAG_BATT_LOW, FLAG_BATT_FLAT = 1, 2, 4, 8
FLAG_NEED_NEUTRAL, FLAG_VALVE_LIMIT, FLAG_TANK_DRY = 16, 32, 64


def parse_status(line):
    """'S fl fr rl rr estop tank armed battery_dV flags' -> dict, or None if it isn't a complete status line.
    Also accepts the 8-field line of firmware v1 (no battery, no flags)."""
    parts = line.split()
    if not parts or parts[0] != "S" or len(parts) not in (8, 10):
        return None
    try:
        nums = [int(x) for x in parts[1:]]
    except ValueError:
        return None
    flags = nums[8] if len(nums) == 9 else 0
    return {
        "pulses": nums[0:4],
        "estop_ok": nums[4] == 1,
        "tank_ok": nums[5] == 1,
        "armed": nums[6] == 1,
        "battery_v": nums[7] / 10.0 if len(nums) == 9 else None,
        "flags": flags,
        "tripped": bool(flags & FLAG_TRIPPED),
        "latch": bool(flags & FLAG_LATCH),
        "batt_low": bool(flags & FLAG_BATT_LOW),
        "batt_flat": bool(flags & FLAG_BATT_FLAT),
        "need_neutral": bool(flags & FLAG_NEED_NEUTRAL),
    }


class Link:
    def __init__(self, cfg, ser=None):
        self.cfg = cfg
        if ser is None:
            import serial                            # only on the rover; the tests pass a fake port
            ser = serial.Serial(cfg["serial_port"], 115200, timeout=0.05)
            time.sleep(2.0)                          # the Mega resets when the port opens
        self.ser = ser
        self.lock = threading.Lock()
        self.pulses = [0, 0, 0, 0]
        self.estop_ok = self.tank_ok = self.armed = False
        self.tripped = self.latch = self.batt_low = self.batt_flat = self.need_neutral = False
        self.battery_v = None
        self.flags = 0
        self.last_status = 0.0
        self.drive = (0, 0)
        self._stop = False
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._feeder, daemon=True).start()

    def send(self, line):
        with self.lock:
            self.ser.write((line + "\n").encode())

    def _reader(self):
        buf = b""
        while not self._stop:
            buf += self.ser.read(256)
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                st = parse_status(raw.decode(errors="ignore"))
                if st:
                    self.pulses = st["pulses"]
                    self.estop_ok, self.tank_ok, self.armed = st["estop_ok"], st["tank_ok"], st["armed"]
                    self.battery_v, self.flags = st["battery_v"], st["flags"]
                    self.tripped, self.latch = st["tripped"], st["latch"]
                    self.batt_low, self.batt_flat, self.need_neutral = st["batt_low"], st["batt_flat"], st["need_neutral"]
                    self.last_status = time.time()

    def _feeder(self):
        while not self._stop:                        # resend the current drive command every 100 ms (watchdog food)
            left, right = self.drive
            self.send(f"D {left} {right}")
            time.sleep(0.1)

    def set_drive(self, left, right):
        new = (max(-100, min(100, int(left))), max(-100, min(100, int(right))))
        changed = new != self.drive
        self.drive = new
        if changed:                                  # don't wait up to 100 ms for the feeder: a stop goes out now
            self.send(f"D {new[0]} {new[1]}")

    def resume(self):
        """After a trip: a person pressed RESET on the rover and tapped Resume. Re-enable, then the neutral."""
        self.set_drive(0, 0)
        self.send("E 1")
        self.send("D 0 0")

    def distance_m(self):
        """Mean distance of the four wheels since start (signs handle reverse). Wheels slip in mud: for where the
        rover really is, r1_supervisor uses the ground (optical-flow) sensor instead."""
        w = self.cfg["wheel"]
        per_pulse = 3.14159 * w["diameter_m"] / w["pulses_per_rev"]
        return sum(self.pulses) / 4.0 * per_pulse

    def close(self):
        self._stop = True
        self.send("D 0 0")
        self.send("E 0")


def load_config(path="config.yaml"):
    import yaml
    with open(path) as f:
        return yaml.safe_load(f)
