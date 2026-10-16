"""Small reusable geometry builders shared by all component modules (screws, springs, cables, pipes, dials…)."""
import math

from mathutils import Vector

from gh import AXIS_ROT, TAU, bm_box, bm_cyl, fillet_path, xform


def helix(r, pitch, turns, z0=0.0, steps_per_turn=24, closed_ends=True):
    """Spring centre-line. Closed (tight) coils at both ends like a real compression spring."""
    pts = []
    n = int(turns * steps_per_turn)
    z = z0
    for i in range(n + 1):
        a = TAU * i / steps_per_turn
        p = pitch
        if closed_ends and (i < steps_per_turn * 0.8 or i > n - steps_per_turn * 0.8):
            p = pitch * 0.25
        if i:
            z += p / steps_per_turn
        pts.append((r * math.cos(a), r * math.sin(a), z))
    return pts


def screw(mb, loc, length=0.02, r=0.0022, head_r=0.0045, m="stainless", axis=None, rot=(0, 0, 0)):
    mb.lathe([(0, 0), (head_r, 0), (head_r, 0.0025), (head_r * 0.8, 0.0035), (0, 0.0035)], m, segs=16, loc=loc,
             axis=axis, rot=rot)
    mb.cyl(r, length, m, segs=10, z0=-length, loc=loc, axis=axis, rot=rot)
    return mb


def cable(mb, pts, r=0.0025, m="cable", fillet=0.03, segs=10):
    mb.sweep(fillet_path(pts, fillet), r, m, segs=segs)
    return mb


def pvc_run(mb, pts, r, m="pvc_grey", fit_m=None):
    """Straight pipe segments with glued 90° elbow fittings at every corner (PVC style)."""
    fit_m = fit_m or m
    P = [Vector(p) for p in pts]
    rf = r * 1.22
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        d = (b - a).normalized()
        a2 = a + d * (rf * 1.2 if i > 0 else 0)
        b2 = b - d * (rf * 1.2 if i < len(P) - 2 else 0)
        mb.sweep([a2, b2], r, m, segs=20, cap=True)
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        d1, d2 = (a - b).normalized(), (c - b).normalized()
        arc = fillet_path([b + d1 * rf * 2.0, b, b + d2 * rf * 2.0], rf * 1.3, steps=8)
        mb.sweep(arc, rf, fit_m, segs=20)
    return mb


def pe_run(mb, pts, r, m="pe_black", bend=0.08):
    """Flexible PE pipe with smooth bends."""
    mb.sweep(fillet_path(pts, bend, steps=10), r, m, segs=16)
    return mb


def vane(r0, r1, sweep_deg, t, n=8):
    """Curved impeller vane outline (CCW polygon) from radius r0 to r1."""
    c = []
    for i in range(n + 1):
        u = i / n
        r = r0 + (r1 - r0) * u
        a = math.radians(sweep_deg) * u
        c.append((r * math.cos(a), r * math.sin(a), a))
    left, right = [], []
    for x, y, a in c:
        nx, ny = -math.sin(a + 0.6), math.cos(a + 0.6)
        left.append((x + nx * t / 2, y + ny * t / 2))
        right.append((x - nx * t / 2, y - ny * t / 2))
    return right + left[::-1]


def blade(span, chord, twist_deg, thick=0.002, n=6):
    """Fan blade outline in XY (root at origin, tip at +X), used with prism()."""
    pts_top, pts_bot = [], []
    for i in range(n + 1):
        u = i / n
        x = span * u
        ch = chord * (0.7 + 0.5 * math.sin(math.pi * u * 0.9))
        pts_top.append((x, ch / 2))
        pts_bot.append((x, -ch / 2))
    return pts_bot + pts_top[::-1]


def dial(mb, r, loc, axis, m_face="plastic_white", m_tick="plastic_black", ticks=11):
    """Gauge dial face with ticks, lying in the plane normal to `axis`."""
    base = xform(loc) @ xform(rot=AXIS_ROT[axis])
    mb.add(bm_cyl(r, 0.001, 40), m_face, M=base)
    for k in range(ticks):
        a = math.radians(225 - 270 / (ticks - 1) * k)
        L = 0.18 * r if k % 5 == 0 else 0.1 * r
        rr = r * 0.82
        M = base @ xform((rr * math.cos(a), rr * math.sin(a), 0.0008), (0, 0, math.degrees(a)))
        mb.add(bm_box(L, r * 0.03, 0.0006), m_tick, M=M)
    return base


def radial(n, r, start=0.0):
    """(x, y, angle_deg) points around a circle."""
    return [(r * math.cos(start + TAU * k / n), r * math.sin(start + TAU * k / n),
             math.degrees(start + TAU * k / n)) for k in range(n)]


def fins_around_x(mb, R, length, n, m, height=0.01, t=0.0028, skip_bottom=True, x0=0.0):
    """Cooling fins around a cylinder whose axis is X (motors)."""
    for k in range(n):
        a = TAU * k / n
        if skip_bottom and math.sin(a) < -0.75:
            continue
        mb.box((length, t, height), m, loc=(x0, (R + height * 0.4) * math.cos(a), (R + height * 0.4) * math.sin(a)),
               rot=(math.degrees(a) - 90, 0, 0))
    return mb


