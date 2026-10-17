"""Farm v4 (11 Oct 2026): the scale-up. GH-01 (45 m²) proves the control system; GH-02 is the house a Kolar farmer
would actually build with it: a 1,024 m² naturally ventilated polyhouse (4 spans × 8 m × 32 m, gothic arches with roof
vents, 40-mesh insect-net sides with roll-up curtains), the type Karnataka subsidises under MIDH / NHB. Plus the drone
that inspects the roofs after storms.

World frame as the greenhouse: x = north, y = west, z = up (metres). GH-02 sits north of GH-01: x 13…45, y −16…16.
"""
import math

from gh import MB, Component
from parts import cable, pvc_run

X0, X1 = 13.0, 45.0                    # GH-02 length along x (32 m)
Y0, SPANS, SPAN = -16.0, 4, 8.0        # 4 spans of 8 m → y −16…16
GUTTER, RISE = 4.5, 2.0                # gutter height, arch rise (top ≈ 6.5 m)
BAY = 4.0                              # column / arch spacing along x
ROW_PITCH = 1.6                        # crop rows (double rows of plants on coco slabs)
DOCK = (10.2, 14.2)                    # drone dock, west of GH-02's front


def arch_pts(y0, n=12, side=0):
    """Points (y, z) of one span's gothic arch: two circular arcs from the gutters meeting at the ridge, with the ridge
    0.35 m off-centre (the vent side). side 0 = full arch, 1 = first half, 2 = second half."""
    yr = y0 + SPAN / 2 + 0.35
    pts = []
    for half, (ya, yb) in enumerate(((y0, yr), (y0 + SPAN, yr))):
        seg = []
        for k in range(n + 1):
            u = k / n
            y = ya + (yb - ya) * u
            z = GUTTER + RISE * math.sin(u * math.pi / 2) ** 0.85
            seg.append((y, z))
        pts.append(seg)
    if side == 1:
        return pts[0]
    if side == 2:
        return pts[1]
    return pts[0] + list(reversed(pts[1]))[1:]


def _film_strip(mb, pts, m, x0, x1, lift=0.0):
    """Cover a (y, z) polyline with thin boxes running along x: a film or net surface following the arch."""
    for (ya, za), (yb, zb) in zip(pts[:-1], pts[1:]):
        dy, dz = yb - ya, zb - za
        ln = math.hypot(dy, dz)
        ang = math.degrees(math.atan2(dz, dy))
        mb.box((x1 - x0, ln + 0.01, 0.008), m, loc=((x0 + x1) / 2, (ya + yb) / 2, (za + zb) / 2 + lift), rot=(ang, 0, 0))


