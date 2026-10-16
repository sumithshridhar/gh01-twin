"""R1 scout-sprayer rover for soil-bed polyhouses (15 Oct 2026): no rails, narrow paths, low margins.

Why this shape (docs/06-scout-rover.md): Indian polyhouses grow in soil beds with 40-60 cm paths, no rails, low margins.
So: a 36 cm wide skid-steer base that drives IN the path, a mast whose height is set per crop, cameras + spray nozzles
on both sides, everything heavy (battery, 15 L tank) slung low between the wheels.

Real parts (prices are estimates from Indian listings, Oct 2026; confirm before buying):
  4 x 10" 24 V 350 W brushless hub motor, 10 x 2.125 pneumatic tyre ............ ~₹6,300 each (Raceway Impex listing)
  4 x ZS-X11H BLDC driver (6-60 V, 400 W) ........................................ ~₹1,200 each
  24 V 30 Ah LiFePO4 pack with BMS ............................................... ~₹18-25k
  Raspberry Pi 5 8 GB + AI HAT+ 26 TOPS (Hailo-8) ................................ ~₹9k + ₹14,999 (Probots)
  7 x Raspberry Pi Camera Module 3 (6 on the mast, 1 Wide at the front) .......... ₹3,158 each
  2 x Arducam 4-channel multi-camera adapter (Pi 5 has 2 camera ports) ........... ~₹4k each
  Slamtec RPLIDAR C1 (55.6 x 55.6 x 41.3 mm) ..................................... ~₹7-8k
  24 V diaphragm sprayer pump (Seaflo 21-series class), 6 x 24 V 1/4" solenoid valves, 6 x TeeJet ConeJet hollow-cone tips
  15 L flat HDPE tank, 40x40 / 20x40 aluminium extrusion, IP65 ABS box, e-stop, LED beacon, bumpers, 4G router
  Total ≈ ₹1.5 L in parts.

Local frame: +X = forward, ±Y = the two beds, z = 0 on the path floor. Wheel centres at x ±0.24, y ±0.145.
"""
import math

import gh
from gh import MB, TAU, Component, bm_box, bm_cyl, emissive, xform
from parts import cable, radial, screw

W_R = 0.127          # 10" tyre radius
W_W = 0.054          # 2.125" tyre width
WX, WY = 0.24, 0.145 # wheel centres
RAIL_Y = 0.098       # 20x40 side rails (centre)
RAIL_Z = 0.175
TRAY_Z = 0.105       # bottom tray (ground clearance 10 cm)
DECK_Z = 0.300       # top of the deck plate
MAST_X = -0.02

gh.SPEC.update({
    "tyre": dict(color=(0.03, 0.03, 0.032), rough=0.78),
    "hub_shell": dict(color=(0.05, 0.05, 0.055), metal=0.6, rough=0.42),
    "hub_face": dict(color=(0.62, 0.63, 0.64), metal=1, rough=0.38),
    "anodised": dict(color=(0.78, 0.79, 0.81), metal=1, rough=0.36),
    "anod_dark": dict(color=(0.11, 0.115, 0.12), metal=1, rough=0.42),
    "slot_dark": dict(color=(0.04, 0.04, 0.042), metal=1, rough=0.55),
    "ip65_grey": dict(color=(0.6, 0.62, 0.63), rough=0.48),
    "tank_white": dict(color=(0.86, 0.86, 0.82), rough=0.42, subsurface=0.25),
    "spray_liquid": dict(color=(0.25, 0.45, 0.55), rough=0.05, alpha=0.5),
    "pu_tube": dict(color=(0.08, 0.32, 0.72), rough=0.35, coat=0.3),
    "brass_valve": dict(color=(0.85, 0.66, 0.34), metal=1, rough=0.3),
    "coil_black": dict(color=(0.03, 0.03, 0.035), rough=0.4),
    "teejet_red": dict(color=(0.75, 0.06, 0.04), rough=0.4),
    "teejet_grey": dict(color=(0.55, 0.57, 0.6), rough=0.4),
    "estop_red": dict(color=(0.8, 0.02, 0.01), rough=0.3, coat=0.5),
    "estop_yellow": dict(color=(0.98, 0.78, 0.02), rough=0.4),
    "bumper": dict(color=(0.02, 0.02, 0.02), rough=0.9),
    "brand_orange": dict(color=(1.0, 0.42, 0.04), rough=0.4),
    "lidar_window": dict(color=(0.02, 0.02, 0.025), rough=0.05, coat=1.0),
    "flash": dict(color=(1.0, 0.98, 0.95), rough=0.3, emit=(1, 0.97, 0.9), emit_strength=0.0),
    "beacon_green": dict(color=(0.1, 0.8, 0.2), rough=0.2, alpha=0.8, emit=(0.1, 1.0, 0.25), emit_strength=0.0),
    "beacon_amber": dict(color=(1.0, 0.55, 0.0), rough=0.2, alpha=0.8, emit=(1.0, 0.5, 0.0), emit_strength=0.0),
    "beacon_red": dict(color=(0.9, 0.05, 0.02), rough=0.2, alpha=0.8, emit=(1.0, 0.05, 0.02), emit_strength=0.0),
    "lfp_blue": dict(color=(0.05, 0.16, 0.42), rough=0.45),
    "led_green_dock": dict(color=(0.1, 0.9, 0.2), rough=0.3, emit=(0.1, 1, 0.2), emit_strength=4.0),
})


# ─────────────────────────────── real parts ───────────────────────────────
def extrusion(mb, length, a=0.02, b=0.04, m="anodised", loc=(0, 0, 0), axis="X"):
    """V-slot aluminium profile a x b (metres) along `axis`, with its centre slots drawn as dark grooves."""
    M = xform(loc) @ xform(rot=gh.AXIS_ROT[axis])
    mb.add(bm_box(b, a, length, bevel=0.0015), m, M=M)
    for sx in (-1, 1):                               # slots on the two wide faces
        for k in ((-0.25, 0.25) if b >= 0.04 else (0.0,)):
            mb.add(bm_box(0.0062, 0.0008, length * 0.999), "slot_dark", M=M @ xform((k * b, sx * a / 2, 0)))
    for sx in (-1, 1):                               # and the narrow faces
        mb.add(bm_box(0.0008, 0.0062, length * 0.999), "slot_dark", M=M @ xform((sx * b / 2, 0, 0)))
    return mb


