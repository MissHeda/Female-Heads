import bpy, bmesh
exec(open(r'C:\Users\Heda\AppData\Local\Temp\claude\8f03d91783da74f4\63ff5fce-fa89-46de-83be-aa45bc30713c\scratchpad\fh\10_export.py').read().split("lod(1.0")[0])
sc=bpy.context.scene; head=bpy.data.objects['FH_head']
me=head.data.copy(); ob=bpy.data.objects.new('FH_tmp_shadow',me); sc.collection.objects.link(ob); ob.matrix_world=head.matrix_world
for g in head.vertex_groups: ob.vertex_groups.new(name=g.name)
bm_=bmesh.new(); bm_.from_mesh(me); dl=bm_.verts.layers.deform.active
drop={i for i,g in enumerate(head.vertex_groups) if g.name.startswith(('eye.','tongue'))}
kill=[v for v in bm_.verts if any(k in drop for k in v[dl].keys())]
bmesh.ops.delete(bm_, geom=kill, context='VERTS'); bm_.to_mesh(me); bm_.free()
r=ob.modifiers.new('r','REMESH'); r.mode='VOXEL'; r.voxel_size=0.007
d=ob.modifiers.new('d','DECIMATE'); d.ratio=0.12; d.use_symmetry=True
with bpy.context.temp_override(object=ob, active_object=ob):
    bpy.ops.object.modifier_apply(modifier='r'); bpy.ops.object.modifier_apply(modifier='d')
print('shadow faces', len(ob.data.polygons))
ob.data.uv_layers.new(name='atlas')
t=ob.modifiers.new('t','DATA_TRANSFER'); t.object=head; t.use_vert_data=True; t.data_types_verts={'VGROUP_WEIGHTS'}; t.vert_mapping='POLYINTERP_NEAREST'
t.layers_vgroup_select_src='ALL'; t.layers_vgroup_select_dst='NAME'
with bpy.context.temp_override(object=ob, active_object=ob): bpy.ops.object.modifier_apply(modifier='t')
dump(ob,'shadow'); bpy.data.objects.remove(ob)
result={}
