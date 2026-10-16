"""Product-shot studio for catalog renders: backdrop, soft lights, auto-framing camera, part-label projection."""
import math
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

from gh import D, MB, descendants

HDRI = Path(bpy.app.binary_path).parent / "5.2" / "datafiles" / "studiolights" / "world" / "studio.exr"


def setup_render(scene, w=1600, h=1000, samples=48, pct=100):
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = samples
    scene.eevee.use_raytracing = True
    try:
        scene.eevee.use_shadows = True
    except Exception:
        pass
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = pct
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 92
    scene.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            scene.view_settings.look = look
            break
        except Exception:
            pass
    scene.render.film_transparent = False


def world(scene, strength=0.35, color=None):
    w = bpy.data.worlds.new("studio_world")
    scene.world = w
    nt = w.node_tree
    bg = nt.nodes["Background"]
    if color is not None:
        bg.inputs["Color"].default_value = (*color, 1)
        bg.inputs["Strength"].default_value = strength
        return w
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(HDRI), check_existing=True)
    map_ = nt.nodes.new("ShaderNodeMapping")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    map_.inputs["Rotation"].default_value = (0, 0, D(40))
    nt.links.new(tc.outputs["Generated"], map_.inputs["Vector"])
    nt.links.new(map_.outputs["Vector"], env.inputs["Vector"])
    # show a flat studio grey to the camera, keep the HDRI for lighting/reflections
    lp = nt.nodes.new("ShaderNodeLightPath")
    flat = nt.nodes.new("ShaderNodeBackground")
    flat.inputs["Color"].default_value = (0.62, 0.63, 0.64, 1)
    flat.inputs["Strength"].default_value = 1.0
    bg.inputs["Strength"].default_value = strength
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bg.outputs["Background"], mix.inputs[1])
    nt.links.new(flat.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], nt.nodes["World Output"].inputs["Surface"])
    return w


class Studio:
    def __init__(self, scene):
        self.scene = scene
        self.coll = bpy.data.collections.new("_studio")
        scene.collection.children.link(self.coll)
        # cyclorama backdrop (floor curving up into a back wall), unit size, scaled per shot
        mb = MB()
        from gh import fillet_path
        pts = fillet_path([(0, -3.0, 0), (0, 1.0, 0), (0, 1.0, 3.0)], 0.35, steps=16)
        import bmesh
        bm = bmesh.new()
        L, R = [], []
        for p in pts:
            L.append(bm.verts.new((-4, p[1], p[2])))
            R.append(bm.verts.new((4, p[1], p[2])))
        for i in range(len(pts) - 1):
            bm.faces.new((L[i], R[i], R[i + 1], L[i + 1]))
        mb.add(bm, _backdrop_mat())
        self.backdrop = mb.build("_backdrop", smooth_angle=80)
        self.coll.objects.link(self.backdrop)
        self.cam_data = bpy.data.cameras.new("_cam")
        self.cam_data.lens = 65
        self.cam = bpy.data.objects.new("_cam", self.cam_data)
        self.coll.objects.link(self.cam)
        scene.camera = self.cam
        self.lights = []
        for name, energy, size, color in (("key", 1.0, 1.2, (1, 0.97, 0.92)), ("fill", 0.35, 2.0, (0.9, 0.95, 1.0)),
                                          ("rim", 0.7, 0.8, (1, 1, 1))):
            ld = bpy.data.lights.new("_" + name, "AREA")
            ld.shape = "DISK"
            ld.color = color
            lo = bpy.data.objects.new("_" + name, ld)
            self.coll.objects.link(lo)
            self.lights.append((lo, energy, size))

    def frame(self, objs, az=35.0, el=20.0, margin=1.12, lens=65, floor=True, look_offset=(0, 0, 0)):
        """Point the camera at the world bbox of `objs` from azimuth/elevation (deg) and fit them in frame."""
        bpy.context.view_layer.update()
        pts = []
        for ob in objs:
            if ob.type != "MESH" or ob.hide_render:
                continue
            for c in ob.bound_box:
                pts.append(ob.matrix_world @ Vector(c))
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        ctr = (lo + hi) / 2 + Vector(look_offset)
        size = (hi - lo).length
        self.cam_data.lens = lens
        self.cam_data.clip_start = size * 0.01
        self.cam_data.clip_end = size * 60
        d = Vector((math.cos(D(el)) * math.sin(D(az)), -math.cos(D(el)) * math.cos(D(az)), math.sin(D(el))))
        dist = size * 1.5
        sc = self.scene
        for _ in range(4):
            self.cam.location = ctr + d * dist
            self.cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            bpy.context.view_layer.update()
            ext = 0.0
            for p in pts:
                v = world_to_camera_view(sc, self.cam, p)
                ext = max(ext, abs(v.x - 0.5) * 2, abs(v.y - 0.5) * 2)
            dist *= ext * margin if ext > 0 else 1.0
        self.cam.location = ctr + d * dist
        bpy.context.view_layer.update()
        # backdrop: floor under the object, back wall behind it
        s = max(size * 2.2, 0.3)
        self.backdrop.scale = (s, s, s)
        back = Vector((-math.sin(D(az)), math.cos(D(az)), 0))
        self.backdrop.location = Vector((ctr.x, ctr.y, lo.z)) + back * (size * 1.2) - back * s * 1.0
        self.backdrop.rotation_euler = (0, 0, D(az))
        self.backdrop.hide_render = (not floor) or el < 0
        # lights around the camera
        right = Vector((math.cos(D(az)), math.sin(D(az)), 0))
        for lo_, energy, lsize in self.lights:
            nm = lo_.name
            if nm == "_key":
                pos = ctr + (d * 0.7 - right * 0.8 + Vector((0, 0, 0.9))).normalized() * size * 2.2
            elif nm == "_fill":
                pos = ctr + (d * 0.8 + right * 0.9 + Vector((0, 0, 0.2))).normalized() * size * 2.4
            else:
                pos = ctr + (-d * 0.8 + right * 0.4 + Vector((0, 0, 0.9))).normalized() * size * 2.0
            lo_.location = pos
            lo_.rotation_euler = (ctr - pos).to_track_quat("-Z", "Y").to_euler()
            lo_.data.size = size * lsize
            lo_.data.energy = energy * 14 * (size * 2.2) ** 2
        return ctr, size

    def project(self, ob_list):
        """Pixel positions (0..1, origin top-left) of each object's bbox centre in the current camera."""
        out = {}
        sc = self.scene
        for key, ob in ob_list:
            ms = [o for o in [ob] + descendants(ob) if o.type == "MESH"]
            pts = [o.matrix_world @ Vector(c) for o in ms for c in o.bound_box]
            if not pts:
                continue
            c = sum(pts, Vector()) / len(pts)
            v = world_to_camera_view(sc, self.cam, c)
            out[key] = (round(v.x, 4), round(1 - v.y, 4))
        return out


_BD = [None]


def _backdrop_mat():
    if _BD[0] is None:
        m = bpy.data.materials.new("_backdrop")
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.55, 0.56, 0.57, 1)
        b.inputs["Roughness"].default_value = 0.85
        _BD[0] = m
    return _BD[0]


def render(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
