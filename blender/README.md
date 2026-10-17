# Blender source for GH-01 and R1

Every part in the twin, and in the videos, is built by these scripts. Each part is a real product at its real size, and
prices come from [`tools/products.py`](../tools/products.py). The scripts are headless Python for Blender 5.2: no .blend
file is needed.

- `lib/gh.py`: the mesh builder, materials, and `Component` (root + named parts, with explode offsets and metadata that survive glTF export).
- `components/*.py`: greenhouse, climate, irrigation, fertigation, sensors, control, plants, robot, farm, scale-up, tutorial bench, **rover (R1)**, **soilhouse (soil beds, mulch, drip, strawberry)**, **rover_kit** (R1 as the pieces you buy), **diy_kits** (Build Parts 3 and 4: ESP32, expansion board, soil sensor, relay, 12 V valve, drip kit, SHT30 probe, saucer sun shield, IP65 boxes).
- `build_greenhouse.py`: builds the twin (`--web 1` exports the glTF the website loads).
- `render_one.py`, `render_rover.py`: studio renders of any component.

```
blender -b --factory-startup -P blender/render_one.py -- --what components.rover:rover,components.rover:mist_arch
```

The farm scripts also expect four CC0 Poly Haven textures in `blender/assets/polyhaven/`: concrete_pavement, corrugated_iron_02, red_brick_03, red_laterite_soil_stones (1k diff + nor_gl).
