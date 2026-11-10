import bpy, bmesh, numpy as np, json, os
OUT=r'C:\Users\Heda\GitHub Repos\Female-Heads\tools\bake'
sc=bpy.context.scene; head=bpy.data.objects['FH_head']
def dump(ob, name):
    dg=bpy.context.evaluated_depsgraph_get(); ev=ob.evaluated_get(dg); me=ev.to_mesh()
    bm_=bmesh.new(); bm_.from_mesh(me); bmesh.ops.triangulate(bm_, faces=bm_.faces[:]); bm_.to_mesh(me); bm_.free()
    me.calc_loop_triangles() if hasattr(me,'calc_loop_triangles') else None
    M=ob.matrix_world
    V=np.array([list(M@v.co) for v in me.vertices],dtype=np.float64)
    uv=me.uv_layers['atlas'].data
    F=[];UV=[];NR=[]
    cn=me.corner_normals
    R=M.to_3x3()
    for p in me.polygons:
        F.append([me.loops[l].vertex_index for l in p.loop_indices])
        UV.append([list(uv[l].uv) for l in p.loop_indices])
        NR.append([list((R@cn[l].vector).normalized()) for l in p.loop_indices])
    names=[g.name for g in ob.vertex_groups]
    G=[]
    for v in me.vertices:
        for g in v.groups:
            if g.weight>0.01: G.append((v.index,g.group,g.weight))
    np.savez(os.path.join(OUT,name+'.npz'),V=V,F=np.array(F),UV=np.array(UV),N=np.array(NR),G=np.array(G),names=np.array(names))
    ev.to_mesh_clear(); print(name,len(V),len(F))
def lod(ratio,name):
    me=head.data.copy(); ob=bpy.data.objects.new('FH_tmp_'+name,me); sc.collection.objects.link(ob); ob.matrix_world=head.matrix_world
    for g in head.vertex_groups: ob.vertex_groups.new(name=g.name)
    if ratio<1:
        m=ob.modifiers.new('d','DECIMATE'); m.ratio=ratio; m.use_symmetry=True; m.symmetry_axis='X'
    dump(ob,name); bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
lod(1.0,'lod1'); lod(0.5,'lod2'); lod(0.22,'lod3'); lod(0.10,'shadow')
result={}