def gh02(cid="gh02", title="GH-02 · 1,024 m² naturally ventilated polyhouse (4 × 8 m spans, 32 m long)"):
    c = Component(
        cid, title, "Structure",
        summary=("The scale-up: the same brain as GH-01 running a house a farmer would really build. 1,024 m², about "
                 "2,500 tomato plants on coco slabs, roof vents and insect-net sides instead of fans and pads."),
        how=("Gothic-arch GI tube frame (76 mm columns every 4 m, 4.5 m gutters, ~6.5 m ridges), 200 µm UV film roof with a "
             "1 m top vent on each span, 40-mesh insect net on all sides behind roll-up film curtains. Naturally ventilated "
             "houses are what Karnataka subsidises most (NHB / MIDH norm ≈ ₹1,060/m², 50 % assistance); fan-pad houses "
             "cost more to build and run. The roof's 1,024 m² also catches ~750 m³ of rain a year for the farm pond."),
        sensors=("2 climate boxes", "vent position", "curtain position", "rain sensor", "wind (weather station)"),
        control="Same AI + safety PLC as GH-01: vents and curtains instead of fans and pad.",
        state={"area_m2": 1024, "plants": 2500, "vents_pct": 35, "curtains": "half open"})
    fr = MB()                                                          # frame: columns, gutters, arches, purlins
    xs = [X0 + BAY * k for k in range(int((X1 - X0) / BAY) + 1)]
    for i in range(SPANS + 1):
        y = Y0 + SPAN * i
        for x in xs:
            fr.box((0.076, 0.076, GUTTER), "galv", loc=(x, y, GUTTER / 2))
            fr.box((0.4, 0.4, 0.3), "concrete", loc=(x, y, 0.0))
        fr.box((X1 - X0, 0.22, 0.12), "galv", loc=((X0 + X1) / 2, y, GUTTER + 0.04))
    for s in range(SPANS):
        y0 = Y0 + SPAN * s
        pts = arch_pts(y0)
        for x in xs:
            fr.sweep([(x, py, pz) for py, pz in pts], 0.024, "galv", segs=10)
        yr = y0 + SPAN / 2 + 0.35
        for yy in (y0 + 2.0, yr, y0 + SPAN - 2.0):                      # purlins along x
            z = GUTTER + RISE * (0.93 if yy == yr else 0.8)
            fr.box((X1 - X0, 0.03, 0.03), "galv", loc=((X0 + X1) / 2, yy, z))
        for x in xs:                                                    # truss tie at gutter height
            fr.box((0.03, SPAN, 0.03), "galv", loc=(x, y0 + SPAN / 2, GUTTER - 0.15))
    c.part("frame", fr, desc="GI frame: 76 mm columns every 4 m on concrete footings, gutters, gothic arches, purlins, ties.")
    rf = MB()                                                          # roof film; the vent strip is open, a flap rides above it
    for s in range(SPANS):
        y0 = Y0 + SPAN * s
        a, b = arch_pts(y0, side=1), arch_pts(y0, side=2)
        _film_strip(rf, a[:-1], "uv_film", X0, X1)
        _film_strip(rf, b, "uv_film", X0, X1)
    c.part("film_roof", rf, explode=(0, 0, 2.0), desc="200 µm UV-stabilised 5-layer film, clamped in lock channels on every arch.")
    vn = MB()
    for s in range(SPANS):
        y0 = Y0 + SPAN * s
        a = arch_pts(y0, side=1)
        _film_strip(vn, a[-3:], "net", X0, X1, lift=-0.02)              # insect net under the vent
        _film_strip(vn, a[-4:], "uv_film", X0, X1, lift=0.42)           # the vent flap, raised 35 % open
        vn.box((X1 - X0, 0.05, 0.05), "galv", loc=((X0 + X1) / 2, a[-1][0], a[-1][1] + 0.05))
    c.part("roof_vents", vn, explode=(0, 0, 1.0), desc="1 m roof vent on each span (insect net + film flap on a rack-and-pinion drive).")
    wl = MB()                                                          # side walls: net + roll-up curtains; end walls: film
    for y in (Y0, Y0 + SPAN * SPANS):
        wl.box((X1 - X0, 0.01, GUTTER - 0.4), "net", loc=((X0 + X1) / 2, y, 0.4 + (GUTTER - 0.4) / 2))
        wl.box((X1 - X0, 0.012, 0.4), "uv_film", loc=((X0 + X1) / 2, y, 0.2))
        wl.cyl(0.07, X1 - X0, "uv_film", segs=14, axis="X", loc=((X0 + X1) / 2, y, 1.9))   # curtain rolled up to 1.9 m
    for x in (X0, X1):
        wl.box((0.01, SPAN * SPANS, GUTTER - 0.4), "net", loc=(x, 0.0, 0.4 + (GUTTER - 0.4) / 2))
        wl.box((0.012, SPAN * SPANS, 0.4), "uv_film", loc=(x, 0.0, 0.2))
        for s in range(SPANS):                                          # gable infill under each arch
            for (ya, za), (yb, zb) in zip(arch_pts(Y0 + SPAN * s)[:-1], arch_pts(Y0 + SPAN * s)[1:]):
                h = (za + zb) / 2 - GUTTER
                wl.box((0.01, abs(yb - ya) + 0.01, h), "uv_film", loc=(x, (ya + yb) / 2, GUTTER + h / 2))
    c.part("walls", wl, desc="40-mesh insect net on all sides, 0.4 m film skirt, roll-up film curtains (shown rolled to 1.9 m).")
    en = MB()                                                          # entry room at the front, in the middle span joint
    ex, ey = X0 - 1.6, 0.0
    for dx in (0, 1.6):
        for dy in (-1.2, 1.2):
            en.box((0.05, 0.05, 2.6), "galv", loc=(ex + dx, ey + dy, 1.3))
    en.box((1.6, 2.4, 0.01), "uv_film", loc=(ex + 0.8, ey, 2.6))
    for dy in (-1.2, 1.2):
        en.box((1.6, 0.01, 2.6), "net", loc=(ex + 0.8, ey + dy, 1.3))
    en.box((0.01, 1.0, 2.1), "plastic_white", loc=(ex, ey, 1.05))
    en.box((1.4, 2.2, 0.06), "disinfectant", loc=(ex + 0.8, ey, 0.03))
    c.part("entry_room", en, explode=(-0.8, 0, 0), desc="Double-door insect-net entry room with footbath.")
    rw = MB()                                                          # crop rows: gutters on stands + white slab line
    rows = []
    for s in range(SPANS):
        y0 = Y0 + SPAN * s
        for r in range(5):
            y = y0 + 0.8 + ROW_PITCH * r
            rows.append(y)
            rw.box((X1 - X0 - 3.0, 0.3, 0.05), "galv", loc=((X0 + X1) / 2 + 0.5, y, 0.45))
            rw.box((X1 - X0 - 3.2, 0.2, 0.08), "slab_film", loc=((X0 + X1) / 2 + 0.5, y, 0.51))
        for xk in range(int(X0) + 2, int(X1), 4):
            rw.box((0.03, SPAN, 0.03), "galv", loc=(xk + 0.5, y0 + SPAN / 2, 3.8))      # crop wire support bars
    c.part("crop_rows", rw, desc="20 rows × 29 m of hanging gutters + coco slabs (≈2,500 plants at 2.5 per m²).")
    rh = MB()                                                          # rain harvest: downpipes at the front → pond
    for i in range(SPANS + 1):
        y = Y0 + SPAN * i
        pvc_run(rh, [(X0 - 0.15, y, GUTTER), (X0 - 0.15, y, 0.15), (X0 - 0.6, y, 0.15)], 0.055, m="pvc_white")
    pvc_run(rh, [(X0 - 0.6, Y0 + SPAN * SPANS, 0.15), (X0 - 0.6, Y0, 0.15), (X0 - 0.6, -10.5, 0.15), (9.4, -10.5, 0.15)], 0.08,
            m="pvc_white")
    c.part("rain_harvest", rh, desc="5 downpipes + 160 mm collector to the farm pond (≈750 m³ a year off 1,024 m² of roof).")
    c.rows = rows
    return c


