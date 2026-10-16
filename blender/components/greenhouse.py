"""The greenhouse itself: structure + cladding, growing rows (gutter, slabs, drip line, crop wire), pipe rails,
main irrigation piping, fog line. World frame: x = length (0 front gable … 9 back gable), y = width (−2.5 … 2.5)."""
import math

from gh import MB, Component, bm_box, fillet_path, xform
from parts import pe_run, pvc_run

L, W, GH, RH = 9.0, 5.0, 3.0, 4.2      # length, width, gutter (eave) height, ridge height
BAY = 1.5
ROWS_Y = (-1.6, 0.0, 1.6)
AISLES_Y = (-0.8, 0.8)
ROW_X0, ROW_X1 = 2.25, 8.75
SLAB_X = [2.8 + 1.07 * i for i in range(6)]
GUTTER_Z = 0.5                          # gutter bottom; slab bottom sits here
SLAB_TOP = 0.58
CUBE_TOP = 0.645
WIRE_Z = 2.75
RAIL_GAUGE, PIPE_R, RAIL_Z = 0.55, 0.0255, 0.1   # pipe-rail centre height
VENT_DEPTH = 0.8
FAN_Y, FAN_Z = 1.6, 1.95                  # exhaust fan centres (front gable), at canopy height
FAN_HOLE = 0.30                           # half-size of the wall opening for a Multifan 4E50 (panel 647.5 mm)
FOG_Z = 3.35                              # 16 mm PE fog line height; foggers hang ~0.37 m below
FOG_X = (3.2, 5.6, 8.0)                   # 3 CoolNet Pro foggers per aisle (30 L/h each, ~8 m² per fogger)
PAD_W, PAD_H, PAD_Z = 2.4, 0.9, 0.3


def roof_z(y):
    return GH + (RH - GH) * (1 - abs(y) / (W / 2))


def rect_minus_holes(y0, y1, z0, z1, holes):
    """Split rectangle [y0,y1]×[z0,z1] minus rectangular holes into rectangles (vertical strips)."""
    ys = sorted({y0, y1} | {h[0] for h in holes if y0 < h[0] < y1} | {h[1] for h in holes if y0 < h[1] < y1})
    out = []
    for a, b in zip(ys[:-1], ys[1:]):
        m = (a + b) / 2
        cuts = sorted((max(h[2], z0), min(h[3], z1)) for h in holes if h[0] <= m <= h[1])
        z = z0
        for c0, c1 in cuts:
            if c0 > z:
                out.append((a, b, z, c0))
            z = max(z, c1)
        if z < z1:
            out.append((a, b, z, z1))
    return out


def gable_triangle(mb, x, m, thick=0.008):
    import bmesh
    bm = bmesh.new()
    pts = [(-W / 2, GH), (W / 2, GH), (0.0, RH)]
    lo = [bm.verts.new((x - thick / 2, y, z)) for y, z in pts]
    hi = [bm.verts.new((x + thick / 2, y, z)) for y, z in pts]
    bm.faces.new(lo)
    bm.faces.new(list(reversed(hi)))
    for i in range(3):
        j = (i + 1) % 3
        bm.faces.new((lo[i], hi[i], hi[j], lo[j]))
    mb.add(bm, m)


def roof_panel(mb, y_from, y_to, m, x0=0.0, x1=L, off=0.03):
    """A sloped roof panel between two y positions (same slope side)."""
    import bmesh
    bm = bmesh.new()
    za, zb = roof_z(y_from) + off, roof_z(y_to) + off
    v = [bm.verts.new(p) for p in ((x0, y_from, za), (x1, y_from, za), (x1, y_to, zb), (x0, y_to, zb))]
    bm.faces.new(v)
    mb.add(bm, m)


