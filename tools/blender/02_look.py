import bpy, sys
sys.path.insert(0, r'C:\Users\Heda\AppData\Local\Temp\claude\8f03d91783da74f4\63ff5fce-fa89-46de-83be-aa45bc30713c\scratchpad\fh')
import importlib, render; importlib.reload(render)
bm=bpy.data.objects['FH_basemesh']
vg=bm.vertex_groups['joint-head'].index
import mathutils
pts=[bm.matrix_world@v.co for v in bm.data.vertices if any(g.group==vg for g in v.groups)]
c=sum(pts,mathutils.Vector())/len(pts)
print('head joint', c)
render.render(None,(c.x,c.y,c.z+0.06),dist=0.75)
result={'c':list(c)}
