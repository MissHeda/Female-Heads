import bpy, mathutils
from bl_ext.user_default.mpfb.services.humanservice import HumanService
bm=bpy.data.objects['FH_basemesh']
if not bm.parent: HumanService.add_builtin_rig(bm, 'default', import_weights=True)
V=bm.data.vertices; M=bm.matrix_world
names={g.index:g.name for g in bm.vertex_groups}
acc={}
for v in V:
    p=M@v.co
    if p.z<1.17: continue
    for g in v.groups:
        n=names[g.group]
        if n.startswith(('joint-','helper-','HelperGeometry','JointCubes','body','Left','Right','Mid')) or g.weight<0.05: continue
        a=acc.setdefault(n,[mathutils.Vector(),0.0,0]); a[0]+=p*g.weight; a[1]+=g.weight; a[2]+=1
for n,(s,w,c) in sorted(acc.items(), key=lambda kv:-kv[1][0].z/kv[1][1]):
    q=s/w; print(f"{n:22s} n={c:5d} ({q.x:+.3f},{q.y:+.3f},{q.z:.3f})")
result={}
