"""Review renders of the R1 rover (15 Oct 2026): close-ups the catalog framing can't give.

  blender -b --factory-startup -P blender/render_rover.py -- [--pct 60] [--out renders/rover]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / "lib"), str(HERE)]

import bpy  # noqa: E402

import gh  # noqa: E402
import studio  # noqa: E402
from components import rover  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {argv[i].lstrip("-"): argv[i + 1] for i in range(0, len(argv) - 1, 2)}
OUT = Path(opt.get("out", HERE.parent / "renders" / "rover")).resolve()
OUT.mkdir(parents=True, exist_ok=True)

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
sc = bpy.context.scene
studio.setup_render(sc, w=1600, h=1000, samples=int(opt.get("samples", 32)), pct=int(opt.get("pct", 60)))
studio.world(sc)
st = studio.Studio(sc)
coll = gh.get_coll("Catalog", scene=sc)
gh.set_collection(coll)

r = rover.rover()
allp = gh.descendants(r.root)


def parts(*names):
    out = []
    for n in names:
        ob = r.parts[n]
        out += [ob] + gh.descendants(ob)
    return out


base = parts("wheel_FL", "wheel_FR", "wheel_RL", "wheel_RR", "chassis", "battery", "ebox", "lidar", "pump", "valves", "console", "bumpers", "front_camera")
shots = [
    ("r_base_front", base, 38, 16, 1.05),
    ("r_base_rear", base, 215, 22, 1.05),
    ("r_side", allp, 90, 4, 1.05),
    ("r_front", allp, 0, 4, 1.05),
]
for name, objs, az, el, mg in shots:
    st.frame(objs, az=az, el=el, margin=mg)
    studio.render(sc, OUT / f"{name}.jpg")
# mast top: pods + beacon only
pods = [o for o in parts("pod_1", "pod_2", "pod_3", "beacon")]
st.frame(pods, az=30, el=12, margin=1.05)
studio.render(sc, OUT / "r_pods.jpg")
for o in allp + [r.root]:
    o.hide_render = True
s = rover.rover_strawberry()
sp = gh.descendants(s.root)
st.frame(sp, az=35, el=20, margin=1.08)
studio.render(sc, OUT / "r_strawberry.jpg")
