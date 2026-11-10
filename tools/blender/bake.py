"""Step 3 (Blender): bake the data passes of FH_head into tools/bake/*.npy (atlas UV, 2048).

pos / nrm: object-space position and normal per texel; src: source UV (r,g) + part id (b*10);
ear: ear weight; normal: tangent-space normals from FH_high (subdivided skin); ao: ambient occlusion.
Run: node ~/.claude/blender-bridge/run.js tools/blender/bake.py      (globals PASSES to limit)
"""
import bpy, os, numpy as np
OUT = r"C:\Users\Heda\GitHub Repos\Female-Heads\tools\bake"; os.makedirs(OUT, exist_ok=True)
R = 2048
PASSES = globals().get("PASSES", {"pos", "src", "normal", "ao"})
sc = bpy.data.scenes["FemaleHead"]; sc.render.engine = "CYCLES"; sc.cycles.device = "GPU"; sc.cycles.samples = 8
head = bpy.data.objects["FH_head"]; high = bpy.data.objects["FH_high"]; me = head.data

def img(name, fill):
    if name in bpy.data.images: bpy.data.images.remove(bpy.data.images[name])
    i = bpy.data.images.new(name, R, R, alpha=True, float_buffer=True); i.generated_color = fill
    i.colorspace_settings.name = "Non-Color"; return i

mat = bpy.data.materials.get("FH_bake") or bpy.data.materials.new("FH_bake")
mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
outn = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission"); tex = nt.nodes.new("ShaderNodeTexImage")
bsdf = nt.nodes.new("ShaderNodeBsdfDiffuse")
geo = nt.nodes.new("ShaderNodeNewGeometry"); uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "src"
part = nt.nodes.new("ShaderNodeAttribute"); part.attribute_name = "fh_part"
ear = nt.nodes.new("ShaderNodeAttribute"); ear.attribute_name = "fh_ear"
sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sepc = nt.nodes.new("ShaderNodeSeparateColor"); comb = nt.nodes.new("ShaderNodeCombineColor")
nt.links.new(uvn.outputs[0], sep.inputs[0]); nt.links.new(part.outputs["Color"], sepc.inputs[0])
nt.links.new(sep.outputs[0], comb.inputs[0]); nt.links.new(sep.outputs[1], comb.inputs[1]); nt.links.new(sepc.outputs[0], comb.inputs[2])
nt.nodes.active = tex
me.materials.clear(); me.materials.append(mat)
for p in me.polygons: p.material_index = 0
me.uv_layers.active = me.uv_layers["atlas"]
for l in me.uv_layers: l.active_render = (l.name == "atlas")

def select(objs):
    for o in sc.objects: o.select_set(False)
    for o in sc.objects:
        if o.type == "MESH": o.hide_render = o not in objs + [head]
    for o in objs + [head]: o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = head

def bake(name, type_, sel=(), surface="emit", **kw):
    i = img("FH_" + name, kw.pop("fill", (0, 0, 0, 0))); tex.image = i
    nt.links.new((em if surface == "emit" else bsdf).outputs[0], outn.inputs[0])
    select(list(sel))
    bpy.ops.object.bake(type=type_, use_selected_to_active=bool(sel), cage_extrusion=0.003 if sel else 0,
                        max_ray_distance=0.008 if sel else 0, margin=12, use_clear=True, target="IMAGE_TEXTURES", **kw)
    a = np.array(i.pixels[:], dtype=np.float32).reshape(R, R, 4)
    np.save(os.path.join(OUT, name + ".npy"), a[..., :3].astype(np.float32)); bpy.data.images.remove(i)
    return a

done = []
if "pos" in PASSES:
    nt.links.new(geo.outputs["Position"], em.inputs[0]); bake("pos", "EMIT")
    nt.links.new(geo.outputs["Normal"], em.inputs[0]); bake("nrm", "EMIT"); done += ["pos", "nrm"]
if "src" in PASSES:
    nt.links.new(comb.outputs[0], em.inputs[0]); bake("src", "EMIT", fill=(0, 0, 0.9, 0))
    nt.links.new(ear.outputs["Color"], em.inputs[0]); bake("ear", "EMIT"); done += ["src", "ear"]
if "normal" in PASSES:
    bake("normal", "NORMAL", sel=[high], surface="bsdf", fill=(0.5, 0.5, 1, 1)); done.append("normal")
if "ao" in PASSES:
    sc.cycles.samples = 96
    bake("ao", "AO", surface="bsdf", fill=(1, 1, 1, 1)); done.append("ao"); sc.cycles.samples = 8
high.hide_render = True; high.hide_set(True)
result = {"done": done}
