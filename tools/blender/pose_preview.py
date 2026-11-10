"""Render the head in poses computed by tools/simulate.py (vanilla face animations replayed on the binarized model).

Globals: NPZ (simulate output), POSES (list of animation names), OUT, TONE. One row: rest pose + each pose, front and 3/4.
"""
import bpy, os, sys, numpy as np
REPO = r"C:\Users\Heda\GitHub Repos\Female-Heads"
NPZ = globals().get("NPZ"); POSES = globals().get("POSES", ["vizem_A", "vizem_E", "vizem_M", "hurt", "dead"])
OUT = globals().get("OUT", os.path.join(REPO, "tools", "out", "poses.png")); TONE = globals().get("TONE", "light")
TEXTURED = globals().get("TEXTURED", True)
sc = bpy.data.scenes["FemaleHead"]; d = np.load(NPZ)
P0 = d["P"]; F = d["F"]; uv = d["uv"]
for o in list(sc.objects):
    if o.name.startswith("FH_pose"): bpy.data.objects.remove(o)
me = bpy.data.meshes.new("FH_pose")
me.from_pydata([(p[0], p[2], p[1]) for p in P0], [], [tuple(int(i) for i in f[::-1]) for f in F]); me.update()
l = me.uv_layers.new(name="atlas")
for p in me.polygons:
    for li in p.loop_indices:
        u, v = uv[me.loops[li].vertex_index]; l.data[li].uv = (u, 1 - v)
    p.use_smooth = True
ob = bpy.data.objects.new("FH_pose", me); sc.collection.objects.link(ob)
sys.path.insert(0, os.path.join(REPO, "tools", "blender"))
import importlib, render; importlib.reload(render)
tiles = []
for k, name in enumerate(["rest"] + list(POSES)):
    Pd = P0 if name == "rest" else d[name]
    for v, p in zip(me.vertices, Pd): v.co = (p[0], p[2], p[1])
    me.update()
    out = OUT.replace(".png", f"_{k}.png")
    if TEXTURED:
        g = {"OBJ": "FH_pose", "TONE": TONE, "OUT": out, "VIEWS": ((0, 0), (40, 5)), "DIST": 0.5, "CENTER": (0, -0.05, 0.668), "RES": 512, "__name__": "x"}
        exec(open(os.path.join(REPO, "tools", "blender", "preview.py")).read(), g)
    else:
        m = bpy.data.materials.get("FH_clay") or bpy.data.materials.new("FH_clay"); me.materials.clear(); me.materials.append(m)
        for o in sc.objects:
            if o.type == "MESH": o.hide_render = o is not ob
        sc.render.engine = "BLENDER_EEVEE"
        render.render(None, (0, -0.05, 0.668), dist=0.5, views=((0, 0), (40, 5)), out=out, res=512)
    tiles.append(out)
imgs = [bpy.data.images.load(t) for t in tiles]
w, h = imgs[0].size; cols = 3; rows = (len(imgs) + cols - 1) // cols
sheet = np.zeros((rows * h, cols * w, 4), dtype=np.float32)
for i, im in enumerate(imgs):
    r, c = divmod(i, cols)
    sheet[(rows - 1 - r) * h:(rows - r) * h, c * w:(c + 1) * w] = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(im); os.remove(tiles[i])
big = bpy.data.images.new("FH_sheet", cols * w, rows * h); big.pixels = sheet.ravel(); big.filepath_raw = OUT; big.file_format = "PNG"; big.save(); bpy.data.images.remove(big)
bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
result = {"poses": ["rest"] + list(POSES)}