# ─────────────────────────────── structure ───────────────────────────────
def greenhouse_structure(cid="greenhouse_structure", title="Greenhouse structure (9 × 5 m, polycarbonate)"):
    c = Component(
        cid, title, "Structure",
        summary="45 m² gable greenhouse: galvanised steel frame, 8 mm twin-wall polycarbonate, ridge vent with insect net.",
        how=("Frames every 1.5 m carry the roof and the crop load (plants hang from the crop wires on the trusses). "
             "Twin-wall polycarbonate diffuses light (fewer leaf burns, light reaches lower leaves) and insulates 2× better "
             "than film. The ridge vent gives free natural ventilation; 40-mesh insect net keeps whitefly and Tuta out. "
             "Fans on the front gable + wet pad on the back gable give active cooling on hot days."),
        sensors=("outdoor weather station", "2 climate boxes inside"),
        control="Vent, fans, pad, fog are the actuators; the structure itself is passive.",
        state={"area_m2": 45, "volume_m3": 162, "vent_open_pct": 35},
        real="Galvanised 60×60 posts, truss frames @1.5 m, 8 mm twin-wall PC; India: polyhouse vendors (NHB norms)",
        cost="₹2–3.5 L (structure + cladding)")
    # foundation kerb + floor
    fd = MB()
    for sy in (-1, 1):
        fd.box((L + 0.3, 0.15, 0.3), "concrete", loc=(L / 2, sy * (W / 2 + 0.05), 0.15))
    for x in (-0.05, L + 0.05):
        for y0, y1 in ((-W / 2 - 0.125, -0.55), (0.55, W / 2 + 0.125)) if x < 0 else ((-W / 2 - 0.125, W / 2 + 0.125),):
            fd.box((0.15, y1 - y0, 0.3), "concrete", loc=(x, (y0 + y1) / 2, 0.15))
    fd.box((2.2, W, 0.04), "concrete", loc=(1.1, 0, 0.02))                   # technical zone slab
    fd.box((L - 2.2, W, 0.01), "ground_cover", loc=(2.2 + (L - 2.2) / 2, 0, 0.005))  # woven white ground cover
    c.part("foundation_floor", fd, desc="Concrete kerb, concrete technical zone, white woven ground cover (reflects light, stops weeds).")
    # steel frame
    fr = MB()
    s = 0.06
    xs = [BAY * i for i in range(int(L / BAY) + 1)]
    for x in xs:
        for sy in (-1, 1):
            fr.box((s, s, GH), "galv", loc=(x, sy * W / 2, GH / 2))              # side posts
        fr.box((0.05, W, 0.05), "galv", loc=(x, 0, GH))                          # bottom chord
        for sy in (-1, 1):                                                        # rafters
            y0, y1 = sy * W / 2, 0.0
            ln = math.hypot(W / 2, RH - GH)
            ang = math.degrees(math.atan2(RH - GH, W / 2))
            fr.box((0.05, ln, 0.06), "galv", loc=(x, sy * W / 4, (GH + RH) / 2), rot=(-sy * ang, 0, 0))
            for k in (1, 2):                                                      # truss web
                yk = sy * W / 2 * (1 - k / 3)
                fr.box((0.03, 0.03, roof_z(yk) - GH), "galv", loc=(x, yk, (roof_z(yk) + GH) / 2))
                ya, yb = sy * W / 2 * (1 - (k - 1) / 3), yk
                d = math.hypot(ya - yb, roof_z(yk) - GH)
                a2 = math.degrees(math.atan2(roof_z(yk) - GH, ya - yb))
                fr.box((0.025, d, 0.025), "galv", loc=(x, (ya + yb) / 2, GH + (roof_z(yk) - GH) / 2), rot=(-a2, 0, 0))
        fr.box((0.04, 0.04, RH - GH), "galv", loc=(x, 0, (GH + RH) / 2))          # king post
    for sy in (-1, 1):
        # gutters along the eaves + wall girts
        prof = [(-0.12, 0.1), (-0.12, 0.0), (0.12, 0.0), (0.12, 0.1), (0.1, 0.1), (0.1, 0.012), (-0.1, 0.012), (-0.1, 0.1)]
        fr.prism(prof, L + 0.2, "galv", z0=-(L + 0.2) / 2, M=xform((L / 2, sy * W / 2, GH + 0.03)) @ xform(rot=(0, 90, 0)) @ xform(rot=(0, 0, 90)))
        for z in (1.0, 2.0):
            fr.box((L, 0.04, 0.04), "galv", loc=(L / 2, sy * W / 2, z))
        for k in (1, 2):
            yk = sy * W / 2 * (1 - k / 3)
            fr.box((L, 0.04, 0.05), "galv", loc=(L / 2, yk, roof_z(yk) + 0.01))   # purlins
    fr.box((L, 0.06, 0.06), "galv", loc=(L / 2, 0, RH + 0.01))                    # ridge
    for x in (0.0, L):                                                            # gable framing
        for y in (-2.0, -1.15, -0.55, 0.55, 1.15, 2.0):
            fr.box((0.05, 0.05, roof_z(y)), "galv", loc=(x, y, roof_z(y) / 2))
        fr.box((0.05, W, 0.05), "galv", loc=(x, 0, 1.0))
    fr.box((0.05, 1.1, 0.05), "galv", loc=(0.0, 0, 2.15))                         # door header
    for sy in (-1, 1):                                                            # fan frames
        fr.box((0.05, 0.7, 0.05), "galv", loc=(0.0, sy * FAN_Y, FAN_Z - FAN_HOLE - 0.025))
        fr.box((0.05, 0.7, 0.05), "galv", loc=(0.0, sy * FAN_Y, FAN_Z + FAN_HOLE + 0.025))
    fr.box((0.05, PAD_W + 0.1, 0.05), "galv", loc=(L, 0, PAD_Z + PAD_H + 0.1))    # pad header
    c.part("steel_frame", fr, explode=(0, 0, 0), desc="Galvanised steel frame: posts, trusses (they also carry the crop wires), purlins, gutters.")
    # cladding
    pc = MB()
    for sy in (-1, 1):
        pc.box((L, 0.008, GH - 0.3), "uv_film", loc=(L / 2, sy * (W / 2 + 0.035), 0.3 + (GH - 0.3) / 2))
    front_holes = [(-0.55, 0.55, 0.0, 2.15)] + [(sy * FAN_Y - FAN_HOLE, sy * FAN_Y + FAN_HOLE, FAN_Z - FAN_HOLE, FAN_Z + FAN_HOLE) for sy in (-1, 1)]
    back_holes = [(-PAD_W / 2 - 0.02, PAD_W / 2 + 0.02, PAD_Z - 0.05, PAD_Z + PAD_H + 0.08)]
    for x, holes in ((-0.035, front_holes), (L + 0.035, back_holes)):
        for y0, y1, z0, z1 in rect_minus_holes(-W / 2, W / 2, 0.3, GH, holes):
            pc.box((0.008, y1 - y0, z1 - z0), "uv_film", loc=(x, (y0 + y1) / 2, (z0 + z1) / 2))
        gable_triangle(pc, x, "uv_film")
    c.part("film_walls", pc, explode=(0, 0, 0), desc="200-micron UV-stabilised polyethylene film on the walls and gables, held in aluminium lock channels (openings for door, fans and pad).")
    rf = MB()
    roof_panel(rf, -W / 2 - 0.1, 0.0, "uv_film")
    roof_panel(rf, W / 2 + 0.1, VENT_DEPTH + 0.05, "uv_film")
    for x in xs:  # glazing bars
        for sy in (-1, 1):
            y_top = 0.0 if sy < 0 else VENT_DEPTH + 0.05
            ln = abs(sy * W / 2 - y_top)
            ang = math.degrees(math.atan2(RH - GH, W / 2))
            rf.box((0.03, math.hypot(ln, ln * (RH - GH) / (W / 2)), 0.02), "alu",
                   loc=(x, (sy * W / 2 + y_top) / 2, (roof_z(sy * W / 2) + roof_z(y_top)) / 2 + 0.035), rot=(-sy * ang, 0, 0))
        for sy in (-1, 1):
            rf.box((0.03, 0.02, GH - 0.3), "alu", loc=(x, sy * (W / 2 + 0.045), 0.3 + (GH - 0.3) / 2))
    c.part("film_roof", rf, explode=(0, 0, 1.2), desc="200-micron UV-stabilised 5-layer film roof (Ginegar/Essen class), clamped in lock channels on every arch. Replaced every 3–4 years.")
    nt = MB()
    roof_panel(nt, VENT_DEPTH + 0.05, 0.02, "net", off=0.0)
    c.part("insect_net", nt, explode=(0, 0, 0.8), desc="40-mesh insect net under the vent – blocks whitefly, thrips and Tuta moths.")
    vw = MB()
    ang = math.degrees(math.atan2(RH - GH, W / 2))
    open_deg = 12
    for d in (0.0, VENT_DEPTH):
        vw.box((L - 0.1, 0.04, 0.03), "alu", loc=(L / 2, d, 0))
    for x in [0.05 + (L - 0.1) * k / 6 for k in range(7)]:
        vw.box((0.03, VENT_DEPTH, 0.03), "alu", loc=(x, VENT_DEPTH / 2, 0))
    vw.box((L - 0.1, VENT_DEPTH, 0.006), "uv_film", loc=(L / 2, VENT_DEPTH / 2, 0.015))
    c.part("vent_window", vw, loc=(0.0, 0.0, RH + 0.04), rot=(-(ang - open_deg), 0, 0), explode=(0, 0.4, 1.6),
           desc="Ridge vent window (hinged at the ridge), shown 35 % open.")
    dr = MB()
    dr.box((1.0, 0.04, 2.05), "alu", loc=(0, 0, 0))
    dr.box((0.9, 0.05, 1.95), "uv_film", loc=(0, 0, 0))
    dr.box((0.03, 0.06, 0.2), "plastic_black", loc=(0.4, 0.0, 0.0))
    dr.box((1.25, 0.06, 0.06), "alu", loc=(0.1, 0.0, 1.07))
    c.part("door", dr, loc=(-0.075, 0.0, 1.07), rot=(0, 0, 90), explode=(-0.8, 0, 0),
           desc="Sliding door. Real builds add a double-door insect-proof entrance (anteroom).")
    return c


