"""Overview renders of greenhouse_twin.blend.

  blender -b greenhouse_twin.blend -P blender/render_greenhouse.py -- [--pct 50] [--samples 32] [--only name1,name2]
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {argv[i].lstrip("-"): argv[i + 1] for i in range(0, len(argv) - 1, 2)}
OUT = Path(opt.get("out", HERE.parent / "renders" / "greenhouse")).resolve()
OUT.mkdir(parents=True, exist_ok=True)
PCT, SAMPLES = int(opt.get("pct", 50)), int(opt.get("samples", 32))
ONLY = set(opt["only"].split(",")) if "only" in opt else None

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.eevee.taa_render_samples = SAMPLES
sc.eevee.use_raytracing = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1600, 900, PCT
sc.render.image_settings.file_format = "JPEG"
sc.render.image_settings.quality = 92
sc.view_settings.view_transform = "AgX"
sc.view_settings.exposure = float(opt.get("exposure", 0.0))

cam_d = bpy.data.cameras.new("shot_cam")
cam = bpy.data.objects.new("shot_cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam


def comp(name):
    return bpy.data.objects.get(name)


def parts(root):
    out, st = [], [root]
    while st:
        o = st.pop()
        out.append(o)
        st.extend(o.children)
    return out


def hide(names, state=True):
    for nm in names:
        r = comp(nm)
        if r is None:
            continue
        for o in parts(r):
            o.hide_render = state


def hide_part(comp_name, part, state=True):
    o = comp(f"{comp_name}.{part}")
    if o:
        o.hide_render = state


def shot(name, loc, target, lens=24, setup=None, teardown=None):
    if ONLY and name not in ONLY:
        return
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam_d.lens = lens
    cam_d.clip_start = 0.02
    cam_d.clip_end = 200
    if setup:
        setup()
    sc.render.filepath = str(OUT / f"{name}.jpg")
    bpy.ops.render.render(write_still=True)
    if teardown:
        teardown()


roof = lambda s: [hide_part("greenhouse_structure", p, s) for p in ("film_roof", "polycarbonate_roof", "insect_net", "vent_window")]

shot("01_exterior", (-7.5, -8.5, 4.2), (4.2, 0.2, 1.6), lens=30)
shot("02_exterior_back", (15.5, 8.0, 5.0), (4.5, 0.0, 1.5), lens=30)
shot("03_aisle_view", (1.3, -0.8, 1.65), (8.5, -0.75, 1.2), lens=22)
shot("04_tech_zone", (2.6, 0.9, 2.1), (0.8, -1.6, 0.9), lens=20)
shot("05_topdown_cutaway", (4.5, -0.01, 14.5), (4.5, 0.0, 0.0), lens=32, setup=lambda: roof(True), teardown=lambda: roof(False))
shot("06_cutaway_34", (-3.5, -7.0, 8.5), (4.6, 0.0, 0.8), lens=26, setup=lambda: roof(True), teardown=lambda: roof(False))
shot("07_robot", (2.75, -0.55, 1.45), (4.7, -0.8, 0.85), lens=22)
shot("08_plant_042", (3.75, 0.9, 1.05), (4.2, 1.55, 0.95), lens=24)
shot("09_climate_fans", (4.5, 0.4, 2.1), (0.0, 0.0, 1.9), lens=22)
shot("10_pad_wall", (6.5, 0.8, 1.4), (9.0, 0.0, 0.9), lens=22)
