"""Pipe-rail scouting + pollination robot and its charging dock.

Local frame: +X = driving direction along the aisle, ±Y = the two crop rows, z = 0 at the rail contact point
(top of the 51 mm pipe rail). Placed in the greenhouse at world z = pipe top.
"""
import math

import gh  # noqa: E402
from gh import MB, TAU, Component, bm_box, bm_lathe, emissive, fillet_path, xform
from parts import cable, radial

GAUGE = 0.55      # rail centre distance
PIPE_R = 0.0255   # 51 mm pipe


def rail_wheel(mb, loc, r=0.06, w=0.05):
    """Double-flanged wheel whose concave groove sits on a round pipe (axis = Y)."""
    g = PIPE_R + 0.002
    prof = [(0.0, -w / 2), (r + 0.012, -w / 2), (r + 0.012, -w / 2 + 0.006)]
    for i in range(9):
        a = math.pi * (i / 8)
        y = -g * math.cos(a) * 0.95
        prof.append((r + 0.012 - (g * math.sin(a)) * 0.6 - 0.004, y))
    prof += [(r + 0.012, w / 2 - 0.006), (r + 0.012, w / 2), (0.0, w / 2)]
    mb.lathe(prof, "plastic_dark", segs=40, axis="Y", loc=loc)
    mb.cyl(0.018, w + 0.012, "stainless", segs=20, axis="Y", loc=loc)
    for x, z, a in radial(5, 0.035):
        mb.cyl(0.004, 0.004, "stainless", segs=8, axis="Y", loc=(loc[0] + x, loc[1] - w / 2 - 0.002, loc[2] + z))
    return mb


def oak_d_lite(mb, loc, facing="+Y"):
    """Luxonis OAK-D Lite stereo depth camera (91 × 28 × 17.5 mm), lenses facing ±Y."""
    s = 1 if facing == "+Y" else -1
    M = xform(loc, (0, 0, 0 if s > 0 else 180))
    mb.add(bm_box(0.091, 0.0175, 0.028), "alu_black", M=M)
    mb.add(bm_box(0.089, 0.002, 0.026), "plastic_black", M=M @ xform((0, 0.0095, 0)))
    for x, rr in ((-0.0375, 0.005), (0.0375, 0.005), (0.0, 0.0065)):
        mb.add(__import__("gh").bm_cyl(rr, 0.003, 24), "chrome", M=M @ xform((x, 0.011, 0)) @ xform(rot=(-90, 0, 0)))
        mb.add(__import__("gh").bm_cyl(rr * 0.65, 0.002, 24), "lens", M=M @ xform((x, 0.0125, 0)) @ xform(rot=(-90, 0, 0)))
    return mb