def motor_x(mb, R, L, m="paint_motor", fins=22, feet=True):
    """A finned TEFC electric motor along X, centred at the origin."""
    mb.lathe([(0.0, -L / 2), (R - 0.01, -L / 2), (R, -L / 2 + 0.01), (R, L / 2 - 0.01), (R - 0.01, L / 2),
              (0.0, L / 2)], m, segs=48, axis="X")
    fins_around_x(mb, R, L * 0.85, fins, m)
    if feet:
        for sx in (-1, 1):
            mb.box((0.035, R * 2.4, 0.012), m, bevel=0.002, loc=(sx * L * 0.28, 0, -R - 0.012))
            for sy in (-1, 1):
                mb.box((0.03, 0.02, R * 0.8), m, loc=(sx * L * 0.28, sy * R * 0.65, -R * 0.75))
    return mb


def label_plate(mb, text, size, loc, rot, w, h, m_bg="sticker_white", m_txt="plastic_black", depth=0.0008):
    """A flat sticker/label with text on top (text faces +Z of the plate before rotation)."""
    M = xform(loc, rot)
    mb.add(bm_box(w, h, depth), m_bg, M=M)
    from gh import bm_text
    mb.add(bm_text(text, size, 0.0004, "CENTER", True), m_txt, M=M @ xform((0, 0, depth / 2 + 0.0002)), smooth=False)
    return mb


def axial_blades(mb, m, n, r0, r1, chord=(0.06, 0.14), pitch=(32, 18), sweep=14.0, camber=0.06, thick=0.003,
                 tip_round=0.18, nu=12, nv=8, z0=0.0, M=None):
    """Twisted, cambered axial-fan blades around the Z axis (hub at r0, tip at r1), as closed shells.

    chord/pitch go root→tip (pitch in degrees from the rotation plane), `sweep` skews the blade forward,
    `tip_round` rounds the last fraction of the span. Build in this Z frame, orient with M (e.g. axis to Y)."""
    import bmesh as _bm
    for k in range(n):
        bm = _bm.new()
        top, bot = [], []
        for i in range(nu + 1):
            u = i / nu
            r = r0 + (r1 - r0) * u
            ch = chord[0] + (chord[1] - chord[0]) * u
            if u > 1 - tip_round:  # round the tip
                t = (u - (1 - tip_round)) / tip_round
                ch *= math.sqrt(max(0.0, 1 - t * t)) * 0.9 + 0.1
            p = math.radians(pitch[0] + (pitch[1] - pitch[0]) * u)
            phi0 = TAU * k / n + math.radians(sweep) * u
            rt, rb = [], []
            for j in range(nv + 1):
                v = j / nv - 0.5
                c = v * ch
                cam = camber * ch * (1 - 4 * v * v)
                s = c * math.cos(p)
                h = z0 + c * math.sin(p) + cam
                phi = phi0 + s / r
                for lst, dz in ((rt, thick / 2), (rb, -thick / 2)):
                    lst.append(bm.verts.new((r * math.cos(phi), r * math.sin(phi), h + dz)))
            top.append(rt)
            bot.append(rb)
        for i in range(nu):
            for j in range(nv):
                bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
                bm.faces.new((bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]))
        for i in range(nu):  # leading and trailing edges
            bm.faces.new((top[i][0], bot[i][0], bot[i + 1][0], top[i + 1][0]))
            bm.faces.new((top[i][nv], top[i + 1][nv], bot[i + 1][nv], bot[i][nv]))
        for j in range(nv):  # root and tip caps
            bm.faces.new((top[0][j], top[0][j + 1], bot[0][j + 1], bot[0][j]))
            bm.faces.new((top[nu][j], bot[nu][j], bot[nu][j + 1], top[nu][j + 1]))
        _bm.ops.recalc_face_normals(bm, faces=bm.faces)
        mb.add(bm, m, M=M)
    return mb


def square_plate_with_hole(mb, m, half, R, t, M=None, segs=64, corner_r=0.0):
    """Flat square plate (side 2·half, thickness t along Z, from z=0 to t) with a centred round hole of radius R."""
    sides = [(-45, 45), (45, 135), (135, 225), (225, 315)]
    per = segs // 4
    for a0, a1 in sides:
        c0 = (half * math.sqrt(2) * math.cos(math.radians(a0)), half * math.sqrt(2) * math.sin(math.radians(a0)))
        c1 = (half * math.sqrt(2) * math.cos(math.radians(a1)), half * math.sqrt(2) * math.sin(math.radians(a1)))
        arc = [(R * math.cos(math.radians(a1 - (a1 - a0) * i / per)), R * math.sin(math.radians(a1 - (a1 - a0) * i / per)))
               for i in range(per + 1)]
        mb.prism([c0, c1] + arc, t, m, M=M)
    return mb