def hub_wheel(mb, loc, side):
    """10" brushless hub motor with a 10 x 2.125 pneumatic tyre. Axle along Y; `side` = +1/-1 (outer face direction)."""
    x, y, z = loc
    M = xform((x, y, z)) @ xform(rot=(-90, 0, 0))     # lathe Z -> world +Y
    # tyre: rounded section, ~42 mm tall
    prof = []
    for i in range(17):
        a = -math.pi / 2 + math.pi * i / 16
        prof.append((0.088 + 0.039 * math.cos(a) ** 0.6 if math.cos(a) > 0 else 0.088, (W_W / 2) * math.sin(a)))
    prof = [(0.086, -W_W / 2 + 0.004)] + prof + [(0.086, W_W / 2 - 0.004)]
    mb.add(gh.bm_lathe(prof, 64), "tyre", M=M)
    # tread blocks (staggered chevrons)
    for k in range(40):
        ph = TAU * k / 40
        for s in (-1, 1):
            off = 0.011 * s + (0.003 if k % 2 else -0.003)
            R = W_R - 0.0008
            Mt = M @ xform((R * math.cos(ph), R * math.sin(ph), off)) @ xform(rot=(0, 0, math.degrees(ph))) @ xform(rot=(0, 0, 0))
            mb.add(bm_box(0.0035, 0.012, 0.014, bevel=0.001), "tyre", M=Mt @ xform(rot=(0, 0, 0)) @ xform(rot=(s * 18, 0, 0)))
    # motor shell (the rim): dark painted casting with 5 lightening pockets, silver side cover
    mb.add(gh.bm_lathe([(0.0, -0.024), (0.07, -0.024), (0.086, -0.026), (0.088, -0.022), (0.088, 0.022), (0.086, 0.026),
                        (0.07, 0.024), (0.0, 0.024)], 64), "hub_shell", M=M)
    for sd in (-1, 1):
        mb.add(bm_cyl(0.062, 0.004, 48, bevel=0.0015), "hub_face", M=M @ xform((0, 0, sd * 0.025)))
        for px, py, _ in radial(5, 0.045):
            mb.add(bm_cyl(0.012, 0.003, 20), "hub_shell", M=M @ xform((px, py, sd * 0.0272)))
        for px, py, _ in radial(6, 0.03, start=0.3):
            mb.add(bm_cyl(0.0032, 0.003, 12), "stainless", M=M @ xform((px, py, sd * 0.0275)))
    mb.add(bm_cyl(0.006, 0.09, 16), "steel_dark", M=M)                                   # 12 mm axle
    for sd in (-1, 1):
        mb.add(bm_cyl(0.0095, 0.007, 6), "stainless", M=M @ xform((0, 0, sd * 0.034)))  # axle nuts
    mb.add(bm_cyl(0.0035, 0.014, 10), "brass", M=M @ xform((0.07, 0.0, 0.018)) @ xform(rot=(0, 90, 0)))  # valve stem
    return mb


def camera_pod(mb, loc, facing, tilt=0.0, flash_m="flash"):
    """IP67 aluminium camera housing (52 x 40 x 34 mm) holding a Camera Module 3, with a white LED flash ring.
    `facing` = +1 / -1 (looks along ±Y); `tilt` degrees (+ = look up)."""
    x, y, z = loc
    M = xform((x, y, z)) @ xform(rot=(0, 0, 0 if facing > 0 else 180)) @ xform(rot=(tilt, 0, 0))
    mb.add(bm_box(0.052, 0.034, 0.040, bevel=0.003), "anod_dark", M=M)
    mb.add(bm_box(0.048, 0.002, 0.036, bevel=0.001), "glass", M=M @ xform((0, 0.0175, 0)))
    mb.add(gh.bm_tube(0.0135, 0.0085, 0.002, 32), flash_m, M=M @ xform((0, 0.0172, 0)) @ xform(rot=(-90, 0, 0)))
    mb.add(bm_cyl(0.0055, 0.003, 24), "lens", M=M @ xform((0, 0.0165, 0)) @ xform(rot=(-90, 0, 0)))
    mb.add(bm_cyl(0.0035, 0.0035, 20), "chrome", M=M @ xform((0, 0.0160, 0)) @ xform(rot=(-90, 0, 0)))
    mb.add(bm_cyl(0.0045, 0.014, 12), "plastic_black", M=M @ xform((0, -0.024, 0)) @ xform(rot=(90, 0, 0)))  # cable gland
    return mb


def teejet_nozzle(mb, loc, facing, tilt=-10.0):
    """TeeJet ConeJet hollow-cone tip in a Quick TeeJet cap on a 1/4" nozzle body (red = TXA8001)."""
    x, y, z = loc
    M = xform((x, y, z)) @ xform(rot=(0, 0, 0 if facing > 0 else 180)) @ xform(rot=(tilt - 90, 0, 0))
    mb.add(bm_cyl(0.008, 0.026, 16, bevel=0.001), "teejet_grey", M=M @ xform((0, 0, -0.01)))  # body (local +Z = spray direction)
    mb.add(bm_cyl(0.0125, 0.012, 6, bevel=0.0015), "teejet_red", M=M @ xform((0, 0, 0.008)))   # quick cap (hex-ish)
    mb.add(bm_cyl(0.004, 0.006, 16), "stainless", M=M @ xform((0, 0, 0.017)))                # tip orifice disc
    return mb


