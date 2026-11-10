"""Preview FH_head with the composed textures (tools/out) -> tools/out/preview_<tone>.png. Globals: TONE, VIEWS, DIST, CENTER, RES."""
import bpy, os, sys
TONE = globals().get("TONE", "light")
O = r"C:\Users\Heda\GitHub Repos\Female-Heads\tools\out"
h = bpy.data.objects[globals().get("OBJ", "FH_head")]
m = bpy.data.materials.get("FH_preview") or bpy.data.materials.new("FH_preview"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], o.inputs[0])
uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "atlas"
def im(name, nc=False):
    p = os.path.join(O, name)
    for i in list(bpy.data.images):
        if i.filepath == p: bpy.data.images.remove(i)
    i = bpy.data.images.load(p)
    if nc: i.colorspace_settings.name = "Non-Color"
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = i; nt.links.new(uv.outputs[0], t.inputs[0]); return t
c = im(f"fh_{TONE}_co.png"); nt.links.new(c.outputs[0], b.inputs["Base Color"])
n = im("fh_nohq.png", True); s = im("fh_smdi.png", True)
sep = nt.nodes.new("ShaderNodeSeparateColor"); comb = nt.nodes.new("ShaderNodeCombineColor"); inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1
nt.links.new(n.outputs[0], sep.inputs[0]); nt.links.new(sep.outputs[0], comb.inputs[0]); nt.links.new(sep.outputs[1], inv.inputs[1]); nt.links.new(inv.outputs[0], comb.inputs[1]); nt.links.new(sep.outputs[2], comb.inputs[2])
nm = nt.nodes.new("ShaderNodeNormalMap"); nm.uv_map = "atlas"; nt.links.new(comb.outputs[0], nm.inputs[1]); nt.links.new(nm.outputs[0], b.inputs["Normal"])
ss = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(s.outputs[0], ss.inputs[0])
rough = nt.nodes.new("ShaderNodeMath"); rough.operation = "SUBTRACT"; rough.inputs[0].default_value = 0.92; nt.links.new(ss.outputs[2], rough.inputs[1]); nt.links.new(rough.outputs[0], b.inputs["Roughness"])
h.data.materials.clear(); h.data.materials.append(m)
for p in h.data.polygons: p.material_index = 0
for l in h.data.uv_layers: l.active_render = (l.name == "atlas")
sys.path.insert(0, r"C:\Users\Heda\GitHub Repos\Female-Heads\tools\blender")
import importlib, render; importlib.reload(render)
sc = bpy.data.scenes["FemaleHead"]
for ob in sc.objects:
    if ob.type == "MESH": ob.hide_render = ob is not h
sc.render.engine = "BLENDER_EEVEE"
render.render(None, globals().get("CENTER", (0, -0.02, 0.672)), dist=globals().get("DIST", 0.82),
              views=globals().get("VIEWS", ((0, 0), (40, 8), (95, 0), (165, 12))), out=globals().get("OUT", os.path.join(O, f"preview_{TONE}.png")), res=globals().get("RES", 640))
result = {}
