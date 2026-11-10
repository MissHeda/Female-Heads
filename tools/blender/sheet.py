"""Contact sheet of the new characters: the reshaped Timberwolf head with each face texture (tools/out/chars.npz,
tools/out/mhfh_<id>_co.png) -> docs/preview.jpg parts in tools/out/sheet_<id>.png. Globals: TAC (bool)."""
import bpy, os, sys, numpy as np
REPO = r"C:\Users\Heda\GitHub Repos\Female-Heads"
O = os.path.join(REPO, "tools", "out")
sys.path.insert(0, os.path.join(REPO, "tools", "blender"))
import importlib, render; importlib.reload(render)
d = np.load(os.path.join(O, "chars.npz")); F = d["F"]; uv = d["uv"]; ids = [str(i) for i in d["ids"]]
sc = bpy.data.scenes.get("FemaleHead") or bpy.data.scenes.new("FemaleHead")
bpy.context.window.scene = sc
for o in list(sc.objects):
    if o.name.startswith("FH_char"): bpy.data.objects.remove(o)
for o in sc.objects:
    if o.type == "MESH": o.hide_render = True
mat = bpy.data.materials.get("FH_char") or bpy.data.materials.new("FH_char"); mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); tx = nt.nodes.new("ShaderNodeTexImage")
nt.links.new(bs.outputs[0], out.inputs[0]); nt.links.new(tx.outputs[0], bs.inputs["Base Color"]); bs.inputs["Roughness"].default_value = 0.62
sc.render.engine = "BLENDER_EEVEE"
tac = globals().get("TAC", False)
for cid in ids:
    P = d[cid]
    me = bpy.data.meshes.new("FH_char")
    me.from_pydata([(p[0], p[2], p[1]) for p in P], [], [tuple(int(i) for i in f[::-1]) for f in F]); me.update()
    l = me.uv_layers.new(name="uv")
    for p in me.polygons:
        p.use_smooth = True
        for li in p.loop_indices:
            u, v = uv[me.loops[li].vertex_index]; l.data[li].uv = (u, 1 - v)
    ob = bpy.data.objects.new("FH_char", me); sc.collection.objects.link(ob); me.materials.append(mat)
    path = os.path.join(O, f"mhfh_{cid}{'_tac' if tac else ''}_co.png")
    for i in list(bpy.data.images):
        if i.filepath == path: bpy.data.images.remove(i)
    tx.image = bpy.data.images.load(path)
    render.render(None, (0, -0.02, 0.675), dist=0.62, views=((0, 0), (40, 5), (95, 0)), out=os.path.join(O, f"sheet_{cid}.png"), res=512)
    bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
result = {"ids": ids}