# ─────────────────────────────── growing row ───────────────────────────────
def growing_row(cid, row, skip_first_slab=False):
    y = ROWS_Y[row - 1]
    c = Component(
        cid, f"Growing row {row} (gutter · slabs · drip line · crop wire)", "Irrigation",
        summary=f"Row {row}: 6 coco slabs × 3 plants on a galvanised gutter, one 16 mm drip line (irrigation zone {row}).",
        how=("The gutter holds the slabs at working height and collects drain water, sloping gently to the front end where "
             "it drains to the drain meter. The drip line has one pressure-compensating dripper per plant. Each plant hangs "
             "from the crop wire on a string with a roller hook."),
        sensors=("zone flow meter", "drain meter (row 3)", "slab scale (row 3, slab 1)", "substrate sensor"),
        control=f"Zone valve {row} (PLC).", state={"zone": row, "last_shot_ml_per_plant": 180, "shots_today": 9},
        real="Galvanised hanging gutter, 100×20×7.5 cm coco slabs, 16 mm PE lateral + PC drippers", cost="₹12–18k per row")
    g = MB()
    x0 = SLAB_X[1] - 0.535 if skip_first_slab else ROW_X0
    prof = [(-0.13, 0.07), (-0.13, 0.0), (0.13, 0.0), (0.13, 0.07), (0.118, 0.07), (0.118, 0.01), (-0.118, 0.01),
            (-0.118, 0.07)]
    g.prism(prof, ROW_X1 - x0, "galv", z0=0.0,
            M=xform((x0, y, GUTTER_Z - 0.01)) @ xform(rot=(0, 90, 0)) @ xform(rot=(0, 0, 90)))
    for x in [x0 + 0.2 + k * 1.25 for k in range(int((ROW_X1 - x0) / 1.25) + 1)]:
        g.box((0.03, 0.03, GUTTER_Z - 0.01), "galv", loc=(x, y - 0.1, (GUTTER_Z - 0.01) / 2))
        g.box((0.03, 0.03, GUTTER_Z - 0.01), "galv", loc=(x, y + 0.1, (GUTTER_Z - 0.01) / 2))
        g.box((0.03, 0.26, 0.03), "galv", loc=(x, y, GUTTER_Z - 0.025))
        g.box((0.12, 0.3, 0.005), "galv", loc=(x, y, 0.003))
    g.cyl(0.02, 0.4, "pvc_grey", segs=16, loc=(x0 - 0.03, y, GUTTER_Z - 0.2))  # drain outlet
    c.part("gutter", g, desc="Galvanised growing gutter on stands (collects drain water).")
    sl = MB()
    for i, xc in enumerate(SLAB_X):
        if skip_first_slab and i == 0:
            continue
        sl.box((1.0, 0.2, SLAB_TOP - GUTTER_Z), "slab_film", bevel=0.015, loc=(xc, y, (SLAB_TOP + GUTTER_Z) / 2))
        for k in range(4):
            sl.box((0.03, 0.004, 0.004), "plastic_dark", loc=(xc - 0.45 + 0.3 * k, y + 0.101, GUTTER_Z + 0.006))
    c.part("coco_slabs", sl, explode=(0, 0, 0.25), desc="Coco-coir slabs (100 × 20 × 7.5 cm) in white film; drain slits at the base.")
    dl = MB()
    ly = y + 0.14 * (1 if row != 1 else -1)  # lateral runs on the gutter edge away from the aisle? keep outside
    ly = y + 0.135
    dl.sweep([(ROW_X0 - 0.05, ly, SLAB_TOP + 0.01), (ROW_X1, ly, SLAB_TOP + 0.01)], 0.008, "pe_black", segs=12)
    for i, xc in enumerate(SLAB_X):
        for j in range(3):
            xp = xc + (j - 1) * 0.33
            dx = xp + 0.04
            dl.cyl(0.0105, 0.01, "plastic_black", segs=20, loc=(dx, ly, SLAB_TOP + 0.022))
            pts = [(dx, ly, SLAB_TOP + 0.027), (dx, ly, SLAB_TOP + 0.05), (dx - 0.01, ly - 0.07, CUBE_TOP + 0.05),
                   (xp + 0.03, y + 0.03, CUBE_TOP + 0.03)]
            dl.sweep(fillet_path(pts, 0.03), 0.002, "pe_black", segs=8)
            dl.cyl(0.0035, 0.07, "plastic_green", segs=10, loc=(xp + 0.03, y + 0.03, CUBE_TOP - 0.01), rot=(-20, 0, 0))
    c.part("drip_line", dl, explode=(0, 0.3, 0.2), desc="16 mm drip lateral with 18 PC drippers, micro-tubes and stakes.")
    cw = MB()
    cw.sweep([(ROW_X0 - 0.05, y, WIRE_Z), (ROW_X1 + 0.05, y, WIRE_Z)], 0.0025, "stainless", segs=6)
    for x in [BAY * k for k in range(2, 6)] + [L - 0.3]:
        cw.box((0.02, 0.02, GH - WIRE_Z), "galv", loc=(x, y, (GH + WIRE_Z) / 2))
    c.part("crop_wire", cw, explode=(0, 0, 0.3), desc="Crop wire at 2.75 m – every plant string hangs from it (roller hooks).")
    return c


