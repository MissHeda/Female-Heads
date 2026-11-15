"""Contact sheet of the characters, rendered from the binarized models (tools/preview_data.py) with their face
textures (tools/out/<name>_co.png). Runs without a window:
  blender -b --python tools/blender/sheet.py -- [suffix ...]      suffix: "" (bun), "_braid", "_tac", "_braid_tac"
Writes tools/out/sheet_<id><suffix>.png (front, three-quarter, side, back).
"""
import bpy, math, os, sys
import numpy as np
from mathutils import Vector

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
O = os.path.join(REPO, "tools", "out"); C = os.path.join(REPO, "tools", "check")
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
IDS = ["kovacs", "reyes", "okoye", "walsh", "lindqvist", "fraser", "novak"]
# "ids=carter,medrano": only these (the Timberwolf faces share one model, mhfh_tftw_braid)
for a in [a for a in args if a.startswith("ids=")]: IDS = a[4:].split(","); args.remove(a)
SUFFIXES = args or ["", "_braid"]
RES = 512; VIEWS = ((0, 0), (40, 5), (95, 0), (165, 8))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = sc.render.resolution_y = RES
sc.world = bpy.data.worlds.new("w"); sc.world.use_nodes = True
bg = sc.world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.6, 0.6, 0.62, 1); bg.inputs[1].default_value = 1.0
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 85
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 3; sun.rotation_euler = (math.radians(50), 0, math.radians(-30)); sc.collection.objects.link(sun)
mat = bpy.data.materials.new("face"); mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); tx = nt.nodes.new("ShaderNodeTexImage")
nt.links.new(bs.outputs[0], out.inputs[0]); nt.links.new(tx.outputs[0], bs.inputs["Base Color"]); bs.inputs["Roughness"].default_value = 0.62

for suffix in SUFFIXES:
    model_suffix = suffix.replace("_tac", "")
    for cid in IDS:
        npz = os.path.join(C, f"mhfh_{cid}{model_suffix}.npz")
        if not os.path.exists(npz): npz = os.path.join(C, f"mhfh_tftw{model_suffix}.npz")
        d = np.load(npz); P, F, uv = d["P"], d["F"], d["uv"]
        me = bpy.data.meshes.new("head")
        me.from_pydata([(p[0], p[2], p[1]) for p in P], [], [tuple(int(i) for i in f[::-1]) for f in F]); me.update()
        l = me.uv_layers.new(name="uv")
        for p in me.polygons:
            p.use_smooth = True
            for li in p.loop_indices:
                u, v = uv[me.loops[li].vertex_index]; l.data[li].uv = (u, 1 - v)
        ob = bpy.data.objects.new("head", me); sc.collection.objects.link(ob); me.materials.append(mat)
        tx.image = bpy.data.images.load(os.path.join(O, f"mhfh_{cid}{suffix}_co.png"))
        tiles = []
        for az, el in VIEWS:
            a, e = math.radians(az), math.radians(el); c = Vector((0, -0.01, 0.655))
            pos = c + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * 0.72
            cam.location = pos; cam.rotation_euler = (c - pos).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = os.path.join(O, f"_tile_{len(tiles)}.png"); bpy.ops.render.render(write_still=True); tiles.append(sc.render.filepath)
        sheet = np.zeros((RES, RES * len(tiles), 4), dtype=np.float32)
        for k, t in enumerate(tiles):
            im = bpy.data.images.load(t); sheet[:, k * RES:(k + 1) * RES] = np.array(im.pixels[:], dtype=np.float32).reshape(RES, RES, 4); bpy.data.images.remove(im); os.remove(t)
        big = bpy.data.images.new("sheet", RES * len(tiles), RES); big.pixels = sheet.ravel()
        big.filepath_raw = os.path.join(O, f"sheet_{cid}{suffix}.png"); big.file_format = "PNG"; big.save(); bpy.data.images.remove(big)
        bpy.data.images.remove(tx.image); bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
        print("rendered", cid + suffix)
