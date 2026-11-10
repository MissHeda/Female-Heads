import bpy, bmesh, math, mathutils
sc=bpy.context.scene
for n in ('FH_head',):
    if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n])
src=bpy.data.objects['FH_basemesh']
_gi=src.vertex_groups['joint-l-eye'].index
_ez=[ (src.matrix_world@v.co).z for v in src.data.vertices if any(g.group==_gi for g in v.groups)]
EZ=sum(_ez)/len(_ez)
def dup(o, name):
    me=o.data.copy(); ob=bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    ob.matrix_world=o.matrix_world.copy()
    for g in o.vertex_groups: ob.vertex_groups.new(name=g.name)
    # vertex group data is in mesh (copied), names recreated in same order
    return ob
def cut_skin(ob):
    bm_=bmesh.new(); bm_.from_mesh(ob.data); dl=bm_.verts.layers.deform.active
    body=ob.vertex_groups['body'].index
    kill=[]
    for v in bm_.verts:
        p=ob.matrix_world@v.co
        zc=EZ-0.212+max(0.0,abs(p.x)-0.045)*1.6+max(0.0,-p.y-0.03)*0.8
        if body not in v[dl] or p.z<zc: kill.append(v)
    bmesh.ops.delete(bm_, geom=kill, context='VERTS')
    # keep largest component
    seen=set(); comps=[]
    for v in bm_.verts:
        if v in seen: continue
        st=[v]; c=[]; seen.add(v)
        while st:
            a=st.pop(); c.append(a)
            for e in a.link_edges:
                b=e.other_vert(a)
                if b not in seen: seen.add(b); st.append(b)
        comps.append(c)
    comps.sort(key=len)
    bmesh.ops.delete(bm_, geom=[v for c in comps[:-1] for v in c], context='VERTS')
    bm_.to_mesh(ob.data); bm_.free()
skin=dup(src,'FH_head'); cut_skin(skin)
_m=skin.modifiers.new('dec','DECIMATE'); _m.ratio=0.5; _m.use_symmetry=True; _m.symmetry_axis='X'
with bpy.context.temp_override(object=skin, active_object=skin): bpy.ops.object.modifier_apply(modifier='dec')
parts=[skin]
for o in list(sc.objects):
    if o.type!='MESH' or o is skin or o is src: continue
    if 'low-poly' in o.name or 'teeth' in o.name or 'tongue' in o.name:
        p=dup(o,'FH_tmp_'+o.name.split('.')[-1])
        if 'teeth' in p.name:
            m=p.modifiers.new('dec','DECIMATE'); m.ratio=0.09
            bpy.context.view_layer.objects.active=p
            with bpy.context.temp_override(object=p, active_object=p): bpy.ops.object.modifier_apply(modifier='dec')
        if 'low-poly' in p.name:
            gl=p.vertex_groups.get('eye.L') or p.vertex_groups.new(name='eye.L'); gr=p.vertex_groups.get('eye.R') or p.vertex_groups.new(name='eye.R')
            for v in p.data.vertices:
                (gl if (p.matrix_world@v.co).x>0 else gr).add([v.index],1.0,'REPLACE')
        parts.append(p)
for o in sc.objects: o.select_set(False)
for p in parts: p.select_set(True)
bpy.context.view_layer.objects.active=skin
with bpy.context.temp_override(active_object=skin, selected_editable_objects=parts, selected_objects=parts):
    bpy.ops.object.join()
skin.modifiers.clear(); skin.parent=None
print('FH_head', len(skin.data.vertices), 'verts', sum(len(p.vertices)-2 for p in skin.data.polygons), 'tris', [m.name for m in skin.data.materials])
skin.hide_render=False
src.hide_render=True; src.hide_set(True)
for o in sc.objects:
    if o.name.startswith('FH_basemesh.'): o.hide_render=True; o.hide_set(True)
import sys; sys.path.insert(0, r'C:\Users\Heda\AppData\Local\Temp\claude\8f03d91783da74f4\63ff5fce-fa89-46de-83be-aa45bc30713c\scratchpad\fh')
import importlib, render; importlib.reload(render)
render.render(None,(0,-0.03,EZ-0.06),dist=0.95,views=((0,0),(45,0),(90,0),(160,0)))
result={}