# ─────────────────────────────── pipe rails ───────────────────────────────
def pipe_rails(cid="pipe_rails", title="Pipe rails (robot track)"):
    c = Component(
        cid, title, "Robot",
        summary="Two 51 mm steel tubes in each aisle – the robot's track. In large greenhouses these are the hot-water heating pipes.",
        how=("Round pipes on low supports give the robot a precise, clean track without floor markings. Position along "
             "the aisle comes from wheel encoders; plant tags correct any drift."),
        sensors=("—",), control="—", state={}, real="51 mm galvanised tube on 10 cm supports, 0.55 m gauge", cost="₹8–12k")
    rl = MB()
    for ay in AISLES_Y:
        for sy in (-1, 1):
            yy = ay + sy * RAIL_GAUGE / 2
            rl.cyl(PIPE_R, ROW_X1 - 2.1, "galv", segs=24, axis="X", loc=((ROW_X1 + 2.1) / 2, yy, RAIL_Z))
            rl.sphere(PIPE_R, "galv", segs=16, rings=8, loc=(ROW_X1, yy, RAIL_Z))
            for x in [2.2 + 0.9 * k for k in range(8)]:
                rl.box((0.05, 0.06, RAIL_Z), "galv_dull", loc=(x, yy, RAIL_Z / 2))
        for x in (2.7, 5.0, 8.0):                       # flat ties: the mecanum wheels pass 1.3 cm above them
            rl.box((0.04, RAIL_GAUGE, 0.012), "galv_dull", loc=(x, ay, 0.006))
        # lead-in guides: the grooved wheels meet the pipe ends on these
        for sy in (-1, 1):
            yy = ay + sy * RAIL_GAUGE / 2
            rl.box((0.35, 0.06, 0.012), "galv", loc=(2.0, yy, RAIL_Z / 2 + 0.02), rot=(0, -14, 0))
    c.part("rails", rl, desc="Pipe rails in aisle 1 and aisle 2 with lead-in guides at the concrete path.")
    # 14 Oct 2026: the handover from path to rails. The path slab is 4 cm above the aisle floor; between the pipes a
    # sloped checker plate runs from slab level down to the floor. Driving in, the mecanum wheels roll down it and the
    # grooved wheels settle onto the pipes; backing out, the plate lifts the robot 1.5 cm and the grooved wheels come off.
    # The drain header from the gutter outlets runs in a channel under these plates.
    tp = MB()
    for ay in AISLES_Y:
        tp.box((0.31, 0.44, 0.012), "galv_dull", loc=(2.35, ay, 0.021), rot=(0, 7.4, 0))
        for k in range(7):
            tp.box((0.28, 0.006, 0.003), "galv", loc=(2.35, ay - 0.18 + k * 0.06, 0.029), rot=(0, 7.4, 0))
    c.part("handover_plates", tp, desc="Sloped checker plates (slab level → floor) between the pipes at each aisle mouth: "
           "where the robot's weight passes from its mecanum wheels to its grooved rail wheels. The drain channel runs under them.")
    # one floor code per aisle, on the path slab in line with the aisle: the camera under the robot's front reads it
    # while the robot slides along the path, and stops it exactly in line with that aisle (like warehouse robots)
    import random
    mk = MB()
    for n, ay in enumerate(AISLES_Y):
        px, py = 1.95, ay
        mk.box((0.16, 0.16, 0.003), "sticker_white", loc=(px, py, 0.0415))
        rnd = random.Random(100 + n)
        for i in range(6):
            for j in range(6):
                if i in (0, 5) or j in (0, 5) or rnd.random() < 0.5:
                    mk.box((0.02, 0.02, 0.001), "plastic_black", loc=(px - 0.05 + i * 0.02, py - 0.05 + j * 0.02, 0.0435))
    c.part("aisle_markers", mk, desc="ArUco floor codes, one per aisle (id 1, 2), on the path slab in line with each aisle: the robot's under-camera reads them.")
    return c


