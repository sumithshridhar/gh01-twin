"""Assemble the full prototype greenhouse from the component library and save greenhouse_twin.blend.

  blender -b --factory-startup -P blender/build_greenhouse.py [-- --plants 54 --out greenhouse_twin.blend]
"""
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / "lib"), str(HERE), str(HERE / "components")]

import bpy  # noqa: E402

import gh  # noqa: E402
from components import (climate, control, farm, fertigation, greenhouse as G, irrigation, plant, scaleup,  # noqa: E402
                        robot, sensors)
from gh import MB, Component  # noqa: E402
from parts import cable, pe_run  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {argv[i].lstrip("-"): argv[i + 1] for i in range(0, len(argv) - 1, 2)}
NPLANTS = int(opt.get("plants", 54))
FARM = opt.get("farm", "1") == "1"        # 6 Oct 2026: the full farm round the house (solar, pond, packhouse, entry, shade)
OUT = Path(opt.get("out", HERE.parent / "greenhouse_twin.blend")).resolve()
WEB = opt.get("web", "0") == "1"          # browser build: lighter plants shared across positions + glTF export
WEB_OUT = (HERE.parent / "web" / "assets").resolve()
if WEB:
    plant.DETAIL = 0.5
    gh.TEXT_RES = 3
t0 = time.time()

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
sc = bpy.context.scene
sc.name = "Greenhouse"
root_coll = gh.get_coll("Greenhouse", scene=sc)
COLL = {}


def coll(name):
    if name not in COLL:
        COLL[name] = gh.get_coll(name, parent=root_coll)
    return COLL[name]


def put(comp, loc, rot=(0, 0, 0), scale=None):
    comp.root.location = loc
    comp.root.rotation_euler = [math.radians(a) for a in rot]
    if scale is not None:
        comp.root.scale = (scale,) * 3
    return comp


def in_(name):
    gh.set_collection(coll(name))


# ───────── structure ─────────
in_("1 Structure")
if FARM:
    ph = farm.POND_C
    put(G.surroundings(hole=(ph[0] - farm.POND_TOP, ph[0] + farm.POND_TOP, ph[1] - farm.POND_TOP, ph[1] + farm.POND_TOP),
                       farm=True), (0, 0, 0))
else:
    put(G.surroundings(), (0, 0, 0))
put(G.greenhouse_structure(), (0, 0, 0))
vd = climate.vent_drive("vent_drive", L=8.6, pinions=[x - 4.5 for x in (1.5, 3.0, 4.5, 6.0, 7.5)], open_deg=12.4,
                        with_window=False)
put(vd, (4.5, 0.0, G.RH + 0.04 - 0.8))

# ───────── crop rows + plants ─────────
in_("2 Crop rows")
for r in (1, 2, 3):
    put(G.growing_row(f"row_{r}", r, skip_first_slab=(r == 3)), (0, 0, 0))
put(fertigation.slab_scale("slab_scale"), (G.SLAB_X[0], G.ROWS_Y[2], 0))
in_("3 Plants")
PLANTS = []
if WEB:  # 6 look variants + #042 (disease) built once, then shared by all 54 positions (each keeps its own tag + record)
    vcoll = gh.get_coll("_plant_variants", parent=root_coll)
    gh.set_collection(vcoll)
    variants = [plant.tomato_plant(f"_pv{k}", None, "fruiting", seed=2000 + k, with_tag=False,
                                   string_top=G.WIRE_Z - G.CUBE_TOP) for k in range(6)]
    v042 = plant.tomato_plant("_pv42", None, "fruiting", seed=1042, with_tag=False, disease=True,
                              string_top=G.WIRE_Z - G.CUBE_TOP)
    in_("3 Plants")
