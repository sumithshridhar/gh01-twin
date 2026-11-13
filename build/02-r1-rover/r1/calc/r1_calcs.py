"""R1's engineering sums, each with its assumptions written down and a pass/fail check (13 Nov 2026, ISSUES.md).

  python r1_calcs.py          prints every sum and "N of N checks pass"

These are ESTIMATES from datasheet-style numbers, not measurements: every assumption marked (bench) is measured in the
bench tests in ISSUES.md, and the sum is redone with the measured number.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pi"))

G = 9.81
CHECKS = []


def check(ok, what, detail=""):
    CHECKS.append((bool(ok), what))
    print(f"  {'PASS' if ok else 'FAIL'}  {what}  {detail}")


# ------------------------------------------------------------------------------------------------ 1. power budget
# Watts. (bench) = measure with a USB meter / clamp meter on the bench.
LOADS_5_12V = {                          # fed through the 24->5 V and 24->12 V converters
    "Pi 5 (working, with cooler)": 7.0,  # (bench) typical 5-8 W under load
    "AI HAT+ (Hailo-8)": 2.5,            # full R1 only
    "Arduino Mega": 0.5,
    "relay board (3-4 relays on)": 1.5,
    "lidar RPLIDAR C1": 1.5,
    "2 ToF + optical-flow sensor": 0.2,
    "USB hub": 1.0,
}
CAM_IDLE, CAM_ACTIVE, RING = 0.3, 1.5, 3.0     # per USB camera (plugged in / streaming), per 12 V LED ring (bench)
DIRECT_24V = {"contactor coil": 8.0, "latch relay coil": 0.5, "tower light": 2.0, "4 motor drivers idle": 2.0}
CONV_EFF = 0.85
CRR_SOFT_SOIL = 0.12                     # rolling resistance, pneumatic tyre on soft path soil (0.08 firm .. 0.15 soft)
HUB_EFF_SLOW = 0.35                      # 10" hub motor + driver at 0.3 m/s (23 rpm, far below its rated speed) (bench)
V = 0.30                                 # m/s


def config(name):
    full = name == "full"
    loads = dict(LOADS_5_12V)
    if not full:
        loads.pop("AI HAT+ (Hailo-8)")   # R1-Scout scores the photos at the dock overnight instead
    cams = 6 if full else 2               # tomato mast vs strawberry
    loads["cameras idle"] = (cams + 1) * CAM_IDLE
    loads["LED rings on for the whole path"] = cams * RING
    base = sum(loads.values()) / CONV_EFF + sum(DIRECT_24V.values())
    mass = 60.0 if full else 40.0        # kg: full = 15 L tank of water + tall mast (section 4); scout: no sprayer
    motors = CRR_SOFT_SOIL * mass * G * V / HUB_EFF_SLOW
    capture_s = 3.6 if full else 1.2     # 6 or 2 cameras x 0.6 s each, one at a time (bench)
    return {"base": base, "moving": base + motors, "stopped": base + CAM_ACTIVE / CONV_EFF, "motors": motors,
            "capture_s": capture_s, "battery_wh": (30 if full else 15) * 25.6, "mass": mass}


def path_wh(c, length=30.0, every=0.25):
    drive_s, stop_s = length / V, length / every * c["capture_s"]
    return (drive_s * c["moving"] + stop_s * c["stopped"]) / 3600.0, drive_s + stop_s


def power():
    print("\n1. Power budget")
    for name in ("full", "scout"):
        c = config(name)
        wh, s = path_wh(c)
        avg_w = wh * 3600 / s
        patrol2h = avg_w * 2
        usable = 0.8 * c["battery_wh"]
        print(f"  R1-{name}: {c['base']:.0f} W electronics, {c['motors']:.0f} W motors -> {c['moving']:.0f} W driving, "
              f"{c['stopped']:.0f} W at a photo stop; one 30 m path = {wh:.1f} Wh in {s / 60:.1f} min; "
              f"2 h patrol = {patrol2h:.0f} Wh; battery {c['battery_wh']:.0f} Wh ({usable:.0f} usable)")
        check(patrol2h * 1.25 <= usable, f"R1-{name}: a 2-hour patrol + 25 % reserve fits the battery",
              f"({patrol2h * 1.25:.0f} <= {usable:.0f} Wh)")
    full = config("full")
    pi_a = (LOADS_5_12V["Pi 5 (working, with cooler)"] + LOADS_5_12V["AI HAT+ (Hailo-8)"]) / 5.0
    check(pi_a <= 0.8 * 5.0, "24->5 V 5 A converter for the Pi + AI HAT runs under 80 %", f"({pi_a:.1f} A)")
    a12 = (1.0 + 7 * CAM_IDLE + CAM_ACTIVE + 7 * RING) / 12.0
    check(a12 <= 0.8 * 3.0, "24->12 V 3 A converter: hub + cameras + all 7 rings under 80 %", f"({a12:.2f} A)")
    branch = (full["base"] - sum(DIRECT_24V.values()) + 2.0 + 0.5) / 24.0     # electronics + tower + latch relay
    check(branch <= 0.8 * 5.0, "5 A fuse branch (electronics before the contactor) under 80 %", f"({branch:.2f} A)")
    spray = (24 * 3.5 + 24 * 0.3) / 24.0                                       # pump ~3.5 A + one valve
    check(spray <= 0.8 * 10.0, "sprayer on its own 10 A fuse after the contactor (e-stop cuts it in hardware)",
          f"({spray:.1f} A)")
    from r1_mission import House, bed_wh
    wh = bed_wh(House(1, "tomato", 1, 30.0, 0.55))
    check(abs(wh - path_wh(full)[0]) < 0.3, "r1_mission's energy per path matches this budget", f"({wh:.1f} Wh)")


# ------------------------------------------------------------------------------------------------ 2. heat
def box_temp(air_c, irradiance, absorb, p_inside, h=4.5, area=0.257, top=0.066):
    """IP65 ABS box 300 x 220 x 120 mm: area 0.257 m2, lid 0.066 m2. h = natural convection + radiation for a
    plastic box (~4.5 W/m2K). Polyhouse film + shade net: ~600 W/m2 at midday, ~250 W/m2 at 8-9 AM (estimates)."""
    return air_c + (p_inside + absorb * irradiance * top) / (h * area)


def heat():
    print("\n2. Electronics box in a polyhouse")
    conv_loss = 6.0                       # the three DC-DC converters (~15 % of ~40 W)
    inside_v1 = 7.0 + 2.5 + 0.5 + 1.5 + conv_loss
    inside_v2 = inside_v1 - conv_loss + 0.5      # converters moved onto the aluminium deck; + the latch relay
    v1_noon = box_temp(40.0, 600, 0.8, inside_v1)
    v2_noon = box_temp(40.0, 600, 0.08, inside_v2)          # white sun shield with an air gap: ~10 % gets through
    v2_morning = box_temp(32.0, 250, 0.08, inside_v2)
    print(f"  v1 (grey box in the sun, converters inside) at noon, 40 C air: {v1_noon:.0f} C inside")
    print(f"  v2 (white shield, converters outside) at noon: {v2_noon:.0f} C; at 8-9 AM, 32 C air: {v2_morning:.0f} C")
    check(v1_noon > 60.0, "v1 would overheat at midday (shows the problem)", f"({v1_noon:.0f} C)")
    check(v2_noon <= 60.0, "v2 stays under the 60 C stop limit even at noon", f"({v2_noon:.0f} C)")
    check(v2_morning + 25.0 < 80.0, "v2 in the morning window: Pi chip (box + ~25 C) under its 80 C throttle point",
          f"({v2_morning + 25:.0f} C)")


# ------------------------------------------------------------------------------------------------ 3. steps
R_WHEEL = 0.127
I_MAX, KT = 16.0, 0.40                    # ZS-X11H ~400 W at 24 V; hub motor torque constant N.m/A (bench)


def climb_mm(mass, mu_soil):
    """4 driven wheels, the front pair at the edge of a step: the climbable contact angle is 2*atan(mu), with mu
    limited by the soil OR by the motors' torque, whichever is lower. Step height = r (1 - cos angle)."""
    mu_torque = 4 * I_MAX * KT / R_WHEEL / (mass * G)
    mu = min(mu_soil, mu_torque)
    return 1000 * R_WHEEL * (1 - math.cos(2 * math.atan(mu))), mu