def solenoid_valve(mb, loc):
    """1/4" 24 V normally-closed solenoid valve (brass body, black coil, DIN plug)."""
    x, y, z = loc
    mb.box((0.03, 0.022, 0.022), "brass_valve", bevel=0.002, loc=(x, y, z))
    mb.cyl(0.013, 0.032, "coil_black", segs=20, bevel=0.002, z0=0.011, loc=(x, y, z))
    mb.box((0.026, 0.02, 0.018), "plastic_black", bevel=0.002, loc=(x, y + 0.02, z + 0.033))
    return mb


def rplidar_c1(mb, loc):
    """Slamtec RPLIDAR C1: 55.6 x 55.6 x 41.3 mm, matte black, round scanning window on top."""
    x, y, z = loc
    mb.box((0.0556, 0.0556, 0.022), "plastic_black", bevel=0.004, loc=(x, y, z + 0.011))
    mb.cyl(0.026, 0.0193, "lidar_window", segs=40, z0=0.022, loc=(x, y, z))
    mb.cyl(0.0255, 0.003, "plastic_black", segs=40, z0=0.0413 - 0.003, loc=(x, y, z))
    return mb


# ─────────────────────────────── the rover ───────────────────────────────
def rover(cid="r1_rover", title="R1 scout-sprayer rover (soil beds, no rails)", mast_top=1.95, crop="tomato"):
    """`crop` = tomato (mast up, pods at 0.6 / 1.2 / 1.8 m) or strawberry (mast down, one pod looking down at the bed)."""
    c = Component(
        cid, title, "Robot",
        summary=("A 36 cm wide rover that drives in the soil path between two beds, photographs every plant from both "
                 "sides, and sprays only the plants the farmer approves. One rover serves several houses and crops: "
                 "the mast is set low for strawberry and high for tomato."),
        how=("Skid steer on 4 hub motors: it turns on the spot at the bed end, so it needs no turning circle. In a row it "
             "keeps to the centre of the path with the 2-D lidar (it sees both bed walls) and reads a tag on a stake at "
             "each bed end, so every photo is saved to the right row and metre. Cameras flash their own light so photos "
             "look the same at 9 AM and 4 PM. The Pi 5's AI chip flags 'something is wrong here'; that photo goes to the "
             "diagnosis service, then to the farmer's phone. Only after he approves does the rover come back and open the "
             "valves at that spot. Between houses a worker drives it with a phone, through the wheel bath at the door."),
        sensors=("6 mast cameras (3 per side, lowest pair tilted up under the leaves)", "front wide camera",
                 "RPLIDAR C1 2-D lidar", "wheel hall sensors", "tank level", "battery monitor", "bumper switches"),
        control=("Raspberry Pi 5 + AI HAT+ (route, cameras, vision); 4 x ZS-X11H motor drivers; spray valves only open "
                 "after a phone approval. E-stop and bumpers cut motor power in hardware; amber beacon = spraying, keep out."),
        state={"mode": "scouting", "house": 1, "row": 3, "x_m": 7.4, "battery_pct": 82, "tank_l": 12.5, "crop": crop,
               "mast_m": mast_top},
        real="DIY from Indian parts: hub motors, LiFePO4, Pi 5 + AI HAT+, Camera Module 3, RPLIDAR C1, 24 V sprayer pump, TeeJet tips",
        cost="≈ ₹1.5 L parts (estimate)")
    # ── wheels ──
    c.wheels = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            wh = MB()
            hub_wheel(wh, (0, 0, 0), sy)
            nm = f"wheel_{'F' if sx > 0 else 'R'}{'L' if sy > 0 else 'R'}"
            c.wheels.append(c.part(nm, wh, loc=(sx * WX, sy * WY, W_R), explode=(0, sy * 0.12, -0.05),
                                   desc="10-inch 24 V brushless hub motor with a pneumatic tyre: grips soft soil, no gearbox to clog with mud."))
    # ── chassis: two 20x40 side rails, cross members, wheel brackets, bottom tray, deck ──
    ch = MB()
    for sy in (-1, 1):
        extrusion(ch, 0.68, 0.02, 0.04, loc=(0, sy * RAIL_Y, RAIL_Z), axis="X")
        for sx in (-1, 1):                         # wheel bracket: 6 mm plate from rail down to the axle
            ch.box((0.07, 0.006, 0.09), "anodised", bevel=0.001, loc=(sx * WX, sy * (WY - 0.04), 0.155))
            ch.box((0.03, 0.03, 0.012), "anodised", loc=(sx * WX, sy * (WY - 0.055), 0.127))       # axle clamp block
            for dz in (0.17, 0.19):
                screw(ch, (sx * WX + 0.02, sy * (WY - 0.043), dz), axis="Y" if sy > 0 else "-Y", length=0.01)
    for x in (-0.32, -0.02, 0.32):
        extrusion(ch, 2 * RAIL_Y - 0.02, 0.02, 0.02, loc=(x, 0, RAIL_Z), axis="Y")
    ch.box((0.64, 0.17, 0.004), "anodised", loc=(0, 0, TRAY_Z))                               # bottom tray
    for sy in (-1, 1):
        ch.box((0.64, 0.004, 0.07), "anodised", loc=(0, sy * 0.085, TRAY_Z + 0.035))
    ch.box((0.70, 0.235, 0.004), "anod_dark", bevel=0.001, loc=(0, 0, DECK_Z - 0.002))       # deck plate
    for k in range(9):
        ch.box((0.66, 0.003, 0.0012), "anodised", loc=(0, -0.10 + k * 0.025, DECK_Z + 0.0006))  # ribbed mat
    for sx in (-1, 1):
        for sy in (-1, 1):                          # deck standoffs
            ch.cyl(0.008, DECK_Z - RAIL_Z - 0.02, "anodised", segs=12, z0=RAIL_Z + 0.02, loc=(sx * 0.30, sy * RAIL_Y, 0))
    for sx in (-1, 1):
        for sy in (-1, 1):                          # phase + hall cables leave through the hollow axles
            x, y = sx * WX, sy * WY
            cable(ch, [(x, y - sy * 0.045, W_R), (x, y - sy * 0.06, W_R + 0.02), (x - 0.03 * sx, sy * RAIL_Y, RAIL_Z)], r=0.004, fillet=0.02)
    c.part("chassis", ch, desc=("Aluminium extrusion frame: two 20x40 rails 19.6 cm apart, a tray 10 cm off the ground "
                                "and a ribbed deck. Overall 36 cm wide, 70 cm long."))
    # ── battery (front, low) ──
    bt = MB()
    bt.box((0.20, 0.16, 0.17), "lfp_blue", bevel=0.008)
    bt.box((0.12, 0.001, 0.05), "sticker_white", loc=(0, -0.0805, 0.03))
    bt.text("LiFePO4 24V 30Ah", 0.011, "plastic_black", loc=(0, -0.081, 0.035), rot=(90, 0, 0), bold=True)
    bt.text("BMS inside", 0.008, "plastic_black", loc=(0, -0.081, 0.02), rot=(90, 0, 0))
    bt.cyl(0.008, 0.012, "pvc_red", segs=12, z0=0.085, loc=(0.06, 0.05, 0))
    bt.cyl(0.008, 0.012, "plastic_black", segs=12, z0=0.085, loc=(0.06, -0.05, 0))
    c.part("battery", bt, loc=(0.175, 0, TRAY_Z + 0.087), explode=(0.0, 0.0, -0.32),
           desc="24 V 30 Ah LiFePO4 (8 kg) on the tray between the wheels: low weight = it can't tip with the mast up. ~5 h.")
    # ── spray tank (rear, low) ──
    tk = MB()
    tk.box((0.38, 0.165, 0.175), "tank_white", bevel=0.02)
    tk.box((0.37, 0.155, 0.10), "spray_liquid", bevel=0.015, loc=(0, 0, -0.035))
    for k in range(4):                              # level marks
        tk.box((0.002, 0.001, 0.012), "plastic_black", loc=(-0.17, -0.083, -0.07 + k * 0.04))
    tk.cyl(0.028, 0.03, "plastic_yellow", segs=24, z0=0.0875, loc=(-0.12, 0.022, 0))               # fill cap through the deck
    tk.box((0.12, 0.001, 0.03), "sticker_yellow", loc=(0.05, -0.0828, 0.04))
    tk.text("15 L", 0.012, "plastic_black", loc=(0.05, -0.0835, 0.04), rot=(90, 0, 0), bold=True)
    c.part("tank", tk, loc=(-0.13, 0, TRAY_Z + 0.09), explode=(0.0, 0.0, -0.36),
           desc="15 L flat HDPE tank, slung low. Rinse it between crops: strawberry and tomato get different sprays.")
    # ── electronics box (front of the deck) with the Pi 5 + AI HAT+ inside ──
    eb = MB()
    eb.box((0.22, 0.17, 0.095), "ip65_grey", bevel=0.01, loc=(0, 0, 0.0475))
    eb.box((0.215, 0.165, 0.004), "ip65_grey", bevel=0.002, loc=(0, 0, 0.097))
    for sx in (-1, 1):
        for sy in (-1, 1):
            eb.cyl(0.004, 0.003, "stainless", segs=10, z0=0.098, loc=(sx * 0.095, sy * 0.07, 0))
    eb.box((0.14, 0.001, 0.035), "plastic_black", loc=(0, -0.0855, 0.05))
    eb.text("GHOST OPS  R1", 0.012, "brand_orange", loc=(0, -0.0862, 0.055), rot=(90, 0, 0), bold=True)
    eb.text("scout · spray", 0.008, "plastic_white", loc=(0, -0.0862, 0.04), rot=(90, 0, 0))
    eb.cyl(0.004, 0.09, "plastic_black", segs=10, z0=0.099, loc=(0.09, 0.06, 0))              # 4G antenna
    eb.cyl(0.0065, 0.02, "plastic_black", segs=12, z0=0.099, loc=(0.09, 0.06, 0))
    for k in range(3):                              # cable glands on the back
        eb.cyl(0.007, 0.014, "plastic_black", segs=12, axis="-X", loc=(-0.112, -0.05 + k * 0.05, 0.03))
    c.part("ebox", eb, loc=(0.205, 0, DECK_Z), explode=(0.0, 0.0, 0.28),
           desc="IP65 box: Raspberry Pi 5 + AI HAT+ (26 TOPS), 4 motor drivers, fuses, 24→5 V converter, 4G router.")
    try:
        from components import bench
        pi = bench.pi5_ai_hat(cid=f"{cid}_pi5", title="Raspberry Pi 5 + AI HAT+ (inside the box)")
        for o in gh.descendants(pi.root):
            if "explode" in o:
                o["explode"] = [0, 0, 0]
        pi.root.parent = c.root
        pi.root.location = (0.205, 0, DECK_Z + 0.03)
        pi.root["explode"] = [0.0, 0.0, 0.16]
        pi.root["base_loc"] = [0.205, 0, DECK_Z + 0.03]
        c.parts["pi5"] = pi.root
    except Exception as e:  # noqa: BLE001  (the bench module is optional for this build)
        print("pi5 skipped:", e)
    # ── lidar + front camera + bumpers ──
    fs = MB()
    fs.box((0.06, 0.06, 0.004), "anod_dark", loc=(0.0, 0, 0.002))
    fs.cyl(0.006, 0.05, "anodised", segs=12, z0=-0.05, loc=(0, 0, 0))
    rplidar_c1(fs, (0, 0, 0.004))
    c.part("lidar", fs, loc=(0.27, 0, DECK_Z + 0.15), explode=(0.12, 0, 0.18),
           desc="Slamtec RPLIDAR C1 (360°, 12 m): it sees both bed walls and keeps the rover in the middle of the path.")
    fc = MB()
    camera_pod(fc, (0, 0, 0), 1)
    c.part("front_camera", fc, loc=(0.345, 0, 0.215), rot=(0, 0, -90), explode=(0.15, 0, 0),
           desc="Front wide camera: reads the tag at each bed end, and is the worker's view when he drives it from his phone.")
    bp = MB()
    for sx in (-1, 1):
        bp.box((0.025, 0.30, 0.045), "bumper", bevel=0.01, loc=(sx * 0.365, 0, 0.165))
        for sy in (-1, 1):
            bp.box((0.02, 0.012, 0.02), "anodised", loc=(sx * 0.345, sy * 0.1, 0.165))
    for sy in (-1, 1):                              # charge pads: the dock's spring contacts press on these
        bp.box((0.004, 0.05, 0.024), "copper", loc=(0.3785, sy * 0.06, 0.165))
    c.part("bumpers", bp, explode=(0, 0, 0), desc="Rubber bumpers with switches front and back: a touch stops the wheels. Two copper charge pads on the front one.")
    # ── pump + valve manifold (rear deck) ──
    pm = MB()
    pm.box((0.11, 0.085, 0.07), "plastic_black", bevel=0.006, loc=(0, 0, 0.035))     # pump head + motor
    pm.cyl(0.03, 0.08, "steel_dark", segs=24, bevel=0.003, axis="X", loc=(0.09, 0, 0.035))
    pm.box((0.03, 0.06, 0.004), "anod_dark", loc=(0.09, 0, 0.002))
    pm.cyl(0.006, 0.02, "plastic_black", segs=12, axis="Y", loc=(-0.02, 0.05, 0.05))   # outlet
    pm.text("24V  4.3 L/min  100 psi", 0.006, "plastic_white", loc=(0, -0.0432, 0.04), rot=(90, 0, 0))
    c.part("pump", pm, loc=(-0.225, -0.055, DECK_Z), explode=(-0.1, -0.25, 0.1),
           desc="24 V diaphragm sprayer pump (4.3 L/min, 100 psi class) draws from the tank under the deck.")
    vm = MB()
    vm.box((0.2, 0.025, 0.025), "anodised", bevel=0.002, loc=(0, 0, 0.0125))          # manifold bar
    for k in range(6):
        solenoid_valve(vm, (-0.085 + k * 0.034, 0.0, 0.037))
    vm.box((0.16, 0.001, 0.012), "sticker_white", loc=(0, -0.0131, 0.012))
    vm.text("L1  R1  L2  R2  L3  R3", 0.0055, "plastic_black", loc=(0, -0.0136, 0.012), rot=(90, 0, 0))
    c.part("valves", vm, loc=(-0.19, 0.07, DECK_Z), explode=(-0.1, 0.25, 0.12),
           desc="6 solenoid valves, one per nozzle: the rover sprays only the side and height where the sick leaves are.")
    # ── mast (telescopic 40x40 + 30x30), pods, nozzles, tubes, beacon ──
    ms = MB()
    lower_top = min(1.05, mast_top - 0.05)
    extrusion(ms, lower_top - DECK_Z, 0.04, 0.04, loc=(MAST_X, 0, (DECK_Z + lower_top) / 2), axis="Z")
    ms.box((0.12, 0.12, 0.008), "anod_dark", loc=(MAST_X, 0, DECK_Z + 0.004))                  # base plate
    for a in (0, 90, 180, 270):                                                                 # gussets
        dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
        ms.box((0.04, 0.004, 0.04), "anod_dark", loc=(MAST_X + dx * 0.04, dy * 0.04, DECK_Z + 0.028),
               rot=(0, 0, a))
    mu = MB()                                   # upper mast: origin at the lock collar so it can slide down
    if mast_top > lower_top + 0.01:
        ms.box((0.05, 0.05, 0.04), "anod_dark", bevel=0.003, loc=(MAST_X, 0, lower_top + 0.01))   # lock collar
        ms.cyl(0.006, 0.05, "stainless", segs=12, axis="X", loc=(MAST_X + 0.045, 0, lower_top + 0.01))
        ms.sphere(0.011, "plastic_black", loc=(MAST_X + 0.075, 0, lower_top + 0.01))           # T-handle knob
        extrusion(mu, mast_top - lower_top + 0.25, 0.03, 0.03, m="anodised", loc=(0, 0, (mast_top - lower_top - 0.25) / 2),
                  axis="Z")
    c.part("mast", ms, explode=(0, 0, 0), desc=("Telescopic mast: 40x40 lower, 30x30 upper with a lock collar. Set "
                                                "it once per crop: 0.65 m for strawberry beds, up to 1.95 m for tomato."))
    up = c.part("mast_upper", mu, loc=(MAST_X, 0, lower_top), desc="Upper mast (30x30), slides inside the lower one.")
    if crop == "tomato":
        levels = [(0.62, 25.0), (1.22, 0.0), (1.82, -10.0)]          # (height, camera tilt): low pair looks up under leaves
    else:
        levels = [(mast_top - 0.06, -42.0)]                           # strawberry: one pair looking down at the bed tops
    c.levels = levels
    c.nozzles = []
    for zi, (zl, tilt) in enumerate(levels):
        pods = MB()
        tubes = MB()
        extrusion(pods, 0.25, 0.02, 0.02, loc=(0, 0, 0), axis="Y")
        ntilt = -12.0 if crop == "tomato" else -45.0
        for sy in (-1, 1):
            camera_pod(pods, (0, sy * 0.14, 0.03), sy, tilt=tilt)
            teejet_nozzle(pods, (0, sy * 0.13, -0.03), sy, tilt=ntilt)
            c.nozzles.append((zi, sy, (MAST_X, sy * 0.152, zl - 0.03 - 0.022 * math.sin(math.radians(-ntilt))), ntilt))
            # PU spray tube: valve -> along the deck -> up the mast -> along the arm to the nozzle (origin on the deck)
            k = zi * 2 + (0 if sy < 0 else 1)
            vx = -0.19 - 0.085 + k * 0.034
            ox = MAST_X - 0.026 - 0.004 * k
            h = zl - DECK_Z
            pts = [(vx, 0.07 + 0.02, 0.07), (vx, 0.045, 0.03), (ox, 0.022 - 0.003 * k, 0.03),
                   (ox, 0.022 - 0.003 * k, h - 0.03), (MAST_X, sy * 0.03, h - 0.03), (MAST_X, sy * 0.115, h - 0.03)]
            cable(tubes, pts, r=0.003, m="pu_tube", fillet=0.03, segs=8)
        cable(tubes, [(MAST_X + 0.022, 0.0, 0.1), (MAST_X + 0.024, 0.0, zl - DECK_Z + 0.03), (MAST_X + 0.02, 0.06, zl - DECK_Z + 0.03)],
              r=0.0035, fillet=0.03)                                   # camera cable
        c.part(f"pod_{zi + 1}", pods, loc=(MAST_X, 0, zl), explode=(0.18 + 0.05 * zi, 0, 0),
               desc=("Camera pods (Camera Module 3 in IP67 housings, white LED flash ring) and TeeJet ConeJet hollow-cone "
                     "nozzles, one per valve. " + ("Lowest pair tilts up 25° to see under the leaves where whitefly and mites hide."
                                                  if (crop == "tomato" and zi == 0) else
                                                  ("Angled down at the bed top for strawberry." if crop != "tomato" else ""))))
        c.part(f"tubes_{zi + 1}", tubes, loc=(0, 0, DECK_Z), desc="6 mm PU tubes from each valve up the mast to its nozzle.")
    bc = MB()
    bc.cyl(0.022, 0.01, "plastic_black", segs=24, z0=0.0)
    for k, m in enumerate(("beacon_red", "beacon_amber", "beacon_green")):
        bc.cyl(0.02, 0.028, m, segs=24, z0=0.012 + k * 0.03)
    bc.cyl(0.021, 0.008, "plastic_black", segs=24, z0=0.102)
    c.part("beacon", bc, parent=up, loc=(0, 0, mast_top - lower_top + 0.003), explode=(0, 0, 0.2),
           desc="LED beacon: green = scouting, amber = spraying (keep out of this house), red = stopped / needs help.")
    # ── rear console: e-stop, charge port, push handle ──
    rc = MB()
    rc.box((0.05, 0.12, 0.07), "ip65_grey", bevel=0.006, loc=(0, 0, 0.035))
    rc.cyl(0.02, 0.012, "estop_yellow", segs=24, z0=0.07, loc=(0, -0.025, 0))
    rc.lathe([(0, 0), (0.019, 0), (0.02, 0.008), (0.018, 0.016), (0, 0.019)], "estop_red", segs=28, loc=(0, -0.025, 0.082))
    rc.box((0.004, 0.035, 0.03), "plastic_red", loc=(-0.027, 0.032, 0.035))                  # Anderson SB50 charge plug
    rc.box((0.004, 0.026, 0.02), "plastic_dark", loc=(-0.0285, 0.032, 0.035))
    c.part("console", rc, loc=(-0.325, 0, DECK_Z), explode=(-0.2, 0, 0.1),
           desc="Rear console: big red e-stop and the 24 V charge plug.")
    hd = MB()
    hp = [(-0.33, -0.09, DECK_Z), (-0.40, -0.09, DECK_Z + 0.28), (-0.42, -0.09, DECK_Z + 0.55), (-0.42, 0.09, DECK_Z + 0.55),
          (-0.40, 0.09, DECK_Z + 0.28), (-0.33, 0.09, DECK_Z)]
    hd.sweep(hp, 0.011, "anodised", segs=12, fillet=0.06)
    hd.sweep([(-0.42, -0.06, DECK_Z + 0.55), (-0.42, 0.06, DECK_Z + 0.55)], 0.015, "rubber", segs=14)
    c.part("handle", hd, explode=(-0.15, 0, 0),
           desc="Push handle: labour is cheap, so a worker can also just push it - the first version is exactly that.")
    return c