n = 0
for r in (1, 2, 3):
    for i, xc in enumerate(G.SLAB_X):
        for j in range(3):
            n += 1
            if n > NPLANTS:
                break
            yaw = (180 if r == 1 else 0) + ((n * 37) % 21 - 10)
            pos = (xc + (j - 1) * 0.33, G.ROWS_Y[r - 1], G.CUBE_TOP)
            no_cube = (r == 3 and i == 0)
            if not WEB:
                p = plant.tomato_plant(f"plant_{n:03d}", None, "fruiting", seed=1000 + n, row=r, slab=i + 1, slot=j + 1,
                                       disease=(n == 42), cube=not no_cube, string_top=G.WIRE_Z - G.CUBE_TOP)
                put(p, pos, (0, 0, yaw))
            else:
                src = v042 if n == 42 else variants[(n * 5) % 6]
                rootp = gh.clone(src.root, f"plant_{n:03d}", coll("3 Plants"))
                tag = f"#{n:03d}"
                rootp["title"] = f"Tomato plant {tag}"
                rootp["plant_id"] = tag
                rootp["summary"] = (f"Plant {tag}: row {r}, slab {i + 1}, slot {j + 1}. Every plant has its own record "
                                    "(its digital identity).")
                import json as _json
                rootp["state"] = _json.dumps(plant.plant_state(tag, "fruiting", r, i + 1, j + 1, n == 42))
                for ch in list(rootp.children):
                    if no_cube and ch.get("part_name") in ("cube", "roots"):
                        bpy.data.objects.remove(ch)
                tgo = plant.tag_mb_web(n, r, i + 1, j + 1).build(f"plant_{n:03d}.id_tag")
                rootp.users_collection[0].objects.link(tgo)
                tgo.parent = rootp
                tgo.location = (0.0, -0.075, 0.0)
                tgo["gh_type"], tgo["part_name"] = "part", "id_tag"
                tgo["desc"] = f"ID tag {tag} with QR code – the robot reads it so every photo is saved to this plant's record."
                tgo["explode"], tgo["base_loc"] = [0.0, -0.2, 0.08], [0.0, -0.075, 0.0]
                rootp.location = pos
                rootp.rotation_euler = (0, 0, math.radians(yaw))
            PLANTS.append({"id": f"plant_{n:03d}", "tag": f"#{n:03d}", "row": r, "slab": i + 1, "slot": j + 1,
                           "pos": [round(v, 3) for v in pos], "disease": n == 42})
print(f"plants done {time.time() - t0:.0f}s")

# ───────── technical zone: water + fertigation ─────────
in_("4 Fertigation")
put(fertigation.water_tank("water_tank"), (1.6, -1.95, 0.04), (0, 0, 200))
put(fertigation.mix_tank("mix_tank"), (0.45, -2.1, 0.04), (0, 0, 90))
put(fertigation.stock_tank("stock_A", "Stock tank A (60 L)", "A", "Calcium nitrate + iron chelate"), (1.02, -2.28, 0.04), (0, 0, 180))
put(fertigation.stock_tank("stock_B", "Stock tank B (60 L)", "B", "Potassium nitrate, MKP, magnesium sulphate, micros"),
    (1.02, -1.86, 0.04), (0, 0, 180))
put(fertigation.stock_tank("stock_acid", "Acid tank (pH−, 60 L)", "pH-", "Nitric/phosphoric acid for pH down",
                           color="hdpe_blue"), (0.18, -0.78, 0.04), (0, 0, 180))
# skid frame + board
sk = Component("fertigation_skid", "Fertigation skid (frame + panel)", "Fertigation",
               summary="Steel frame holding the pump, filter, meters, dosing pumps and the probe panel in one serviceable unit.",
               how="Everything wet is on one skid above a drip tray: easy to inspect, calibrate and repair.",
               state={}, real="Galvanised frame + PVC board", cost="₹8–12k")
fk = MB()
for x in (0.3, 1.95):
    for y in (-1.5, -1.2):          # 14 Oct 2026: front posts 15 cm back (were at -1.05, inside the robot's aisle-1 exit)
        fk.box((0.04, 0.04, 1.75), "galv", loc=(x, y, 0.04 + 0.875))
fk.box((1.6, 0.04, 0.04), "galv", loc=(1.185, -1.5, 1.8))
fk.box((1.6, 0.012, 1.25), "pvc_white", loc=(1.185, -1.48, 1.12))
fk.box((1.58, 0.32, 0.03), "plastic_dark", loc=(1.185, -1.36, 0.055))
sk.part("frame_board", fk, desc="Frame, white mounting board and drip tray.")
put(irrigation.irrigation_pump("irrigation_pump"), (0.45, -1.485, 0.1), (0, 0, -90))
put(irrigation.disc_filter("disc_filter"), (0.82, -1.3, 0.9))
put(irrigation.flow_meter("flow_meter"), (1.15, -1.3, 0.9))
put(irrigation.pressure_transmitter("pressure_tx"), (1.36, -1.3, 0.92))
put(irrigation.pressure_gauge("pressure_gauge"), (1.52, -1.3, 0.97), (0, 0, 180))
for k, (lab, liq) in enumerate((("A", "stock A"), ("B", "stock B"), ("acid", "acid (pH−)"))):
    put(fertigation.dosing_pump(f"dosing_pump_{lab}", f"Dosing pump {lab}", liq), (0.75 + 0.2 * k, -1.37, 1.45), (0, 0, 180))
