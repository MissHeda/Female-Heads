import bpy, bmesh, math, mathutils
sc=bpy.context.scene
head=bpy.data.objects['FH_head']; src=bpy.data.objects['FH_basemesh']
gi=src.vertex_groups['joint-l-eye'].index
EZ=sum((src.matrix_world@v.co).z for v in src.data.vertices if any(g.group==gi for g in v.groups))
EZ/= sum(1 for v in src.data.vertices if any(g.group==gi for g in v.groups))
# --- bun: low bun at the back of the head
Hw=head.matrix_world
bz=EZ-0.035
back=max((Hw@v.co).y for v in head.data.vertices if abs((Hw@v.co).z-bz)<0.01 and abs((Hw@v.co).x)<0.02)
if 'FH_bun' in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects['FH_bun'])
bm_=bmesh.new()
bmesh.ops.create_uvsphere(bm_, u_segments=20, v_segments=12, radius=1.0)
for v in bm_.verts:
    x,y,z=v.co
    ang=math.atan2(z,x)
    r=1.0+0.07*math.sin(3*ang+4*y)        # coiled ridges
    v.co=mathutils.Vector((x*0.034*r, y*0.024*(1-0.25*(y<0)), z*0.027*r))
me=bpy.data.meshes.new('FH_bun'); bm_.to_mesh(me); bm_.free()
bun=bpy.data.objects.new('FH_bun',me); sc.collection.objects.link(bun)
bun.location=(0, back+0.010, bz)
for p in me.polygons: p.use_smooth=True
g=bun.vertex_groups.new(name='head'); g.add(list(range(len(me.vertices))),1.0,'REPLACE')
bun.vertex_groups.new(name='FH_bunmark').add(list(range(len(me.vertices))),1.0,'REPLACE')
if not me.uv_layers: me.uv_layers.new(name='UVMap')
# mark head parts for later
mark=head.vertex_groups.get('FH_bunmark') or head.vertex_groups.new(name='FH_bunmark')
# join bun into head
with bpy.context.temp_override(active_object=head, selected_editable_objects=[head,bun], selected_objects=[head,bun]):
    bpy.ops.object.join()
me=head.data
print('uv layers', [u.name for u in me.uv_layers], 'verts', len(me.vertices), 'tris', sum(len(p.vertices)-2 for p in me.polygons))
# --- atlas UV: copy first layer, then pack
base=me.uv_layers[0]
at=me.uv_layers.get('atlas') or me.uv_layers.new(name='atlas')
for i,l in enumerate(base.data): at.data[i].uv=l.uv
me.uv_layers.active=at
win=bpy.context.window_manager.windows[0]
area=next(a for a in win.screen.areas if a.type=='VIEW_3D')
region=next(r for r in area.regions if r.type=='WINDOW')
for o in sc.objects: o.select_set(False)
head.select_set(True); bpy.context.view_layer.objects.active=head
with bpy.context.temp_override(window=win, area=area, region=region, screen=win.screen, active_object=head, object=head):
    bpy.ops.object.mode_set(mode='EDIT')
    import bmesh as B
    bmE=B.from_edit_mesh(me); bun_idx=head.vertex_groups['FH_bunmark'].index; dl=bmE.verts.layers.deform.active
    for f in bmE.faces:
        f.select = all(bun_idx in v[dl] for v in f.verts)
    B.update_edit_mesh(me)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')
me.uv_layers.active=at
result={'v':len(me.vertices)}
