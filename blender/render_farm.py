"""Review renders of the farm round GH-01 (6 Oct 2026), in the same Kolar red-soil look as the videos.

  blender -b greenhouse_twin_v3.blend -P blender/render_farm.py -- [--views aerial,entry] [--pct 100] [--samples 24]
        -> renders/farm/<view>.jpg
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\Sumith Shridhar\data-story-engine\stories\gh01-full")
import gh01_look  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {argv[i].lstrip("-"): argv[i + 1] for i in range(0, len(argv) - 1, 2)}
opt.setdefault("el", "50")
opt.setdefault("az", "235")          # afternoon sun from the south-west (+x is north, as in the web twin)
opt.setdefault("sun", "4.2")
opt.setdefault("sky", "0.12")
OUT = HERE.parent / "renders" / "farm"
OUT.mkdir(parents=True, exist_ok=True)
V = Vector

VIEWS = {   # name: (camera position, target, lens mm, extra exposure)
    "aerial": ((-15.0, 21.0, 17.0), (4.2, -3.0, 0.0), 26, 0.0),
    "entry": ((-10.0, -3.4, 1.7), (-1.2, 0.5, 1.5), 28, 0.15),
    "packhouse": ((-5.5, 14.5, 4.2), (3.5, 8.5, 1.8), 28, 0.1),
    "packhouse_inside": ((1.75, 9.9, 1.75), (5.3, 7.4, 1.2), 22, 0.45),
    "pond": ((-3.2, -3.6, 3.4), (5.2, -10.8, -1.2), 24, 0.1),
    "back_corner": ((14.0, -7.5, 2.4), (8.6, -0.5, 1.8), 26, 0.15),
    "shade_net": ((1.5, 9.5, 8.5), (4.6, -0.3, 3.4), 30, 0.0),
    # farm v4 (11 Oct 2026)
    "v4_aerial": ((-32.0, 38.0, 34.0), (20.0, -2.0, 0.0), 24, 0.0),
    "v4_gh02": ((5.0, 22.0, 6.0), (30.0, 0.0, 4.0), 24, 0.05),
    "v4_gh02_inside": ((14.5, -11.5, 2.2), (40.0, -5.0, 2.6), 20, 0.4),
    "v4_drain": ((-4.2, 4.6, 1.9), (-1.0, 1.7, 0.8), 26, 0.15),
    "v4_mast": ((-4.5, 9.0, 2.0), (0.6, 4.3, 3.5), 24, 0.1),
    "v4_dock": ((7.0, 17.5, 2.2), (10.2, 14.2, 0.6), 30, 0.1),
    "v4_vermi": ((5.0, 13.5, 3.0), (9.2, 8.1, 0.5), 26, 0.15),
}
names = opt.get("views", ",".join(VIEWS)).split(",")

sc = bpy.context.scene
OB = bpy.data.objects
comps = {o["gh_id"]: o for o in OB if o.get("gh_type") == "component" and o.parent is None}


def desc(r):
    out, st = [], [r]
    while st:
        o = st.pop()
        out.append(o)
        st.extend(o.children)
    return out


gh01_look.setup(sc, comps, desc, opt, int(opt.get("samples", 24)), int(opt.get("pct", 100)), 30)
sc.render.resolution_x, sc.render.resolution_y = 1600, 1000
sc.render.use_motion_blur = False
sun = next(o for o in OB if o.type == "LIGHT" and o.data.type == "SUN")
sun.data.color = (1.0, 0.95, 0.88)                       # daylight, not golden hour
red = bpy.data.materials.get("red_soil")
if red:                                                   # the pond berm is soil too
    for o in OB:
        if o.type == "MESH":
            for s in o.material_slots:
                if s.material and s.material.name.startswith("gravel"):
                    s.material = red

cam_d = bpy.data.cameras.new("cam")
cam_d.sensor_width = 36.0
cam = bpy.data.objects.new("cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
cam_d.clip_start = 0.02
cam_d.clip_end = 3000
for n in names:
    pos, tgt, lens, ex = VIEWS[n]
    cam.location = V(pos)
    cam.rotation_euler = (V(tgt) - V(pos)).to_track_quat("-Z", "Y").to_euler()
    cam_d.lens = lens
    sc.view_settings.exposure = float(opt.get("exposure", 0.0)) + ex
    sc.render.filepath = str(OUT / f"{n}.jpg")
    bpy.ops.render.render(write_still=True)
    print("[farm] rendered", n, flush=True)
