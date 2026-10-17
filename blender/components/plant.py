"""Procedural greenhouse tomato plant (indeterminate, single stem on a string) with its own digital identity.

Stages: seedling → young (at planting) → flowering → fruiting (production).
Origin = top centre of the plant's cube (the cube sits on the coco slab).
"""
import json
import math
import random

import bmesh
from mathutils import Matrix, Vector

from gh import MB, TAU, Component, bm_box, bm_cyl, fillet_path, xform

UP = Vector((0, 0, 1))
DETAIL = 1.0   # 0.5 for the web build (fewer vertices per leaflet / fruit)
FRUIT_COL = {"green": (0.22, 0.42, 0.07), "breaker": (0.55, 0.47, 0.1), "turning": (0.78, 0.33, 0.06),
             "pink": (0.78, 0.14, 0.05), "red": (0.62, 0.035, 0.012)}


# ─────────────────────────────── low-level organ meshes ───────────────────────────────
def leaflet_bm(L, W, rnd, droop=0.25, fold=0.35, lobes=0.14, nu=8, nv=5, young=False):
    """One leaflet in its local frame: +x along the blade, +y across, +z = upper surface."""
    bm = bmesh.new()
    ph = rnd.uniform(0, TAU)
    rows = []
    for i in range(nu + 1):
        u = i / nu
        w = 0.5 * W * max(math.sin(math.pi * min(u, 0.999) ** 0.62), 0.0) ** 0.7
        if 0.12 < u < 0.92:
            w *= 1 + lobes * math.sin(u * 7 * math.pi + ph)
        w = max(w, 0.0008 if i < nu else 0.0002)
        row = []
        for j in range(nv):
            v = -1 + 2 * j / (nv - 1)
            x = u * L
            y = v * w
            z = abs(v) * w * fold - (u ** 2) * L * droop
            if young:
                z += abs(v) * w * 0.5  # young leaflets are folded more
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    for i in range(nu):
        for j in range(nv - 1):
            bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
    return bm


def frame_matrix(origin, fwd, up):
    f = fwd.normalized()
    s = up.cross(f).normalized()
    u = f.cross(s).normalized()
    M = Matrix((f, s, u)).transposed().to_4x4()
    M.translation = origin
    return M