def rover_strawberry():
    return rover(cid="r1_rover_sb", title="R1 rover, strawberry setting (mast down)", mast_top=0.68, crop="strawberry")


def wheel_bath(cid="wheel_bath", title="Wheel bath at the house door"):
    """Shallow tray (1.2 x 0.62 m, 6 cm deep) with ramps, filled with disinfectant: the rover drives through it."""
    c = Component(cid, title, "Biosecurity",
                  summary="Disinfectant tray at every house door. The rover's tyres pass through it before they enter "
                          "and after they leave, so it doesn't carry disease from one house to the next.",
                  how="Like the footbath for boots. Change the liquid every 2-3 days. Route rule: clean houses first, sick house last.",
                  real="HDPE tray + 2 ramps, quaternary-ammonium or peroxide disinfectant", cost="~₹4-6k (estimate)")
    tb = MB()
    L, Wd, D = 1.2, 0.62, 0.06
    tb.box((L, Wd, 0.008), "hdpe_blue", loc=(0, 0, 0.004))
    for sy in (-1, 1):
        tb.box((L, 0.015, D), "hdpe_blue", bevel=0.004, loc=(0, sy * (Wd / 2 - 0.0075), D / 2))
    for sx in (-1, 1):
        # ramp: a sloped plate from the floor up to the rim
        ang = math.degrees(math.atan2(D, 0.25))
        tb.box((0.26, Wd, 0.012), "hdpe_blue", loc=(sx * (L / 2 + 0.12), 0, D / 2), rot=(0, sx * ang, 0))
        for k in range(5):
            tb.box((0.012, Wd - 0.04, 0.006), "plastic_dark", loc=(sx * (L / 2 + 0.03 + k * 0.045), 0, D * (1 - (0.03 + k * 0.045) / 0.25) + 0.008),
                   rot=(0, sx * ang, 0))
    tb.box((L - 0.03, Wd - 0.035, 0.035), "disinfectant", loc=(0, 0, 0.026))
    c.part("tray", tb, desc="1.2 x 0.62 m tray, 6 cm deep, ramps both ends; the liquid covers the tyre contact patch.")
    return c


