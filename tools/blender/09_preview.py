import bpy, os, sys
TONE=globals().get('TONE','light')
O=r'C:\Users\Heda\GitHub Repos\Female-Heads\tools\out'
h=bpy.data.objects['FH_head']
m=bpy.data.materials.get('FH_preview') or bpy.data.materials.new('FH_preview'); m.use_nodes=True; nt=m.node_tree; nt.nodes.clear()
o=nt.nodes.new('ShaderNodeOutputMaterial'); b=nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(b.outputs[0],o.inputs[0])
def im(p,nc=False):
    for i in list(bpy.data.images):
        if i.filepath==p: bpy.data.images.remove(i)
    i=bpy.data.images.load(p); 
    if nc: i.colorspace_settings.name='Non-Color'
    t=nt.nodes.new('ShaderNodeTexImage'); t.image=i; return t
c=im(os.path.join(O,f'fh_{TONE}_co.png')); nt.links.new(c.outputs[0],b.inputs['Base Color'])
n=im(os.path.join(O,'fh_nohq.png'),True)
sep=nt.nodes.new('ShaderNodeSeparateColor'); comb=nt.nodes.new('ShaderNodeCombineColor'); inv=nt.nodes.new('ShaderNodeMath'); inv.operation='SUBTRACT'; inv.inputs[0].default_value=1
nt.links.new(n.outputs[0],sep.inputs[0]); nt.links.new(sep.outputs[0],comb.inputs[0]); nt.links.new(sep.outputs[1],inv.inputs[1]); nt.links.new(inv.outputs[0],comb.inputs[1]); nt.links.new(sep.outputs[2],comb.inputs[2])
nm=nt.nodes.new('ShaderNodeNormalMap'); nm.uv_map='atlas'; nt.links.new(comb.outputs[0],nm.inputs[1]); nt.links.new(nm.outputs[0],b.inputs['Normal'])
b.inputs['Roughness'].default_value=0.55
h.data.materials.clear(); h.data.materials.append(m)
h.data.uv_layers.active=h.data.uv_layers['atlas']
for l in h.data.uv_layers: l.active_render=(l.name=='atlas')
sys.path.insert(0, r'C:\Users\Heda\AppData\Local\Temp\claude\8f03d91783da74f4\63ff5fce-fa89-46de-83be-aa45bc30713c\scratchpad\fh')
import importlib, render; importlib.reload(render)
for ob in bpy.context.scene.objects:
    if ob.name.startswith('FH_basemesh'): ob.hide_render=True
bpy.context.scene.render.engine='BLENDER_EEVEE'
render.render(None,(0,-0.02,1.46),dist=0.85,views=((0,0),(40,10),(100,0),(170,10)))
result={}
