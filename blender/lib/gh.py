"""Shared helpers for the greenhouse component library (Blender 5.2, headless).

Every component is an Empty ("root") with parts parented to it. Roots and parts carry custom properties that
survive glTF export as `extras`, so the later web twin can read them:
  root: gh_type="component", gh_id, title, category, summary, how_it_works, sensors, control, state (json), real_part
  part: gh_type="part", part_name, desc, explode (xyz offset in the parent's space), base_loc
"""
import json
import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

TAU = math.tau
D = math.radians

# ───────────────────────────── materials ─────────────────────────────
_MATS = {}

SPEC = {
    # metals
    "galv": dict(color=(0.60, 0.62, 0.63), metal=1, rough=0.42),
    "galv_dull": dict(color=(0.52, 0.54, 0.55), metal=1, rough=0.6),
    "steel_dark": dict(color=(0.22, 0.23, 0.24), metal=1, rough=0.45),
    "stainless": dict(color=(0.75, 0.75, 0.74), metal=1, rough=0.32),
    "alu": dict(color=(0.80, 0.81, 0.83), metal=1, rough=0.32),
    "alu_black": dict(color=(0.04, 0.04, 0.045), metal=1, rough=0.4),
    "brass": dict(color=(0.86, 0.66, 0.36), metal=1, rough=0.28),
    "copper": dict(color=(0.93, 0.58, 0.42), metal=1, rough=0.3),
    "chrome": dict(color=(0.9, 0.9, 0.9), metal=1, rough=0.08),
    # paints / plastics
    "ral7035": dict(color=(0.74, 0.75, 0.73), rough=0.45),  # light-grey cabinet paint
    "anthracite": dict(color=(0.085, 0.09, 0.095), rough=0.55),  # Multifan panel grey
    "chhotu_green": dict(color=(0.22, 0.72, 0.08), rough=0.4),     # Kirloskar Chhotu motor green
    "grundfos_black": dict(color=(0.03, 0.03, 0.032), rough=0.45),
    "paint_green": dict(color=(0.10, 0.32, 0.18), rough=0.4),
    "paint_blue": dict(color=(0.05, 0.18, 0.45), rough=0.4),
    "paint_motor": dict(color=(0.02, 0.1, 0.28), rough=0.35, coat=0.3),
    "pvc_grey": dict(color=(0.42, 0.44, 0.46), rough=0.38),
    "pvc_white": dict(color=(0.86, 0.86, 0.84), rough=0.32),
    "pvc_blue": dict(color=(0.07, 0.22, 0.55), rough=0.35),
    "pvc_red": dict(color=(0.62, 0.05, 0.04), rough=0.35),
    "pe_black": dict(color=(0.018, 0.018, 0.02), rough=0.42),
    "plastic_black": dict(color=(0.025, 0.025, 0.028), rough=0.5),
    "plastic_dark": dict(color=(0.07, 0.075, 0.08), rough=0.45),
    "plastic_white": dict(color=(0.88, 0.88, 0.86), rough=0.4),
    "plastic_cream": dict(color=(0.84, 0.81, 0.72), rough=0.45),
    "plastic_yellow": dict(color=(0.95, 0.72, 0.02), rough=0.4),
    "plastic_orange": dict(color=(0.95, 0.35, 0.03), rough=0.4),
    "plastic_red": dict(color=(0.7, 0.02, 0.02), rough=0.35),
    "plastic_green": dict(color=(0.05, 0.45, 0.12), rough=0.4),
    "plastic_blue": dict(color=(0.03, 0.2, 0.6), rough=0.4),
    "plastic_purple": dict(color=(0.35, 0.12, 0.5), rough=0.4),
    "hdpe_white": dict(color=(0.9, 0.9, 0.87), rough=0.55, subsurface=0.15),
    "hdpe_blue": dict(color=(0.1, 0.3, 0.65), rough=0.5),
    "tank_black": dict(color=(0.03, 0.03, 0.03), rough=0.55),
    "rubber": dict(color=(0.015, 0.015, 0.015), rough=0.85),
    "silicone": dict(color=(0.55, 0.12, 0.08), rough=0.6),
    "silicone_clear": dict(color=(0.85, 0.85, 0.8), rough=0.3, alpha=0.6),
    "norprene": dict(color=(0.86, 0.72, 0.45), rough=0.45),
    "epoxy_black": dict(color=(0.03, 0.03, 0.035), rough=0.3),
    "sticker_white": dict(color=(0.93, 0.93, 0.92), rough=0.6),
    "sticker_yellow": dict(color=(0.98, 0.78, 0.02), rough=0.6),
    # transparent
    "glass": dict(color=(0.75, 0.85, 0.85), rough=0.03, alpha=0.4, coat=1.0),
    "acrylic": dict(color=(0.78, 0.88, 0.92), rough=0.05, alpha=0.38, coat=1.0),
    "polycarb": dict(color=(0.93, 0.96, 0.97), rough=0.15, alpha=0.16),
    "uv_film": dict(color=(0.95, 0.97, 0.96), rough=0.22, alpha=0.13, sheen=0.2),   # 200 µm UV poly film
    "water": dict(color=(0.35, 0.55, 0.6), rough=0.05, alpha=0.45),
    "nutrient": dict(color=(0.45, 0.32, 0.12), rough=0.05, alpha=0.6),
    "net": dict(color=(0.9, 0.9, 0.9), rough=0.8, alpha=0.35),
    "diffuser": dict(color=(0.95, 0.95, 0.95), rough=0.4, subsurface=0.3),
    # electronics
    "pcb": dict(color=(0.02, 0.22, 0.1), rough=0.35),
    "pcb_blue": dict(color=(0.02, 0.08, 0.3), rough=0.35),
    "chip": dict(color=(0.02, 0.02, 0.02), rough=0.3),
    "gold": dict(color=(1.0, 0.76, 0.33), metal=1, rough=0.25),
    "wire_red": dict(color=(0.6, 0.03, 0.02), rough=0.4),
    "wire_black": dict(color=(0.02, 0.02, 0.02), rough=0.4),
    "wire_blue": dict(color=(0.03, 0.1, 0.5), rough=0.4),
    "wire_grey": dict(color=(0.35, 0.36, 0.37), rough=0.5),
    "cable": dict(color=(0.03, 0.03, 0.035), rough=0.55),
    "lens": dict(color=(0.01, 0.01, 0.015), rough=0.02, coat=1.0),
    "led_white": dict(color=(1, 0.95, 0.85), rough=0.3, emit=(1, 0.93, 0.8), emit_strength=0.0),
    "led_green": dict(color=(0.1, 0.9, 0.2), rough=0.3, emit=(0.1, 1, 0.2), emit_strength=3.0),
    "led_red": dict(color=(0.9, 0.05, 0.02), rough=0.3, emit=(1, 0.05, 0.02), emit_strength=3.0),
    "led_amber": dict(color=(1, 0.5, 0.0), rough=0.3, emit=(1, 0.45, 0.0), emit_strength=3.0),
    "led_blue": dict(color=(0.1, 0.3, 1), rough=0.3, emit=(0.1, 0.35, 1), emit_strength=3.0),
    "screen": dict(color=(0.01, 0.012, 0.015), rough=0.05, coat=1.0),
    # agriculture
    "coco": dict(color=(0.30, 0.17, 0.08), rough=0.95, noise=("coco", 180.0, 0.35)),
    "coco_dry": dict(color=(0.45, 0.3, 0.16), rough=0.95, noise=("coco", 180.0, 0.35)),
    "rockwool": dict(color=(0.55, 0.47, 0.32), rough=0.95, noise=("fibre", 250.0, 0.25)),
    "slab_film": dict(color=(0.9, 0.9, 0.88), rough=0.45, sheen=0.3),
    "soil": dict(color=(0.16, 0.1, 0.06), rough=0.95, noise=("coco", 120.0, 0.4)),
    "leaf": dict(color=(0.07, 0.22, 0.035), rough=0.55, sheen=0.08, vcol=True),
    "leaf_under": dict(color=(0.2, 0.38, 0.12), rough=0.6, sheen=0.5),
    "stem": dict(color=(0.16, 0.30, 0.06), rough=0.6, sheen=0.15, vcol=True),
    "stem_old": dict(color=(0.26, 0.30, 0.1), rough=0.65, sheen=0.1),
    "sepal": dict(color=(0.08, 0.26, 0.04), rough=0.55, sheen=0.1),
    "flower": dict(color=(0.95, 0.62, 0.02), rough=0.6),
    "anther": dict(color=(0.9, 0.62, 0.02), rough=0.5),
    "tomato": dict(color=(0.55, 0.035, 0.012), rough=0.14, coat=0.6, subsurface=0.1, vcol=True),
    "fruit": dict(color=(1.0, 1.0, 1.0), rough=0.2, coat=0.5, vcol=True),
    "cotyledon": dict(color=(0.12, 0.3, 0.05), rough=0.55),
    "seed": dict(color=(0.72, 0.6, 0.38), rough=0.7),
    "twine": dict(color=(0.85, 0.83, 0.78), rough=0.9),
    "concrete": dict(color=(0.48, 0.47, 0.45), rough=0.9, noise=("concrete", 30.0, 0.15)),
    "gravel": dict(color=(0.30, 0.25, 0.19), rough=0.95, noise=("concrete", 60.0, 0.3)),
    "ground_cover": dict(color=(0.9, 0.9, 0.88), rough=0.7),  # white woven floor cloth
    "pad": dict(color=(0.55, 0.38, 0.19), rough=0.95, noise=("pad", 25.0, 0.5)),
    "sticky": dict(color=(1.0, 0.85, 0.0), rough=0.15, coat=0.8),
    "insect": dict(color=(0.02, 0.02, 0.02), rough=0.6),
    "whitefly": dict(color=(0.95, 0.95, 0.92), rough=0.6),
    # farm site (6 Oct 2026)
    "solar_cell": dict(color=(0.015, 0.03, 0.075), rough=0.12, coat=1.0),        # mono-PERC cells under glass
    "cell_line": dict(color=(0.42, 0.45, 0.5), rough=0.4),                       # cell gaps / busbars
    "hdpe_liner": dict(color=(0.03, 0.03, 0.032), rough=0.35, sheen=0.2),        # 500 µm pond liner
    "pond_water": dict(color=(0.07, 0.13, 0.09), rough=0.03, alpha=0.88, coat=1.0),      # murky green farm-pond water
    "aluminet": dict(color=(0.8, 0.81, 0.83), metal=0.85, rough=0.42, alpha=0.85,
                     pattern=("stripes", 0.04, 0.75, 0.15)),        # knitted aluminised strips with gaps
    "chainlink": dict(color=(0.62, 0.64, 0.65), metal=1, rough=0.45, alpha=0.5,
                      pattern=("diamond", 0.07, 0.14, 0.0)),        # GI wire diamonds
    "brick": dict(color=(0.45, 0.17, 0.08), rough=0.9, noise=("concrete", 40.0, 0.2)),
    "sand_wet": dict(color=(0.32, 0.22, 0.13), rough=0.95, noise=("coco", 150.0, 0.3)),
    "straw": dict(color=(0.62, 0.5, 0.28), rough=0.95, noise=("fibre", 120.0, 0.3)),
    "plaster_white": dict(color=(0.86, 0.85, 0.82), rough=0.85, noise=("concrete", 25.0, 0.08)),
    "disinfectant": dict(color=(0.15, 0.4, 0.55), rough=0.05, alpha=0.55),
    "signboard": dict(color=(0.03, 0.05, 0.045), rough=0.35, coat=0.4),
    "accent_green": dict(color=(0.1, 0.85, 0.35), rough=0.3, emit=(0.1, 0.9, 0.35), emit_strength=1.5),
}


