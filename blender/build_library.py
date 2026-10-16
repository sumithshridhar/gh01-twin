"""Build component_library.blend (every component in a labelled grid) and optionally render the catalog.

  blender -b --factory-startup -P blender/build_library.py -- [--render 1] [--pct 100] [--samples 48] [--only fn1,fn2]

Catalog output: renders/catalog/<fn>_a.jpg (assembled), <fn>_x.jpg (exploded) and renders/catalog/catalog.json
with each component's metadata and the on-image position of every exploded part (for hover labels).
"""
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / "lib"), str(HERE)]

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import gh  # noqa: E402
import studio  # noqa: E402
from catalog import CATALOG  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {argv[i].lstrip("-"): argv[i + 1] for i in range(0, len(argv) - 1, 2)}
RENDER = opt.get("render", "0") == "1"
ONLY = set(opt["only"].split(",")) if "only" in opt else None
OUT = (HERE.parent / "renders" / "catalog").resolve()
OUT.mkdir(parents=True, exist_ok=True)

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
sc = bpy.context.scene
sc.name = "Component library"
lib = gh.get_coll("Component library", scene=sc)


def bbox(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


built = []  # (category, fn, component)
y_cursor = 0.0
for cat, items in CATALOG:
    cc = gh.get_coll(cat, parent=lib)
    gh.set_collection(cc)
    x_cursor, row_depth = 0.0, 0.0
    for mod, fn in items:
        if ONLY and fn not in ONLY:
            continue
        comp = getattr(importlib.import_module(mod), fn)()
        objs = gh.descendants(comp.root)
        lo, hi = bbox(objs)
        size = hi - lo
        # place: left edge at the cursor, front edge on the row line, standing on the floor
        comp.root.location += Vector((x_cursor - lo.x, y_cursor - lo.y, -lo.z))
        # title label on the floor in front
        mb = gh.MB()
        mb.text(comp.root["title"], 0.05, "plastic_black", depth=0.002, align="LEFT", bold=True)
        lab = mb.build(f"{comp.root.name}.label")
        cc.objects.link(lab)
        lab.location = (x_cursor, y_cursor - 0.12, 0.001)
        x_cursor += max(size.x, 0.35) + 0.5
        row_depth = max(row_depth, size.y)
        built.append((cat, fn, comp))
    cl = gh.MB()
    cl.text(cat.upper(), 0.14, "plastic_green", depth=0.004, align="LEFT", bold=True)
    lb = cl.build(f"_cat_{cat}")
    cc.objects.link(lb)
    lb.location = (-0.2, y_cursor - 0.4, 0.001)
    y_cursor += row_depth + 1.4
if not ONLY:  # a partial build must not overwrite the full library
    bpy.ops.wm.save_as_mainfile(filepath=str((HERE.parent / "component_library.blend").resolve()), compress=True)
print(f"library saved: {len(built)} components")

if RENDER:
    studio.setup_render(sc, w=1400, h=875, samples=int(opt.get("samples", 48)), pct=int(opt.get("pct", 100)))
    sc.render.image_settings.quality = 86
    studio.world(sc)
    st = studio.Studio(sc)
    everything = [o for _, _, c in built for o in [c.root] + gh.descendants(c.root)]
    labels = [o for o in bpy.data.objects if o.name.endswith(".label") or o.name.startswith("_cat_")]
    for o in labels:
        o.hide_render = True
    meta_path = OUT / "catalog.json"
    catalog = json.loads(meta_path.read_text()) if (ONLY and meta_path.exists()) else {"categories": [], "items": {}}
    for cat, fn, comp in built:
        for o in everything:
            o.hide_render = True
        mine = [comp.root] + gh.descendants(comp.root)
        for o in mine:
            o.hide_render = False
        az, el = (comp.root["view"][0], comp.root["view"][1]) if "view" in comp.root else (35, 22)
        st.frame(mine, az=az, el=el)
        studio.render(sc, OUT / f"{fn}_a.jpg")
        gh.explode(comp.root, 1.0)
        bpy.context.view_layer.update()
        st.frame(mine, az=az, el=el)
        studio.render(sc, OUT / f"{fn}_x.jpg")
        parts = [(o["part_name"], o) for o in comp.root.children if o.get("gh_type") in ("part", "group")]
        pos = st.project(parts)
        gh.explode(comp.root, 0.0)
        r = comp.root
        catalog["items"][fn] = {
            "id": r["gh_id"], "title": r["title"], "category": cat, "summary": r["summary"],
            "how_it_works": r["how_it_works"], "sensors": r["sensors"], "control": r["control"],
            "state": json.loads(r["state"]), "real_part": r["real_part"], "cost": r["cost"],
            "parts": [{"name": nm.replace("_", " "), "desc": o.get("desc", ""), "x": pos[nm][0], "y": pos[nm][1]}
                      for nm, o in parts if nm in pos],
        }
        if cat not in catalog["categories"]:
            catalog["categories"].append(cat)
        print("rendered", fn)
    catalog["order"] = [fn for _, items in CATALOG for _, fn in items if fn in catalog["items"]]
    meta_path.write_text(json.dumps(catalog, indent=1, ensure_ascii=False), encoding="utf-8")
    print("catalog.json written")