# ─────────────────────────────── main irrigation piping ───────────────────────────────
SKID_Y = -1.15   # fertigation skid line (y)


def irrigation_mains(cid="irrigation_mains", title="Main irrigation piping (PVC)"):
    c = Component(
        cid, title, "Irrigation",
        summary="PVC pipes from the mix tank → pump → filter → meter → overhead manifold → 3 zone valves → drip lines.",
        how=("The main line runs overhead across the technical zone so the robot can drive underneath; at each row it drops "
             "down through its zone valve to the drip lateral."),
        sensors=("pressure transmitter", "flow meter"), control="—", state={"pressure_bar": 2.1},
        real="32 mm PVC-U pressure pipe (PN10) + 25 mm drops", cost="₹6–10k")
    p = MB()
    r = 0.016
    pvc_run(p, [(0.45, -1.785, 0.1), (0.45, -1.66, 0.1)], r)                                  # mix tank → pump inlet
    pvc_run(p, [(0.45, -1.515, 0.2), (0.45, -1.515, 0.9), (0.45, -1.3, 0.9), (1.9, -1.3, 0.9),  # pump → meter run
                (1.9, -1.3, 2.85), (2.15, -1.3, 2.85)], r)
    pvc_run(p, [(2.15, ROWS_Y[0] + 0.135, 2.85), (2.15, ROWS_Y[2] + 0.135, 2.85)], r)          # overhead manifold
    for y in ROWS_Y:                                                                              # drops to each zone
        yy = y + 0.135
        pvc_run(p, [(2.15, yy, 2.85), (2.15, yy, 1.07)], 0.0125)
        pvc_run(p, [(2.15, yy, 0.93), (2.15, yy, SLAB_TOP + 0.01), (2.21, yy, SLAB_TOP + 0.01)], 0.0125)
    c.part("pipes", p, desc="32 mm PVC mains + 25 mm zone drops.")
    return c