def mist_arch(cid="mist_arch", title="Disinfectant mist arch at the house door"):
    """Portal of 40 mm GI tube (1.1 m clear, 2.3 m tall) with 10 low-pressure brass mist nozzles aimed inward,
    a 12 V misting pump on a 20 L can, and an IR beam sensor: the rover breaks the beam, the arch mists it for 4 s.
    Nozzle positions (local, metres) and their aim are kept on the component for the video's mist."""
    c = Component(cid, title, "Biosecurity",
                  summary="The rover drives through it at every door: a 4-second disinfectant mist cleans the mast, "
                          "cameras and body, the parts that brush leaves.",
                  how="An IR beam across the doorway triggers a 12 V misting pump (about 7 bar) for 4 s. Same liquid "
                      "as the wheel bath. The rover waits 30 s to drip off before it enters.",
                  real="40 mm GI square tube, 10 x 0.3 mm brass misting nozzles, 12 V misting pump, E3F IR beam sensor, 20 L can",
                  cost="~₹8-12k (estimate)")
    fr = MB()
    Wd, Hh = 0.58, 2.3
    for sy in (-1, 1):
        fr.box((0.04, 0.04, Hh), "galv", bevel=0.002, loc=(0, sy * Wd, Hh / 2))
        fr.box((0.2, 0.2, 0.008), "galv", loc=(0, sy * Wd, 0.004))                     # base plates
    fr.box((0.04, 2 * Wd + 0.04, 0.04), "galv", bevel=0.002, loc=(0, 0, Hh))
    fr.box((0.002, 0.5, 0.12), "sticker_yellow", loc=(-0.021, 0, Hh - 0.12))
    fr.text("DISINFECTION", 0.04, "plastic_black", loc=(-0.0225, 0, Hh - 0.12), rot=(90, 0, -90), bold=True)
    c.part("frame", fr, desc="Portal frame, 40 mm GI tube, 1.16 m clear.")
    pp = MB()
    c.nozzles = []
    for sy in (-1, 1):
        y = sy * (Wd - 0.03)
        pp.sweep([(0.03, y, 0.15), (0.03, y, Hh - 0.03)], 0.006, "pe_black", segs=8)
        for z in (0.3, 0.75, 1.2, 1.65):
            pp.cyl(0.006, 0.02, "brass", segs=10, axis="-Y" if sy > 0 else "Y", loc=(0.03, y - sy * 0.01, z))
            c.nozzles.append(((0.03, y - sy * 0.022, z), (0.0, -sy, 0.0)))
    pp.sweep([(0.03, -(Wd - 0.03), Hh - 0.03), (0.03, Wd - 0.03, Hh - 0.03)], 0.006, "pe_black", segs=8)
    for y in (-0.2, 0.2):
        pp.cyl(0.006, 0.02, "brass", segs=10, axis="-Z", loc=(0.03, y, Hh - 0.05))
        c.nozzles.append(((0.03, y, Hh - 0.062), (0.0, 0.0, -1.0)))
    c.part("mist_line", pp, desc="10 brass mist nozzles (0.3 mm) on a 12 mm PE line, aimed at the rover's body and mast.")
    pu = MB()
    pu.box((0.3, 0.24, 0.36), "hdpe_white", bevel=0.02, loc=(0, 0, 0.18))
    pu.cyl(0.04, 0.03, "plastic_blue", segs=16, z0=0.36, loc=(0.05, 0, 0))
    pu.box((0.16, 0.12, 0.1), "plastic_black", bevel=0.008, loc=(0, 0, 0.41))
    pu.text("12V MIST PUMP", 0.012, "plastic_white", loc=(-0.081, 0, 0.41), rot=(90, 0, -90))
    pu.sweep(gh.fillet_path([(0.0, 0.0, 0.46), (0.0, 0.0, 0.55), (0.0, -0.18, 0.55), (0.03, -0.15, 0.6)], 0.05), 0.006, "pe_black", segs=8)
    c.part("pump", pu, loc=(-0.2, Wd + 0.25, 0), desc="12 V misting pump on a 20 L disinfectant can.")
    bs = MB()
    for sy in (-1, 1):
        bs.box((0.03, 0.025, 0.05), "plastic_black", bevel=0.003, loc=(0.03, sy * (Wd - 0.035), 0.42))
        bs.cyl(0.006, 0.004, "lens", segs=12, axis="-Y" if sy > 0 else "Y", loc=(0.03, sy * (Wd - 0.049), 0.42))
    c.part("beam", bs, desc="IR beam sensor: the rover breaks it, the arch mists.")
    return c


