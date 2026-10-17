"""Prepare the assembled greenhouse for the browser and export glTF binaries.

- Base colours that come from node set-ups (vertex-colour tint, noise grain) are flattened to plain factors,
  because glTF only understands a constant base colour (or a texture).
- Vertex colours are kept only where they carry information (leaf/fruit/stem tint), pre-multiplied by the colour.
- UVs are kept only on meshes that use an image texture.
"""
import bpy

import gh


def _spec_color(mat_name):
    base = mat_name.split(".")[0]
    s = gh.SPEC.get(base)
    return s["color"] if s else None


def _uses_image(m):
    return any(n.bl_idname == "ShaderNodeTexImage" for n in m.node_tree.nodes) if m and m.node_tree else False


def _is_vcol(m):
    if not m:
        return False
    s = gh.SPEC.get(m.name.split(".")[0])
    return bool(s and s.get("vcol"))


def prepare(objects):
    meshes = {o.data for o in objects if o.type == "MESH"}
    for me in meshes:
        mats = list(me.materials)
        vcol_idx = {i for i, m in enumerate(mats) if _is_vcol(m)}
        col = me.color_attributes.get("Col")
        if col is not None:
            if vcol_idx:
                # multiply the tint by the material colour for faces that use a vcol material; white elsewhere
                vmat = {}
                for p in me.polygons:
                    for v in p.vertices:
                        vmat[v] = p.material_index
                data = col.data
                for v, mi in vmat.items():
                    if mi in vcol_idx:
                        c = _spec_color(mats[mi].name) or (1, 1, 1)
                        t = data[v].color
                        data[v].color = (t[0] * c[0], t[1] * c[1], t[2] * c[2], 1.0)
                    else:
                        data[v].color = (1.0, 1.0, 1.0, 1.0)
            else:
                me.color_attributes.remove(col)
        if not any(_uses_image(m) for m in mats):
            while me.uv_layers:
                me.uv_layers.remove(me.uv_layers[0])
    for m in bpy.data.materials:
        if not m.node_tree:
            continue
        b = m.node_tree.nodes.get("Principled BSDF")
        if b is None or _uses_image(m):
            continue
        for sock in ("Base Color", "Normal"):
            for lk in list(b.inputs[sock].links):
                m.node_tree.links.remove(lk)
        if _is_vcol(m):
            b.inputs["Base Color"].default_value = (1, 1, 1, 1)
        else:
            c = _spec_color(m.name)
            if c:
                b.inputs["Base Color"].default_value = (*c, 1.0)


def export(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        try:
            o.select_set(True)
        except RuntimeError:
            pass
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True, export_extras=True, export_yup=True,
        export_apply=False, export_vertex_color="NAME", export_vertex_color_name="Col", export_all_vertex_colors=False,
        export_active_vertex_color_when_no_material=False, export_materials="EXPORT", export_image_format="JPEG",
        export_lights=False, export_cameras=False, export_texcoords=True, export_normals=True)
