"""Run when opening a .blend in the Blender UI: switch viewports to Material Preview and frame the greenhouse."""
import math

import bpy
from mathutils import Euler, Vector


def frame():
    """Greenhouse: fixed view. Library: fit the whole component grid."""
    if bpy.data.objects.get("greenhouse_structure"):
        return Vector((4.5, 0.0, 1.2)), 16.0
    pts = [o.matrix_world @ Vector(c) for o in bpy.data.objects
           if o.type == "MESH" and not o.name.startswith("_") for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return (lo + hi) / 2, (hi - lo).length * 0.75


def setup():
    loc, dist = frame()
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type != "VIEW_3D":
                continue
            for sp in area.spaces:
                if sp.type == "VIEW_3D":
                    sp.shading.type = "MATERIAL"
                    sp.clip_end = 500
                    r3d = sp.region_3d
                    r3d.view_perspective = "PERSP"
                    r3d.view_location = loc
                    r3d.view_rotation = Euler((math.radians(62), 0, math.radians(-40))).to_quaternion()
                    r3d.view_distance = dist
    return None


bpy.app.timers.register(setup, first_interval=1.0)
