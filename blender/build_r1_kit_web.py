"""Export the R1 rover as a kit for the website's "Build R1" scene (10 Nov 2026): the 43 parts of
components/rover_kit.py, each one its own node, plus where each part lies on the blue tarp before it is fitted
(the same knolling as the Build R1 videos). The web (js/buildr1.js) flies the parts from the tarp onto the rover,
one build step at a time (the 9 steps of build/02-r1-rover/README.md).

  assets/r1_kit.glb.json   the parts in their fitted place (gzip + base64 glb, like the other assets)
  assets/r1_kit.json       per part: name, step, label, note, tarp pose [x, y, z, qw, qx, qy, qz] (Blender coordinates,
                           relative to the rover's origin) + the tarp's centre and size

  blender -b --factory-startup -P blender/build_r1_kit_web.py
"""
import base64
import gzip
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / "lib"), str(HERE), str(HERE / "components")]
import bpy  # noqa: E402
from mathutils import Euler, Matrix, Vector as V  # noqa: E402

import gh  # noqa: E402
import webexport  # noqa: E402
from components import rover_kit as RK  # noqa: E402

A = HERE.parent / "assets"
if not A.exists():
    A = HERE.parent / "web" / "assets"
gh.TEXT_RES = 6
WIRES = {"power_cables", "phase_wires", "tubes"}           # fitted in place, never laid on the tarp
STEPS = ["Frame", "Wheels", "Heavy parts low", "Power", "Motor drivers", "Brain", "Mast and cameras", "Sprayer",
         "Safety and sensing"]

t0 = time.time()
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
sc = bpy.context.scene
coll = gh.get_coll("Kit", scene=sc)
gh.set_collection(coll)
kit = RK.build(coll)
bpy.context.view_layer.update()


def piece_objs(p):
    return [p.ob] + gh.descendants(p.ob)


def bbox(p, M=None):
    pts = []
    for o in piece_objs(p):
        if o.type == "MESH":
            W = o.matrix_world if M is None else M @ (ASM[p.name].inverted() @ o.matrix_world)
            pts += [W @ V(c) for c in o.bound_box]
    return (V((min(v.x for v in pts), min(v.y for v in pts), min(v.z for v in pts))),
            V((max(v.x for v in pts), max(v.y for v in pts), max(v.z for v in pts))))


ASM = {p.name: p.ob.matrix_world.copy() for p in kit.pieces}
flat = [p for p in kit.pieces if p.name not in WIRES]

# 1. turn every part so it lies flat (lowest side up), long side along x
ROT = [Euler((0, 0, 0)), Euler((math.pi / 2, 0, 0)), Euler((0, math.pi / 2, 0))]
KN = {}
for p in flat:
    lo, hi = bbox(p)
    c, d = (lo + hi) / 2, hi - lo
    best = None
    for e in ROT:
        Rm = e.to_matrix()
        cs = [Rm @ V((sx * d.x / 2, sy * d.y / 2, sz * d.z / 2)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        ex = V((max(v.x for v in cs) - min(v.x for v in cs), max(v.y for v in cs) - min(v.y for v in cs),
                max(v.z for v in cs) - min(v.z for v in cs)))
        if best is None or ex.z < best[1].z - 1e-4:
            best = (e, ex)
    e, ex = best
    if ex.y > ex.x:
        e = (Euler((0, 0, math.pi / 2)).to_matrix() @ e.to_matrix()).to_euler()
        ex = V((ex.y, ex.x, ex.z))
    KN[p.name] = Matrix.Translation(V((0, 0, ex.z / 2 + 0.002))) @ e.to_quaternion().to_matrix().to_4x4() @ Matrix.Translation(-c) @ ASM[p.name]

# 2. pack them into tidy rows, in build order (step 1 at the back, step 9 at the front)
rows_in = []
for p in flat:
    lo, hi = bbox(p, KN[p.name])
    rows_in.append((p, hi.x - lo.x, hi.y - lo.y, (lo + hi) / 2))
ROW_W, GAP = 2.3, 0.07
rows, cur, cur_w = [], [], 0.0
for r in rows_in:
    if cur and cur_w + r[1] > ROW_W:
        rows.append(cur)
        cur, cur_w = [], 0.0
    cur.append(r)
    cur_w += r[1] + GAP
if cur:
    rows.append(cur)
heights = [max(r[2] for r in row) for row in rows]
TOTAL_H = sum(heights) + GAP * (len(rows) - 1)
TW, TH = ROW_W + 0.45, TOTAL_H + 0.45
TARP = V((0.0, -(0.85 + TH / 2), 0.0))                     # the tarp lies beside the rover, on its right
TIDY = {}
y = TOTAL_H / 2
for row, hh in zip(rows, heights):
    w = sum(r[1] for r in row) + GAP * (len(row) - 1)
    x = -w / 2
    for p, wx, wy, mid in row:
        TIDY[p.name] = V((x + wx / 2 - mid.x, y - hh / 2 - mid.y, 0.004))
        x += wx + GAP
    y -= hh + GAP

pieces = []
for p in kit.pieces:
    d = {"name": p.name, "node": p.ob.name, "step": p.step, "label": p.label, "note": p.sub}
    if p.name in TIDY:
        M = Matrix.Translation(TARP + TIDY[p.name]) @ KN[p.name]
        loc, q, _s = M.decompose()
        d["tarp"] = [round(v, 4) for v in (*loc, q.w, q.x, q.y, q.z)]
    pieces.append(d)

objs = list(coll.all_objects)
webexport.prepare(objs)
glb = A / "r1_kit.glb"
webexport.export(glb, objs)
(A / "r1_kit.glb.json").write_text(json.dumps({"gz": base64.b64encode(gzip.compress(glb.read_bytes(), 9)).decode()}), encoding="utf-8")
size = glb.stat().st_size
glb.unlink()
meta = {"steps": STEPS, "pieces": pieces, "tarp": {"c": [round(v, 3) for v in TARP], "w": round(TW, 3), "h": round(TH, 3)}}
(A / "r1_kit.json").write_text(json.dumps(meta, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print(f"[kit] {len(pieces)} parts, {len(rows)} rows, tarp {TW:.2f} x {TH:.2f} m, glb {size // 1024} KB, {time.time() - t0:.1f}s -> {A}")
