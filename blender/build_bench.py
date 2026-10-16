"""Build the tutorial bench parts (components/bench.py) and export web/assets/bench_pestcam.glb (14 Oct 2026).

  blender -b --factory-startup -P blender/build_bench.py [-- --blend 1]
  python tools/pack_glb.py

Every part is built at its own origin; the web (web/js/bench.js) lays them out on the bench and animates them.
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / "lib"), str(HERE), str(HERE / "components")]

import bpy  # noqa: E402

import gh  # noqa: E402
from components import bench  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {argv[i].lstrip("-"): argv[i + 1] for i in range(0, len(argv) - 1, 2)}
OUT = (HERE.parent / "web" / "assets" / "bench_pestcam.glb").resolve()
gh.TEXT_RES = 6
t0 = time.time()

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
sc = bpy.context.scene
coll = gh.get_coll("Bench", scene=sc)
gh.set_collection(coll)
roots = []
for k, fn in enumerate(bench.ALL):
    c = fn()
    c.place((0.25 * k, 0, 0))          # spread out in the .blend (the web resets every position)
    roots.append(c.root)
objs = list(coll.all_objects)
nverts = sum(len(o.data.vertices) for o in objs if o.type == "MESH")
print(f"bench parts={len(roots)} verts={nverts:,} build {time.time() - t0:.1f}s")
if opt.get("blend", "0") == "1":
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE.parent / "bench_pestcam.blend"), compress=True)
for r in roots:
    r.location = (0, 0, 0)
import webexport  # noqa: E402
webexport.prepare(objs)
webexport.export(OUT, objs)
print("exported", OUT.name, OUT.stat().st_size // 1024, "KB")