def mat(name):
    """Get (or create) a named material from SPEC. Principled BSDF only, so it exports cleanly to glTF."""
    if name in _MATS:
        return _MATS[name]
    s = SPEC[name]
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    col = s["color"]
    b.inputs["Base Color"].default_value = (*col, 1.0)
    b.inputs["Metallic"].default_value = s.get("metal", 0.0)
    b.inputs["Roughness"].default_value = s.get("rough", 0.5)
    if s.get("coat"):
        b.inputs["Coat Weight"].default_value = s["coat"]
        b.inputs["Coat Roughness"].default_value = 0.08
    if s.get("sheen"):
        b.inputs["Sheen Weight"].default_value = s["sheen"]
        b.inputs["Sheen Roughness"].default_value = 0.4
    if s.get("subsurface"):
        b.inputs["Subsurface Weight"].default_value = s["subsurface"]
        b.inputs["Subsurface Radius"].default_value = (0.02, 0.02, 0.01)
    if s.get("emit"):
        b.inputs["Emission Color"].default_value = (*s["emit"], 1.0)
        b.inputs["Emission Strength"].default_value = s.get("emit_strength", 0.0)
    a = s.get("alpha", 1.0)
    if a < 1.0:
        b.inputs["Alpha"].default_value = a
        m.surface_render_method = "BLENDED"
        m.use_backface_culling = False
    m.diffuse_color = (*col, a)  # viewport solid colour
    if s.get("vcol"):  # per-vertex tint (leaves/fruit variety); glTF exports it as COLOR_0
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = "Col"
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs["A"].default_value = (*col, 1.0)
        nt.links.new(at.outputs["Color"], mix.inputs["B"])
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    if s.get("noise") and s["noise"][0] == "pad":  # cross-fluted cellulose: diagonal bands
        kind, scale, amt = s["noise"]
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1, 1, -1)  # second flute direction (x − z)
        waves = []
        for src in (tc.outputs["Object"], mp.outputs["Vector"]):
            w_ = nt.nodes.new("ShaderNodeTexWave")
            w_.bands_direction = "DIAGONAL"
            w_.inputs["Scale"].default_value = scale
            nt.links.new(src, w_.inputs["Vector"])
            waves.append(w_)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
        mn = nt.nodes.new("ShaderNodeMath")
        mn.operation = "MINIMUM"
        nt.links.new(waves[0].outputs["Fac"], mn.inputs[0])
        nt.links.new(waves[1].outputs["Fac"], mn.inputs[1])
        wv = mn
        ramp = nt.nodes.new("ShaderNodeMix")
        ramp.data_type = "RGBA"
        ramp.inputs["A"].default_value = (col[0] * 0.3, col[1] * 0.3, col[2] * 0.3, 1.0)
        ramp.inputs["B"].default_value = (*col, 1.0)
        nt.links.new(mn.outputs["Value"], ramp.inputs["Factor"])
        nt.links.new(ramp.outputs["Result"], b.inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = amt
        nt.links.new(wv.outputs["Value"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    elif s.get("noise"):  # render-only surface grain (dropped on glTF export; fine)
        kind, scale, amt = s["noise"]
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = scale
        nz.inputs["Detail"].default_value = 6.0
        nz.inputs["Roughness"].default_value = 0.65
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = amt
        nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
        if not s.get("vcol"):
            ramp = nt.nodes.new("ShaderNodeMix")
            ramp.data_type = "RGBA"
            ramp.inputs["Factor"].default_value = 0.35
            ramp.inputs["A"].default_value = (*col, 1.0)
            ramp.inputs["B"].default_value = (col[0] * 0.55, col[1] * 0.55, col[2] * 0.55, 1.0)
            nt.links.new(nz.outputs["Fac"], ramp.inputs["Factor"])
            nt.links.new(ramp.outputs["Result"], b.inputs["Base Color"])
    if s.get("pattern"):  # render-only alpha mask (glTF keeps the plain alpha): chain-link diamonds / net strips
        kind, sp, wd, gap_a = s["pattern"]
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs[0])

        def node_math(op, a, b=None):
            n_ = nt.nodes.new("ShaderNodeMath")
            n_.operation = op
            for i_, v_ in enumerate((a, b)):
                if v_ is None:
                    continue
                if isinstance(v_, (int, float)):
                    n_.inputs[i_].default_value = v_
                else:
                    nt.links.new(v_, n_.inputs[i_])
            return n_.outputs[0]
        if kind == "diamond":       # panels stand along x or y, so u = x + y runs along every panel
            u = node_math("ADD", sep.outputs["X"], sep.outputs["Y"])
            d1 = node_math("FRACT", node_math("DIVIDE", node_math("ADD", u, sep.outputs["Z"]), sp))
            d2 = node_math("FRACT", node_math("DIVIDE", node_math("SUBTRACT", u, sep.outputs["Z"]), sp))
            wire = node_math("MAXIMUM", node_math("LESS_THAN", d1, wd), node_math("LESS_THAN", d2, wd))
        else:                       # strips run along x (the net's travel), gaps across y
            wire = node_math("LESS_THAN", node_math("FRACT", node_math("DIVIDE", sep.outputs["Y"], sp)), wd)
        alpha = node_math("ADD", node_math("MULTIPLY", wire, a - gap_a), gap_a)
        nt.links.new(alpha, b.inputs["Alpha"])
        m.surface_render_method = "DITHERED"
    _MATS[name] = m
    return m


def emissive(name, color, strength):
    """A dedicated emissive material (screens, status lights)."""
    key = f"emit::{name}"
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Emission Color"].default_value = (*color, 1)
    b.inputs["Emission Strength"].default_value = strength
    b.inputs["Roughness"].default_value = 0.2
    _MATS[key] = m
    return m


# ───────────────────────────── transforms ─────────────────────────────
def xform(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    """rot in degrees (XYZ Euler)."""
    s = scale if hasattr(scale, "__len__") else (scale, scale, scale)
    return (Matrix.Translation(Vector(loc)) @ Euler([D(a) for a in rot]).to_matrix().to_4x4()
            @ Matrix.Diagonal((*s, 1.0)))


AXIS_ROT = {"Z": (0, 0, 0), "X": (0, 90, 0), "Y": (-90, 0, 0), "-Z": (180, 0, 0), "-X": (0, -90, 0), "-Y": (90, 0, 0)}


# ───────────────────────────── raw bmesh generators ─────────────────────────────
def bm_lathe(profile, segs=48, closed=False, arc=TAU, phase=0.0):
    """Revolve an (r, z) outline around Z. Outline order: outer surface upward, inner surface downward."""
    bm = bmesh.new()
    full = abs(arc - TAU) < 1e-6
    n = segs if full else segs + 1
    angs = [phase + arc * i / segs for i in range(n)]
    rings = []
    for r, z in profile:
        if r < 1e-7:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a in angs])
    pairs = list(zip(rings[:-1], rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    m = segs
    for A, B in pairs:
        for j in range(m):
            j1 = (j + 1) % n if full else j + 1
            if len(A) == 1 and len(B) == 1:
                continue
            try:
                if len(A) == 1:
                    bm.faces.new((A[0], B[j1], B[j]))
                elif len(B) == 1:
                    bm.faces.new((A[j], A[j1], B[0]))
                else:
                    bm.faces.new((A[j], A[j1], B[j1], B[j]))
            except ValueError:
                pass
    return bm


def bm_box(sx, sy, sz, bevel=0.0, segs=3):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=min(bevel, 0.49 * min(sx, sy, sz)),
                        segments=segs, profile=0.5, affect="EDGES", clamp_overlap=True)
    return bm


def bm_cyl(r, h, segs=32, bevel=0.0, r_top=None, z0=None):
    """Solid cylinder/cone from z=0..h (or centred if z0 is None → -h/2..h/2) with optional chamfer."""
    rt = r if r_top is None else r_top
    base = -h / 2 if z0 is None else z0
    b = min(bevel, 0.45 * min(r, rt if rt > 0 else r, h))
    if b > 0:
        prof = [(0, base), (r - b, base), (r, base + b), (rt, base + h - b), (max(rt - b, 0), base + h), (0, base + h)]
    else:
        prof = [(0, base), (r, base), (rt, base + h), (0, base + h)]
    return bm_lathe(prof, segs)


def bm_tube(r_out, r_in, h, segs=32, z0=None):
    base = -h / 2 if z0 is None else z0
    return bm_lathe([(r_in, base), (r_out, base), (r_out, base + h), (r_in, base + h)], segs, closed=True)


def bm_torus(R, r, segs=32, rsegs=12, arc=TAU):
    prof = [(R + r * math.cos(a), r * math.sin(a)) for a in [TAU * i / rsegs for i in range(rsegs)]]
    return bm_lathe(prof, segs, closed=True, arc=arc)


def bm_sphere(r, segs=24, rings=12, squash=1.0):
    prof = [(r * math.sin(math.pi * i / rings), -r * squash * math.cos(math.pi * i / rings)) for i in range(rings + 1)]
    prof[0] = (0, prof[0][1])
    prof[-1] = (0, prof[-1][1])
    return bm_lathe(prof, segs)


def bm_prism(pts, depth, z0=0.0, bevel=0.0):
    """Extrude a 2D polygon (CCW, XY plane) along +Z."""
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]
    hi = [bm.verts.new((x, y, z0 + depth)) for x, y in pts]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    if bevel > 0:
        side = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-9]
        bmesh.ops.bevel(bm, geom=side, offset=bevel, segments=2, profile=0.5, affect="EDGES", clamp_overlap=True)
    return bm


