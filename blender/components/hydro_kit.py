"""Build Part 5, the hydro box (14 Nov 2026): a home NFT rack on a concrete roof, made to run itself.

Four clickable components (each explodes into its parts on the site):
  hydro_rack       MS frame, 4 PVC NFT channels on a 3 % slope, net cups and lettuce, inlet manifold, return header
  hydro_reservoir  ~70 L tub, cut open: water, 12 V pump, float switch, pH / EC / temperature probes, flow sensor
  hydro_box        IP65 box: ESP32 on its expansion board + a 4-channel relay board
  hydro_dosing     a shelf with 3 peristaltic pumps and 3 bottles (nutrient A, nutrient B, pH-down)
Sizes are the real products in build/05-hydro-box/README.md. Everything sits around O (the scene origin).

    import hydro_kit as HK
    info = HK.build(coll)          # -> dict of points the web uses (camera aims, label anchors)
"""
import math
import random

from mathutils import Vector

import gh
from gh import MB, Component, xform
from components import diy_kits as DK

O = Vector((0.0, 0.0, 0.0))         # where the other alt scenes live; the site hides GH-01 while this scene is up
L, CH_W, CH_H = 2.0, 0.10, 0.05     # channel length, width, height (m)
YS = (-0.21, -0.07, 0.07, 0.21)     # channel centres
Z_HI, Z_LO = 0.92, 0.86             # channel tops at the inlet / outlet end (3 % slope)
CUP_DX = 0.20
TUB = dict(x0=2.14, x1=2.76, y0=-0.22, y1=0.22, z0=0.03, z1=0.45, t=0.012)
WATER_Z = 0.32
SHELF = dict(x0=2.92, x1=3.36, y0=-0.16, y1=0.16, z=0.46)

gh.SPEC.setdefault("lettuce", dict(color=(0.22, 0.48, 0.07), rough=0.55, sheen=0.25))
gh.SPEC.setdefault("lettuce_light", dict(color=(0.45, 0.70, 0.16), rough=0.5, sheen=0.3))
gh.SPEC.setdefault("hydro_water", dict(color=(0.10, 0.36, 0.48), rough=0.04, alpha=0.78))
gh.SPEC.setdefault("cut_cream", dict(color=(0.86, 0.80, 0.66), rough=0.6))
gh.SPEC.setdefault("ms_paint", dict(color=(0.16, 0.17, 0.18), rough=0.5, metal=0.6))


def P(x, y, z):
    return tuple(O + Vector((x, y, z)))


def ztop(x):
    return Z_HI + (Z_LO - Z_HI) * x / L


SLOPE = math.degrees(math.atan2(Z_HI - Z_LO, L))


def lettuce(mb, at, rnd, size=1.0):
    """A loose-leaf lettuce head: two rings of cupped leaves around a light heart."""
    for ring, (n, ln, tilt0, mat) in enumerate(((9, 0.085, 28, "lettuce"), (7, 0.060, 52, "lettuce_light"), (5, 0.035, 70, "lettuce_light"))):
        for i in range(n):
            yaw = 360.0 * i / n + rnd.uniform(-14, 14) + ring * 23
            tilt = tilt0 + rnd.uniform(-8, 8)
            le = ln * size * rnd.uniform(0.85, 1.15)
            a, t = math.radians(yaw), math.radians(tilt)
            c = Vector(at) + Vector((math.cos(a) * math.cos(t), math.sin(a) * math.cos(t), math.sin(t))) * le * 0.55
            mb.sphere(le * 0.5, mat, segs=10, rings=6, loc=tuple(c), rot=(0, -tilt, yaw), scale=(1.0, 0.62, 0.16))