def fruit_bm(r, rnd, squash=0.82, lobes=5, amp=0.045, rings=12, segs=22):
    bm = bmesh.new()
    ph = rnd.uniform(0, TAU)
    verts = []
    top = bm.verts.new((0, 0, r * squash * 0.9))
    bot = bm.verts.new((0, 0, -r * squash * 0.95))
    for i in range(1, rings):
        phi = math.pi * i / rings
        ring = []
        for j in range(segs):
            th = TAU * j / segs
            rr = r * math.sin(phi) * (1 + amp * math.cos(lobes * th + ph) * math.sin(phi) ** 2)
            z = -r * squash * math.cos(phi)
            if i <= 2:
                z -= r * 0.06  # shallow shoulder dip at the stem end? (top is +z; keep bottom round)
            ring.append(bm.verts.new((rr * math.cos(th), rr * math.sin(th), -z)))
        verts.append(ring)
    for i in range(len(verts) - 1):
        A, B = verts[i], verts[i + 1]
        for j in range(segs):
            j1 = (j + 1) % segs
            bm.faces.new((A[j], A[j1], B[j1], B[j]))
    for j in range(segs):
        j1 = (j + 1) % segs
        bm.faces.new((top, verts[0][j1], verts[0][j]))
        bm.faces.new((bot, verts[-1][j], verts[-1][j1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def sepal_star_bm(n, L, W, droop, rnd):
    """Calyx: n narrow green sepals radiating from the centre, curling downward."""
    bm = bmesh.new()
    for k in range(n):
        a = TAU * k / n + rnd.uniform(-0.2, 0.2)
        d = Vector((math.cos(a), math.sin(a), 0))
        s = Vector((-math.sin(a), math.cos(a), 0))
        pts_l, pts_r = [], []
        for i in range(5):
            u = i / 4
            w = W * (1 - u) * (0.6 if i == 0 else 1)
            p = d * (L * u) + Vector((0, 0, -droop * u * u))
            pts_l.append(bm.verts.new(p + s * w / 2))
            pts_r.append(bm.verts.new(p - s * w / 2))
        for i in range(4):
            bm.faces.new((pts_r[i], pts_r[i + 1], pts_l[i + 1], pts_l[i]))
    return bm


def flower_bm(rnd, size=0.011, open_=1.0):
    """Tomato flower: 5–6 reflexed yellow petals + anther cone. Axis = +z (the flower faces +z)."""
    bm_p = bmesh.new()
    n = rnd.choice((5, 6, 6))
    for k in range(n):
        a = TAU * k / n + rnd.uniform(-0.1, 0.1)
        d = Vector((math.cos(a), math.sin(a), 0))
        s = Vector((-math.sin(a), math.cos(a), 0))
        L = size * rnd.uniform(0.9, 1.1)
        row_l, row_r = [], []
        for i in range(5):
            u = i / 4
            w = size * 0.32 * math.sin(math.pi * min(u * 0.9 + 0.08, 1.0))
            back = -size * 0.9 * open_ * u * u  # petals bend backwards when open
            p = d * (L * u * (0.4 + 0.6 * open_)) + Vector((0, 0, back + size * 0.2 * (1 - open_) * u))
            row_l.append(bm_p.verts.new(p + s * w))
            row_r.append(bm_p.verts.new(p - s * w))
        for i in range(4):
            bm_p.faces.new((row_r[i], row_r[i + 1], row_l[i + 1], row_l[i]))
    return bm_p


def qr_modules(seed_txt, n=21):
    rnd = random.Random(seed_txt)
    grid = [[rnd.random() < 0.5 for _ in range(n)] for _ in range(n)]

    def finder(r0, c0):
        for i in range(7):
            for j in range(7):
                on = i in (0, 6) or j in (0, 6) or (2 <= i <= 4 and 2 <= j <= 4)
                grid[r0 + i][c0 + j] = on
        for i in range(-1, 8):
            for j in range(-1, 8):
                ii, jj = r0 + i, c0 + j
                if 0 <= ii < n and 0 <= jj < n and not (0 <= i < 7 and 0 <= j < 7):
                    grid[ii][jj] = False
    finder(0, 0)
    finder(0, n - 7)
    finder(n - 7, 0)
    return grid


# ─────────────────────────────── stage presets ───────────────────────────────
STAGES = {
    # nodes, height, leaf length (max), removed lower leaves, trusses [(node, kind)]
    "seedling": dict(nodes=2, H=0.075, leaf=0.07, removed=0, trusses=[], cotyledons=True),
    "young": dict(nodes=7, H=0.33, leaf=0.24, removed=0, trusses=[(7, "buds")], cotyledons=False),
    "flowering": dict(nodes=12, H=0.85, leaf=0.44, removed=0,
                      trusses=[(7, "set"), (10, "flowers"), (12, "buds")], cotyledons=False),
    "fruiting": dict(nodes=26, H=1.85, leaf=0.5, removed=8,
                     trusses=[(8, "red"), (11, "red"), (14, "turning"), (17, "green_big"), (20, "green_small"),
                              (23, "flowers"), (26, "buds")], cotyledons=False),
}


def tomato_plant(cid="plant_042", title=None, stage="fruiting", seed=42, row=3, slab=2, slot=3, disease=False,
                 with_string=True, with_tag=True, cube=True, plant_no=None, string_top=2.1):
    rnd = random.Random(seed)
    P = STAGES[stage]
    no = plant_no if plant_no is not None else int("".join(ch for ch in cid if ch.isdigit()) or 42)
    tag = f"#{no:03d}"
    state = plant_state(tag, stage, row, slab, slot, disease)
    c = Component(
        cid, title or f"Tomato plant {tag} ({stage})", "Plants",
        summary=f"Plant {tag}: row {row}, slab {slab}, slot {slot}. Every plant has its own record (its digital identity).",
        how=("The robot photographs this plant from 5 heights twice a week and links every image to this ID via the tag. "
             "From the images + depth it measures stem growth, leaf count, truss height, flowers and fruit per truss with "
             "ripeness. The slab scale and drip meter give its water use; together they build its history and a harvest "
             "forecast (fruit ripen ~7–9 weeks after flowering, faster when warm)."),
        sensors=("robot stereo cameras", "canopy camera", "slab scale (its slab)", "substrate sensor (row)"),
        control="Receives water/nutrients by row zone; individual actions are human (pruning, harvest) guided by the twin.",
        state=state,
        real="Indeterminate truss tomato on coco, high-wire string system", cost="—")
    c.root["plant_id"] = tag
    stem = MB()
    leaves = MB()
    fl = MB()
    fr = MB()
    sy = MB()
    H = P["H"]
    nodes = P["nodes"]
    # stem centre-line with a gentle wobble and zig-zag at trusses
    npts = max(8, int(H / 0.02))
    wob = [rnd.uniform(0, TAU) for _ in range(3)]
    spine = []
    for i in range(npts + 1):
        t = i / npts
        z = H * t
        x = 0.012 * math.sin(t * 9 + wob[0]) * t + 0.006 * math.sin(t * 23 + wob[1])
        y = 0.012 * math.sin(t * 7 + wob[2]) * t
        spine.append(Vector((x, y, z)))
    r0 = {"seedling": 0.0018, "young": 0.004, "flowering": 0.0065, "fruiting": 0.0075}[stage]
    radii = [r0 * (1 - 0.45 * (i / npts)) for i in range(npts + 1)]
    stem.add(__import__("gh").bm_sweep(spine, r0, 10, True, radii), "stem", tint=(1, 1, 1))

    def spine_at(z):
        t = max(0.0, min(1.0, z / H))
        k = t * npts
        i = min(int(k), npts - 1)
        f = k - i
        return spine[i].lerp(spine[i + 1], f)

    truss_nodes = {n: k for n, k in P["trusses"]}
    phi = rnd.uniform(0, TAU)
    # cotyledons (seedling)
    if P.get("cotyledons"):
        for s in (-1, 1):
            b = leaflet_bm(0.028, 0.008, rnd, droop=0.1, fold=0.2, lobes=0.0, nu=6, nv=3)
            M = frame_matrix(spine_at(H * 0.55), Vector((s * math.cos(phi), s * math.sin(phi), 0.35)), UP)
            leaves.add(b, "cotyledon", M=M, tint=(1, 1, 1))
    spots_on = set()
    if disease:
        spots_on = {P["removed"] + 1, P["removed"] + 2}
    for n in range(1, nodes + 1):
        z = H * (n - 0.35) / nodes if stage != "seedling" else H * (0.75 + 0.2 * n / nodes)
        base = spine_at(z)
        phi += math.radians(137.5 + rnd.uniform(-15, 15))
        age = (nodes - n) / max(nodes - 1, 1)          # 1 = oldest (bottom), 0 = youngest (top)
        if n <= P["removed"]:
            # leaf removed (de-leafing): leave a small scar
            stem.add(bm_cyl(0.004, 0.006, 8), "stem_old", M=frame_matrix(base, Vector((math.cos(phi), math.sin(phi), 0.3)), UP)
                     @ xform(rot=(0, 90, 0)))
            continue
        Ll = P["leaf"] * (0.35 + 0.65 * min(1.0, 0.25 + age * 1.6)) * rnd.uniform(0.9, 1.1)
        if stage == "seedling":
            Ll = P["leaf"] * (0.7 + 0.3 * n)
        e0 = 0.75 - 0.35 * age                       # young leaves point up, old ones spread
        dirh = Vector((math.cos(phi), math.sin(phi), 0))
        side = UP.cross(dirh).normalized()
        curl = rnd.uniform(-0.06, 0.06)
        pts = []
        for i in range(11):
            t = i / 10
            h = Ll * t * 0.95
            zz = Ll * (e0 * t - (0.45 + 0.5 * age) * t * t)
            pts.append(base + dirh * (h + 0.005) + UP * zz + side * (curl * Ll * t * t))
        rr = [0.0028 * (Ll / 0.4) * (1 - 0.7 * i / 10) + 0.0006 for i in range(11)]
        stem.add(__import__("gh").bm_sweep(pts, 0.002, 6, True, rr), "stem", tint=(1, 1, 1))

        def rachis(t):
            k = t * 10
            i = min(int(k), 9)
            f = k - i
            p = pts[i].lerp(pts[i + 1], f)
            tan = (pts[i + 1] - pts[i]).normalized()
            return p, tan
        leaf_bm = bmesh.new()
        lt = rnd.uniform(0.85, 1.12)
        yellow = age > 0.85 and stage == "fruiting" and rnd.random() < 0.6
        tint = (lt * 1.25, lt * 1.1, lt * 0.55) if yellow else (lt, lt * rnd.uniform(0.95, 1.05), lt)
        pairs = [(0.22, 0.55), (0.4, 0.85), (0.57, 1.0), (0.72, 0.95), (0.86, 0.78)]
        if stage == "seedling":
            pairs = [(0.55, 0.8)]
        LW = 0.25 * Ll if stage != "seedling" else 0.4 * Ll
        young = age < 0.15
        items = []
        for t, sc in pairs:
            for s in (-1, 1):
                items.append((t, sc, s))
        items.append((1.0, 1.05, 0))
        if stage != "seedling":
            for t in (0.31, 0.49, 0.65, 0.79):
                for s in (-1, 1):
                    items.append((t, 0.3, s))
        for t, sc, s in items:
            p, tan = rachis(min(t, 0.999))
            upv = (UP - tan * UP.dot(tan)).normalized()
            sd = tan.cross(upv).normalized()
            if s == 0:
                f = tan
            else:
                a = math.radians(rnd.uniform(35, 55))
                f = (sd * s * math.cos(a) + tan * math.sin(a)).normalized()
                f = (f - upv * rnd.uniform(0.0, 0.25)).normalized()
            upl = (upv + sd * s * rnd.uniform(-0.2, 0.2)).normalized()
            Lf = LW * sc * rnd.uniform(0.9, 1.1)
            b = leaflet_bm(Lf, Lf * 0.62, rnd, droop=0.18 + 0.12 * age, young=young, lobes=0.18,
                           nu=max(4, round(8 * DETAIL)), nv=3 if DETAIL < 0.8 else 5)
            M = frame_matrix(p, f, upl)
            for v in b.verts:
                v.co = M @ v.co
            bmesh.ops.translate(b, verts=b.verts, vec=(0, 0, 0))
            # merge into this leaf's bmesh
            vmap = {}
            for v in b.verts:
                vmap[v] = leaf_bm.verts.new(v.co)
            for fc in b.faces:
                leaf_bm.faces.new([vmap[v] for v in fc.verts])
            if n in spots_on and s != 0 and rnd.random() < 0.8:
                for _ in range(rnd.randint(2, 5)):
                    q = M @ Vector((Lf * rnd.uniform(0.25, 0.8), Lf * rnd.uniform(-0.12, 0.12), 0.0015))
                    sy.add(bmesh_disc(0.004 * rnd.uniform(0.6, 1.3)), "soil", M=frame_matrix(q, f, upl), tint=(1, 1, 1))
            b.free()
        leaves.add(leaf_bm, "leaf", tint=(tint[0] * (0.85 if n in spots_on else 1), tint[1] * (0.8 if n in spots_on else 1),
                                          tint[2] * (0.5 if n in spots_on else 1)))
        # truss between leaves
        if n in truss_nodes:
            kind = truss_nodes[n]
            add_truss(stem, fl, fr, spine_at(z + H / nodes * 0.5), phi + math.pi * rnd.uniform(0.8, 1.2), kind, rnd)
    c.part("stem", stem, desc="Main stem + leaf stalks. Bare lower stem = old leaves removed (de-leafing).",
           smooth_angle=80)
    c.part("leaves", leaves, explode=(0.0, -0.25, 0.1),
           desc="Compound leaves (5–9 leaflets). Their area drives transpiration and photosynthesis.", smooth_angle=80)
    if not fl.empty():
        c.part("flowers", fl, explode=(0.0, -0.45, 0.2),
               desc="Open flowers on the upper trusses – the robot pollinates these with air pulses.", smooth_angle=80)
    if not fr.empty():
        c.part("fruit", fr, explode=(0.0, -0.35, 0.0),
               desc="Fruit: red at the bottom (oldest truss) → green higher up. Count + colour → yield forecast.",
               smooth_angle=80)
    if not sy.empty():
        c.part("leaf_spots", sy, explode=(0.0, -0.3, 0.05),
               desc="Brown leaf spots on 2 lower leaves – flagged by the robot's vision (possible early blight). Human check.",
               smooth_angle=80)
    # cube + roots
    if cube:
        cb = MB()
        cb.box((0.1, 0.1, 0.065), "rockwool", bevel=0.004, loc=(0, 0, -0.0325))
        cb.add(bm_box(0.102, 0.102, 0.045), "pe_black", loc=(0, 0, -0.04))
        c.part("cube", cb, explode=(0, 0, -0.12), desc="Propagation cube (10 cm) the plant started in; sits in the slab.")
        rt = MB()
        for k in range(10):
            a = TAU * k / 10 + rnd.uniform(-0.2, 0.2)
            L = rnd.uniform(0.08, 0.18)
            pts = [Vector((0.02 * math.cos(a), 0.02 * math.sin(a), -0.06))]
            for i in range(1, 6):
                t = i / 5
                pts.append(Vector((math.cos(a) * (0.02 + L * t), math.sin(a) * (0.02 + L * t) * 0.35,
                                   -0.065 - 0.04 * t * t + rnd.uniform(-0.004, 0.004))))
            rt.add(__import__("gh").bm_sweep(pts, 0.0012, 5, True), "plastic_cream")
        c.part("roots", rt, explode=(0, 0, -0.22), desc="Roots growing out of the cube into the coco slab (white = healthy).")
    if with_string:
        st = MB()
        top = string_top
        spts = [Vector((0.0, 0.012, top))] + [spine_at(z) + Vector((0.009 * math.cos(z * 18), 0.009 * math.sin(z * 18), 0))
                                              for z in [H - H * i / 30 for i in range(31)]]
        st.add(__import__("gh").bm_sweep(spts, 0.0012, 5, True), "twine")
        for z in [H * f for f in (0.25, 0.5, 0.75)]:
            p = spine_at(z)
            st.add(__import__("gh").bm_torus(0.011, 0.0018, 16, 6), "plastic_white", loc=tuple(p))
        st.add(__import__("gh").bm_cyl(0.02, 0.012, 16), "plastic_green", loc=(0.0, 0.012, top + 0.03))
        st.add(__import__("gh").bm_torus(0.012, 0.002, 16, 6), "stainless", loc=(0.0, 0.012, top + 0.06), rot=(90, 0, 0))
        c.part("string_hook", st, explode=(0.0, 0.2, 0.0),
               desc="Support string + roller hook on the crop wire; clips hold the stem. Plants are lowered as they grow.")
    if with_tag:
        c.part("id_tag", tag_mb(tag, row, slab, slot), loc=(0.0, -0.075, 0.0), explode=(0.0, -0.2, 0.08),
               desc=f"ID tag {tag} with QR code – the robot reads it so every photo is saved to this plant's record.")
    return c


def tag_mb(tag, row, slab, slot):
    tg = MB()
    tg.box((0.004, 0.004, 0.14), "plastic_white", loc=(0, 0, -0.07))
    tg.box((0.075, 0.003, 0.048), "plastic_white", bevel=0.001, loc=(0.0, 0.0, 0.02))
    grid = qr_modules(tag)
    n = len(grid)
    cell = 0.036 / n
    for i in range(n):
        for j in range(n):
            if grid[i][j]:
                tg.box((cell, 0.0008, cell), "plastic_black", loc=(-0.035 + 0.003 + j * cell + cell / 2, -0.0018,
                                                                   0.02 + 0.018 - i * cell - cell / 2))
    tg.text(tag, 0.016, "plastic_black", loc=(0.019, -0.0018, 0.026), rot=(90, 0, 0), bold=True)
    tg.text(f"R{row} S{slab} P{slot}", 0.0075, "plastic_green", loc=(0.019, -0.0018, 0.008), rot=(90, 0, 0), bold=True)
    return tg


def tag_mb_web(n, row, slab, slot, cols=9, rows=6):
    """Web version of the ID tag: one textured plate cut from the shared tag atlas (tools/make_tags.py)."""
    from pathlib import Path
    from gh import image_mat
    tg = MB()
    tg.box((0.004, 0.004, 0.14), "plastic_white", loc=(0, 0, -0.07))
    tg.box((0.078, 0.004, 0.051), "plastic_white", loc=(0.0, 0.001, 0.02))
    m = image_mat("tag_atlas", Path(__file__).resolve().parents[1] / "assets" / "tag_atlas.png", rough=0.6)
    col, ri = (n - 1) % cols, (n - 1) // cols
    tg.add(bm_box(0.075, 0.048, 0.001), m, M=xform((0.0, -0.0012, 0.02), (90, 0, 0)),
           planar_uv=(0, 1, 1 / (0.075 * cols), 1 / (0.048 * rows), (0.5 + col) / cols, (0.5 + rows - 1 - ri) / rows))
    return tg


def plant_state(tag, stage, row, slab, slot, disease):
    P = STAGES[stage]
    fruit_counts = {}
    for _, kind in P["trusses"]:
        fruit_counts[kind] = fruit_counts.get(kind, 0) + (0 if kind in ("buds", "flowers") else 5)
    return {
        "plant_id": tag, "row": row, "slab": slab, "slot": slot, "variety": "Truss tomato (indeterminate)",
        "stage": stage, "planted": "2026-07-04", "height_m": round(P["H"], 2),
        "stem_growth_cm_week": 24.5 if stage == "fruiting" else 18.0,
        "trusses": len(P["trusses"]), "flowering_truss": sum(1 for _, k in P["trusses"] if k == "flowers"),
        "fruit": {"red": fruit_counts.get("red", 0), "turning": fruit_counts.get("turning", 0),
                  "green": fruit_counts.get("green_big", 0) + fruit_counts.get("green_small", 0) + fruit_counts.get("set", 0)},
        "water_status": "OK – slab uptake normal", "health": "leaf spots on 2 lower leaves (check)" if disease else "healthy",
        "expected_harvest": "2026-10-02 · 0.9 kg" if stage == "fruiting" else "—",
    }


def bmesh_disc(r, segs=10):
    return bm_cyl(r, 0.0008, segs)


def add_truss(stem, fl, fr, base, az, kind, rnd):
    """A truss (inflorescence) leaving the stem at `base` in direction az."""
    d = Vector((math.cos(az), math.sin(az), 0))
    s = UP.cross(d).normalized()
    n = {"red": 5, "turning": 5, "green_big": 5, "green_small": 6, "set": 5, "flowers": 7, "buds": 6}[kind]
    L0 = 0.05
    pts = [base, base + d * L0 * 0.5 + UP * 0.01, base + d * L0 - UP * 0.01]
    for i in range(n):
        pts.append(pts[-1] + d * 0.018 + s * (0.012 if i % 2 else -0.012) - UP * (0.012 if kind != "buds" else 0.004))
    stem.add(__import__("gh").bm_sweep(fillet_path(pts, 0.008), 0.0022, 6, True), "stem", tint=(1, 1, 1))
    for i in range(n):
        p = pts[3 + i]
        side = s * (1 if i % 2 else -1)
        if kind in ("red", "turning", "green_big", "green_small", "set"):
            r = {"red": 0.03, "turning": 0.03, "green_big": 0.028, "green_small": 0.02, "set": 0.012}[kind]
            r *= rnd.uniform(0.88, 1.08) * (1 - 0.05 * i)
            if kind == "red":
                col = FRUIT_COL["red"] if i < 4 else FRUIT_COL["pink"]
            elif kind == "turning":
                col = FRUIT_COL["pink"] if i < 2 else (FRUIT_COL["turning"] if i < 4 else FRUIT_COL["breaker"])
            else:
                col = FRUIT_COL["green"]
            knuckle = p + side * 0.02 - UP * 0.01
            stem.add(__import__("gh").bm_sweep([p, p + side * 0.012, knuckle], 0.0014, 6, True), "stem", tint=(1, 1, 1))
            c = knuckle + side * r * 0.35 - UP * r * 0.95
            fr.add(fruit_bm(r, rnd, rings=max(7, round(12 * DETAIL)), segs=max(12, round(22 * DETAIL))), "fruit", loc=tuple(c), rot=(rnd.uniform(-15, 15), rnd.uniform(-15, 15), rnd.uniform(0, 360)),
                   tint=col)
            stem.add(sepal_star_bm(6, r * 0.55, r * 0.22, r * 0.2, rnd), "sepal",
                     M=xform(tuple(c + UP * r * 0.8)), tint=(1, 1, 1))
        else:
            tip = p + side * 0.022 + d * 0.005 - UP * 0.012
            stem.add(__import__("gh").bm_sweep([p, p + side * 0.012, tip], 0.001, 5, True), "stem", tint=(1, 1, 1))
            fdir = (side * 0.6 - UP * 0.8 + d * 0.3).normalized()
            M = _look(tip, fdir)
            if kind == "flowers" and i < 5:
                fl.add(flower_bm(rnd, 0.011, 1.0 if i < 4 else 0.3), "flower", M=M, tint=(1, 1, 1))
                fl.add(bm_cyl(0.0028, 0.008, 10, 0.0, 0.0012, 0.0), "anther", M=M, tint=(1, 1, 1))
                stem.add(sepal_star_bm(5, 0.008, 0.002, 0.003, rnd), "sepal", M=M @ xform((0, 0, -0.001), (180, 0, 0)),
                         tint=(1, 1, 1))
            else:  # bud
                fl.add(__import__("gh").bm_sphere(0.0035, 10, 6, 1.6), "sepal", M=M, tint=(1, 1, 1))


def _look(p, z_dir):
    z = z_dir.normalized()
    ref = Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((1, 0, 0))
    x = ref.cross(z).normalized()
    y = z.cross(x)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = p
    return M


# catalog wrappers: the same plant (#042) at four points of its life
def plant_seedling():
    return tomato_plant("plant_042_w03", "Plant #042 · seedling (week 3)", "seedling", seed=3, with_string=False,
                        plant_no=42)


def plant_young():
    return tomato_plant("plant_042_w05", "Plant #042 · at planting (week 5)", "young", seed=5, with_string=False,
                        plant_no=42)


def plant_flowering():
    return tomato_plant("plant_042_w09", "Plant #042 · flowering (week 9)", "flowering", seed=9, plant_no=42,
                        string_top=1.0)


def plant_fruiting():
    return tomato_plant("plant_042", "Plant #042 · production (week 13)", "fruiting", seed=42, disease=True)