put(fertigation.flow_cell("sensor_flow_cell"), (1.55, -1.43, 1.35), (0, 0, 180))
put(fertigation.ph_probe("ph_probe"), (1.55 + 0.06, -1.43, 1.34))
put(fertigation.ec_probe("ec_probe"), (1.55, -1.43, 1.33))
put(control.esp32_node("esp32_node_fert"), (1.2, -1.41, 1.72), (0, 0, 180))
put(sensors.level_sensor("level_water_tank"), (1.72, -1.9, 1.175))
put(sensors.level_sensor("level_mix_tank"), (0.3, -2.1, 0.9))
put(fertigation.drain_meter("drain_meter"), (2.2, 0.0, 0.04), (0, 0, 90))
put(sensors.substrate_sensor("substrate_sensor"), (G.SLAB_X[1] + 0.17, 1.6 - 0.06, G.SLAB_TOP + 0.018))
tb = MB()  # dosing tubes stock → pumps → mix tank
for k, (sx, sy) in enumerate(((1.02 + 0.03, -2.28 + 0.0), (1.02 + 0.03, -1.86), (0.18 + 0.03, -0.78))):
    px = 0.75 + 0.2 * k
    pe_run(tb, [(sx - 0.08, sy + 0.0, 0.8), (sx - 0.08, sy, 1.0), (px - 0.03, -1.4, 1.0), (px - 0.03, -1.3, 1.37)], 0.003,
           m="pe_black", bend=0.05)
    pe_run(tb, [(px + 0.03, -1.3, 1.37), (px + 0.03, -1.35, 1.1), (0.55, -1.8, 1.1), (0.5, -2.0, 0.9)], 0.003,
           m="silicone_clear", bend=0.05)
sk.part("dosing_tubes", tb, desc="4 mm dosing tubes: stock tanks → pumps → mix tank.")
put(sk, (0, 0, 0))

in_("5 Irrigation")
put(G.irrigation_mains(), (0, 0, 0))
for r, y in enumerate(G.ROWS_Y, 1):
    put(irrigation.solenoid_valve(f"zone_valve_{r}", f"Zone valve {r} (row {r})"), (2.15, y + 0.135, 1.0), (0, 90, 0))

# ───────── climate ─────────
in_("6 Climate")
for k, sy in enumerate((-1, 1)):
    put(climate.exhaust_fan(f"exhaust_fan_{k + 1}", f"Exhaust fan {k + 1} (Multifan 4E50)"), (0.05, sy * G.FAN_Y, G.FAN_Z), (0, 0, -90),
        scale=0.6)
put(climate.cooling_pad("cooling_pad", width=G.PAD_W, height=G.PAD_H), (G.L - 0.05, 0.0, G.PAD_Z - 0.18), (0, 0, 90))
put(climate.haf_fan("haf_fan_1"), (3.0, -2.1, 2.55))
put(climate.haf_fan("haf_fan_2"), (7.0, 2.1, 2.55), (0, 0, 180))
put(climate.fog_pump("fog_pump"), (0.75, 2.05, 0.06), (0, 0, 180))
put(G.fog_line(), (0, 0, 0))

# ───────── sensors + cameras + lights ─────────
in_("7 Sensors")
put(sensors.climate_box("climate_box_1"), (5.475, 0.0, 2.0))
put(sensors.climate_box("climate_box_2"), (7.615, 1.6, 2.0))
put(sensors.par_sensor("par_sensor"), (4.4, 0.25, G.GH + 0.03), (0, 0, 90))
put(sensors.weather_station("weather_station"), (-1.4, 3.2, 0.0))
for k, (x, y, rz) in enumerate(((2.3, -1.6, -90), (3.2, 1.6, -90), (8.72, 0.0, 90))):
    put(sensors.sticky_trap_cam(f"sticky_trap_{k + 1}"), (x, y, G.WIRE_Z - 0.56), (0, 0, rz))
put(sensors.canopy_camera("canopy_camera_1"), (4.5, -1.6, 2.93), (-90, 0, 0))
put(sensors.canopy_camera("canopy_camera_2"), (7.5, 1.6, 2.93), (-90, 0, 0))
put(control.esp32_node("esp32_node_crop"), (7.5, -2.43, 1.3), (0, 0, 0))
# (the 6 LED toplights were removed on 6 Oct 2026: Karnataka sun is enough for tomato; see tools/products.py "led")