def steps():
    print("\n3. What it can drive over (step height)")
    from r1_supervisor import Cfg
    c = Cfg()
    dry, mu_d = climb_mm(60.0, 0.6)
    wet, mu_w = climb_mm(60.0, 0.25)
    print(f"  full R1 (60 kg): dry soil {dry:.0f} mm (mu {mu_d:.2f}, motor-limited), wet {wet:.0f} mm (mu {mu_w:.2f})")
    check(c.step_max * 1000 <= 0.8 * dry, "the software's dry limit is <= 80 % of what the wheels can climb",
          f"({c.step_max * 1000:.0f} <= {0.8 * dry:.1f} mm)")
    check(c.step_max_wet * 1000 <= 0.8 * wet, "the wet limit too", f"({c.step_max_wet * 1000:.0f} <= {0.8 * wet:.1f} mm)")
    check(16 <= c.step_max * 1000, "a 16 mm drip lateral is crossed on dry soil")
    check(40 > dry, "a 40-63 mm header pipe can't be climbed: the rover stops and asks for a ramp", f"({dry:.0f} mm)")


# ------------------------------------------------------------------------------------------------ 4. tipping
PARTS = [  # (kg, height of its centre in m) for R1 full, tomato mast at 1.95 m, tank full (from blender/components/rover.py)
    (18.0, 0.127),   # 4 hub motors with tyres
    (8.0, 0.192),    # 24 V 30 Ah LiFePO4 on the tray
    (16.0, 0.195),   # 15 L of water + tank
    (6.0, 0.22),     # frame, deck, tray
    (3.0, 0.36),     # electronics box
    (2.0, 0.33),     # pump + valves
    (6.5, 1.05),     # mast, 6 camera pods, arms, tubes, tower light
    (1.0, 0.17),     # lidar bracket, bumpers
]
HALF_TRACK, HALF_BASE = 0.145, 0.24