def fog_line(cid="fog_line", title="Fog line (16 mm PE, 6 CoolNet foggers)"):
    c = Component(
        cid, title, "Climate",
        summary="Two 16 mm PE lines above the aisles, each with 3 Netafim CoolNet Pro 4-way foggers hanging above the crop.",
        how=("Fed at 4 bar through the fog valve station. Each fogger (4 × 7.5 L/h) makes ~65 µm droplets that evaporate "
             "before they reach the leaves; one fogger covers about 8 m²."),
        sensors=("fog-line pressure gauge",), control="Fog valve relay (PLC).", state={"spraying": False},
        real="16 mm PE line + 6 × Netafim CoolNet Pro 4-way foggers on 30 cm hangers", cost="≈₹4k")
    f = MB()
    zf = FOG_Z
    for ay in AISLES_Y:
        f.cyl(0.008, ROW_X1 - 2.2, "pe_black", segs=16, axis="X", loc=((ROW_X1 + 2.2) / 2, ay, zf))
        for x in FOG_X:     # simplified CoolNet Pro: hanger tube, weight, LPD ball, 4-way cross
            f.cyl(0.0025, 0.3, "plastic_white", segs=8, z0=zf - 0.3, loc=(x, ay, 0))
            f.cyl(0.0085, 0.032, "steel_dark", segs=12, z0=zf - 0.26, loc=(x, ay, 0))
            f.sphere(0.012, "pvc_white", segs=16, rings=8, loc=(x, ay, zf - 0.33))
            for k in range(2):
                f.box((0.07, 0.009, 0.009), "pvc_white", loc=(x, ay, zf - 0.365), rot=(0, 0, 45 + 90 * k))
        for x in [BAY * k for k in range(2, 6)]:
            f.box((0.01, 0.01, roof_z(ay) - zf), "galv", loc=(x, ay, (roof_z(ay) + zf) / 2))
    f.sweep(fillet_path([(0.57, 2.0, 1.36), (0.57, 2.0, zf), (2.2, 2.0, zf), (2.2, 0.8, zf)], 0.1), 0.008, "pe_black", segs=12)
    f.sweep([(2.2, 0.8, zf), (2.2, -0.8, zf)], 0.008, "pe_black", segs=12)
    c.part("line", f, desc="16 mm PE fog lines with 6 CoolNet Pro foggers over the aisles.")
    return c