def charging_dock(cid="charging_dock", title="Charging dock (drive-on, spring contacts)"):
    """Just inside the door: the rover drives nose-first between two guide rails until its copper bumper pads press two
    spring-loaded brass contacts. A 29.2 V 10 A LiFePO4 charger in an IP65 box feeds them. Local frame: the rover arrives
    along -x (contacts at x = 0, facing +x)."""
    c = Component(cid, title, "Robot",
                  summary="Drive-on charging: no plugging in. The rover also syncs its photos here, on the router's Wi-Fi.",
                  how="Guide rails centre the rover; spring contacts touch the bumper's copper pads; the charger only switches on when "
                      "both pads read the battery voltage (no live contacts when nothing is docked).",
                  real="29.2 V 10 A LiFePO4 charger, 2 spring-loaded brass contacts, HDPE base, 40x40 extrusion post",
                  cost="~₹6-9k (estimate)")
    bs = MB()
    bs.box((0.75, 0.62, 0.012), "hdpe_blue", bevel=0.003, loc=(-0.36, 0, 0.006))
    for sy in (-1, 1):
        bs.box((0.6, 0.03, 0.05), "hdpe_blue", bevel=0.006, loc=(-0.42, sy * 0.205, 0.037), rot=(0, 0, sy * 4))
    bs.box((0.12, 0.002, 0.04), "sticker_yellow", loc=(-0.2, -0.3, 0.013), rot=(90, 0, 0))
    c.part("base", bs, desc="HDPE base with two guide rails that centre the rover.")
    pt = MB()
    extrusion(pt, 0.42, 0.04, 0.04, loc=(0.03, 0, 0.21), axis="Z")
    pt.box((0.05, 0.22, 0.05), "anod_dark", bevel=0.004, loc=(0.01, 0, 0.165))
    for sy in (-1, 1):
        pt.box((0.03, 0.03, 0.026), "plastic_black", loc=(-0.02, sy * 0.06, 0.165))
        pt.cyl(0.006, 0.02, "brass", segs=12, axis="-X", loc=(-0.04, sy * 0.06, 0.165))
        pt.torus(0.006, 0.0015, "stainless", segs=12, rsegs=6, axis="X", loc=(-0.028, sy * 0.06, 0.165))
    pt.box((0.16, 0.12, 0.2), "ip65_grey", bevel=0.008, loc=(0.03, 0, 0.53))
    pt.box((0.002, 0.08, 0.03), "plastic_black", loc=(-0.051, 0, 0.58))
    pt.text("29.2V 10A LiFePO4", 0.008, "plastic_white", loc=(-0.052, 0, 0.58), rot=(90, 0, -90))
    pt.cyl(0.006, 0.01, "led_green", segs=12, axis="-X", loc=(-0.052, 0.04, 0.5))
    cable(pt, [(0.03, 0.0, 0.43), (0.03, 0.03, 0.3), (0.035, 0.02, 0.19)], r=0.004)
    cable(pt, [(0.06, 0.04, 0.6), (0.1, 0.06, 0.66), (0.1, 0.25, 0.4), (0.1, 0.3, 0.0)], r=0.004)       # mains
    c.part("post", pt, desc="Post with the two spring-loaded brass contacts at bumper height, and the charger box.")
    return c