def tipping():
    print("\n4. Tipping (tall mast, full tank)")
    from r1_supervisor import Cfg
    m = sum(k for k, _ in PARTS)
    z = sum(k * h for k, h in PARTS) / m
    side = math.degrees(math.atan(HALF_TRACK / z))
    rut = math.degrees(math.asin(Cfg().hole_max / (2 * HALF_TRACK)))
    deep = math.degrees(math.asin(0.10 / (2 * HALF_TRACK)))
    print(f"  {m:.1f} kg, centre of mass {z * 100:.0f} cm up: tips sideways at {side:.1f} deg")
    print(f"  one wheel in a 10 cm rut + 5 deg cross slope = {deep + 5:.1f} deg (margin {side - deep - 5:.1f} deg: too thin)")
    check(side - rut - 5 >= 8.0, "the deepest rut the software allows (60 mm) + 5 deg slope leaves >= 8 deg margin",
          f"({side - rut - 5:.1f} deg)")
    brake = G * HALF_BASE / z
    check(brake > 0.6 * G, "it can't tip forward when braking (needs more grip than soil gives)", f"({brake:.1f} m/s2)")


# ------------------------------------------------------------------------------------------------ 5. stopping
def stopping():
    print("\n5. Stopping before something in the path")
    from r1_supervisor import Cfg
    c = Cfg()
    react = 0.10 + (c.persist - 1) * 0.10 + 0.02 + 0.005   # wait for a scan + 2 more to confirm + compute + serial
    decel = 1.5                                              # m/s2, conservative for hub-motor braking on soil (bench)
    d = c.v_cruise * react + c.v_cruise ** 2 / (2 * decel)
    print(f"  at {c.v_cruise} m/s: {react:.2f} s to react + braking = {d * 100:.0f} cm (it stops at {c.stop_gap * 100:.0f} cm)")
    check(d <= 0.6 * c.stop_gap, "stopping distance at cruise speed is under 60 % of the stop gap", f"({d * 100:.0f} cm)")
    check(0.05 < c.stop_gap, "the lidar can see that close (RPLIDAR C1 minimum range 5 cm)")


# ------------------------------------------------------------------------------------------------ 6. cameras
H_FOV, V_FOV = 66.0, 41.0                 # IMX708 standard lens, landscape (Camera Module 3 datasheet)


def band(h, tilt, d, vfov):
    return (h + d * math.tan(math.radians(tilt - vfov / 2)), h + d * math.tan(math.radians(tilt + vfov / 2)))


def covered(intervals, lo, hi, step=0.005):
    n = int(round((hi - lo) / step))
    seen = sum(any(a <= lo + i * step <= b for a, b in intervals) for i in range(n + 1))
    return seen / (n + 1)


