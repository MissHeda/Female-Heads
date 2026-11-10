"""Contact sheet of FH_head with the current material (tools/out/view.png). Globals: VIEWS, DIST, CENTER, OUT, RES."""
import bpy, sys, os
sys.path.insert(0, r"C:\Users\Heda\GitHub Repos\Female-Heads\tools\blender")
import importlib, render; importlib.reload(render)
sc = bpy.data.scenes["FemaleHead"]
for o in sc.objects:
    if o.type == "MESH": o.hide_render = (o.name != globals().get("OBJ", "FH_head"))
render.render(None, globals().get("CENTER", (0, -0.02, 0.665)), dist=globals().get("DIST", 0.9),
              views=globals().get("VIEWS", ((0, 0), (40, 8), (90, 0), (165, 10))),
              out=globals().get("OUT", r"C:\Users\Heda\GitHub Repos\Female-Heads\tools\out\view.png"), res=globals().get("RES", 640))
result = {}