def antenna_pole(cid="antenna_pole", title="4G router + LoRa gateway on a pole outside"):
    """6.5 m GI pole outside the door: an IP65 box with a 4G router (e.g. TP-Link TL-MR100) and a LoRa gateway inside,
    a flat 4G MIMO panel antenna at the top (above the polyhouse film, which weakens signal), and a fibreglass LoRa antenna."""
    c = Component(cid, title, "Network",
                  summary="Puts the internet where the signal is: 4G outside and above the house, Wi-Fi to the dock inside, "
                          "LoRa for every climate box on the farm.",
                  real="TP-Link TL-MR100 4G router, 4G LTE MIMO panel antenna, 865-867 MHz LoRa gateway + 3 dBi fibreglass antenna, IP65 box, 50 mm GI pole",
                  cost="~₹12-18k (estimate)")
    pl = MB()
    pl.cyl(0.025, 6.5, "galv", segs=20, z0=0.0)
    pl.cyl(0.12, 0.1, "concrete", segs=20, z0=-0.02)
    pl.cyl(0.028, 0.012, "galv", segs=20, z0=6.49)
    c.part("pole", pl, desc="6.5 m, 50 mm GI pole in a concrete footing: the antenna sits above the roof (~5.9 m).")
    bx = MB()
    bx.box((0.22, 0.12, 0.3), "ip65_grey", bevel=0.01, loc=(0, 0, 0))
    for zz in (-0.08, 0.08):
        bx.box((0.03, 0.06, 0.02), "galv", loc=(0.08, 0, zz))                                    # pole clamps
    bx.text("4G + LoRa", 0.02, "plastic_black", loc=(0, -0.061, 0.08), rot=(90, 0, 0), bold=True)
    for k in range(3):
        bx.cyl(0.006, 0.015, "plastic_black", segs=10, axis="-Z", loc=(-0.06 + 0.06 * k, 0, -0.15))      # glands
    c.part("box", bx, loc=(-0.09, 0, 1.6), desc="IP65 box: 4G router + LoRa gateway + a 12 V supply.")
    an = MB()
    an.box((0.06, 0.24, 0.24), "plastic_white", bevel=0.012, loc=(0, 0, 0))
    an.box((0.04, 0.05, 0.05), "galv", loc=(0.05, 0, 0))
    an.text("LTE", 0.03, "plastic_dark", loc=(-0.031, 0, 0.05), rot=(90, 0, -90), bold=True)
    c.part("panel_antenna", an, loc=(-0.06, 0, 6.3), rot=(0, 0, 0), desc="4G LTE MIMO panel antenna, above the polyhouse film.")
    lo = MB()
    lo.cyl(0.012, 0.6, "plastic_white", segs=14, z0=0.0, r_top=0.009)
    lo.box((0.04, 0.04, 0.04), "galv", loc=(0, 0, -0.02))
    c.part("lora_antenna", lo, loc=(0.0, 0.12, 6.5), desc="865 MHz fibreglass LoRa antenna for the climate boxes.")
    cb = MB()
    cable(cb, [(-0.09, 0.03, 1.75), (-0.04, 0.04, 3.4), (-0.04, 0.03, 6.2), (-0.06, 0.0, 6.25)], r=0.004)
    cable(cb, [(-0.09, -0.03, 1.75), (-0.03, -0.03, 3.6), (0.0, 0.08, 6.45), (0.0, 0.12, 6.5)], r=0.004)
    cable(cb, [(-0.09, 0.0, 1.45), (-0.04, 0.0, 1.0), (-0.03, 0.0, 0.1), (-0.3, 0.0, 0.0)], r=0.005)
    c.part("cables", cb, desc="Antenna and power cables.")
    return c


ALL = [rover, rover_strawberry, wheel_bath, mist_arch, charging_dock, antenna_pole]
