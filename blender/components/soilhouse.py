"""Soil-bed polyhouse, the way most Indian growers farm (15 Oct 2026): no rails, no coco slabs, no heating pipes.

Naturally ventilated GI polyhouse (gothic arches, roof vents, 40-mesh insect-net sides, roll-up curtains), raised soil
beds under silver-on-black mulch with drip laterals, a sub-main header at the bed ends, and paths of bare soil.
Bed sizes follow Indian practice (docs/06-scout-rover.md):
  tomato:     beds 1.0 m wide at the top, 30 cm high, 1.5 m pitch  -> 45 cm path at the bottom; paired rows 45 cm apart
  strawberry: beds 0.6 m wide, 40 cm high, 1.05 m pitch           -> ~42 cm path; two rows 30 cm apart

Local frame of a house: x = 0 at the front gable (door), beds run along +x; y = 0 on the centre line; z = 0 on the floor.
"""
import math
import random

import bmesh
import bpy
from mathutils import Vector

import gh
from gh import MB, TAU, Component, bm_box, bm_cyl, xform

gh.SPEC.update({
    "mulch_silver": dict(color=(0.74, 0.75, 0.77), metal=0.55, rough=0.32, noise=("coco", 9.0, 0.12)),
    "mulch_black": dict(color=(0.02, 0.02, 0.022), rough=0.45),
    "soil_bed": dict(color=(0.30, 0.15, 0.08), rough=0.97, noise=("coco", 60.0, 0.6)),
    "drip_black": dict(color=(0.015, 0.015, 0.017), rough=0.38),
    "sb_leaf": dict(color=(0.055, 0.21, 0.04), rough=0.42, sheen=0.12, vcol=True),
    "sb_petiole": dict(color=(0.22, 0.3, 0.08), rough=0.6, sheen=0.3, vcol=True),
    "sb_petal": dict(color=(0.95, 0.95, 0.92), rough=0.45, subsurface=0.2),
    "sb_centre": dict(color=(0.9, 0.75, 0.1), rough=0.6),
    "sb_calyx": dict(color=(0.1, 0.3, 0.05), rough=0.5, sheen=0.2),
    "dead_leaf": dict(color=(0.28, 0.22, 0.09), rough=0.85, vcol=True),
})

SB = dict(top=0.6, bottom=0.66, h=0.40, pitch=1.05, rows=(-0.15, 0.15), spacing=0.30)
TM = dict(top=1.0, bottom=1.05, h=0.30, pitch=1.50, rows=(-0.225, 0.225), spacing=0.45)


