"""Build the soil-bed polyhouse scene for the website (17 Oct 2026): one 8 m span x 12 m strawberry polyhouse
(components/soilhouse.py), the R1 rover in its strawberry setting (components/rover.py), the wheel bath and mist arch at
the door, and the Build Part 3 watering kit installed on zone 1 (components/diy_kits.zone_kit). Exports

  web/assets/rover_house.glb   the house, beds, kit, rover (the rover keeps its own root so the web can drive it)
  web/assets/sb_plant.glb      one strawberry plant at the origin (the web instances it on every planting hole)
  web/assets/rover_house.json  planting holes [x, y, z, rz, s] + the rover's path (Blender coordinates)

  blender -b --factory-startup -P blender/build_rover_web.py
  python tools/pack_glb.py
"""
import json
import math
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / "lib"), str(HERE), str(HERE / "components")]

import bpy  # noqa: E402

import gh  # noqa: E402
import webexport  # noqa: E402
from components import diy_kits as DK  # noqa: E402
from components import rover as R  # noqa: E402
from components import soilhouse as S  # noqa: E402

A = (HERE.parent / "web" / "assets").resolve()
gh.TEXT_RES = 6
t0 = time.time()
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
sc = bpy.context.scene
coll = gh.get_coll("Web", scene=sc)
gh.set_collection(coll)

L, SPAN, X0, X1 = 12.0, 8.0, 1.6, 11.0
P = S.SB
n = int((SPAN - 0.5) // P["pitch"])
used = n * P["pitch"]
bc = [-SPAN / 2 + (SPAN - used) / 2 + P["pitch"] * (k + 0.5) for k in range(n)]
ph = S.polyhouse(cid="ph_web", L=L, spans=1, span=SPAN)
bd = S.beds("beds_zone1", "strawberry", X0, X1, bc[:4], seed=31)
bd2 = S.beds("beds_zone2", "strawberry", X0, X1, bc[4:], seed=32)
fl = S.path_floor("floor_web", 0.0, L, -SPAN / 2, SPAN / 2, seed=33, res=0.5)
bath = R.wheel_bath(cid="bath_web")
bath.place((-0.95, ph.door_y, 0.04))
arch = R.mist_arch(cid="arch_web")
arch.place((-2.3, ph.door_y, 0.04))
mb = gh.MB()
for xa, xb, ya, yb in ((-40, 52, -40, -SPAN / 2), (-40, 52, SPAN / 2, 40), (-40, 0, -SPAN / 2, SPAN / 2), (L, 52, -SPAN / 2, SPAN / 2)):
    mb.box((xb - xa, yb - ya, 0.02), "sand_wet", loc=((xa + xb) / 2, (ya + yb) / 2, -0.012))
ground = mb.build("ground_web")
coll.objects.link(ground)
kit, info = DK.zone_kit(coll, corner=(0.0, -SPAN / 2), inward=1.0, header_end=(X0 - 0.63, min(bc[:4]) - P["pitch"] / 2),
                        bed_y=bc[0], bed_h=P["h"], sensor_x=2.0)
for p in kit.pieces:
    if p.name == "lid":
        bpy.data.objects.remove(p.ob)
paths = [a + P["pitch"] / 2 for a in bc[:-1]]
rv = R.rover(cid="r1_web", title="R1 rover, strawberry setting", mast_top=0.68, crop="strawberry")
rv.place((X0 + 0.6, paths[1], 0.0))
house_objs = [o for o in coll.all_objects]
for o in bpy.data.objects:
    if o.type == "MESH" and any(m and m.name in ("uv_film", "net") for m in o.data.materials):
        o.visible_shadow = False
print(f"house objs={len(house_objs)} verts={sum(len(o.data.vertices) for o in house_objs if o.type == 'MESH'):,} {time.time() - t0:.1f}s")

# the plant (its own collection, at the origin)
pc = gh.get_coll("Plant", scene=sc)
gh.set_collection(pc)
plant = S.strawberry_plant(cid="sb_web", seed=204, ripe=4, green=2, flowers=2, outward=1.0)
plant_objs = list(pc.all_objects)
rnd = random.Random(7)
holes = []
for x, y, z, yc in bd.positions + bd2.positions:
    out = 1 if y > yc else -1
    holes.append([round(x, 3), round(y, 3), round(z, 3), round((0.0 if out > 0 else math.pi) + rnd.uniform(-0.5, 0.5), 3), round(rnd.uniform(0.9, 1.1), 3)])

webexport.prepare(house_objs + plant_objs)
webexport.export(A / "rover_house.glb", house_objs)
webexport.export(A / "sb_plant.glb", plant_objs)
meta = {"holes": holes, "paths": [round(y, 3) for y in paths], "x0": X0, "x1": X1, "door_y": ph.door_y, "rover": "r1_web",
        "box": [round(v, 3) for v in info["box_c"]], "valve": [round(v, 3) for v in (info["valve_M"] @ __import__("mathutils").Vector((0, 0, 0.03)))],
        "sensor": [round(v, 3) for v in info["sensor_top"]], "beds": [round(y, 3) for y in bc]}
(A / "rover_house.json").write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")
for f in ("rover_house.glb", "sb_plant.glb"):
    print("exported", f, (A / f).stat().st_size // 1024, "KB")
print("holes", len(holes), "paths", meta["paths"])