# ───────── control + interface ─────────
in_("9 Control")
put(control.control_cabinet("control_cabinet"), (0.2, 1.05, 0.95), (0, 0, 90))
put(control.hmi_tablet("farmer_tablet"), (0.06, -0.8, 1.45), (0, 0, 90))
cb = MB()
for y in (0.8, 0.95, 1.1, 1.25):
    cable(cb, [(0.25, y, 0.4), (0.25, y, 0.2), (0.6, y * 0.3, 0.06), (1.0, -1.0, 0.06), (1.05, -1.35, 0.3)], r=0.006)
cab = Component("cable_tray", "Field cabling", "Control", summary="Power and signal cables from the cabinet to the field.",
                state={})
cab.part("cables", cb, desc="Cables to the skid, fans, valves and nodes (run in trays / conduit in a real build).")

# ───────── robot ─────────
in_("10 Robot")
put(G.pipe_rails(), (0, 0, 0))
put(robot.scout_robot("scout_robot", lift=1.1), (4.6, G.AISLES_Y[0], G.RAIL_Z + G.PIPE_R))
put(robot.charging_dock("robot_dock"), (0.95, G.AISLES_Y[1], 0.04))   # 14 Oct 2026: 10 cm back, clear of the path drive

# ───────── the farm round the house (6 Oct 2026) ─────────
if FARM:
    in_("11 Entry + shade")
    put(farm.entry_room(), (0, 0, 0))
    put(farm.shade_net(), (0, 0, 0))
    in_("12 Power")
    put(farm.solar_array(), (0, 0, 0))
    xw = farm.PH["x1"] - 0.15                                    # inside face of the packhouse's north wall
    put(farm.hybrid_inverter(), (xw, 7.35, 1.5), (0, 0, 90))
    put(farm.battery_bank(), (xw, 8.3, 0.15), (0, 0, 90))
    put(farm.power_panel(), (xw, 6.35, 1.6), (0, 0, 90))
    in_("13 Water")
    put(farm.farm_pond(), (0, 0, 0))
    put(farm.pond_fence(), (0, 0, 0))
    put(farm.pond_pump(), (0, 0, 0))
    put(farm.level_pond(), (0, 0, 0))
    put(farm.rain_harvest(), (0, 0, 0))
    put(farm.borewell(), (0, 0, 0))
    put(farm.tank_valves(), (0, 0, 0))
    in_("14 Packhouse")
    put(farm.packhouse(), (0, 0, 0))
    put(farm.cool_chamber(), (4.45, 10.6, 0.15))
    put(farm.pack_station(), (2.8, 8.2, 0.15))
    put(farm.farm_sign(), (-4.4, 1.9, 0.0))
    in_("15 Farm v4")                                        # 11 Oct 2026: drain recycling, windbreak, comms mast, vermicompost
    put(farm.drain_recycle(), (0, 0, 0))
    put(farm.windbreak(), (0, 0, 0))
    put(farm.comms_mast(), (0, 0, 0))
    put(farm.vermicompost(), (0, 0, 0))
    in_("16 GH-02")                                          # 11 Oct 2026: the 1,024 m² scale-up house + inspection drone
    put(scaleup.gh02(), (0, 0, 0))
    put(scaleup.drone_dock(), (0, 0, 0))
    put(scaleup.drone(), (scaleup.DOCK[0], scaleup.DOCK[1], 0.75))

# ───────── scene settings ─────────
sc.unit_settings.system = "METRIC"
sc.render.engine = "BLENDER_EEVEE"
sc.eevee.use_raytracing = True
sun_d = bpy.data.lights.new("sun", "SUN")
sun_d.energy = 4.0
sun_d.angle = math.radians(1.5)
sun = bpy.data.objects.new("sun", sun_d)
sun.rotation_euler = (math.radians(38), math.radians(8), math.radians(130))
root_coll.objects.link(sun)
w = bpy.data.worlds.new("sky")
sc.world = w
bg = w.node_tree.nodes["Background"]
try:
    sky = w.node_tree.nodes.new("ShaderNodeTexSky")
    w.node_tree.links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.35
except Exception:
    bg.inputs["Color"].default_value = (0.55, 0.7, 0.9, 1)
nverts = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == "MESH")
ncomp = sum(1 for o in bpy.data.objects if o.get("gh_type") == "component")
print(f"components={ncomp} mesh verts={nverts:,} build {time.time() - t0:.0f}s")
if not WEB:
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT), compress=True)
    print("saved", OUT)