def build(coll=None):
    rnd = random.Random(55)
    info = {}
    # ── the roof: a concrete slab and a brick parapet (context, not a component) ──
    mb = MB()
    mb.box((5.6, 4.0, 0.12), "concrete", loc=P(1.4, 0.2, -0.06))
    mb.box((5.6, 0.23, 1.0), "concrete", loc=P(1.4, 2.08, 0.5))
    mb.box((0.23, 4.0, 1.0), "concrete", loc=P(-1.38, 0.2, 0.5))
    roof = mb.build("hydro_roof")
    (coll or gh._ACTIVE_COLL[0]).objects.link(roof)
    roof["web_real"] = "concrete"
    info["roof"] = roof.name

    # ── 1. the NFT rack ──
    rack = Component("hydro_rack", "NFT rack", "Hydroponics",
                     summary="4 PVC channels on a 3 % slope, 36 lettuce in net cups. A thin film of water runs past the roots.",
                     how="The pump lifts water to the high end; it runs down the channels past the roots and falls back into the tank.",
                     real="Home NFT kit, 4 channels × 2 m (100 × 50 mm PVC)", cost="₹5,100-₹46,800 for a kit (README)")
    mb = MB()
    for x in (0.05, L - 0.05):
        for y in (-0.30, 0.30):
            mb.box((0.025, 0.025, ztop(x) - CH_H), "ms_paint", loc=P(x, y, (ztop(x) - CH_H) / 2))
        mb.box((0.025, 0.62, 0.025), "ms_paint", loc=P(x, 0, ztop(x) - CH_H - 0.012))
        mb.box((0.025, 0.62, 0.025), "ms_paint", loc=P(x, 0, 0.18))
    for y in (-0.30, 0.30):
        mb.box((L - 0.1, 0.025, 0.025), "ms_paint", loc=P(L / 2, y, 0.18))
    rack.part("frame", mb, desc="Painted MS square tube, high end 4 cm taller than the low end")
    for k, y in enumerate(YS):
        mb = MB()
        mb.box((L, CH_W, CH_H), "pvc_white", bevel=0.004, loc=P(L / 2, y, (Z_HI + Z_LO) / 2 - CH_H / 2), rot=(0, SLOPE, 0))
        for x in (0.0, L):
            mb.box((0.012, CH_W + 0.008, CH_H + 0.008), "pvc_grey", loc=P(x, y, ztop(x) - CH_H / 2))
        for j in range(9):
            x = 0.2 + CUP_DX * j
            mb.cyl(0.024, 0.05, "plastic_black", segs=16, r_top=0.026, z0=0.0, loc=P(x, y, ztop(x) - 0.045))
        rack.part(f"channel_{k + 1}", mb, explode=(0, 0, 0.18 + 0.06 * k), desc="100 × 50 mm PVC channel, 9 net cups")
    mb = MB()
    for y in YS:
        for j in range(9):
            x = 0.2 + CUP_DX * j
            lettuce(mb, P(x, y, ztop(x) + 0.004), rnd, size=rnd.uniform(0.9, 1.15))
    rack.part("plants", mb, explode=(0, 0, 0.5), desc="36 loose-leaf lettuce")
    mb = MB()
    mb.cyl(0.008, 0.62, "pe_black", segs=12, z0=0.0, loc=P(-0.07, -0.31, Z_HI + 0.05), axis="Y")
    for y in YS:
        mb.sweep([P(-0.07, y, Z_HI + 0.05), P(-0.03, y, Z_HI + 0.06), P(0.03, y, Z_HI - 0.01)], 0.0025, "pe_black", segs=8, fillet=0.02)
    rack.part("manifold", mb, explode=(-0.2, 0, 0.2), desc="16 mm inlet manifold, one 4 mm line into each channel")
    mb = MB()
    mb.cyl(0.025, 0.56, "pvc_grey", segs=20, z0=0.0, loc=P(L + 0.05, -0.28, Z_LO - CH_H - 0.06), axis="Y")
    for y in YS:
        mb.cyl(0.016, 0.07, "pvc_grey", segs=14, z0=0.0, loc=P(L + 0.02, y, Z_LO - CH_H - 0.06))
    mb.sweep([P(L + 0.05, 0.0, Z_LO - CH_H - 0.06), P(L + 0.20, 0.0, Z_LO - CH_H - 0.12), P(2.30, 0.0, TUB["z1"] + 0.05),
              P(2.30, 0.0, TUB["z1"] - 0.05)], 0.025, "pvc_grey", segs=20, fillet=0.08)
    rack.part("return", mb, explode=(0.2, 0, 0), desc="50 mm return header: the water falls back into the tank")
    rack.root.location = (0, 0, 0)

    # ── 2. the reservoir, cut open ──
    res = Component("hydro_reservoir", "Reservoir (cut open)", "Hydroponics",
                    summary="About 70 L of nutrient water, with the pump, the float switch and the three probes.",
                    how="The float switch stops the pump before it runs dry. The flow sensor proves water is moving. pH, EC and "
                        "temperature are read once a minute.", sensors=("pH", "EC", "water temperature", "float switch", "flow"),
                    real="70 L tub, 12 V 240 L/h brushless pump, float switch, DFRobot pH + TDS probes", cost="see README")
    T = TUB
    mb = MB()
    cx, cy = (T["x0"] + T["x1"]) / 2, (T["y0"] + T["y1"]) / 2
    w, d, h, t = T["x1"] - T["x0"], T["y1"] - T["y0"], T["z1"] - T["z0"], T["t"]
    mb.box((w, d, t), "tank_black", loc=P(cx, cy, T["z0"] + t / 2))                       # floor
    mb.box((w, t, h), "tank_black", loc=P(cx, T["y1"] - t / 2, T["z0"] + h / 2))          # back
    for x in (T["x0"] + t / 2, T["x1"] - t / 2):
        mb.box((t, d, h), "tank_black", loc=P(x, cy, T["z0"] + h / 2))                    # sides
    mb.box((w, d / 2, t), "tank_black", loc=P(cx, T["y1"] - d / 4, T["z1"] + t / 2))      # back half of the lid
    for x in (T["x0"] + t / 2, T["x1"] - t / 2):                                           # cream cut faces
        mb.box((t + 0.002, 0.004, h), "cut_cream", loc=P(x, T["y0"] + 0.002, T["z0"] + h / 2))
    mb.box((w, 0.004, t + 0.002), "cut_cream", loc=P(cx, T["y0"] + 0.002, T["z0"] + t / 2))
    mb.box((w, 0.004, t + 0.002), "cut_cream", loc=P(cx, cy + 0.002, T["z1"] + t / 2))
    res.part("tub", mb, desc="About 70 L of water at the float mark; the front is cut away to show inside")
    mb = MB()
    mb.box((w - 2 * t - 0.002, d - t - 0.004, WATER_Z - T["z0"] - t), "hydro_water",
           loc=P(cx, cy - t / 2 + 0.001, (T["z0"] + t + WATER_Z) / 2))
    res.part("water", mb, desc="Nutrient water")
    mb = MB()
    px, py = 2.60, -0.06
    mb.box((0.055, 0.045, 0.04), "plastic_black", bevel=0.004, loc=P(px, py, T["z0"] + t + 0.02))
    mb.cyl(0.008, 0.03, "plastic_black", segs=12, z0=0.0, loc=P(px, py, T["z0"] + t + 0.04))
    res.part("pump", mb, explode=(0, -0.25, 0.25), desc="12 V brushless pump, 240 L/h (₹534)")
    hose = [P(px, py, T["z0"] + t + 0.07), P(px, py, T["z1"] + 0.06), P(2.05, py, T["z1"] + 0.10), P(1.0, -0.36, 0.22),
            P(-0.07, -0.36, 0.22), P(-0.07, -0.33, Z_HI + 0.05)]
    mb = MB()
    mb.sweep(hose, 0.008, "pe_black", segs=10, fillet=0.08)
    rack.part("feed", mb, desc="16 mm line from the pump up to the inlet manifold")
    fx = Vector(hose[1]).lerp(Vector(hose[2]), 0.45)
    mb = MB()
    mb.box((0.06, 0.033, 0.035), "plastic_black", bevel=0.003, loc=tuple(fx))
    for s in (-1, 1):
        mb.cyl(0.011, 0.012, "brass", segs=12, z0=0.0, loc=tuple(fx + Vector((s * 0.03, 0, 0))), axis="X" if s > 0 else "-X")
    res.part("flow", mb, explode=(0, -0.2, 0.2), desc="Hall flow sensor: proves water is really moving (≈ ₹250)")
    info["flow"] = tuple(fx)
    mb = MB()
    fxs = 2.70
    mb.box((0.03, 0.01, 0.12), "plastic_white", loc=P(fxs, 0.16, T["z1"] - 0.06))
    mb.cyl(0.004, 0.11, "plastic_white", segs=10, z0=0.0, loc=P(fxs, 0.13, 0.13))
    mb.cyl(0.012, 0.024, "plastic_white", segs=16, z0=0.0, loc=P(fxs, 0.13, 0.15))
    res.part("float", mb, explode=(0.2, 0, 0.25), desc="Float switch: below the mark the pump stops, even with no computer (₹450)")
    info["float"] = P(fxs, 0.13, 0.17)
    mb = MB()
    mb.box((0.30, 0.03, 0.012), "plastic_white", loc=P(2.45, 0.12, T["z1"] + 0.02))
    mb.cyl(0.006, 0.17, "glass", segs=16, z0=0.0, loc=P(2.36, 0.12, 0.20))
    mb.cyl(0.0085, 0.05, "plastic_black", segs=16, z0=0.0, loc=P(2.36, 0.12, 0.37))
    res.part("ph_probe", mb, explode=(-0.1, 0, 0.35), desc="pH probe (DFRobot Gravity kit, ₹3,909). The weak part: it drifts")
    mb = MB()
    mb.cyl(0.0055, 0.08, "plastic_black", segs=14, z0=0.0, loc=P(2.46, 0.12, 0.22))
    mb.cyl(0.0035, 0.16, "cable", segs=8, z0=0.0, loc=P(2.46, 0.12, 0.30))
    res.part("ec_probe", mb, explode=(0, 0, 0.42), desc="EC probe: nutrient strength (DFRobot TDS, ₹1,248)")
    mb = MB()
    mb.cyl(0.003, 0.05, "stainless", segs=10, z0=0.0, loc=P(2.55, 0.12, 0.24))
    mb.cyl(0.0022, 0.18, "cable", segs=8, z0=0.0, loc=P(2.55, 0.12, 0.29))
    res.part("temp_probe", mb, explode=(0.1, 0, 0.35), desc="Water temperature (EC changes with it)")
    info["ph"] = P(2.36, 0.12, 0.30)
    info["ec"] = P(2.46, 0.12, 0.28)
    info["water"] = P(2.45, -0.10, 0.22)

    # ── 3. the hydro box on the rack leg ──
    box = Component("hydro_box", "Hydro box", "Hydroponics",
                    summary="ESP32 + a 4-channel relay board: pump and three dosing pumps. Checks every action worked.",
                    how="Once a minute: read pH, EC, temperature, float and flow; dose a little, wait 15 minutes, check the reading "
                        "moved. Nothing twice: stop that channel and send a message.", control="ESP32 (rules: build/05-hydro-box)",
                    real="ESP32 DevKit + expansion board, 4-channel 5 V relay, IP65 box", cost="≈ ₹9,400 with everything (README)")
    W, H, D = 200.0, 140.0, 70.0
    MB_ = DK.box_frame(P(L - 0.05, -0.325, 0.62))
    mb = MB()
    DK.ip65_base(mb, MB_, W, H, D, glands=(-60.0, -20.0, 20.0, 60.0))
    box.part("base", mb, desc="IP65 box, 200 × 140 × 70 mm")
    Me = MB_ @ xform((-0.045, 0.01, 8 * DK.MM))
    mb = MB()
    DK.expansion_board(mb, Me)
    DK.esp32_devkit(mb, Me @ xform((DK.EX0 * DK.MM, 0, DK.ESP_ON_EXP_Z * DK.MM)))
    box.part("brain", mb, explode=(0, -0.16, 0.05), desc="ESP32 on its expansion board (₹570)")
    Mr = MB_ @ xform((0.055, 0.0, 8 * DK.MM))
    mb = MB()
    DK.B(mb, Mr, "pcb_blue", 0, 0, 0, 72, 56, 1.6)
    for i, (ox, oy) in enumerate(((-17, 13), (17, 13), (-17, -13), (17, -13))):
        DK.B(mb, Mr, "plastic_blue", ox, oy, 1.6, 15, 19, 15.5, bevel=0.6)
        DK.B(mb, Mr, "plastic_green", ox + (-12 if ox < 0 else 12), oy, 1.6, 7, 15, 9)
    box.part("relays", mb, explode=(0.08, -0.16, 0.05), desc="4-channel relay board: pump, nutrient A + B, pH-down")
    info["box"] = tuple(MB_ @ Vector((0, 0, 0.04)))
    mb = MB()
    tops = [info["ph"], info["ec"], P(2.55, 0.12, 0.47), info["float"]]
    gl = MB_ @ Vector((0, -H / 2 * DK.MM - 0.01, D / 2 * DK.MM))
    for k, tp in enumerate(tops):
        a = Vector(tp) + Vector((0, 0, 0.12))
        mb.sweep([a, a + Vector((-0.05, -0.05, 0.12)), Vector(gl) + Vector((-0.06 + 0.04 * k, -0.02, -0.12)),
                  Vector(gl) + Vector((-0.06 + 0.04 * k, 0, 0))], 0.0022, "cable", segs=6, fillet=0.05)
    box.part("cables", mb, desc="Probe, float and flow cables into the box")

    # ── 4. dosing shelf ──
    dose = Component("hydro_dosing", "Dosing pumps", "Hydroponics",
                     summary="Three 12 V peristaltic pumps: nutrient A, nutrient B, pH-down. 4-second doses only.",
                     how="A dose is tiny on purpose. If two doses don't move the reading, the box stops that pump: bottle empty, "
                         "tube blocked, or the probe has drifted.", real="3 × Kamoer 12 V 37 mL/min peristaltic pump", cost="₹1,197")
    S = SHELF
    mb = MB()
    sx, sy = (S["x0"] + S["x1"]) / 2, (S["y0"] + S["y1"]) / 2
    mb.box((S["x1"] - S["x0"], S["y1"] - S["y0"], 0.018), "wood_post", loc=P(sx, sy, S["z"] - 0.009))
    for x in (S["x0"] + 0.02, S["x1"] - 0.02):
        for y in (S["y0"] + 0.02, S["y1"] - 0.02):
            mb.box((0.02, 0.02, S["z"] - 0.018), "ms_paint", loc=P(x, y, (S["z"] - 0.018) / 2))
    dose.part("shelf", mb, desc="A small shelf beside the tank")
    for k, (lab, cap) in enumerate((("A", "plastic_blue"), ("B", "plastic_orange"), ("pH-", "plastic_red"))):
        x = S["x0"] + 0.08 + 0.14 * k
        mb = MB()
        mb.cyl(0.034, 0.16, "hdpe_white", segs=20, z0=0.0, loc=P(x, 0.07, S["z"]))
        mb.cyl(0.014, 0.025, cap, segs=14, z0=0.0, loc=P(x, 0.07, S["z"] + 0.16))
        mb.box((0.05, 0.002, 0.06), "sticker_white", loc=P(x, 0.07 - 0.035, S["z"] + 0.08))
        mb.text(lab, 0.028, "plastic_black", depth=0.001, loc=P(x, 0.07 - 0.0365, S["z"] + 0.072), rot=(90, 0, 0))
        dose.part(f"bottle_{lab}", mb, explode=(0, 0.15, 0.2), desc=f"500 mL bottle: {'nutrient ' + lab if lab != 'pH-' else 'pH-down'}")
        mb = MB()
        mb.box((0.032, 0.05, 0.034), "plastic_black", bevel=0.003, loc=P(x, -0.07, S["z"] + 0.017))
        mb.cyl(0.017, 0.016, "silicone_clear", segs=18, z0=0.0, loc=P(x, -0.095, S["z"] + 0.022), axis="-Y")
        mb.sweep([P(x, 0.07, S["z"] + 0.185), P(x, 0.02, S["z"] + 0.12), P(x - 0.008, -0.11, S["z"] + 0.03)], 0.002, "silicone_clear",
                 segs=6, fillet=0.03)
        mb.sweep([P(x + 0.008, -0.11, S["z"] + 0.03), P(x, -0.16, S["z"] + 0.08), P(2.72, -0.05 + 0.03 * k, T["z1"] + 0.06),
                  P(2.68, -0.05 + 0.03 * k, WATER_Z + 0.03)], 0.002, "silicone_clear", segs=6, fillet=0.04)
        dose.part(f"pump_{lab}", mb, explode=(0, -0.18, 0.12), desc="Kamoer 12 V peristaltic pump, 37 mL/min (₹399)")
    info["dosing"] = P(sx, -0.07, S["z"] + 0.05)
    info["rack"] = P(1.0, 0.0, Z_HI + 0.1)
    info["origin"] = tuple(O)
    return info
