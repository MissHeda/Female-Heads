import bpy, math, mathutils, os
OUT = os.environ.get('FH_OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'render.png'))
def render(target_objs, center, dist=0.6, views=((0,0),(60,0),(90,0),(180,0)), out=OUT, res=512):
    sc = bpy.context.scene
    cam = bpy.data.objects.get('FH_cam')
    if not cam:
        cam = bpy.data.objects.new('FH_cam', bpy.data.cameras.new('FH_cam')); sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.lens = 85
    if not sc.world: sc.world = bpy.data.worlds.new('FHw')
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get('Background'); bg.inputs[0].default_value=(0.6,0.6,0.62,1); bg.inputs[1].default_value=1.0
    if 'FH_key' not in bpy.data.objects:
        l = bpy.data.objects.new('FH_key', bpy.data.lights.new('FH_key','SUN')); l.data.energy=3; l.rotation_euler=(math.radians(50),0,math.radians(-30)); sc.collection.objects.link(l)
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = res; sc.render.resolution_y = res
    sc.render.film_transparent=False
    import tempfile
    tiles=[]
    for i,(az,el) in enumerate(views):
        a=math.radians(az); e=math.radians(el)
        c=mathutils.Vector(center)
        pos=c+mathutils.Vector((math.sin(a)*math.cos(e), -math.cos(a)*math.cos(e), math.sin(e)))*dist
        cam.location=pos
        cam.rotation_euler=(c-pos).to_track_quat('-Z','Y').to_euler()
        p=out.replace('.png',f'_{i}.png'); sc.render.filepath=p
        bpy.ops.render.render(write_still=True); tiles.append(p)
    # stitch
    imgs=[bpy.data.images.load(p) for p in tiles]
    W=res*len(imgs); big=bpy.data.images.new('FH_sheet',W,res)
    import numpy as np
    arr=np.zeros((res,W,4),dtype=np.float32)
    for k,im in enumerate(imgs):
        px=np.array(im.pixels[:],dtype=np.float32).reshape(res,res,4); arr[:,k*res:(k+1)*res]=px; bpy.data.images.remove(im)
    big.pixels=arr.ravel(); big.filepath_raw=out; big.file_format='PNG'; big.save(); bpy.data.images.remove(big)
    for p in tiles: os.remove(p)
    return out