else:
    import json
    import webexport
    WEB_OUT.mkdir(parents=True, exist_ok=True)
    groups = {"gh_env": ["1 Structure", "2 Crop rows", "5 Irrigation"],
              "gh_tech": ["4 Fertigation", "9 Control"],
              "gh_equip": ["6 Climate", "7 Sensors", "10 Robot"],
              "gh_plants": ["3 Plants"]}
    if FARM:
        groups["gh_farm"] = ["11 Entry + shade", "12 Power", "13 Water", "14 Packhouse", "15 Farm v4", "16 GH-02"]
    allobjs = [o for names in groups.values() for nm in names for o in COLL[nm].all_objects]
    webexport.prepare(allobjs)
    for fname, names in groups.items():
        objs = [o for nm in names for o in COLL[nm].all_objects]
        webexport.export(WEB_OUT / f"{fname}.glb", objs)
        print("exported", fname, (WEB_OUT / f"{fname}.glb").stat().st_size // 1024, "KB")
    # simulation data: water network, drippers, fog nozzles, robot route, plants (Blender coords, z-up)
    ST = G.SLAB_TOP + 0.01
    zones = []
    for r, y in enumerate(G.ROWS_Y, 1):
        yy = y + 0.135
        drips = [[round(xc + (j - 1) * 0.33 + 0.03, 3), round(y + 0.03, 3), round(G.CUBE_TOP, 3)]
                 for xc in G.SLAB_X for j in range(3)]
        zones.append({"zone": r, "row_y": y,
                      "manifold": [[2.15, -1.3, 2.85], [2.15, yy, 2.85]],
                      "drop": [[2.15, yy, 2.85], [2.15, yy, ST], [2.21, yy, ST]],
                      "lateral": [[2.2, yy, ST], [G.ROW_X1, yy, ST]], "drippers": drips})
    PW, PH = G.PAD_W, G.PAD_H
    pad = lambda x, y, z: [round(G.L - 0.05 - y, 3), round(x, 3), round(z + G.PAD_Z - 0.18, 3)]
    sim = {
        "units": "metres, Blender z-up (convert to three.js: x, z, -y)",
        "house": {"L": G.L, "W": G.W, "GH": G.GH, "RH": G.RH},
        "water": {"tank_to_pump": [[0.45, -1.785, 0.1], [0.45, -1.66, 0.1]],
                  "pump_to_manifold": [[0.45, -1.515, 0.2], [0.45, -1.515, 0.9], [0.45, -1.3, 0.9], [1.9, -1.3, 0.9],
                                       [1.9, -1.3, 2.85], [2.15, -1.3, 2.85]],
                  "zones": zones},
        "fog": {"lines": [[[2.2, a, G.FOG_Z], [G.ROW_X1, a, G.FOG_Z]] for a in G.AISLES_Y],
                "feed": [[0.57, 2.0, 1.36], [0.57, 2.0, G.FOG_Z], [2.2, 2.0, G.FOG_Z], [2.2, 0.8, G.FOG_Z], [2.2, -0.8, G.FOG_Z]],
                "nozzles": [[x, a, round(G.FOG_Z - 0.37, 3)] for a in G.AISLES_Y for x in G.FOG_X]},
        "pad": {"riser": [pad(PW / 2 + 0.35, -0.2, 0.56), pad(PW / 2 + 0.35, -0.2, PH + 0.24), pad(PW / 2 + 0.02, 0, PH + 0.24)],
                "top": [pad(-PW / 2, 0, PH + 0.24), pad(PW / 2, 0, PH + 0.24)], "face_x": G.L - 0.05, "width": PW,
                "z0": G.PAD_Z, "z1": G.PAD_Z + PH},
        "robot": {"aisles_y": list(G.AISLES_Y), "x_min": 2.35, "x_max": 8.55, "rail_z": G.RAIL_Z + G.PIPE_R,
                  "dock": [0.95, G.AISLES_Y[1], 0.04],
                  # 14 Oct 2026: row changes. The robot backs out to path_x (on the slab, mecanum wheels down), slides
                  # sideways to the next aisle, reads its marker and drives in. Handover plates: slab level at x 2.2,
                  # floor at 2.5; floor_drop = mecanum wheel bottom below the rail contact plane.
                  "path_x": 1.55, "slab_z": 0.04, "handover": [2.2, 2.5], "floor_drop": 0.10,
                  "markers": [[1.95, a, 0.042] for a in G.AISLES_Y], "cam_x": 0.40, "stops": sorted({round(p["pos"][0], 3) for p in PLANTS})},
        "plants": PLANTS,
        "vent": {"hinge_z": G.RH + 0.04, "closed_deg": 25.6, "shown_open_deg": 12.0},
    }
    (WEB_OUT / "sim.json").write_text(json.dumps(sim, indent=1), encoding="utf-8")
    print("sim.json written")
