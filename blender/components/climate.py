"""Climate hardware: exhaust fan, evaporative cooling pad wall, HAF circulation fan, ridge-vent rack-and-pinion drive,
high-pressure fog nozzle + fog pump."""
import math

from gh import MB, TAU, Component, bm_box, bm_lathe, fillet_path, xform
from parts import (axial_blades, blade, cable, dial, helix, kirloskar_chhotu, motor_x, octagon, polygon_plate_with_hole,
                   pvc_run, radial, screw, square_plate_with_hole)


def belt_path(c1, r1, c2, r2, y, n=40):
    """Closed belt around two pulleys in the XZ plane (at depth y)."""
    dx, dz = c2[0] - c1[0], c2[1] - c1[1]
    d = math.hypot(dx, dz)
    phi = math.atan2(dz, dx)
    beta = math.acos((r1 - r2) / d)
    pts = []
    a0, a1 = phi + beta, phi + TAU - beta
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        pts.append((c1[0] + r1 * math.cos(a), y, c1[1] + r1 * math.sin(a)))
    b0, b1 = phi - beta, phi + beta
    for i in range(n // 3 + 1):
        a = b0 + (b1 - b0) * i / (n // 3)
        pts.append((c2[0] + r2 * math.cos(a), y, c2[1] + r2 * math.sin(a)))
    pts.append(pts[0])
    return pts


# ─────────────────────────────── exhaust fan ───────────────────────────────
def exhaust_fan(cid="exhaust_fan", title="Exhaust fan (Multifan 4E50)", size_in=None):
    """Vostermans Multifan 4E50 panel fan + gravity shutter, modelled 1:1 from the Multifan dimension sheet:
    panel B = 647.5 mm, bolt square A = 600, venturi C = 540, venturi depth E = 84, motor/guard depth D = 192.
    Component frame: +Y = greenhouse side (air comes in here), -Y = outside (shutter)."""
    c = Component(
        cid, title, "Climate",
        summary="Pulls hot, humid air out; fresh air is sucked in through the wet cooling pad on the far wall.",
        how=("A 420 W direct-drive motor spins six red blades at about 1,350 rpm inside a bell-mouth ring. One fan moves "
             "about 6,300 m³/h against the pad (30 Pa); two fans give ~12,600 m³/h, 1.6× what this 45 m² house needs "
             "(sizing rule ~2.5 m³/min per m² of floor, +10 % for Kolar's altitude). So one fan alone can still cool the "
             "house if the other fails. The outside gravity shutter opens with the airflow and falls shut when the fan "
             "stops, so hot air, rain and insects can't come back in."),
        sensors=("air temperature (2 boxes)", "motor current", "airflow switch on the shutter"),
        control=("PLC contactor per fan, 2 stages (fan 1, then fan 2). HARD-WIRED thermostat forces both ON above 35 °C "
                 "even if the PLC and AI fail."),
        state={"running": True, "stage": 1, "current_a": 1.9, "rpm": 1350},
        real="Vostermans Multifan 4E50 (V4E50K), 50 cm, 1~230 V, 420 W, IP55 motor + Multifan gravity shutter",
        cost="≈₹32k each (import; quote needed)")
    RY = xform(rot=(-90, 0, 0))             # build around Z, then Z → +Y (greenhouse side)
    B, A, C, E, D = 0.6475, 0.600, 0.540, 0.084, 0.192
    pn = MB()
    square_plate_with_hole(pn, "anthracite", B / 2, C / 2 + 0.03, 0.003, M=RY @ xform((0, 0, -0.003)))
    # bell-mouth venturi ring: straight throat at the panel, flared lip on the greenhouse side
    pn.add(bm_lathe([(C / 2 + 0.03, 0.0), (C / 2 + 0.003, 0.0), (C / 2 + 0.003, E * 0.55), (C / 2 + 0.018, E * 0.85),
                     (C / 2 + 0.042, E), (C / 2 + 0.046, E - 0.004), (C / 2 + 0.022, E * 0.8), (C / 2 + 0.008, E * 0.5),
                     (C / 2 + 0.008, 0.002), (C / 2 + 0.03, 0.002)], 96, closed=True), "anthracite", M=RY)
    for sx in (-1, 1):                       # stiffening ribs + the 4 bolt holes (A = 600 mm square)
        for sz in (-1, 1):
            pn.cyl(0.0075, 0.004, "steel_dark", segs=16, M=RY @ xform((sx * A / 2, sz * A / 2, 0.0)))
            pn.cyl(0.011, 0.003, "stainless", segs=6, M=RY @ xform((sx * A / 2, sz * A / 2, 0.003)))
    c.part("panel", pn, desc="Anthracite panel (647.5 mm square) with a bell-mouth venturi ring: the ring stops air "
                             "slipping round the blade tips, which is most of a fan's efficiency.")
    bl = MB()
    axial_blades(bl, "plastic_red", 6, 0.052, 0.247, chord=(0.07, 0.15), pitch=(34, 20), sweep=16, camber=0.07,
                 thick=0.004, z0=0.0, M=RY)
    bl.cyl(0.056, 0.05, "plastic_black", segs=40, bevel=0.006, M=RY)
    c.part("impeller", bl, loc=(0, 0.045, 0), explode=(0, 0.28, 0),
           desc="6 red glass-fibre-reinforced blades, Ø ≈ 500 mm, on a black hub.")
    mo = MB()
    mo.lathe([(0.0, 0.0), (0.058, 0.0), (0.064, 0.008), (0.064, 0.085), (0.058, 0.095), (0.0, 0.095)], "plastic_black",
             segs=48, M=RY)
    for k in range(16):                      # cooling ribs
        a = TAU * k / 16
        mo.box((0.006, 0.006, 0.07), "plastic_black", M=RY @ xform((0.066 * math.cos(a), 0.066 * math.sin(a), 0.047),
                                                                     (0, 0, math.degrees(a))))
    mo.cyl(0.036, 0.001, "plastic_blue", segs=40, M=RY @ xform((0, 0, 0.0955)))
    mo.text("Multifan", 0.012, "sticker_white", depth=0.0004, bold=True, M=RY @ xform((0, -0.004, 0.0962)))
    mo.box((0.045, 0.03, 0.03), "plastic_black", bevel=0.004, M=RY @ xform((0.0, -0.075, 0.05)))  # terminal box
    cable(mo, [(0.0, 0.045, 0.09), (0.0, 0.09, 0.15), (0.0, 0.092, 0.285), (0.0, -0.005, 0.305), (0.0, -0.09, 0.33)],
          r=0.0035, fillet=0.015)
    c.part("motor", mo, loc=(0, 0.095, 0), explode=(0, 0.5, 0),
           desc="420 W, 4-pole, IP55 external-rotor motor, carried by the wire guard. Direct drive: no belt to wear.")
    gd = MB()
    for k in range(2, 12):
        gd.torus(0.0265 * k, 0.0017, "plastic_black", segs=72, rsegs=6, M=RY @ xform((0, 0, D)))
    for k in range(16):
        a = 360 * k / 16
        gd.box((0.225, 0.0032, 0.0032), "plastic_black", M=RY @ xform((0, 0, D)) @ xform(rot=(0, 0, a)) @ xform((0.1795, 0, 0)))
    for k in range(4):                       # legs from the guard rim back to the panel
        a = math.radians(45 + 90 * k)
        p0 = (0.2915 * math.cos(a), 0.2915 * math.sin(a), D)
        p1 = (0.3125 * math.cos(a), 0.3125 * math.sin(a), E + 0.002)
        gd.sweep([p0, p1], 0.003, "plastic_black", segs=8, M=RY)
    gd.cyl(0.07, 0.006, "plastic_black", segs=40, M=RY @ xform((0, 0, D - 0.004)))  # motor plate
    c.part("wire_guard", gd, explode=(0, 0.75, 0), desc="Black wire guard on the greenhouse side; the motor bolts to its centre.")
    sh = MB()
    fw, fd = B, 0.07
    for s_ in (-1, 1):
        sh.box((0.025, fd, fw), "pvc_white", loc=(s_ * (fw / 2 - 0.0125), -fd / 2 - 0.004, 0))
        sh.box((fw, fd, 0.025), "pvc_white", loc=(0, -fd / 2 - 0.004, s_ * (fw / 2 - 0.0125)))
    n_l = 8
    for k in range(n_l):                     # louvres hang from pivots; drawn open (fan running)
        z = fw / 2 - 0.035 - k * (fw - 0.05) / n_l
        sh.box((fw - 0.05, 0.078, 0.0022), "pvc_white", bevel=0.0008,
               M=xform((0, -0.03, z)) @ xform(rot=(-55, 0, 0)) @ xform((0, -0.039, 0)))
        sh.cyl(0.003, fw - 0.05, "stainless", segs=8, axis="X", loc=(0, -0.03, z))
    c.part("gravity_shutter", sh, explode=(0, -0.45, 0),
           desc="Outside gravity shutter: 8 plastic louvres. Air pushes them open; they fall shut when the fan stops.")
    return c


# ─────────────────────────────── cooling pad wall ───────────────────────────────
def cooling_pad(cid="cooling_pad", title="Evaporative cooling pad (wet wall)", width=1.8, height=1.5):
    c = Component(
        cid, title, "Climate",
        summary="Fresh air is sucked through a wet cellulose honeycomb and cooled by evaporation (6–10 °C in dry weather).",
        how=("A small pump lifts water to a perforated pipe on top; it trickles down the 150 mm cross-fluted cellulose "
             "pad. The exhaust fans pull outside air through the wet pad; evaporation takes heat from the air. Works best "
             "in dry air (Indian summer). Excess water returns to the sump. Pad pump runs only when fans run (PLC "
             "interlock) and above a set temperature."),
        sensors=("sump level float", "pad water-flow switch", "air T/RH before/after pad"),
        control="PLC relay; interlocked with fans; AI decides stage by forecast + VPD limits (don't over-humidify).",
        state={"pump_on": True, "cooling_delta_c": 7.5, "sump_level": "ok"},
        real="Munters CELdek 7090-15 (150 mm) cellulose pad, aluminium frame, Kirloskar Chhotu 0.5 HP pad pump",
        cost="≈₹17k (pad ₹140–150/sq ft, pump ₹4.2k)")
    nblk = max(1, round(width / 0.6))
    bw = width / nblk
    pd = MB()
    for k in range(nblk):
        x = -width / 2 + bw * (k + 0.5)
        pd.box((bw - 0.006, 0.15, height), "pad", bevel=0.004, loc=(x, 0, height / 2))
    c.part("pad_blocks", pd, loc=(0, 0, 0.18), explode=(0, -0.45, 0), desc="Cross-fluted cellulose pads (150 mm).")
    fr = MB()
    fr.box((width + 0.04, 0.2, 0.03), "alu", loc=(0, 0, 0.165))
    for sx in (-1, 1):
        fr.box((0.03, 0.2, height + 0.25), "alu", loc=(sx * (width / 2 + 0.02), 0, 0.18 + height / 2 + 0.1))
    fr.box((width + 0.04, 0.2, 0.012), "alu", loc=(0, 0, height + 0.19))
    c.part("frame", fr, desc="Aluminium frame.")
    ds = MB()
    ds.cyl(0.02, width, "pvc_grey", segs=20, axis="X")
    for k in range(int(width / 0.05)):
        ds.cyl(0.0025, 0.004, "chip", segs=8, loc=(-width / 2 + 0.025 + k * 0.05, 0, -0.019))
    ds.add(bm_lathe([(0.05, -width / 2 - 0.02), (0.05, width / 2 + 0.02)], 16, arc=math.pi, phase=0), "alu",
           M=xform(rot=(0, 90, 0)))
    c.part("water_distributor", ds, loc=(0, 0, height + 0.24), explode=(0, 0, 0.35),
           desc="Perforated distribution pipe + cover: spreads water evenly over the pad top.")
    gt = MB()
    prof = [(-0.12, 0.08), (-0.12, 0.0), (0.12, 0.0), (0.12, 0.08), (0.11, 0.08), (0.11, 0.01), (-0.11, 0.01),
            (-0.11, 0.08)]
    gt.prism(prof, width + 0.04, "pvc_grey", z0=-(width + 0.04) / 2, M=xform(rot=(0, 90, 0)) @ xform(rot=(0, 0, 90)))
    gt.cyl(0.02, 0.1, "pvc_grey", segs=20, loc=(width / 2 - 0.05, 0, -0.05))
    c.part("gutter", gt, loc=(0, 0, 0.08), explode=(0, -0.2, -0.2), desc="Return gutter – excess water flows back to the sump.")
    sm = MB()
    sm.box((0.62, 0.36, 0.35), "tank_black", bevel=0.02, loc=(-0.06, 0, 0.175))
    sm.cyl(0.013, 0.3, "pvc_grey", segs=16, z0=0.04, loc=(0.03, 0, 0))                     # suction pipe into the sump
    c.part("sump_tank", sm, loc=(width / 2 + 0.35, -0.2, 0.0), explode=(0.4, -0.3, 0), desc="~75 L sump tank with float valve.")
    pp = MB()
    kirloskar_chhotu(pp)
    c.part("pad_pump", pp, loc=(width / 2 + 0.35 - 0.09, -0.2, 0.35), explode=(0.5, -0.5, 0.45),
           desc="Kirloskar Chhotu 0.5 HP monoblock pump on the sump lid: lifts water to the top of the pad.")
    sp = MB()
    pvc_run(sp, [(width / 2 + 0.35, -0.2, 0.56), (width / 2 + 0.35, -0.2, height + 0.24),
                 (width / 2 + 0.02, 0.0, height + 0.24)], 0.02)
    c.part("riser_pipe", sp, explode=(0.4, -0.3, 0.2), desc="Riser pipe from pump to distributor.")
    return c


# ─────────────────────────────── HAF fan ───────────────────────────────
def haf_fan(cid="haf_fan", title="Air-circulation fan (Multifan greenhouse fan)"):
    """Vostermans Multifan greenhouse circulation fan, 45 cm: white octagonal housing, 3 blades, white guard,
    front motor. Airflow along +X."""
    c = Component(
        cid, title, "Climate",
        summary="Keeps air gently moving along the rows: even temperature, drier leaf surfaces, less fungus.",
        how=("Hung above the crop, two fans push air in a slow loop around the house (~0.5 m/s at the leaves). Moving "
             "air breaks the still, humid layer around each leaf, so leaves dry faster and Botrytis and leaf mould get "
             "fewer wet hours. One 45 cm Multifan moves ~5,000 m³/h for about 110 W."),
        sensors=("temperature spread between the two climate boxes",),
        control="PLC relay; runs most of the day, harder at night and when humid.",
        state={"running": True, "airflow_m3h": 5000},
        real="Vostermans Multifan greenhouse circulation fan, 45 cm, ~5,000 m³/h, IP55 motor",
        cost="≈₹18k (import) · Indian 80 W fan ≈₹9.7k")
    RX = xform(rot=(0, 90, 0))              # build around Z, then Z → +X (airflow)
    R, D = 0.232, 0.30
    hs = MB()
    oc = octagon(0.56, 0.11)
    polygon_plate_with_hole(hs, "plastic_white", oc, R + 0.004, 0.004, M=RX @ xform((0, 0, -0.004)))
    polygon_plate_with_hole(hs, "plastic_white", oc, R + 0.004, 0.004, M=RX @ xform((0, 0, -D)))
    for i in range(8):                        # octagon side walls
        (x0, y0), (x1, y1) = oc[i], oc[(i + 1) % 8]
        L_ = math.hypot(x1 - x0, y1 - y0)
        hs.box((L_, 0.004, D), "plastic_white", M=RX @ xform(((x0 + x1) / 2, (y0 + y1) / 2, -D / 2),
                                                             (0, 0, math.degrees(math.atan2(y1 - y0, x1 - x0)))))
    hs.tube(R + 0.004, R, D, "plastic_white", segs=72, z0=-D, M=RX)
    hs.add(bm_lathe([(R, 0.0), (R + 0.004, 0.0), (R + 0.03, 0.03), (R + 0.052, 0.036), (R + 0.052, 0.04),
                     (R + 0.026, 0.035), (R, 0.004)], 72, closed=True), "plastic_white", M=RX)
    for k in range(6):                        # screw bosses on the front ring
        a = TAU * k / 6 + TAU / 12
        p = ((R + 0.04) * math.cos(a), (R + 0.04) * math.sin(a))
        hs.cyl(0.009, 0.012, "plastic_white", segs=16, M=RX @ xform((p[0], p[1], 0.03)))
        hs.cyl(0.004, 0.003, "stainless", segs=6, M=RX @ xform((p[0], p[1], 0.037)))
    c.part("housing", hs, desc="White glass-fibre-reinforced octagonal housing with a short duct and bell-mouth front ring.")
    bl = MB()
    axial_blades(bl, "plastic_dark", 3, 0.05, 0.224, chord=(0.1, 0.19), pitch=(30, 17), sweep=20, camber=0.06,
                 thick=0.004, M=RX)
    bl.cyl(0.055, 0.06, "plastic_dark", segs=40, bevel=0.008, M=RX)
    c.part("impeller", bl, loc=(-0.07, 0, 0), explode=(0.18, 0, 0.35), desc="3-blade 45 cm impeller.")
    mo = MB()
    mo.lathe([(0.0, 0.0), (0.056, 0.0), (0.06, 0.01), (0.06, 0.11), (0.052, 0.125), (0.0, 0.125)], "plastic_white",
             segs=48, M=RX)
    mo.text("Multifan", 0.011, "plastic_black", depth=0.0005, bold=True,
            M=RX @ xform((0, 0, 0.1255)) @ xform(rot=(0, 0, 90)))
    mo.cyl(0.006, 0.012, "plastic_red", segs=12, M=RX @ xform((0.045, 0.0, 0.1)) @ xform(rot=(90, 0, 0)))
    c.part("motor", mo, loc=(-0.05, 0, 0), explode=(0.42, 0, 0),
           desc="External-rotor motor (IP55) mounted in front, in the guard.")
    gd = MB()
    G = 0.105
    for k in range(1, 10):
        gd.torus(0.029 * k, 0.0018, "plastic_white", segs=64, rsegs=6, M=RX @ xform((0, 0, G)))
    for k in range(12):
        a = 360 * k / 12
        gd.box((0.2, 0.003, 0.003), "plastic_white",
               M=RX @ xform((0, 0, G)) @ xform(rot=(0, 0, a)) @ xform((0.16, 0, 0)))
    for k in range(4):                         # the 4 heavy struts that carry the motor
        a = math.radians(45 + 90 * k)
        gd.sweep([(0.06 * math.cos(a), 0.06 * math.sin(a), G), (0.26 * math.cos(a), 0.26 * math.sin(a), G),
                  ((R + 0.04) * math.cos(a), (R + 0.04) * math.sin(a), 0.035)], 0.004, "plastic_white", segs=8, M=RX)
    c.part("front_guard", gd, explode=(0.6, 0, 0), desc="White wire guard; its four struts carry the motor.")
    hg = MB()
    hg.box((0.2, 0.06, 0.03), "plastic_white", bevel=0.006, loc=(-0.15, 0, 0.28 + 0.015))
    for sx in (-1, 1):
        hg.torus(0.012, 0.003, "stainless", segs=16, rsegs=6, axis="Y", loc=(-0.15 + sx * 0.07, 0, 0.318))
        hg.sweep([(-0.15 + sx * 0.07, 0, 0.33), (-0.15 + sx * 0.07, 0, 0.85)], 0.0028, "stainless", segs=6)
    c.part("hanger", hg, explode=(0, 0, 0.3), desc="Top bracket with two eye bolts; chains to the roof truss.")
    return c


# ─────────────────────────────── ridge vent drive ───────────────────────────────
def vent_drive(cid="vent_drive", title="Ridge-vent rack-and-pinion drive", L=1.6, pinions=(0.3,), open_deg=20,
               with_window=True):
    c = Component(
        cid, title, "Climate",
        summary="Opens and closes the roof vent in steps (0–100 %) for natural ventilation.",
        how=("A geared motor turns a long drive shaft along the ridge. At every truss a pinion gear on the shaft pushes "
             "a curved rack, which lifts the vent window around its ridge hinge. Cam limit switches stop the motor at "
             "fully open / closed. Wind and rain from the weather station close it for storms (hard limit in PLC)."),
        sensors=("position encoder / limit switches", "wind speed", "rain sensor"),
        control="PLC (open/close relays with interlock so both can never be on). AI sends a % target.",
        state={"position_pct": 35, "moving": False},
        real="MAXPOWER MP-series 370 W greenhouse gearmotor (2.6 rpm) with limit-switch box, 1\" torque tube, curved racks",
        cost="≈₹32k landed (import)")
    RH = 0.8                      # hinge → free-edge distance (vent window depth)
    hinge = (0.0, 0.0, 0.8)       # ridge hinge line (y, z) in the drive's local frame
    ang = lambda a: (hinge[1] + RH * math.cos(math.radians(a)), hinge[2] + RH * math.sin(math.radians(a)))
    pin_y, pin_z = ang(-45)       # pinion sits on the rack arc, below the window
    g2 = MB()
    g2.box((0.16, 0.14, 0.18), "ral7035", bevel=0.012)
    g2.lathe([(0.0, 0.08), (0.055, 0.08), (0.06, 0.09), (0.06, 0.3), (0.05, 0.31), (0.0, 0.31)], "ral7035",
             segs=40, axis="-Y")
    for k in range(14):
        a = TAU * k / 14
        g2.box((0.0025, 0.2, 0.01), "ral7035", loc=(0.064 * math.cos(a), -0.2, 0.064 * math.sin(a)),
               rot=(0, -math.degrees(a) + 90, 0))
    g2.box((0.07, 0.06, 0.05), "ral7035", bevel=0.004, loc=(0, -0.2, 0.085))
    c.part("gearmotor", g2, loc=(-L / 2 - 0.1, pin_y, pin_z), explode=(-0.35, 0, 0),
           desc="Motor + worm gearbox (self-locking – wind can't push the vent open).")
    ls = MB()
    ls.box((0.1, 0.07, 0.09), "plastic_dark", bevel=0.006)
    ls.cyl(0.006, 0.01, "plastic_black", segs=6, z0=-0.055, loc=(0.02, 0, 0))
    c.part("limit_switch_box", ls, loc=(-L / 2 - 0.1, pin_y + 0.11, pin_z + 0.02), explode=(-0.35, 0.25, 0.15),
           desc="Cam limit switches (open/closed end stops).")
    sh = MB()
    sh.cyl(0.0167, L + 0.1, "galv", segs=20, axis="X")
    c.part("drive_shaft", sh, loc=(0, pin_y, pin_z), explode=(0, 0, -0.2), desc="1\" galvanised torque tube along the ridge.")
    a0 = int(round(-26 + open_deg))
    pb = MB()
    rk = MB()
    for px in pinions:
        M = xform((px, pin_y, pin_z))
        pb.add(__import__("gh").bm_box(0.12, 0.09, 0.12, 0.006), "galv", M=M)
        pb.add(__import__("gh").bm_cyl(0.045, 0.03, 18), "steel_dark", M=M @ xform(rot=(0, 90, 0)))
        for k in range(18):
            a = TAU * k / 18
            pb.add(__import__("gh").bm_box(0.03, 0.008, 0.01), "steel_dark",
                   M=M @ xform((0, 0.048 * math.cos(a), 0.048 * math.sin(a)), (math.degrees(a), 0, 0)))
        pb.add(__import__("gh").bm_box(0.06, 0.05, 0.25), "galv", M=M @ xform((0, 0, -0.18)))
        pts = [(px, *ang(a)) for a in range(a0, -71, -2)]
        rk.sweep(pts, 0.012, "galv", segs=8, flat=(0.025, 0.03))
        for a in range(a0 - 2, -70, -3):
            y, z = hinge[1] + (RH - 0.018) * math.cos(math.radians(a)), hinge[2] + (RH - 0.018) * math.sin(math.radians(a))
            rk.box((0.022, 0.008, 0.01), "galv", loc=(px, y, z), rot=(a, 0, 0))
    c.part("pinion_boxes", pb, explode=(0, 0.25, -0.15), desc="Pinion gear + bearing box at each truss.")
    c.part("curved_racks", rk, explode=(0, 0.3, 0.3),
           desc="Curved racks (centre = the ridge hinge) – the pinions push them up, lifting the vent window.")
    if not with_window:
        return c
    vw = MB()
    wa = math.radians(a0)
    for d in (0.0, RH):   # hinge side + free edge beams
        vw.box((L, 0.04, 0.03), "alu", loc=(0, d, 0))
    for x in (-L / 2, 0.0, L / 2):
        vw.box((0.03, RH, 0.03), "alu", loc=(x, RH / 2, 0))
    vw.box((L, RH, 0.004), "polycarb", loc=(0, RH / 2, 0.012))
    c.part("vent_window", vw, loc=(0, hinge[1], hinge[2]), rot=(math.degrees(wa), 0, 0), explode=(0, 0, 0.45),
           desc="Vent window (polycarbonate in aluminium frame), hinged at the ridge.")
    rg = MB()
    rg.box((L + 0.2, 0.06, 0.08), "galv", loc=(0, -0.02, 0.02))
    rg.cyl(0.012, L + 0.2, "alu", segs=16, axis="X", loc=(0, 0.0, 0.0))
    c.part("ridge_beam_hinge", rg, loc=(0, hinge[1], hinge[2]), explode=(0, -0.2, 0.2), desc="Ridge beam + hinge profile.")
    return c


# ─────────────────────────────── fog nozzle + fog pump ───────────────────────────────
def fog_nozzle(cid="fog_nozzle", title="Fogger (Netafim CoolNet Pro 4-way)"):
    """Netafim CoolNet Pro 4-way fogger hanging on 30 cm of white PE tube below the 16 mm fog line.
    Sizes from product photos: LPD sphere about 24 mm, cross span about 70 mm."""
    c = Component(
        cid, title, "Climate",
        summary="Sprays fine fog (~65 µm droplets) to cool the air and raise humidity without soaking the leaves.",
        how=("Water at 4 bar reaches four nozzles; each one swirls it and breaks it into droplets small enough to "
             "evaporate before they land. Evaporation takes heat out of the air (cooling) and adds humidity (lower VPD). "
             "The anti-leak valve (LPD) above the nozzles only opens above ~2 bar and snaps shut when the valve closes, "
             "so the line does not drip on the plants. 4 nozzles × 7.5 L/h = 30 L/h per fogger; 6 foggers cover this house."),
        sensors=("air RH / temperature (VPD)", "fog-line pressure gauge"),
        control="Fog valve via PLC; AI asks for a VPD target, PLC runs short pulses with an RH limit (max 85 %).",
        state={"spraying": False, "pressure_bar": 0, "flow_l_h": 30},
        real="Netafim CoolNet Pro 4-way fogger + LPD anti-leak valve + 30 cm hanger", cost="₹250–400 each")
    ln = MB()
    ln.cyl(0.008, 0.14, "pe_black", segs=24, axis="X")
    ln.cyl(0.0035, 0.018, "plastic_black", segs=12, z0=-0.018)          # barbed hanger connector
    c.part("fog_line_tap", ln, desc="16 mm PE fog line with a barbed hanger connector.")
    hg = MB()
    hg.cyl(0.0025, 0.29, "plastic_white", segs=10, z0=-0.30)
    hg.cyl(0.0085, 0.032, "steel_dark", segs=16, bevel=0.002, z0=-0.26)   # stabilising weight
    c.part("hanger_tube", hg, desc="30 cm white PE hanger tube with a weight so the fogger hangs straight.")
    lp = MB()
    lp.cyl(0.004, 0.018, "pvc_white", segs=16, z0=-0.018)
    lp.sphere(0.012, "pvc_white", segs=24, rings=12, loc=(0, 0, -0.03))
    lp.cyl(0.0022, 0.002, "plastic_purple", segs=12, M=xform((0, -0.0119, -0.03)) @ xform(rot=(90, 0, 0)))
    lp.cyl(0.0065, 0.014, "pvc_white", segs=16, z0=-0.055)
    c.part("anti_leak_valve", lp, loc=(0, 0, -0.30), explode=(0, 0, 0.04),
           desc="LPD anti-leak valve (purple pin = CoolNet Pro): stays shut below ~2 bar, so no drips between pulses.")
    cr = MB()
    cr.cyl(0.009, 0.016, "pvc_white", segs=20, z0=-0.008)
    for k in range(4):
        M = xform(rot=(0, 0, 90 * k + 45))
        cr.cyl(0.0045, 0.028, "pvc_white", segs=14, axis="X", M=M @ xform((0.018, 0, 0)))
        cr.cyl(0.0078, 0.006, "pvc_white", segs=16, axis="X", M=M @ xform((0.029, 0, 0)))
    c.part("cross_hub", cr, loc=(0, 0, -0.365), explode=(0, 0, -0.03), desc="4-way cross that splits the flow to the nozzles.")
    nz = c.group("nozzles", explode=(0, 0, -0.06), desc="4 swirl nozzles.")
    for k in range(4):
        a = math.radians(90 * k + 45)
        m_ = MB()
        m_.cyl(0.0068, 0.012, "pvc_white", segs=16, axis="X", loc=(0.006, 0, 0))
        m_.cyl(0.0042, 0.004, "plastic_black", segs=14, axis="X", loc=(0.0135, 0, 0))
        m_.cyl(0.0006, 0.0008, "chip", segs=8, axis="X", loc=(0.0158, 0, 0))
        c.part(f"nozzle_{k + 1}", m_, parent=nz, loc=(0.032 * math.cos(a), 0.032 * math.sin(a), -0.365),
               rot=(0, 0, math.degrees(a)), explode=(0.03 * math.cos(a), 0.03 * math.sin(a), 0),
               desc="Swirl nozzle, 7.5 L/h at 4 bar.")
    return c


def fog_pump(cid="fog_pump", title="Fog valve station (valve + filter + 4 bar regulator)"):
    """Replaces the old 70-bar fog pump: the main pump feeds the fog line through its own valve, filter and a
    pressure regulator, on a small wall board. +X = along the wall, +Y = into the house."""
    c = Component(
        cid, title, "Climate",
        summary="Lets water from the main pump into the fog line at a steady 4 bar, only when the PLC opens it.",
        how=("CoolNet foggers need clean water at 4 bar. The main Grundfos pump makes a little more than that, so the "
             "fog branch has its own 120-mesh disc filter, a Senninger regulator fixed at 4.1 bar (60 psi), a 24 V AC "
             "solenoid valve and a gauge. The PLC interlock never opens the fog valve during a watering shot."),
        sensors=("pressure gauge (manual check)", "shares the main pressure transmitter"),
        control="PLC relay (24 V AC coil); max pulse length and RH limit enforced in the PLC.",
        state={"open": False, "pressure_bar": 0.0},
        real="Rain Bird 100-HV 1\" valve + Azud 3/4\" disc filter + Senninger PRLG-60 regulator + 63 mm gauge",
        cost="≈₹7k", view=(205, 16))
    bd = MB()
    bd.box((0.5, 0.012, 0.5), "pvc_white", loc=(0, -0.006, 0.55))
    for sx in (-1, 1):
        bd.box((0.03, 0.03, 0.9), "galv", loc=(sx * 0.27, -0.02, 0.45))
    c.part("board", bd, desc="Mounting board on galvanised posts.")
    pp = MB()
    pvc_run(pp, [(-0.35, 0.05, 0.36), (-0.2, 0.05, 0.36), (0.18, 0.05, 0.36), (0.18, 0.05, 0.9), (0.18, 0.05, 1.3)],
            0.0133, m="pvc_grey")
    c.part("fog_riser", pp, desc="3/4\" PVC branch from the main pump, rising to the fog line.")
    fv = MB()   # Rain Bird 100-HV style valve, simplified
    fv.cyl(0.02, 0.1, "plastic_black", segs=32, axis="X")
    fv.lathe([(0.0, 0.0), (0.042, 0.0), (0.044, 0.02), (0.03, 0.035), (0.0, 0.037)], "plastic_black", segs=40,
             loc=(0, 0, 0.012))
    fv.cyl(0.013, 0.035, "plastic_black", segs=24, z0=0.0, loc=(0.03, 0, 0.03))
    cable(fv, [(0.03, 0.0, 0.065), (0.05, 0.0, 0.1), (0.12, 0.0, 0.14)], r=0.002, m="wire_black")
    c.part("fog_valve", fv, loc=(-0.12, 0.05, 0.36), explode=(0, 0.12, 0.08), desc="Rain Bird 100-HV solenoid valve, 24 V AC.")
    ft = MB()
    ft.cyl(0.035, 0.1, "plastic_black", segs=32, z0=-0.1)
    ft.cyl(0.03, 0.06, "plastic_red", segs=32, z0=-0.085)
    ft.cyl(0.016, 0.08, "plastic_black", segs=24, axis="X")
    c.part("disc_filter", ft, loc=(0.05, 0.05, 0.36), explode=(0, 0.14, -0.1), desc="3/4\" disc filter, 120 mesh (red discs).")
    rg = MB()
    rg.cyl(0.03, 0.09, "plastic_dark", segs=32, bevel=0.004)
    rg.text("60 PSI", 0.012, "sticker_white", depth=0.0005, bold=True, loc=(0, 0.0305, 0.0), rot=(-90, 0, 180))
    c.part("pressure_regulator", rg, loc=(0.18, 0.05, 0.62), explode=(0.12, 0.12, 0),
           desc="Senninger PRLG-60: holds the fog line at 4.1 bar.")
    gg = MB()
    gg.cyl(0.0315, 0.03, "stainless", segs=40, axis="Y", loc=(0, 0.03, 0))
    dial(gg, 0.028, (0, 0.046, 0), "Y")
    gg.cyl(0.005, 0.03, "brass", segs=12, z0=-0.045)
    c.part("gauge", gg, loc=(0.18, 0.05, 0.82), explode=(0.12, 0.14, 0.05), desc="0–10 bar glycerine gauge.")
    return c