def fillet_path(pts, radius=0.05, steps=6):
    """Round the corners of a polyline (for pipes/cables)."""
    P = [Vector(p) for p in pts]
    if len(P) < 3 or radius <= 0:
        return P
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        d1, d2 = (a - b), (c - b)
        l1, l2 = d1.length, d2.length
        if l1 < 1e-9 or l2 < 1e-9:
            continue
        d1.normalize()
        d2.normalize()
        if d1.dot(d2) < -0.999:  # straight
            out.append(b)
            continue
        t = min(radius, 0.45 * l1, 0.45 * l2)
        p0, p2 = b + d1 * t, b + d2 * t
        for k in range(steps + 1):
            u = k / steps
            out.append((1 - u) ** 2 * p0 + 2 * (1 - u) * u * b + u * u * p2)
    out.append(P[-1])
    return out


def bm_sweep(pts, radius, segs=12, cap=True, radii=None, flat=None):
    """Tube along a polyline using parallel-transport frames. `flat`=(w,h) makes a rectangular section."""
    P = [Vector(p) for p in pts]
    n = len(P)
    T = []
    for i in range(n):
        d = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)])
        T.append(d.normalized() if d.length > 1e-12 else Vector((0, 0, 1)))
    ref = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = [T[0].cross(ref).normalized()]
    for i in range(1, n):
        q = T[i - 1].rotation_difference(T[i])
        N.append((q @ N[-1]).normalized())
    bm = bmesh.new()
    rings = []
    if flat:
        w, h = flat
        shape = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    else:
        shape = [(math.cos(TAU * j / segs), math.sin(TAU * j / segs)) for j in range(segs)]
    for i in range(n):
        t, nn = T[i], N[i]
        bb = t.cross(nn)
        r = radii[i] if radii else radius
        if flat:
            rings.append([bm.verts.new(P[i] + nn * x + bb * y) for x, y in shape])
        else:
            rings.append([bm.verts.new(P[i] + r * (nn * x + bb * y)) for x, y in shape])
    m = len(shape)
    for i in range(n - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(m):
            j1 = (j + 1) % m
            bm.faces.new((A[j], A[j1], B[j1], B[j]))
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    return bm


TEXT_RES = 12  # curve resolution of text meshes (lowered for the web build)


def bm_text(s, size=0.02, depth=0.001, align="CENTER", font_bold=False):
    cu = bpy.data.curves.new("txt", "FONT")
    cu.resolution_u = TEXT_RES
    cu.body = s
    cu.size = size
    cu.extrude = depth / 2
    cu.align_x = align
    cu.align_y = "CENTER"
    if font_bold:
        try:
            cu.font = bpy.data.fonts.load("C:/Windows/Fonts/arialbd.ttf", check_existing=True)
        except Exception:
            pass
    else:
        try:
            cu.font = bpy.data.fonts.load("C:/Windows/Fonts/arial.ttf", check_existing=True)
        except Exception:
            pass
    ob = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    return bm


# ───────────────────────────── mesh builder ─────────────────────────────
class MB:
    """Accumulates many primitives (each with its own material + transform) into ONE mesh object."""

    def __init__(self):
        self.bm = bmesh.new()
        self.col = self.bm.verts.layers.float_color.new("Col")
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.mats = []

    def _mi(self, m):
        if isinstance(m, str):
            m = mat(m)
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def add(self, src, m, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), axis=None, M=None, tint=None, smooth=True,
            planar_uv=None):
        """Append bmesh `src` (consumed). `axis` points the primitive's local +Z along X/Y/Z/-X…"""
        if M is None:
            M = xform(loc, rot, scale)
            if axis:
                M = M @ xform(rot=AXIS_ROT[axis])
        mi = self._mi(m)
        tint = tint or (1, 1, 1)
        vmap = {}
        for v in src.verts:
            nv = self.bm.verts.new(M @ v.co)
            nv[self.col] = (*tint, 1.0)
            vmap[v] = nv
        uvsrc = src.loops.layers.uv.active
        for f in src.faces:
            try:
                nf = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = mi
            nf.smooth = smooth
            if uvsrc is not None:
                for l_new, l_old in zip(nf.loops, f.loops):
                    l_new[self.uv].uv = l_old[uvsrc].uv
            elif planar_uv:
                ax0, ax1, s0, s1, o0, o1 = (tuple(planar_uv) + (0.5, 0.5))[:6]  # project local coords to UV
                for l_new, l_old in zip(nf.loops, f.loops):
                    co = l_old.vert.co
                    l_new[self.uv].uv = (co[ax0] * s0 + o0, co[ax1] * s1 + o1)
        src.free()
        return self

    # convenience wrappers
    def box(self, size, m, bevel=0.0, **kw):
        return self.add(bm_box(*size, bevel=bevel), m, **kw)

    def cyl(self, r, h, m, segs=32, bevel=0.0, r_top=None, z0=None, **kw):
        return self.add(bm_cyl(r, h, segs, bevel, r_top, z0), m, **kw)

    def tube(self, r_out, r_in, h, m, segs=32, z0=None, **kw):
        return self.add(bm_tube(r_out, r_in, h, segs, z0), m, **kw)

    def lathe(self, profile, m, segs=48, closed=False, arc=TAU, **kw):
        return self.add(bm_lathe(profile, segs, closed, arc), m, **kw)

    def torus(self, R, r, m, segs=32, rsegs=12, **kw):
        return self.add(bm_torus(R, r, segs, rsegs), m, **kw)

    def sphere(self, r, m, segs=24, rings=12, squash=1.0, **kw):
        return self.add(bm_sphere(r, segs, rings, squash), m, **kw)

    def prism(self, pts, depth, m, z0=0.0, bevel=0.0, **kw):
        return self.add(bm_prism(pts, depth, z0, bevel), m, **kw)

    def sweep(self, pts, r, m, segs=12, cap=True, fillet=0.0, radii=None, flat=None, **kw):
        if fillet > 0:
            pts = fillet_path(pts, fillet)
            radii = None
        return self.add(bm_sweep(pts, r, segs, cap, radii, flat), m, **kw)

    def text(self, s, size, m, depth=0.001, align="CENTER", bold=False, **kw):
        return self.add(bm_text(s, size, depth, align, bold), m, smooth=False, **kw)

    def empty(self):
        return len(self.bm.verts) == 0

    def build(self, name, smooth_angle=35.0):
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        if smooth_angle is not None and len(me.polygons):
            flags = [p.use_smooth for p in me.polygons]
            me.set_sharp_from_angle(angle=D(smooth_angle))
            for p, f in zip(me.polygons, flags):
                p.use_smooth = f
        ob = bpy.data.objects.new(name, me)
        return ob