def scout_robot(cid="scout_robot", title="Scout & pollination robot (pipe-rail)", lift=1.05):
    c = Component(
        cid, title, "Robot",
        summary=("Drives along the pipe rails between rows, photographs every plant from 5 heights, counts flowers "
                 "and fruit, spots pests/disease, and pollinates open flowers with gentle air pulses."),
        how=("Two drives: on the 51 mm pipe rails, 2 gearmotors turn the grooved wheels (forward/back only, it can't steer "
             "or derail); on the concrete path, 4 mecanum wheels carry it. To change rows it backs off the rails over a "
             "sloped plate (the mecanum wheels take its weight, the grooved wheels lift off), slides sideways along the "
             "path until its side camera centres the next aisle's marker (±1 cm), then drives forward onto the rails. "
             "In the row it drives slowly (0.1–0.3 m/s). Wheel encoders + each plant's tag give its exact position, so every image is "
             "saved to the right plant record. At each plant the camera head moves up the mast: two OAK-D Lite stereo "
             "cameras (one per row) capture colour + depth; the Jetson runs detection (flowers, fruit + ripeness, symptoms, "
             "insects). For each open flower it aims the nozzle and gives a short air pulse – the vibration releases pollen "
             "(like a bumblebee buzz). Bumpers, E-stops and a heartbeat watchdog stop it instantly; the greenhouse keeps "
             "running if the robot fails."),
        sensors=("2 × OAK-D Lite stereo-depth cameras", "wheel encoders", "IR leaf-temperature sensor", "ToF distance",
                 "bumper switches", "battery monitor"),
        control=("ROS 2 on Jetson Orin Nano Super (mission, vision). ESP32 (micro-ROS) runs motors with its own safety loop. "
                 "E-stop + bumpers cut motor power in hardware."),
        state={"mode": "scouting", "aisle": 1, "x_m": 3.4, "battery_pct": 76, "plants_done_today": 31,
               "flowers_pollinated": 118, "lift_m": lift},
        real=("DIY on proven parts: aluminium frame, 2 × 24 V BLDC gearmotors (rails), 4 × 127 mm mecanum wheels + gearmotors (path), 24 V 50 Ah LiFePO4, NEMA 23 belt lift, "
              "Jetson Orin Nano Super, 2 × OAK-D Lite, 12 V diaphragm air pump. Reference: Arugga Polly+, Ecoation OKO."),
        cost="₹1.5–2.2 L (prototype BOM)")
    L, Wd = 0.9, 0.62
    Z0 = 0.06 + 0.04          # frame bottom above rail contact
    # chassis frame + deck
    fr = MB()
    for sy in (-1, 1):
        fr.box((L, 0.04, 0.04), "alu_black", bevel=0.002, loc=(0, sy * (Wd / 2 - 0.02), Z0 + 0.02))
    for sx in (-1, 1, 0):
        fr.box((0.04, Wd - 0.08, 0.04), "alu_black", bevel=0.002, loc=(sx * (L / 2 - 0.02), 0, Z0 + 0.02))
    for sx in (-1, 1):
        for sy in (-1, 1):
            fr.box((0.03, 0.06, 0.1), "alu_black", loc=(sx * 0.35, sy * GAUGE / 2, 0.075))  # wheel forks
    fr.box((L - 0.02, Wd - 0.02, 0.006), "alu", bevel=0.002, loc=(0, 0, Z0 + 0.043))
    for k in range(10):  # chequer plate texture
        fr.box((0.8, 0.004, 0.002), "alu", loc=(0, -0.27 + k * 0.06, Z0 + 0.047))
    c.part("chassis", fr, desc="Aluminium extrusion frame + deck plate.")
    DECK = Z0 + 0.046
    # rail wheels
    rw = MB()
    for sx in (-1, 1):
        for sy in (-1, 1):
            rail_wheel(rw, (sx * 0.35, sy * GAUGE / 2, 0.06))
    c.part("rail_wheels", rw, explode=(0, 0, -0.18),
           desc="4 double-flanged grooved wheels – they sit on the round pipe rails and cannot derail.")
    # 14 Oct 2026: the path drive is 4 mecanum wheels (was 2 rubber hub wheels, which could not hold the robot up on
    # the concrete). Mecanum lets it slide sideways along the path from one aisle to the next: no turning circle,
    # which GH-01's 1.7 m path in front of the tanks doesn't have room for.
    fw = MB()
    MR, MW = 0.0635, 0.05          # 127 mm mecanum wheel; bottom at z = -0.10 (2.5 cm above the aisle floor on rails)
    AZ = -0.10 + MR
    import mathutils
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * 0.20, sy * 0.19
            hand = sx * sy                                      # X-configuration: diagonal wheels share a hand
            fw.cyl(0.032, MW - 0.004, "alu", segs=28, axis="Y", loc=(cx, cy, AZ))
            for dy in (-1, 1):
                fw.cyl(MR - 0.012, 0.004, "alu_black", segs=28, axis="Y", loc=(cx, cy + dy * (MW / 2 - 0.002), AZ))
            for k in range(9):                                  # 9 free rollers at 45 degrees round the rim
                ph = TAU * k / 9
                rr = MR - 0.0125
                px, pz = cx + rr * math.cos(ph), AZ + rr * math.sin(ph)
                tang = mathutils.Vector((-math.sin(ph), 0.0, math.cos(ph)))
                d = (tang * math.cos(math.radians(45)) + mathutils.Vector((0, hand * math.sin(math.radians(45)), 0))).normalized()
                q = mathutils.Vector((0, 0, 1)).rotation_difference(d)
                M = mathutils.Matrix.Translation((px, cy, pz)) @ q.to_matrix().to_4x4()
                fw.add(gh.bm_cyl(0.0125, 0.046, 12, 0.004, r_top=0.0125, z0=-0.023), "rubber", M=M)
            fw.cyl(0.024, 0.06, "steel_dark", segs=24, bevel=0.003, axis="Y", loc=(cx, sy * 0.125, AZ))       # gearmotor
            fw.box((0.06, 0.008, 0.14), "alu_black", loc=(cx, sy * 0.158, AZ + 0.06))                       # bracket
            fw.box((0.025, 0.02, 0.02), "plastic_black", loc=(cx, sy * 0.09, AZ + 0.02))                    # encoder
    pc = MB()                                                    # the downward camera that reads the floor codes
    pc.box((0.05, 0.05, 0.025), "alu_black", bevel=0.003)
    pc.cyl(0.009, 0.006, "lens", segs=20, axis="-Z", loc=(0, 0, -0.0125))
    pc.box((0.03, 0.002, 0.006), "led_white", loc=(0.0, 0.026, -0.008))
    c.part("path_camera", pc, loc=(0.40, 0.0, Z0 - 0.015), explode=(0.15, 0, -0.2),
           desc="Downward camera + ring light under the front: reads the floor code at each aisle mouth (±2 mm).")
    c.part("floor_wheels", fw, explode=(0, 0, -0.3),
           desc=("4 × 127 mm mecanum wheels, each with its own 24 V gearmotor + encoder: on the concrete path they drive "
                 "forward, backward and sideways (no turning circle). On the rails they hang 2.5 cm above the floor."))
    dm = MB()
    for sy in (-1, 1):
        dm.cyl(0.035, 0.12, "steel_dark", segs=32, bevel=0.004, axis="Y", loc=(-0.35, sy * (GAUGE / 2 - 0.1), 0.06))
        dm.cyl(0.028, 0.03, "alu", segs=32, axis="Y", loc=(-0.35, sy * (GAUGE / 2 - 0.175), 0.06))
        dm.box((0.03, 0.02, 0.03), "plastic_black", loc=(-0.35, sy * (GAUGE / 2 - 0.02), 0.11))  # encoder
        cable(dm, [(-0.35, sy * (GAUGE / 2 - 0.04), 0.06), (-0.3, sy * 0.1, 0.09), (-0.2, sy * 0.05, DECK)], r=0.004)
    c.part("drive_motors", dm, explode=(-0.2, 0, -0.1),
           desc="2 × 24 V BLDC gearmotors with magnetic encoders (position along the row to ±5 mm).")
    bt = MB()
    bt.box((0.34, 0.26, 0.16), "plastic_dark", bevel=0.01)
    bt.box((0.2, 0.001, 0.05), "sticker_white", loc=(0, -0.131, 0.02))
    bt.text("LiFePO4 24 V 50 Ah", 0.016, "plastic_black", loc=(0, -0.1315, 0.02), rot=(90, 0, 0), bold=True)
    bt.box((0.05, 0.03, 0.02), "plastic_orange", loc=(0.12, 0.0, 0.09))
    c.part("battery", bt, loc=(-0.2, 0, DECK + 0.08), explode=(-0.25, -0.25, 0.35),
           desc="24 V 50 Ah LiFePO4 battery – ~8 h of scouting, safe chemistry, BMS inside.")
    cb = MB()
    cb.box((0.3, 0.24, 0.14), "plastic_white", bevel=0.012)
    for k in range(6):
        cb.box((0.004, 0.001, 0.08), "plastic_dark", loc=(-0.13 + k * 0.012, -0.121, 0.0))
    cb.cyl(0.004, 0.14, "plastic_black", segs=12, z0=0.07, loc=(0.12, 0.09, 0))
    cb.text("SCOUT-01", 0.026, "plastic_green", loc=(0.05, -0.1215, 0.02), rot=(90, 0, 0), bold=True)
    c.part("compute_enclosure", cb, loc=(0.25, 0, DECK + 0.07), explode=(0.3, -0.35, 0.3),
           desc="Splash-proof electronics box with Wi-Fi antenna.")
    js = MB()
    js.box((0.1, 0.08, 0.02), "pcb", loc=(0, 0, 0))
    js.box((0.07, 0.045, 0.018), "alu_black", loc=(0, 0.01, 0.019))
    for k in range(10):
        js.box((0.07, 0.002, 0.012), "alu_black", loc=(0, -0.012 + k * 0.005, 0.034))
    js.cyl(0.018, 0.008, "plastic_black", segs=24, loc=(0, 0.01, 0.044))
    js.text("Jetson Orin Nano Super", 0.006, "plastic_white", loc=(0.0, -0.035, 0.011), bold=True)
    c.part("jetson_orin_nano", js, loc=(0.2, 0.0, DECK + 0.03), explode=(0.3, -0.35, 0.62),
           desc="Jetson Orin Nano Super (67 TOPS): ROS 2 + vision models run here.")
    mc = MB()
    mc.box((0.08, 0.06, 0.0016), "pcb_blue")
    for k in range(4):
        mc.box((0.012, 0.012, 0.01), "chip", loc=(-0.028 + k * 0.018, 0.0, 0.005))
    mc.box((0.05, 0.028, 0.0016), "pcb", loc=(0.0, 0.05, 0.0))
    mc.box((0.018, 0.012, 0.004), "alu", loc=(0.0, 0.05, 0.003))
    c.part("motor_io_board", mc, loc=(0.33, 0.0, DECK + 0.03), explode=(0.45, -0.35, 0.5),
           desc="Motor drivers + ESP32 (micro-ROS): wheels, lift, pump, bumpers – own safety loop.")
    # mast + lift
    MH = 2.2
    ms = MB()
    ms.box((0.04, 0.08, MH), "alu", bevel=0.002, loc=(0, 0, MH / 2))
    for sy in (-1, 1):
        ms.box((0.008, 0.004, MH - 0.02), "steel_dark", loc=(0, sy * 0.042, MH / 2))  # guide rails
    ms.box((0.12, 0.12, 0.012), "alu_black", loc=(0, 0, MH + 0.006))
    ms.box((0.16, 0.16, 0.012), "alu_black", loc=(0, 0, 0.006))
    for sy in (-1, 1):
        ms.box((0.012, 0.012, 0.5), "alu_black", loc=(0.0, sy * 0.16, 0.25), rot=(sy * 30, 0, 0))
    ms.cyl(0.02, 0.03, "alu_black", segs=24, axis="X", loc=(0.035, 0, MH - 0.03))
    c.part("mast", ms, loc=(-0.02, 0, DECK), explode=(0, 0, 0.0), desc="2 m aluminium mast with linear guide rails.")
    ld = MB()
    ld.box((0.057, 0.057, 0.08), "steel_dark", bevel=0.003, loc=(0.05, 0, 0.05))
    ld.cyl(0.02, 0.03, "alu", segs=24, axis="X", loc=(0.035, 0, 0.11))
    ld.box((0.002, 0.016, MH - 0.14), "rubber", loc=(0.043, 0, MH / 2 + 0.04))
    ld.box((0.002, 0.016, MH - 0.14), "rubber", loc=(0.03, 0, MH / 2 + 0.04))
    c.part("lift_drive", ld, loc=(-0.02, 0, DECK), explode=(0.25, 0, 0.0),
           desc="NEMA 23 stepper + toothed belt: moves the camera head from 0.3 m to 2.0 m.")
    # sensor head on the carriage
    hd = c.group("sensor_head", loc=(0.0, 0, DECK + lift), explode=(0.35, 0, 0.3),
                 desc="Camera head: two stereo cameras (one per row), flash panels, IR leaf-temp sensor, pollination nozzles.")
    ca = MB()
    ca.box((0.08, 0.12, 0.1), "plastic_white", bevel=0.01, loc=(0.02, 0, 0))
    ca.box((0.06, 0.56, 0.03), "alu_black", bevel=0.003, loc=(0.03, 0, 0))
    c.part("carriage", ca, parent=hd, desc="Carriage (rides the mast guides) + cross-arm.")
    for sy, name in ((1, "camera_left_row"), (-1, "camera_right_row")):
        cm = MB()
        oak_d_lite(cm, (0.0, 0.0, 0.0), "+Y" if sy > 0 else "-Y")
        c.part(name, cm, parent=hd, loc=(0.03, sy * 0.29, 0.04), explode=(0, sy * 0.22, 0.1),
               desc="OAK-D Lite: colour + stereo depth (measures stem length, truss height, fruit size in mm).")
        fl = MB()
        fl.box((0.2, 0.012, 0.05), "plastic_white", bevel=0.004)
        for i in range(10):
            fl.box((0.008, 0.002, 0.008), "led_white", loc=(-0.09 + i * 0.02, sy * 0.007, 0.0))
        c.part(f"flash_{'left' if sy > 0 else 'right'}", fl, parent=hd, loc=(0.03, sy * 0.285, -0.035),
               rot=(0, 0, 0), explode=(0, sy * 0.3, -0.06),
               desc="LED flash panel – same light for every photo (day or night), so the AI sees consistent colours.")
        nz = MB()
        nz.box((0.04, 0.02, 0.036), "plastic_black", bevel=0.002)          # pan servo
        nz.box((0.02, 0.036, 0.04), "plastic_black", bevel=0.002, loc=(0, sy * 0.02, 0.03))  # tilt servo
        nz.cyl(0.006, 0.05, "brass", segs=16, axis="Y" if sy > 0 else "-Y", loc=(0, sy * 0.05, 0.05))
        nz.lathe([(0.0, 0.0), (0.009, 0.0), (0.004, 0.018), (0.0015, 0.02), (0.0, 0.02)], "plastic_orange", segs=20,
                 axis="Y" if sy > 0 else "-Y", loc=(0, sy * 0.075, 0.05))
        c.part(f"pollinator_{'left' if sy > 0 else 'right'}", nz, parent=hd, loc=(0.03, sy * 0.2, 0.06),
               explode=(0, sy * 0.25, 0.25),
               desc="Pollination nozzle on a pan-tilt servo: aims at an open flower and gives a 50 ms air pulse.")
    ir = MB()
    ir.cyl(0.009, 0.02, "stainless", segs=20, axis="Y", loc=(0, 0.0, 0))
    ir.cyl(0.009, 0.02, "stainless", segs=20, axis="-Y", loc=(0, 0.0, 0))
    c.part("ir_leaf_temp", ir, parent=hd, loc=(0.03, 0.0, -0.04), explode=(0.1, 0, -0.15),
           desc="IR thermometers (both sides): leaf temperature → leaf VPD and water-stress index.")
    # drag chain from deck to carriage
    dc = MB()
    top = DECK + lift + 0.08
    path = fillet_path([(0.06, 0.05, DECK + 0.25), (0.06, 0.05, top), (0.1, 0.05, top + 0.05), (0.1, 0.05, DECK + lift)],
                       0.04, steps=10)
    import mathutils
    P = [mathutils.Vector(p) for p in path]
    acc, step = 0.0, 0.022
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        seg = (b - a).length
        d = (b - a).normalized()
        t = step - acc
        while t < seg:
            p = a + d * t
            rot = math.degrees(math.atan2(d.x, d.z))
            dc.box((0.012, 0.03, 0.02), "plastic_black", bevel=0.002, loc=tuple(p), rot=(0, rot, 0))
            t += step
        acc = (acc + seg) % step
    c.part("cable_chain", dc, explode=(0.3, 0.15, 0.0), desc="Cable/air-hose carrier – guides the camera cables and pollination air tube.")
    ai = MB()
    ai.box((0.12, 0.08, 0.08), "plastic_dark", bevel=0.006, loc=(0, 0, 0.04))
    ai.cyl(0.035, 0.18, "plastic_white", segs=24, axis="X", loc=(0.0, 0.12, 0.035))
    cable(ai, [(0.06, 0.0, 0.05), (0.1, 0.0, 0.08), (0.1, 0.05, 0.2)], r=0.003, m="silicone_clear")
    c.part("air_system", ai, loc=(-0.22, 0.2, DECK + 0.0), explode=(-0.3, 0.35, 0.45),
           desc="12 V diaphragm air pump + 0.5 L buffer tank for the pollination pulses.")
    # safety
    sf = MB()
    for sx in (-1, 1):
        sf.box((0.05, Wd + 0.02, 0.06), "sticker_yellow", bevel=0.02, loc=(sx * (L / 2 + 0.03), 0, Z0 + 0.03))
        for sy in (-1, 1):
            x0, y0 = sx * (L / 2 - 0.05), sy * (Wd / 2 - 0.06)
            sf.box((0.06, 0.06, 0.06), "sticker_yellow", bevel=0.006, loc=(x0, y0, DECK + 0.03))
            sf.cyl(0.018, 0.02, "plastic_red", segs=24, z0=DECK + 0.06, loc=(x0, y0, 0))
            sf.sphere(0.022, "plastic_red", segs=24, rings=8, squash=0.45, loc=(x0, y0, DECK + 0.085))
    for k, m in enumerate(("led_green", "led_amber", "led_red")):
        sf.cyl(0.025, 0.04, m, segs=24, z0=DECK + MH + 0.012 + 0.042 * k, loc=(-0.02, 0, 0))
    sf.cyl(0.022, 0.012, "plastic_dark", segs=24, z0=DECK + MH + 0.138, loc=(-0.02, 0, 0))
    c.part("safety", sf, explode=(0, 0, 0.15),
           desc="Front/rear bumpers (stop on touch), 4 E-stops (cut motor power), status light tower.")
    shl = MB()
    shl.box((L - 0.06, Wd - 0.12, 0.2), "plastic_white", bevel=0.03, loc=(0.02, 0, DECK + 0.1))
    shl.box((L - 0.02, Wd - 0.1, 0.03), "plastic_green", bevel=0.01, loc=(0.02, 0, DECK + 0.015))
    shl.box((0.24, 0.001, 0.05), "screen", loc=(0.2, -(Wd - 0.12) / 2 - 0.001, DECK + 0.14))
    shl.text("SCOUT-01", 0.035, "plastic_green", loc=(-0.12, -(Wd - 0.12) / 2 - 0.002, DECK + 0.13), rot=(90, 0, 0),
             bold=True)
    for sy in (-1, 1):
        shl.cyl(0.012, 0.004, "lens", segs=20, axis="X", loc=(L / 2 - 0.01, sy * 0.12, DECK + 0.12))  # ToF sensors
        shl.cyl(0.012, 0.004, "lens", segs=20, axis="-X", loc=(-L / 2 + 0.05, sy * 0.12, DECK + 0.12))
    c.part("body_shell", shl, explode=(0, 0, 0.9),
           desc="Splash-proof body shell (lift off to reach battery, computer, pump). ToF sensors front/back.")
    rl = MB()
    for sy in (-1, 1):
        rl.cyl(PIPE_R, 1.6, "galv", segs=24, axis="X", loc=(0, sy * GAUGE / 2, -PIPE_R))
        for x in (-0.6, 0.0, 0.6):
            rl.box((0.04, 0.05, 0.1), "galv_dull", loc=(x, sy * GAUGE / 2, -PIPE_R - 0.06))
    c.part("pipe_rails", rl, explode=(0, 0, -0.35),
           desc="51 mm pipe rails on the floor of the aisle (in big greenhouses these are the heating pipes).")
    cc = MB()
    for sy in (-1, 1):
        cc.box((0.02, 0.06, 0.03), "copper", loc=(-L / 2 - 0.065, sy * 0.1, Z0 + 0.03))
    c.part("charging_contacts", cc, explode=(-0.2, 0, 0), desc="Charging contacts – meet the dock's spring plates at the aisle end.")
    return c