def polygon_plate_with_hole(mb, m, poly, R, t, M=None, per=10):
    """Flat convex polygon plate (vertices around the origin, CCW, in XY) with a centred round hole of radius R;
    thickness t along +Z. One simple piece per polygon edge, so bm_prism can extrude it."""
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        a0, a1 = math.atan2(y0, x0), math.atan2(y1, x1)
        if a1 < a0:
            a1 += TAU
        arc = [(R * math.cos(a1 - (a1 - a0) * k / per), R * math.sin(a1 - (a1 - a0) * k / per)) for k in range(per + 1)]
        mb.prism([(x0, y0), (x1, y1)] + arc, t, m, M=M)
    return mb


def octagon(flat, chamfer):
    """Chamfered-square outline (flat-to-flat size `flat`, corner chamfer leg `chamfer`), CCW."""
    h, c = flat / 2, chamfer
    return [(h, -h + c), (h, h - c), (h - c, h), (-h + c, h), (-h, h - c), (-h, -h + c), (-h + c, -h), (h - c, -h)]


def kirloskar_chhotu(mb):
    """Kirloskar Chhotu 0.5 HP monoblock pump (~280 × 150 × 220 mm): green finned motor along −X, black end cover,
    black terminal box with the yellow badge, black cast-iron head at +X with side suction and a vertical flanged
    outlet. Base at z = 0; the outlet flange top is at (0.09, 0, 0.21)."""
    zc, R = 0.085, 0.062
    mb.box((0.17, 0.13, 0.012), "chhotu_green", bevel=0.003, loc=(-0.1, 0, 0.006))                  # foot
    mb.box((0.1, 0.05, zc - R + 0.01), "chhotu_green", loc=(-0.1, 0, (zc - R + 0.01) / 2 + 0.006))
    mb.cyl(R, 0.17, "chhotu_green", segs=40, axis="X", loc=(-0.105, 0, zc))
    fins_around_x(mb, R, 0.15, 18, "chhotu_green", height=0.008, x0=-0.105, skip_bottom=True)
    mb.lathe([(0.0, 0.0), (R + 0.004, 0.0), (R + 0.004, 0.02), (R - 0.01, 0.055), (0.0, 0.06)], "plastic_black",
             segs=40, axis="-X", loc=(-0.19, 0, zc))                                                 # end cover
    mb.box((0.09, 0.08, 0.045), "plastic_black", bevel=0.004, loc=(-0.1, 0, zc + R + 0.02))           # terminal box
    mb.cyl(0.017, 0.001, "sticker_yellow", segs=24, axis="-Y", loc=(-0.1, -0.0405, zc + R + 0.02))
    cable(mb, [(-0.055, 0.0, zc + R + 0.03), (-0.02, 0.02, zc + R + 0.06), (0.03, 0.06, zc + R + 0.1)], r=0.004)
    mb.cyl(0.072, 0.02, "steel_dark", segs=40, axis="X", loc=(-0.01, 0, zc))                        # bracket
    mb.cyl(0.07, 0.055, "steel_dark", segs=40, axis="X", loc=(0.035, 0, zc))                        # volute
    mb.cyl(0.021, 0.05, "steel_dark", segs=24, axis="X", loc=(0.085, 0, zc - 0.03))                 # suction 1"
    mb.cyl(0.028, 0.03, "steel_dark", segs=6, axis="X", loc=(0.105, 0, zc - 0.03))
    mb.cyl(0.03, 0.08, "steel_dark", segs=24, r_top=0.022, z0=zc + 0.03, loc=(0.09, 0, 0))         # discharge neck
    mb.cyl(0.045, 0.012, "steel_dark", segs=32, z0=0.198, loc=(0.09, 0, 0))                          # outlet flange
    for k in range(4):
        a = math.radians(45 + 90 * k)
        mb.cyl(0.005, 0.02, "brass", segs=6, z0=0.195, loc=(0.09 + 0.034 * math.cos(a), 0.034 * math.sin(a), 0))
    return mb


def s_load_cell(mb, m="stainless", w=0.0508, h=0.0762, t=0.0127, loc=(0, 0, 0)):
    """Zemic H3-style S-beam load cell (2 in × 3 in × 0.5 in), standing upright in XZ, centred at loc."""
    W2, H2, s, zs, xs = w / 2, h / 2, 0.004, 0.0127, 0.012
    pts = [(-W2, -H2), (W2, -H2), (W2, -zs - s), (-xs, -zs - s), (-xs, -zs + s), (W2, -zs + s), (W2, H2), (-W2, H2),
           (-W2, zs + s), (xs, zs + s), (xs, zs - s), (-W2, zs - s)]
    mb.prism(pts, t, m, z0=-t / 2, M=xform(loc) @ xform(rot=(90, 0, 0)))
    for sy in (-1, 1):   # sealed gauge pocket covers
        mb.cyl(0.0085, 0.001, "plastic_black", segs=24,
               M=xform((loc[0], loc[1] + sy * (t / 2 + 0.0004), loc[2])) @ xform(rot=(90, 0, 0)))
    return mb
