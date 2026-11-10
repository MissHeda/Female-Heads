import bpy, mathutils
from bl_ext.user_default.mpfb.services.targetservice import TargetService
bm=bpy.data.objects['FH_basemesh']
if bm.data.shape_keys: TargetService.bake_targets(bm)
V=bm.data.vertices; M=bm.matrix_world
def grp(name):
    i=bm.vertex_groups[name].index
    P=[M@v.co for v in V if any(g.group==i for g in v.groups)]
    return sum(P,mathutils.Vector())/len(P)
body=bm.vertex_groups['body'].index
zs=[(M@v.co).z for v in V if any(g.group==body for g in v.groups)]
print('top', round(max(zs),4), 'n', len(V))
for n in ('joint-head','joint-head-2','joint-neck','joint-jaw','joint-mouth','joint-l-eye','joint-r-eye','joint-l-upperlid','joint-l-lowerlid'):
    c=grp(n); print(n, tuple(round(x,4) for x in c))
result={}