def cameras():
    print("\n6. What the cameras can see")
    d = 0.55 / 2 + 0.25 - 0.14            # tomato: path 55 cm, near row 25 cm into the bed, pod 14 cm off centre
    lo, hi = 0.45, 1.95                    # canopy band (lower leaves stripped below ~0.4 m)
    v1 = [band(h, t, d, V_FOV) for h, t in ((0.62, 25), (1.22, 0), (1.82, -10))]
    v2 = [band(h, t, d, H_FOV) for h, t in ((0.62, 10), (1.22, 0), (1.82, -10))]   # portrait: 66 deg is vertical
    c1, c2 = covered(v1, lo, hi), covered(v2, lo, hi)
    print(f"  tomato, plant row {d * 100:.0f} cm from the cameras: v1 landscape sees {c1:.0%} of 0.45-1.95 m, "
          f"v2 portrait sees {c2:.0%}")
    check(c1 < 0.75, "v1 left bands of the plant unseen (shows the problem)", f"({c1:.0%})")
    check(c2 >= 0.99, "v2 sees the whole canopy band", f"({c2:.0%})")
    foot = 2 * d * math.tan(math.radians(V_FOV / 2))          # portrait: the narrow side runs along the path
    check(foot >= 0.25, "along the path, each photo is wider than the 25 cm station spacing (no gaps)", f"({foot * 100:.0f} cm)")
    check(foot / 0.125 >= 2.0, "in amber/red houses (12.5 cm stations) every leaf is seen from 2 positions",
          f"({foot / 0.125:.1f} views)")
    # strawberry: what one camera must see, from the bed centre's canopy top down to the fruit hanging off the bed side
    edge, canopy, hang = 0.45 / 2, 0.65, 0.30     # path edge (45 cm path), canopy top on a 45 cm bed, hanging fruit
    def need(cam_h, cam_y=0.14):
        far = math.degrees(math.atan2(canopy - cam_h, edge + 0.30 - cam_y))
        low = math.degrees(math.atan2(hang - cam_h, edge - cam_y))
        return low, far
    lo1, hi1 = need(0.62)
    lo2, hi2 = need(0.85)
    v1s = (-42 - V_FOV / 2, -42 + V_FOV / 2)
    v2s = (-52 - H_FOV / 2, -52 + H_FOV / 2)
    print(f"  strawberry: v1 camera at 0.62 m needs {lo1:.0f}..{hi1:+.0f} deg and sees {v1s[0]:.0f}..{v1s[1]:.0f}; "
          f"v2 at 0.85 m needs {lo2:.0f}..{hi2:.0f} and sees {v2s[0]:.0f}..{v2s[1]:.0f}")
    check(not (v1s[0] <= lo1 and hi1 <= v1s[1]), "v1 strawberry camera missed the bed centre and the hanging fruit (problem)")
    check(v2s[0] <= lo2 and hi2 <= v2s[1], "v2 strawberry camera (0.85 m, -52 deg, portrait) sees all of it")


# ------------------------------------------------------------------------------------------------ 7. path width
def fit(runs=6):
    print("\n7. How wide a path R1 needs (tracking measured in the simulator)")
    import numpy as np
    from r1_sim import Sim, World
    errs = []
    for i in range(runs):
        w = World(length=20.0, width=0.55)
        w.phase = tuple(np.random.default_rng(i).uniform(0, 6.28, 4))
        errs += Sim(w, seed=100 + i).run().y_err
    sigma = float(np.std(errs))
    need = 0.36 + 2 * (3 * sigma + 0.015 + 0.01)        # body + 3 sigma tracking + crooked wall + 1 cm for leaves
    print(f"  tracking error {sigma * 100:.1f} cm (1 sigma) -> paths of {need * 100:.0f} cm or more; "
          f"strawberry paths are 40-50 cm, tomato/vegetable paths 50-60 cm")
    from r1_mission import plan_day, House
    go, refused = plan_day([House(1, "tomato", 1, 30, need)], min_path_m=0.48)
    check(need <= 0.48, "R1 fits a 48 cm path (the limit r1_mission uses)", f"(needs {need * 100:.1f} cm)")
    check(need > 0.45, "R1 does NOT fit a 45 cm strawberry path: those houses get the camera trolley", f"({need * 100:.1f} cm)")


def main():
    print("R1 engineering checks (estimates; (bench) values to be measured)")
    for f in (power, heat, steps, tipping, stopping, cameras, fit):
        f()
    ok = sum(c for c, _ in CHECKS)
    print(f"\n{'ALL PASSED' if ok == len(CHECKS) else 'FAILED'}: {ok} of {len(CHECKS)} checks")
    return ok == len(CHECKS)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
