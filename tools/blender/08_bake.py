# globals expected: TONE in ('light','dark'), PASSES set
import bpy, math, mathutils, os, numpy as np
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.locationservice import LocationService
OUT=r'C:\Users\Heda\GitHub Repos\Female-Heads\tools\bake'; os.makedirs(OUT,exist_ok=True)
R=2048
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.device='GPU'; sc.cycles.samples=16
head=bpy.data.objects['FH_head']; bm=bpy.data.objects['FH_basemesh']
def obj(sub): return next(o for o in sc.objects if o.name.startswith('FH_basemesh.') and sub in o.name)
eyes,brow,lash,teeth,tongue=obj('low-poly'),obj('eyebrow'),obj('eyelashes'),obj('teeth'),obj('tongue')
def img(name,float_=False,clear=(0,0,0,0)):
    if name in bpy.data.images: bpy.data.images.remove(bpy.data.images[name])
    i=bpy.data.images.new(name,R,R,alpha=True,float_buffer=float_)
    i.generated_color=clear
    if float_: i.colorspace_settings.name='Non-Color'
    return i
# bake material on head
mat=bpy.data.materials.get('FH_bake') or bpy.data.materials.new('FH_bake')
mat.use_nodes=True; nt=mat.node_tree; nt.nodes.clear()
outn=nt.nodes.new('ShaderNodeOutputMaterial'); em=nt.nodes.new('ShaderNodeEmission'); tex=nt.nodes.new('ShaderNodeTexImage')
geo=nt.nodes.new('ShaderNodeNewGeometry'); nt.links.new(em.outputs[0],outn.inputs[0])
nt.nodes.active=tex
if len(head.data.materials)!=1 or head.data.materials[0]!=mat:
    head.data.materials.clear(); head.data.materials.append(mat)
    for p in head.data.polygons: p.material_index=0
head.data.uv_layers.active=head.data.uv_layers['atlas']
for l in head.data.uv_layers: l.active_render = (l.name=='atlas')
def show(objs):
    for o in sc.objects:
        o.select_set(False)
    for o in objs+[head]:
        o.hide_set(False); o.hide_render=False; o.select_set(True)
    bpy.context.view_layer.objects.active=head
def hideall():
    for o in sc.objects:
        if o.name.startswith('FH_basemesh'): o.hide_render=True
def bake(target, type_, sel, **kw):
    tex.image=target
    show(sel)
    bpy.ops.object.bake(type=type_, use_selected_to_active=bool(sel), cage_extrusion=0.004 if sel else 0, max_ray_distance=0.012 if sel else 0, margin=16, use_clear=True, target='IMAGE_TEXTURES', **kw)
    hideall()
def npimg(i): return np.array(i.pixels[:],dtype=np.float32).reshape(R,R,4)
def save(arr,name,srgb=True):
    i=bpy.data.images.new(name,R,R,alpha=True); 
    if not srgb: i.colorspace_settings.name='Non-Color'
    i.pixels=np.clip(arr,0,1).astype(np.float32).ravel(); i.filepath_raw=os.path.join(OUT,name+'.png'); i.file_format='PNG'; i.save(); bpy.data.images.remove(i)
res={}
if 'skin' in PASSES:
    d=LocationService.get_user_data()
    skin={'light':'young_caucasian_female','dark':'young_african_female'}[TONE]
    HumanService.set_character_skin(os.path.join(d,'skins',skin,skin+'.mhmat'), bm)
    i=img('FH_skin'); bake(i,'DIFFUSE',[bm,eyes,teeth,tongue],pass_filter={'COLOR'})
    np.save(os.path.join(OUT,f'skin_{TONE}.npy'), npimg(i)); res['skin']=True
if 'brow' in PASSES:
    # emission copies of brow/lash materials: color, then alpha
    for mode in ('col','alpha'):
        saved={}
        for o in (brow,):
            m=o.active_material; saved[o]=m
            m2=m.copy(); o.active_material=m2; t=m2.node_tree
            ti=next(n for n in t.nodes if n.type=='TEX_IMAGE' and n.image)
            for n in list(t.nodes):
                if n.type=='OUTPUT_MATERIAL': out=n
            e=t.nodes.new('ShaderNodeEmission'); t.links.new(ti.outputs['Color' if mode=='col' else 'Alpha'], e.inputs[0]); t.links.new(e.outputs[0], out.inputs[0])
        i=img('FH_brow_'+mode); bake(i,'EMIT',[brow])
        np.save(os.path.join(OUT,f'brow_{mode}.npy'), npimg(i))
        for o,m in saved.items():
            tmp=o.active_material; o.active_material=m; bpy.data.materials.remove(tmp)
    res['brow']=True
if 'pos' in PASSES:
    for what,sock in (('pos','Position'),('nrm','Normal')):
        nt.links.new(geo.outputs[sock], em.inputs[0])
        i=img('FH_'+what,True); bake(i,'EMIT',[])
        np.save(os.path.join(OUT,f'{what}.npy'), npimg(i))
    res['pos']=True
if 'normal' in PASSES:
    sub=bm.modifiers.new('fh_sub','SUBSURF'); sub.levels=2; sub.render_levels=2
    i=img('FH_nrm_t',False,(0.5,0.5,1,1)); i.colorspace_settings.name='Non-Color'
    bake(i,'NORMAL',[bm,eyes,teeth,tongue])
    bm.modifiers.remove(sub)
    np.save(os.path.join(OUT,'normal.npy'), npimg(i)); res['normal']=True
if 'ao' in PASSES:
    sc.cycles.samples=128
    i=img('FH_ao',False,(1,1,1,1)); bake(i,'AO',[])
    np.save(os.path.join(OUT,'ao.npy'), npimg(i)); res['ao']=True
    sc.cycles.samples=16
result=res