def charging_dock(cid="robot_dock", title="Robot charging dock"):
    c = Component(
        cid, title, "Robot",
        summary="At the end of the rails: the robot parks here, charges and uploads its images.",
        how=("The robot drives slowly into the dock until its copper contacts press on spring-loaded plates. The charger "
             "only switches on when it detects the robot's battery (no live exposed contacts). A printed ArUco marker "
             "lets the robot's camera confirm the exact docking position."),
        sensors=("contact detection", "charger current"), control="Charger with its own logic; status to edge server.",
        state={"robot_docked": False, "charging_a": 0},
        real="24 V 10 A LiFePO4 charger + spring contact plates on a galvanised post", cost="₹8–15k")
    po = MB()
    po.box((0.06, 0.06, 0.6), "galv", bevel=0.004, loc=(0, 0, 0.3))
    po.box((0.25, 0.25, 0.01), "galv", loc=(0, 0, 0.005))
    po.box((0.05, 0.62, 0.05), "rubber", bevel=0.01, loc=(0.03, 0, 0.16))
    c.part("post_bumper", po, desc="Post + rubber end-stop.")
    sp = MB()
    for sy in (-1, 1):
        sp.box((0.03, 0.08, 0.04), "plastic_dark", loc=(0.05, sy * 0.1, 0.13))
        sp.box((0.006, 0.07, 0.035), "copper", loc=(0.068, sy * 0.1, 0.13))
    c.part("contact_plates", sp, explode=(0.15, 0, 0), desc="Spring-loaded contact plates.")
    ch = MB()
    ch.box((0.2, 0.08, 0.14), "plastic_white", bevel=0.008)
    ch.box((0.03, 0.002, 0.01), "led_green", loc=(0.05, -0.041, 0.04))
    cable(ch, [(0.0, 0.0, -0.07), (0.0, 0.0, -0.15), (0.05, 0.05, -0.3)], r=0.005)
    c.part("charger", ch, loc=(-0.05, 0.0, 0.5), explode=(0, 0, 0.25), desc="24 V charger (turns on only when a robot is detected).")
    mk = MB()
    mk.box((0.004, 0.15, 0.15), "sticker_white", loc=(0.0, 0, 0))
    import random
    rnd = random.Random(42)
    for i in range(6):
        for j in range(6):
            edge = i in (0, 5) or j in (0, 5)
            if edge or rnd.random() < 0.5:
                mk.box((0.001, 0.022, 0.022), "plastic_black", loc=(0.0025, -0.055 + i * 0.022, -0.055 + j * 0.022))
    c.part("aruco_marker", mk, loc=(0.035, 0.0, 0.38), explode=(0.12, 0, 0.1), desc="ArUco marker for precise docking.")
    return c
