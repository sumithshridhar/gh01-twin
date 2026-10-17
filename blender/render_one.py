"""Quick look at one or more components: build → render assembled + exploded.

  blender -b --factory-startup -P blender/render_one.py -- --what components.irrigation:solenoid_valve [--pct 50]
"""
import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / "lib"), str(HERE)]

import bpy  # noqa: E402

import gh  # noqa: E402
import studio  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {argv[i].lstrip("-"): argv[i + 1] for i in range(0, len(argv) - 1, 2)}
OUT = Path(opt.get("out", HERE.parent / "renders" / "test")).resolve()
OUT.mkdir(parents=True, exist_ok=True)
PCT = int(opt.get("pct", 50))

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
sc = bpy.context.scene
studio.setup_render(sc, samples=int(opt.get("samples", 32)), pct=PCT)
studio.world(sc)
sc.view_settings.exposure = float(opt.get("exposure", 0.0))
st = studio.Studio(sc)
coll = gh.get_coll("Catalog", scene=sc)
gh.set_collection(coll)

for spec in opt["what"].split(","):
    mod, fn = spec.split(":")
    comp = getattr(importlib.import_module(mod), fn)()
    objs = [o for o in gh.descendants(comp.root)]
    az, el = float(opt.get("az", 35)), float(opt.get("el", 22))
    if "view" in comp.root:
        az, el = comp.root["view"][0], comp.root["view"][1]
    st.frame(objs, az=az, el=el)
    studio.render(sc, OUT / f"{fn}_a.jpg")
    gh.explode(comp.root, 1.0)
    bpy.context.view_layer.update()
    st.frame(objs, az=az, el=el)
    studio.render(sc, OUT / f"{fn}_x.jpg")
    gh.explode(comp.root, 0.0)
    for o in objs + [comp.root]:
        o.hide_render = True
if opt.get("save"):
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(opt["save"])))
