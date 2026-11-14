"""Build Part 5, the hydro box scene (components/hydro_kit.py), and export it for the site (14 Nov 2026).

  blender -b --factory-startup -P blender/build_hydro_web.py [-- --blend 1]

Writes assets/hydro_kit.glb.json (the glb, gzipped + base64, the format js/*.js load) and assets/hydro_kit.json (points
the web uses: label anchors, camera aims). The glb is y-up in the twin's frame, like rover_house.
"""
import base64
import gzip
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / "lib"), str(HERE), str(HERE / "components")]

import bpy  # noqa: E402

import gh  # noqa: E402
from components import hydro_kit as HK  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {argv[i].lstrip("-"): argv[i + 1] for i in range(0, len(argv) - 1, 2)}
A = (HERE.parent / "assets").resolve()
gh.TEXT_RES = 6
t0 = time.time()
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
sc = bpy.context.scene
coll = gh.get_coll("Hydro", scene=sc)
gh.set_collection(coll)
info = HK.build(coll)
objs = list(coll.all_objects)
nverts = sum(len(o.data.vertices) for o in objs if o.type == "MESH")
print(f"hydro objects={len(objs)} verts={nverts:,} build {time.time() - t0:.1f}s")
if opt.get("blend", "0") == "1":
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent / "hydro_kit.blend"), compress=True)
import webexport  # noqa: E402
webexport.prepare(objs)
glb = A / "hydro_kit.glb"
webexport.export(glb, objs)
raw = glb.read_bytes()
(A / "hydro_kit.glb.json").write_text(json.dumps({"gz": base64.b64encode(gzip.compress(raw, 9)).decode()}), encoding="utf-8")
glb.unlink()
meta = {k: [round(float(v), 3) for v in p] if not isinstance(p, str) else p for k, p in info.items()}
(A / "hydro_kit.json").write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")
print("exported hydro_kit.glb.json", (A / "hydro_kit.glb.json").stat().st_size // 1024, "KB (glb", len(raw) // 1024, "KB)")