# ───────────────────────────── components & parts ─────────────────────────────
_ACTIVE_COLL = [None]


def set_collection(coll):
    _ACTIVE_COLL[0] = coll


def get_coll(name, parent=None, scene=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        if parent is not None:
            parent.children.link(c)
        elif scene is not None:
            scene.collection.children.link(c)
    return c


_CATALOG = None


def catalog_entry(cid):
    """The real-product line (tools/products.py) that this component id belongs to, or None.
    Matches the exact id first, then the id without a trailing _1/_2 (exhaust_fan_1 → exhaust_fan)."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = {}
        try:
            import importlib.util
            from pathlib import Path
            src = Path(__file__).resolve().parents[2] / "tools" / "products.py"
            spec = importlib.util.spec_from_file_location("gh_products", src)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for e in mod.P:
                for k in e["comps"]:
                    _CATALOG.setdefault(k, e)
        except Exception as ex:  # the model still builds without prices
            print("real-product catalog not loaded:", ex)
    import re
    base = re.sub(r"_\d+$", "", cid)
    return _CATALOG.get(cid) or _CATALOG.get(base) or next(
        (e for k, e in _CATALOG.items() if re.sub(r"_\d+$", "", k) == base), None)


def catalog_cost(e):
    unit = f"₹{e['unit']:,}"
    txt = f"{unit} each" if e["qty"] > 1 else unit
    if e.get("est"):
        txt += " (estimate, quote needed)"
    if e.get("opt"):
        txt += " · optional"
    return txt


class Component:
    """One clickable, explodable component (a pump, a valve, a plant…).
    If the id is in the real-product catalog, `real_part` and `cost` come from there (one source of truth)."""

    def __init__(self, cid, title, category, summary="", how="", sensors=(), control="", state=None, real="",
                 cost="", coll=None, view=None):
        parent_coll = coll or _ACTIVE_COLL[0]
        self.coll = bpy.data.collections.new(cid)
        parent_coll.children.link(self.coll)
        self.root = bpy.data.objects.new(cid, None)
        self.root.empty_display_type = "PLAIN_AXES"
        self.root.empty_display_size = 0.05
        self.coll.objects.link(self.root)
        r = self.root
        r["gh_type"] = "component"
        r["gh_id"] = cid
        r["title"] = title
        r["category"] = category
        r["summary"] = summary
        r["how_it_works"] = how
        r["sensors"] = ", ".join(sensors) if not isinstance(sensors, str) else sensors
        r["control"] = control
        r["state"] = json.dumps(state or {})
        e = catalog_entry(cid)
        r["real_part"] = e["product"] if e else real
        r["cost"] = catalog_cost(e) if e else cost
        if e:
            r["catalog_key"] = e["key"]
        if view:
            r["view"] = list(view)  # preferred catalog camera (azimuth, elevation)
        self.parts = {}

    def part(self, name, mb, explode=(0, 0, 0), desc="", parent=None, loc=(0, 0, 0), rot=(0, 0, 0),
             smooth_angle=35.0):
        ob = mb.build(f"{self.root.name}.{name}", smooth_angle) if isinstance(mb, MB) else mb
        self.coll.objects.link(ob)
        ob.parent = parent if parent is not None else self.root
        ob.location = loc
        ob.rotation_euler = [D(a) for a in rot]
        ob["gh_type"] = "part"
        ob["part_name"] = name
        ob["desc"] = desc
        ob["explode"] = list(explode)
        ob["base_loc"] = list(loc)
        self.parts[name] = ob
        return ob

    def group(self, name, explode=(0, 0, 0), desc="", parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
        """A sub-assembly empty whose children explode together."""
        e = bpy.data.objects.new(f"{self.root.name}.{name}", None)
        e.empty_display_size = 0.02
        self.coll.objects.link(e)
        e.parent = parent if parent is not None else self.root
        e.location = loc
        e.rotation_euler = [D(a) for a in rot]
        e["gh_type"] = "group"
        e["part_name"] = name
        e["desc"] = desc
        e["explode"] = list(explode)
        e["base_loc"] = list(loc)
        self.parts[name] = e
        return e

    def place(self, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
        self.root.location = loc
        self.root.rotation_euler = [D(a) for a in rot]
        self.root.scale = (scale, scale, scale)
        return self


def explode(root, t):
    """Move every part of a component by t × its explode offset (t=0 assembled, 1 exploded)."""
    stack = list(root.children)
    while stack:
        ob = stack.pop()
        if "explode" in ob and "base_loc" in ob:
            b = Vector(ob["base_loc"])
            ob.location = b + t * Vector(ob["explode"])
        stack.extend(ob.children)


def descendants(root):
    out, stack = [], list(root.children)
    while stack:
        ob = stack.pop()
        out.append(ob)
        stack.extend(ob.children)
    return out


def clone(root, new_id, coll):
    """Linked duplicate of a whole component (meshes shared) → cheap repeats (drippers, valves…)."""
    sub = bpy.data.collections.new(new_id)
    coll.children.link(sub)
    mapping = {}

    def rec(ob, parent):
        c = ob.copy()  # shares mesh data
        sub.objects.link(c)
        c.parent = parent
        if parent is None:
            c.name = new_id
            c["gh_id"] = new_id
        else:
            c.name = ob.name.replace(root.name, new_id, 1)
        mapping[ob] = c
        for ch in ob.children:
            rec(ch, c)
        return c

    return rec(root, None)


def seed(n):
    random.seed(n)


def image_mat(name, path, emit=0.0, rough=0.4, alpha=False):
    """Material with an image texture (screens, labels, QR codes). Emissive when emit > 0."""
    key = f"img::{name}"
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(str(path), check_existing=True)
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if emit > 0:
        nt.links.new(tx.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
    if alpha:
        nt.links.new(tx.outputs["Alpha"], b.inputs["Alpha"])
        m.surface_render_method = "BLENDED"
    _MATS[key] = m
    return m