def drone_dock(cid="drone_dock", title="Drone dock (auto-charging, weatherproof)"):
    c = Component(
        cid, title, "Robot",
        summary="Home of the inspection drone: it charges here, and flies a roof and perimeter survey after every storm.",
        how=("A weatherproof dock with a sliding roof and charging contacts (DJI Dock-class). After the weather station "
             "logs a storm (rain + gusts), the twin waits for the wind to drop below 8 m/s, then sends the drone over both "
             "roofs: the camera looks for torn film, flapping curtains and blocked gutters, and the photos go to the farmer."),
        sensors=("dock weather station", "drone battery", "camera"), control="Twin schedules flights; the drone has its own geofence.",
        state={"battery_pct": 100, "last_flight": "—"})
    dx, dy = DOCK
    m = MB()
    m.box((1.4, 1.4, 0.1), "concrete", loc=(dx, dy, 0.05))
    m.box((1.0, 1.0, 0.55), "plastic_white", bevel=0.03, loc=(dx, dy, 0.375))
    m.box((0.86, 0.86, 0.01), "anthracite", loc=(dx, dy, 0.655))
    m.box((0.5, 0.06, 0.003), "plastic_yellow", loc=(dx, dy, 0.661))
    m.box((0.06, 0.5, 0.003), "plastic_yellow", loc=(dx, dy, 0.661))
    for sy in (-1, 1):                                                 # roof halves slid open
        m.box((1.02, 0.5, 0.06), "plastic_white", bevel=0.02, loc=(dx, dy + sy * 0.78, 0.7))
    m.cyl(0.02, 1.2, "galv", segs=10, z0=0.1, loc=(dx + 0.6, dy - 0.6, 0))
    m.box((0.12, 0.12, 0.08), "plastic_white", loc=(dx + 0.6, dy - 0.6, 1.33))
    c.part("dock", m, desc="Weatherproof dock: sliding roof, landing pad with charging contacts, its own small weather station.")
    return c


def drone(cid="drone", title="Inspection drone (enterprise quadcopter, 4K camera)"):
    c = Component(
        cid, title, "Robot",
        summary="Flies over both roofs after storms, so a torn film or a jammed vent is found the same day, not at the next walk.",
        how="A small enterprise quadcopter (~0.9 kg) with a zoom camera on a gimbal; it flies a lawn-mower pattern 10 m above the roofs.",
        sensors=("camera", "GNSS", "battery"), control="Mission from the twin; geofenced to the farm.", state={"battery_pct": 100})
    m = MB()
    m.box((0.2, 0.12, 0.06), "anthracite", bevel=0.015, loc=(0, 0, 0.0))
    for a in (45, 135, 225, 315):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        m.box((0.2, 0.025, 0.02), "anthracite", loc=(0.1 * ca, 0.1 * sa, 0.0), rot=(0, 0, a))
        m.cyl(0.018, 0.03, "plastic_dark", segs=14, z0=0.0, loc=(0.2 * ca, 0.2 * sa, 0))
        m.cyl(0.115, 0.004, "plastic_dark", segs=24, z0=0.032, loc=(0.2 * ca, 0.2 * sa, 0))
    m.sphere(0.035, "plastic_black", loc=(0.11, 0, -0.05))
    m.cyl(0.014, 0.01, "lens", segs=14, axis="X", loc=(0.145, 0, -0.05))
    for sy in (-1, 1):
        m.box((0.16, 0.012, 0.012), "plastic_dark", loc=(0, sy * 0.07, -0.07))
        m.box((0.012, 0.012, 0.07), "plastic_dark", loc=(0.05, sy * 0.07, -0.035))
        m.box((0.012, 0.012, 0.07), "plastic_dark", loc=(-0.05, sy * 0.07, -0.035))
    m.cyl(0.006, 0.004, "led_green", segs=10, loc=(-0.1, 0, 0.03))
    c.part("body", m, desc="Quadcopter: carbon arms, 4 motors + props, gimbal camera, landing skids.")
    return c