def surroundings(cid="site", title="Site (outside ground)", hole=None, farm=False):
    """Ground round the greenhouse. `hole` = (x0, x1, y0, y1) leaves an opening (the farm pond); `farm` adds the
    entrance apron and paths of the full farm layout (6 Oct 2026)."""
    c = Component(cid, title, "Structure", summary="Ground around the greenhouse.", state={})
    g = MB()
    X0, X1, Y0, Y1 = L / 2 - 80, L / 2 + 80, -80, 80
    if hole:
        hx0, hx1, hy0, hy1 = hole
        for (a, b, c_, d) in ((X0, hx0, Y0, Y1), (hx1, X1, Y0, Y1), (hx0, hx1, Y0, hy0), (hx0, hx1, hy1, Y1)):
            g.box((b - a, d - c_, 0.1), "gravel", loc=((a + b) / 2, (c_ + d) / 2, -0.05))
    else:
        g.box((X1 - X0, Y1 - Y0, 0.1), "gravel", loc=(L / 2, 0, -0.05))
    c.part("ground", g, desc="Outside ground (Kolar red soil).")
    p = MB()
    if farm:
        p.box((1.5, 1.5, 0.06), "concrete", loc=(-2.85, 0, 0.03))                  # apron at the entry room
        p.box((1.2, 14.0, 0.03), "concrete", loc=(-3.0, 2.1, 0.015))               # main path along the front
        p.box((5.1, 1.2, 0.03), "concrete", loc=(-1.05, 8.5, 0.015))               # → packhouse (open south side)
        p.box((9.2, 0.9, 0.03), "concrete", loc=(1.0, -4.1, 0.015))                # → pond gate
    else:
        p.box((3.0, 1.4, 0.06), "concrete", loc=(-1.6, 0, 0.03))
    c.part("paths", p, desc="Entrance apron and concrete paths.")
    return c
