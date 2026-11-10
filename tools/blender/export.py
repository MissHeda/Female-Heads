"""Step 4 (Blender): export FH_head and its LODs to tools/bake/*.npz for tools/build_p3d.py.

lod1 = FH_head as built, lod2/lod3 = decimated, shadow = closed voxel shell of skin + bun with transferred weights.
Run: node ~/.claude/blender-bridge/run.js tools/blender/export.py
"""
import bpy, bmesh, numpy as np, os
OUT = r"C:\Users\Heda\GitHub Repos\Female-Heads\tools\bake"
sc = bpy.data.scenes["FemaleHead"]; head = bpy.data.objects["FH_head"]


def dump(ob, name):
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg); me = ev.to_mesh()
    b = bmesh.new(); b.from_mesh(me); bmesh.ops.triangulate(b, faces=b.faces[:]); b.to_mesh(me); b.free()
    V = np.array([list(v.co) for v in me.vertices], dtype=np.float64)
    uv = me.uv_layers["atlas"].data if "atlas" in me.uv_layers else None
    cn = me.corner_normals
    F, UV, NR = [], [], []
    for p in me.polygons:
        F.append([me.loops[l].vertex_index for l in p.loop_indices])
        UV.append([list(uv[l].uv) if uv else [0, 0] for l in p.loop_indices])
        NR.append([list(cn[l].vector) for l in p.loop_indices])
    names = [g.name for g in ob.vertex_groups]
    G = [(v.index, g.group, g.weight) for v in me.vertices for g in v.groups if g.weight > 0.005]
    np.savez(os.path.join(OUT, name + ".npz"), V=V, F=np.array(F), UV=np.array(UV), N=np.array(NR), G=np.array(G), names=np.array(names))
    ev.to_mesh_clear(); print(name, len(V), "points", len(F), "faces")


def copy(name):
    me = head.data.copy(); ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    for g in head.vertex_groups: ob.vertex_groups.new(name=g.name)
    return ob


def apply(ob, mod):
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_apply(modifier=mod.name)


dump(head, "lod1")
for name, ratio in (("lod2", 0.5), ("lod3", 0.22)):
    ob = copy("FH_tmp_" + name)
    m = ob.modifiers.new("d", "DECIMATE"); m.ratio = ratio; m.use_symmetry = True; m.symmetry_axis = "X"
    dump(ob, name); bpy.data.meshes.remove(ob.data)

# shadow volume: one closed shell
ob = copy("FH_tmp_shadow"); me = ob.data
b = bmesh.new(); b.from_mesh(me); dl = b.verts.layers.deform.active
drop = {head.vertex_groups[n].index for n in ("FH_p_eye", "FH_p_tongue", "FH_p_teeth", "FH_p_cavity") if n in head.vertex_groups}
bmesh.ops.delete(b, geom=[v for v in b.verts if any(k in drop and v[dl][k] > 0.5 for k in v[dl].keys())], context="VERTS")
b.to_mesh(me); b.free()
r = ob.modifiers.new("r", "REMESH"); r.mode = "VOXEL"; r.voxel_size = 0.005; apply(ob, r)
d = ob.modifiers.new("d", "DECIMATE"); d.ratio = min(1.0, 520 / max(1, sum(len(p.vertices) - 2 for p in ob.data.polygons))); apply(ob, d)
# a shadow volume must be closed: drop anything decimation left non-manifold and fill the holes
b = bmesh.new(); b.from_mesh(ob.data)
for _ in range(4):
    bad = [e for e in b.edges if not e.is_manifold]
    if not bad: break
    bmesh.ops.delete(b, geom=list({f for e in bad for f in e.link_faces if len(e.link_faces) > 2}), context="FACES")
    bmesh.ops.holes_fill(b, edges=[e for e in b.edges if e.is_boundary], sides=0)
    bmesh.ops.triangulate(b, faces=b.faces[:])
print("shadow non-manifold edges", sum(1 for e in b.edges if not e.is_manifold))
bmesh.ops.recalc_face_normals(b, faces=b.faces[:]); b.to_mesh(ob.data); b.free()
# stay inside the visual model so the head does not shadow itself
s = ob.modifiers.new("s", "DISPLACE"); s.strength = -0.0025; s.mid_level = 0.0; apply(ob, s)
t = ob.modifiers.new("t", "DATA_TRANSFER"); t.object = head; t.use_vert_data = True; t.data_types_verts = {"VGROUP_WEIGHTS"}
t.vert_mapping = "POLYINTERP_NEAREST"; t.layers_vgroup_select_src = "ALL"; t.layers_vgroup_select_dst = "NAME"; apply(ob, t)
dump(ob, "shadow"); bpy.data.meshes.remove(ob.data)
result = {"ok": True}