# ─────────────────────────────── materials built from nodes ───────────────────────────────
def berry_material(name, red=(0.62, 0.02, 0.015), achene=(0.85, 0.7, 0.18)):
    """Strawberry skin: glossy red with yellow seeds (achenes) sitting in small pits - Voronoi cells."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.22
    b.inputs["Coat Weight"].default_value = 0.6
    b.inputs["Coat Roughness"].default_value = 0.1
    b.inputs["Subsurface Weight"].default_value = 0.15
    b.inputs["Subsurface Radius"].default_value = (0.01, 0.003, 0.002)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.feature = "F1"
    vo.inputs["Scale"].default_value = 260.0
    nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
    seed = nt.nodes.new("ShaderNodeMapRange")
    seed.inputs["From Min"].default_value, seed.inputs["From Max"].default_value = 0.13, 0.2
    seed.inputs["To Min"].default_value, seed.inputs["To Max"].default_value = 1.0, 0.0
    nt.links.new(vo.outputs["Distance"], seed.inputs["Value"])
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "Col"
    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    mixc.blend_type = "MULTIPLY"
    mixc.inputs["Factor"].default_value = 1.0
    mixc.inputs["A"].default_value = (*red, 1)
    nt.links.new(at.outputs["Color"], mixc.inputs["B"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(seed.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mixc.outputs["Result"], mix.inputs["A"])
    mix.inputs["B"].default_value = (*achene, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    pit = nt.nodes.new("ShaderNodeMapRange")
    pit.inputs["From Min"].default_value, pit.inputs["From Max"].default_value = 0.0, 0.35
    nt.links.new(vo.outputs["Distance"], pit.inputs["Value"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.0015
    nt.links.new(pit.outputs["Result"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = (*red, 1)
    return m


def soil_material(name="path_soil"):
    """Bare path soil inside the house: red-brown, darker where damp, clods and crumbs from three noise scales."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 1.6
    n1.inputs["Detail"].default_value = 4
    n2 = nt.nodes.new("ShaderNodeTexVoronoi")
    n2.inputs["Scale"].default_value = 55.0
    n3 = nt.nodes.new("ShaderNodeTexNoise")
    n3.inputs["Scale"].default_value = 260.0
    n3.inputs["Detail"].default_value = 3
    for n in (n1, n2, n3):
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.35, (0.16, 0.075, 0.04, 1)   # damp
    cr.elements[1].position, cr.elements[1].color = 0.68, (0.36, 0.19, 0.10, 1)    # dry red-brown
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    crumb = nt.nodes.new("ShaderNodeMix")
    crumb.data_type = "RGBA"
    crumb.blend_type = "MULTIPLY"
    crumb.inputs["Factor"].default_value = 0.45
    nt.links.new(ramp.outputs["Color"], crumb.inputs["A"])
    nt.links.new(n3.outputs["Color"], crumb.inputs["B"])
    nt.links.new(crumb.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = 0.78, 0.98
    nt.links.new(n1.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    nt.links.new(n2.outputs["Distance"], add.inputs[0])
    nt.links.new(n3.outputs["Fac"], add.inputs[1])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.8
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(add.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    m.diffuse_color = (0.3, 0.16, 0.08, 1)
    return m


# ─────────────────────────────── strawberry plant ───────────────────────────────
def frame_matrix(origin, fwd, up):
    from mathutils import Matrix
    f = fwd.normalized()
    u = (up - f * up.dot(f)).normalized()
    s = u.cross(f)
    M = Matrix.Identity(4)
    M.col[0][:3], M.col[1][:3], M.col[2][:3], M.col[3][:3] = f, s, u, origin
    return M


def sb_leaflet(L, W, rnd, fold=0.32, cup=0.18, teeth=11):
    """Strawberry leaflet: ovate, saw-toothed edge, folded along the midrib, pleated along the veins. +x = tip."""
    bm = bmesh.new()
    nu, nv = teeth * 2, 7
    rows = []
    for i in range(nu + 1):
        u = i / nu
        w = 0.5 * W * max(math.sin(math.pi * min(0.999, u ** 0.85)), 0.0) ** 0.75
        if 0.08 < u < 0.97:
            w *= 1.0 + (0.09 if i % 2 else -0.03)          # serration
        w = max(w, 0.0005)
        row = []
        for j in range(nv):
            v = -1 + 2 * j / (nv - 1)
            pleat = 0.0025 * math.sin(u * teeth * math.pi) * abs(v)          # vein pleats
            z = abs(v) * w * fold + (v * v) * w * cup * (1 - u) - (u ** 2) * L * 0.12 + pleat
            row.append(bm.verts.new((u * L, v * w, z)))
        rows.append(row)
    for i in range(nu):
        for j in range(nv - 1):
            bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
    return bm


def berry_bm(Lb, Rb, rnd, segs=20, rings=10):
    """Conical strawberry hanging tip-down: local +z = up to the calyx; tip at z = -Lb."""
    prof = [(0.0, -Lb)]
    for i in range(1, rings + 1):
        t = i / rings                                     # 0 tip → 1 shoulder
        r = Rb * (math.sin(t * math.pi * 0.5) ** 0.9) * (1 - 0.18 * max(0, t - 0.82) / 0.18)
        prof.append((r, -Lb + Lb * t))
    prof.append((Rb * 0.45, 0.002))
    prof.append((0.0, 0.003))
    bm = gh.bm_lathe(prof, segs)
    k = rnd.uniform(0.85, 1.15)
    for v in bm.verts:
        v.co.x *= k                                       # slightly flattened / wedge-shaped berries
    return bm


def strawberry_plant(cid="sb_001", seed=1, ripe=4, green=2, flowers=2, outward=1.0, sick=False):
    """One strawberry plant (crown at the origin, on the mulch). Berries hang towards `outward` (+1/-1 = ±y)."""
    rnd = random.Random(seed)
    c = Component(cid, "Strawberry plant", "Plants",
                  summary="Day-neutral strawberry on a mulched raised bed. Leaves 15-25 cm tall; berries hang over the bed edge.",
                  real="Strawberry (Fragaria x ananassa), e.g. Winter Dawn / Sweet Charlie, on silver mulch")
    UP = Vector((0, 0, 1))
    lv, pt, fl, fr, cx = MB(), MB(), MB(), MB(), MB()
    nleaf = rnd.randint(9, 13)
    phi = rnd.uniform(0, TAU)
    pt.cyl(0.018, 0.03, "sb_petiole", segs=10, r_top=0.012, z0=-0.01, tint=(0.8, 0.75, 0.6))      # crown
    for k in range(nleaf):
        phi += math.radians(137.5 + rnd.uniform(-20, 20))
        age = rnd.random()
        Lp = rnd.uniform(0.10, 0.19) * (0.75 + 0.35 * age)
        el = math.radians(rnd.uniform(48, 75) - 20 * age)
        d = Vector((math.cos(phi), math.sin(phi), 0))
        pts = []
        for i in range(9):
            t = i / 8
            h = Lp * t * math.cos(el)
            zz = Lp * (t * math.sin(el) - 0.18 * t * t * (0.5 + age))
            pts.append(Vector((0, 0, 0.012)) + d * (h + 0.006) + UP * zz)
        tint = rnd.uniform(0.85, 1.1)
        pt.add(gh.bm_sweep(pts, 0.0016, 6, True, [0.0019 - 0.0006 * i / 8 for i in range(9)]), "sb_petiole",
               tint=(tint, tint, tint))
        tip = pts[-1]
        tan = (pts[-1] - pts[-2]).normalized()
        flat = Vector((tan.x, tan.y, 0)).normalized()
        lt = (tint * (0.9 if sick else 1.0), tint * rnd.uniform(0.95, 1.05) * (1.15 if sick else 1.0), tint * (1.6 if sick else 1.0))
        Ll = rnd.uniform(0.045, 0.065) * (0.8 + 0.3 * age)
        for s, ang in ((0, 0.0), (-1, 52.0), (1, 52.0)):
            a = math.radians(ang) * s
            f = Vector((flat.x * math.cos(a) - flat.y * math.sin(a), flat.x * math.sin(a) + flat.y * math.cos(a), 0))
            f = (f + UP * rnd.uniform(-0.25, 0.15)).normalized()
            b = sb_leaflet(Ll * (1.0 if s == 0 else 0.92), Ll * 0.72, rnd)
            M = frame_matrix(tip + f * 0.004, f, (UP + flat * -0.2).normalized())
            lv.add(b, "sb_leaf", M=M, tint=lt)
    # flowers on arching stalks
    for k in range(flowers):
        a = rnd.uniform(0, TAU)
        d = Vector((math.cos(a), math.sin(a), 0))
        top = Vector((0, 0, 0.01)) + d * rnd.uniform(0.05, 0.09) + UP * rnd.uniform(0.07, 0.12)
        pts = [Vector((0, 0, 0.01)), d * 0.02 + UP * 0.07, top]
        pt.add(gh.bm_sweep(gh.fillet_path(pts, 0.04), 0.0012, 6), "sb_petiole", tint=(1, 1, 1))
        fd = (d * 0.6 + UP).normalized()
        Mf = frame_matrix(top, fd, Vector((0, 0, 1)) if abs(fd.z) < 0.99 else Vector((1, 0, 0)))
        Mf = Mf @ xform(rot=(0, -90, 0))          # flower faces along fd
        for p in range(5):
            ang = TAU * p / 5 + rnd.uniform(-0.1, 0.1)
            pb = gh.bm_sphere(0.009, 10, 5, squash=0.12)
            fl.add(pb, "sb_petal", M=Mf @ xform((0.0085 * math.cos(ang), 0.0085 * math.sin(ang), 0.001), (0, 0, math.degrees(ang)),
                                                (1.05, 0.9, 1)))
        fl.add(gh.bm_sphere(0.0045, 12, 6, squash=0.6), "sb_centre", M=Mf @ xform((0, 0, 0.002)))
        for p in range(14):
            ang = TAU * p / 14
            fl.add(bm_cyl(0.0005, 0.003, 4), "sb_centre", M=Mf @ xform((0.0055 * math.cos(ang), 0.0055 * math.sin(ang), 0.002)))
    # berries: hang over the bed edge on the `outward` side
    nb = ripe + green
    for k in range(nb):
        a = math.radians(rnd.uniform(-55, 55)) + (math.pi / 2 if outward > 0 else -math.pi / 2)
        d = Vector((math.cos(a), math.sin(a), 0))
        reach = rnd.uniform(0.08, 0.16)
        hang = Vector((0, 0, 0.012)) + d * reach + UP * rnd.uniform(-0.01, 0.03)
        pts = [Vector((0, 0, 0.012)), d * reach * 0.4 + UP * 0.07, hang + UP * 0.02, hang]
        pt.add(gh.bm_sweep(gh.fillet_path(pts, 0.05), 0.0013, 6), "sb_petiole", tint=(1, 0.95, 0.85))
        is_ripe = k < ripe
        Lb = rnd.uniform(0.028, 0.04) if is_ripe else rnd.uniform(0.016, 0.026)
        Rb = Lb * rnd.uniform(0.62, 0.75)
        M = xform(tuple(hang), (rnd.uniform(-25, 25), rnd.uniform(-25, 25), rnd.uniform(0, 360)))
        if is_ripe:
            tint = (rnd.uniform(0.85, 1.1), rnd.uniform(0.8, 1.3), 1.0)
        else:
            tint = (rnd.choice((0.9, 1.2, 1.4)) * 1.0, 3.0, 1.6)  # pale green-white: multiplies the red base
        fr.add(berry_bm(Lb, Rb, rnd), berry_material("sb_berry"), M=M, tint=tint)
        n = 10
        for p in range(n):
            ang = TAU * p / n
            sp = gh.bm_sphere(0.008 if is_ripe else 0.006, 6, 4, squash=0.12)
            cx.add(sp, "sb_calyx", M=M @ xform((0.0065 * math.cos(ang), 0.0065 * math.sin(ang), 0.001),
                                                (0, -18, math.degrees(ang)), (1.0, 0.38, 1)))
    c.part("crown_stalks", pt, desc="Crown, leaf stalks, flower and fruit stalks.", smooth_angle=80)
    c.part("leaves", lv, desc="Trifoliate saw-toothed leaves." + (" Pale and cupped: powdery mildew." if sick else ""), smooth_angle=80)
    if not fl.empty():
        c.part("flowers", fl, desc="White 5-petal flowers.", smooth_angle=80)
    if not fr.empty():
        c.part("berries", fr, desc="Ripe and green berries hanging over the mulch.", smooth_angle=80)
        c.part("calyx", cx, desc="Green calyx (cap) on each berry.", smooth_angle=80)
    return c


# ─────────────────────────────── polyhouse structure ───────────────────────────────
def arch(y0, span, gutter, rise, n=14):
    """Gothic arch over one span: (y, z) from gutter to gutter, pointed at the ridge."""
    pts = []
    k = 0.82
    for i in range(n + 1):
        t = i / n
        u = t * 2 if t <= 0.5 else (1 - t) * 2
        z = gutter + rise * math.sin(u * math.pi / 2 * k) / math.sin(math.pi / 2 * k)
        pts.append((y0 + span * t, z))
    return pts


def film_strip(mb, pts, m, x0, x1, lift=0.0):
    for (ya, za), (yb, zb) in zip(pts[:-1], pts[1:]):
        L = math.hypot(yb - ya, zb - za)
        ang = math.degrees(math.atan2(zb - za, yb - ya))
        mb.box((x1 - x0, L + 0.01, 0.002), m, loc=((x0 + x1) / 2, (ya + yb) / 2, (za + zb) / 2 + lift), rot=(ang, 0, 0))


def polyhouse(cid="ph1", title="Soil-bed polyhouse", L=20.0, spans=2, span=8.0, gutter=4.0, rise=1.9, bay=4.0, door_y=None):
    """The structure only (frame, film, vents, net walls, door). Beds come from `beds()`."""
    c = Component(cid, title, "Structure",
                  summary="Naturally ventilated GI polyhouse: gothic arches, 200 µm UV film roof, roof vents, insect-net sides.",
                  real="NHB/MIDH-type naturally ventilated polyhouse, 8 m spans, 4 m bays")
    Y0 = -spans * span / 2
    xs = [bay * k for k in range(int(L / bay) + 1)]
    fr = MB()
    for i in range(spans + 1):
        y = Y0 + span * i
        for x in xs:
            fr.box((0.076, 0.076, gutter), "galv", loc=(x, y, gutter / 2))
            fr.cyl(0.11, 0.06, "concrete", segs=16, z0=-0.02, loc=(x, y, 0))
        fr.box((L, 0.2, 0.1), "galv", loc=(L / 2, y, gutter + 0.04))                      # gutter
    for s in range(spans):
        y0 = Y0 + span * s
        pts = arch(y0, span, gutter, rise)
        for x in xs:
            fr.sweep([(x, py, pz) for py, pz in pts], 0.024, "galv", segs=10)
            fr.box((0.03, span, 0.03), "galv", loc=(x, y0 + span / 2, gutter - 0.12))      # truss tie
            for f_ in (0.25, 0.75):                                                         # struts tie -> arch
                yy = y0 + span * f_
                zz = next(pz for py, pz in pts if py >= yy - 1e-6)
                fr.sweep([(x, yy, gutter - 0.12), (x, yy, zz)], 0.014, "galv", segs=8)
        for f_ in (0.22, 0.5, 0.78):                                                        # purlins
            yy = y0 + span * f_
            zz = max(pz for py, pz in pts if abs(py - yy) < span / 13) - 0.02
            fr.box((L, 0.03, 0.03), "galv", loc=(L / 2, yy, zz))
    c.part("frame", fr, desc="GI frame: 76 mm columns every 4 m, gutters, gothic arches, purlins, truss ties.")
    rf = MB()
    vn = MB()
    for s in range(spans):
        y0 = Y0 + span * s
        pts = arch(y0, span, gutter, rise)
        half = len(pts) // 2
        film_strip(rf, pts[:half - 1], "uv_film", 0, L)          # windward side up to the vent
        film_strip(rf, pts[half:], "uv_film", 0, L)
        film_strip(vn, pts[half - 1:half + 1], "net", 0, L, lift=-0.02)          # vent opening: insect net
        film_strip(vn, pts[half - 2:half], "uv_film", 0, L, lift=0.45)           # vent flap, raised
    c.part("film_roof", rf, desc="200 µm UV-stabilised diffused film.")
    c.part("roof_vents", vn, desc="Ridge vent on each span (net + film flap).")
    wl = MB()
    W = spans * span
    for y in (Y0, Y0 + W):
        wl.box((L, 0.006, gutter - 0.45), "net", loc=(L / 2, y, 0.45 + (gutter - 0.45) / 2))
        wl.box((L, 0.01, 0.45), "uv_film", loc=(L / 2, y, 0.225))
        wl.cyl(0.06, L, "uv_film", segs=14, axis="X", loc=(L / 2, y, 2.1))                  # rolled-up curtain
    dy = door_y if door_y is not None else Y0 + span / 2
    for x in (0.0, L):
        if x == 0.0:                                   # front gable: leave the doorway open (1.24 x 2.3 m)
            a, b = dy - 0.62, dy + 0.62
            wl.box((0.006, a - Y0, gutter), "uv_film", loc=(x, (Y0 + a) / 2, gutter / 2))
            wl.box((0.006, Y0 + W - b, gutter), "uv_film", loc=(x, (b + Y0 + W) / 2, gutter / 2))
            wl.box((0.006, b - a, gutter - 2.3), "uv_film", loc=(x, dy, 2.3 + (gutter - 2.3) / 2))
        else:
            wl.box((0.006, W, gutter), "uv_film", loc=(x, 0.0, gutter / 2))
        for s in range(spans):
            pts = arch(Y0 + span * s, span, gutter, rise)
            for (ya, za), (yb, zb) in zip(pts[:-1], pts[1:]):
                h = (za + zb) / 2 - gutter
                wl.box((0.006, abs(yb - ya) + 0.01, h), "uv_film", loc=(x, (ya + yb) / 2, gutter + h / 2))
    c.part("walls", wl, desc="40-mesh insect-net sides, 45 cm film skirt, roll-up curtains; film gables.")
    # door: double door in the front gable, 1.24 m clear (the rover needs ~0.5 m), both leaves swung open outward
    dr = MB()
    for sy in (-1, 1):
        dr.box((0.06, 0.06, 2.36), "galv", loc=(-0.01, dy + sy * 0.65, 1.18))
    dr.box((0.06, 1.36, 0.06), "galv", loc=(-0.01, dy, 2.33))
    for sy in (-1, 1):                                  # leaf: 25 mm GI frame + insect net, hinged at the jamb
        yh = dy + sy * 0.6
        for zz in (0.08, 1.1, 2.18):
            dr.box((0.6, 0.025, 0.025), "galv", loc=(-0.32, yh, zz))
        for xx in (-0.03, -0.61):
            dr.box((0.025, 0.025, 2.12), "galv", loc=(xx, yh, 1.13))
        dr.box((0.56, 0.004, 2.06), "net", loc=(-0.32, yh, 1.13))
        dr.cyl(0.012, 0.1, "steel_dark", segs=10, loc=(-0.01, yh, 0.45))
        dr.cyl(0.012, 0.1, "steel_dark", segs=10, loc=(-0.01, yh, 1.85))
    dr.box((2.9, 1.7, 0.08), "concrete", bevel=0.01, loc=(-1.45, dy, 0.0))                 # door apron (bath + mist arch)
    c.part("door", dr, desc="Double door (1.2 m) with insect-net leaves.")
    c.door_y = dy
    c.span_y0 = [Y0 + span * s for s in range(spans)]
    return c


# ─────────────────────────────── beds, mulch, drip ───────────────────────────────
def bed_profile(top, bottom, h, r=0.04):
    """Cross-section of a raised bed (y, z), rounded shoulders."""
    pts = [(-bottom / 2, 0.0)]
    for i in range(5):
        a = math.pi / 2 * i / 4
        pts.append((-top / 2 + r - r * math.cos(a), h - r + r * math.sin(a)))
    for i in range(5):
        a = math.pi / 2 * i / 4
        pts.append((top / 2 - r + r * math.sin(a), h - r + r * math.cos(a)))
    pts.append((bottom / 2, 0.0))
    return pts


def extrude_profile(mb, prof, x0, x1, m, yc=0.0, z0=0.0, nx=1, jitter=None, rnd=None, end_caps=True):
    bm = bmesh.new()
    rows = []
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx
        row = []
        for j, (y, z) in enumerate(prof):
            dz = 0.0
            if jitter and 0 < j < len(prof) - 1:
                dz = jitter * math.sin(x * 2.1 + j) * math.sin(x * 0.7)
            row.append(bm.verts.new((x, yc + y, z0 + z + dz)))
        rows.append(row)
    for i in range(nx):
        for j in range(len(prof) - 1):
            bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    if end_caps:
        bm.faces.new(list(reversed(rows[0])))
        bm.faces.new(rows[-1])
    mb.add(bm, m)


def beds(cid, crop, x0, x1, y_centres, plant_cb=None, seed=1):
    """Raised soil beds under silver mulch with drip laterals; `plant_cb(x, y, z, k)` places each plant."""
    P = TM if crop == "tomato" else SB
    rnd = random.Random(seed)
    c = Component(cid, f"Raised beds ({crop})", "Beds",
                  summary=(f"{len(y_centres)} raised soil beds, {int(P['top'] * 100)} cm wide, {int(P['h'] * 100)} cm high, "
                           f"{int(round((P['pitch'] - P['bottom']) * 100))} cm paths. Silver mulch on top repels whitefly and thrips."),
                  real="Raised soil beds, 25-30 µm silver/black mulch, 16 mm inline drip laterals")
    sb, ml, dp, ho = MB(), MB(), MB(), MB()
    prof = bed_profile(P["top"], P["bottom"], P["h"])
    # the film lies over the whole bed (top and both sides) and is buried at the foot under a ridge of soil
    mprof = bed_profile(P["top"] + 0.008, P["bottom"] + 0.006, P["h"] + 0.004, r=0.045)
    mprof = [(mprof[0][0], 0.012)] + mprof[1:-1] + [(mprof[-1][0], 0.012)]
    positions = []
    for yc in y_centres:
        extrude_profile(sb, prof, x0, x1, "soil_bed", yc=yc, nx=1)
        extrude_profile(ml, mprof, x0 + 0.02, x1 - 0.02, "mulch_silver", yc=yc, nx=int((x1 - x0) / 0.5), jitter=0.004)
        for sy in (-1, 1):                                    # soil heaped on the buried mulch edge
            ml.sweep([(x0, yc + sy * (P["bottom"] / 2 + 0.01), 0.0), (x1, yc + sy * (P["bottom"] / 2 + 0.01), 0.0)], 0.03,
                     "soil_bed", segs=8, flat=None)
        for ry in P["rows"]:
            y = yc + ry
            dp.sweep([(x0 - 0.35, y, P["h"] + 0.012), (x1 - 0.05, y, P["h"] + 0.012)], 0.008, "drip_black", segs=8)
            dp.sweep(gh.fillet_path([(x0 - 0.35, y, P["h"] + 0.012), (x0 - 0.5, y, P["h"] * 0.4), (x0 - 0.6, y, 0.03)], 0.06),
                     0.008, "drip_black", segs=8)
            dp.cyl(0.012, 0.03, "plastic_green", segs=12, axis="X", loc=(x0 - 0.61, y, 0.03))        # start connector
            n = int((x1 - x0 - 0.3) / P["spacing"])
            for k in range(n):
                x = x0 + 0.25 + k * P["spacing"] + rnd.uniform(-0.02, 0.02)
                ho.cyl(0.045 if crop == "tomato" else 0.05, 0.004, "soil_bed", segs=14, loc=(x, y + rnd.uniform(-0.01, 0.01), P["h"] + 0.006))
                positions.append((x, y, P["h"] + 0.004, yc))
                dp.cyl(0.0105, 0.012, "drip_black", segs=10, axis="X", loc=(x + 0.12, y, P["h"] + 0.012))   # emitter bump
    # sub-main header across the bed ends
    yl = min(y_centres) - P["pitch"] / 2
    yr = max(y_centres) + P["pitch"] / 2
    dp.sweep([(x0 - 0.63, yl, 0.005), (x0 - 0.63, yr, 0.005)], 0.032, "pvc_grey", segs=16)      # half buried: the rover rolls over it
    c.part("soil", sb, desc="Raised soil beds (organic soil + farmyard manure).")
    c.part("mulch", ml, desc="Silver-on-black mulch film tucked into the soil at the bed foot; planting holes cut through it.")
    c.part("drip", dp, desc="16 mm inline drip laterals (one per plant row) from a 63 mm sub-main header.")
    c.part("holes", ho, desc="Planting holes in the mulch.")
    c.positions = positions
    c.P = P
    return c


def path_floor(cid, x0, x1, y0, y1, seed=3, res=0.25):
    """The soil floor of the house: a gently uneven grid with a few pruned leaves lying in the paths."""
    rnd = random.Random(seed)
    c = Component(cid, "Path soil", "Site", summary="Bare soil paths.")
    bm = bmesh.new()
    nx, ny = int((x1 - x0) / res), int((y1 - y0) / res)
    vs = []
    for i in range(nx + 1):
        row = []
        for j in range(ny + 1):
            x, y = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
            z = 0.012 * math.sin(x * 1.3 + 0.7 * math.sin(y * 2.1)) * math.sin(y * 3.3 + x * 0.4) - 0.004
            row.append(bm.verts.new((x, y, z)))
        vs.append(row)
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    mb = MB()
    mb.add(bm, soil_material())
    c.part("floor", mb, smooth_angle=80)
    return c


def dead_leaves(cid, spots, seed=5):
    """Pruned tomato leaves lying in the paths (spots: list of (x, y))."""
    rnd = random.Random(seed)
    from components.plant import leaflet_bm
    c = Component(cid, "Pruned leaves", "Site")
    mb = MB()
    for (x, y) in spots:
        for k in range(rnd.randint(2, 5)):
            L = rnd.uniform(0.05, 0.09)
            b = leaflet_bm(L, L * 0.6, rnd, droop=0.02, fold=0.5)
            t = rnd.uniform(0.6, 1.0)
            mb.add(b, "dead_leaf", loc=(x + rnd.uniform(-0.12, 0.12), y + rnd.uniform(-0.08, 0.08), 0.01),
                   rot=(rnd.uniform(-15, 15), rnd.uniform(-10, 10), rnd.uniform(0, 360)), tint=(t, t * rnd.uniform(0.8, 1.1), t * 0.8))
    c.part("leaves", mb, smooth_angle=80)
    return c


def crop_wires(cid, x0, x1, rows_y, z=3.0):
    c = Component(cid, "Crop wires", "Structure", summary="GI crop wires over each tomato row; the plants' strings hang from them.")
    mb = MB()
    for y in rows_y:
        mb.sweep([(x0, y, z), (x1, y, z)], 0.0018, "galv", segs=6)
    c.part("wires", mb)
    return c
