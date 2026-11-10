"""Step 1 (Blender + MPFB): create the female base human in its own scene "FemaleHead".

Macro shape + face detail targets -> eyes -> bake targets -> MakeHuman default rig (face bone weights)
-> teeth (only measured for the arch) and tongue.
Run: node ~/.claude/blender-bridge/run.js tools/blender/base.py
"""
import bpy, os
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.locationservice import LocationService

MACRO = {"gender": 0.0, "age": 0.52, "muscle": 0.55, "weight": 0.45, "proportions": 0.9, "height": 0.5,
         "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.15, "caucasian": 0.7, "african": 0.15}}
# face detail targets (MakeHuman modifiers), "l-"/"r-" pairs are written once with a leading "*"
DETAILS = {
    "eyes/*-eye-trans-out": 0.6,          # eye centres towards the vanilla eye pivots (65 mm apart)
    "eyes/*-eye-scale-incr": 0.0,
    "eyes/*-eye-corner2-up": 0.25,
    "eyes/*-eye-height2-decr": 0.3,       # lids a little lower: relaxed instead of staring
    "mouth/mouth-upperlip-volume-incr": 0.45,
    "mouth/mouth-lowerlip-volume-incr": 0.55,
    "mouth/mouth-scale-horiz-incr": 0.25,
    "mouth/mouth-trans-down": 0.1,       # towards the vanilla lip bones
    "mouth/mouth-cupidsbow-incr": 0.3,
    "nose/nose-scale-horiz-decr": 0.2,
    "nose/nose-scale-depth-decr": 0.15,
    "nose/nose-point-up": 0.2,
    "nose/nose-hump-decr": 0.2,
    "cheek/*-cheek-bones-incr": 0.2,
    "cheek/*-cheek-volume-decr": 0.15,
    "chin/chin-width-decr": 0.25,
    "chin/chin-height-incr": 0.2,
    "head/head-oval": 0.4,
    "head/head-scale-horiz-incr": 0.0,
}

sc = bpy.data.scenes.get("FemaleHead") or bpy.data.scenes.new("FemaleHead")
bpy.context.window.scene = sc
for o in list(sc.objects):
    bpy.data.objects.remove(o)

bm = HumanService.create_human(macro_detail_dict=MACRO, feet_on_ground=True)
bm.name = "FH_basemesh"
tdir = os.path.join(os.path.dirname(TargetService.target_full_path("mouth-trans-down") or ""), "..")
for key, w in DETAILS.items():
    grp, name = key.split("/")
    for n in ([name.replace("*", "l"), name.replace("*", "r")] if "*" in name else [name]):
        path = TargetService.target_full_path(n)
        if not path:
            print("MISSING target", n); continue
        TargetService.load_target(bm, path, weight=w, name=n)

d = LocationService.get_user_data()
HumanService.add_mhclo_asset(os.path.join(d, "eyes", "low-poly", "low-poly.mhclo"), bm, asset_type="Eyes", subdiv_levels=0)
HumanService.set_character_skin(os.path.join(d, "skins", "young_caucasian_female", "young_caucasian_female.mhmat"), bm)
if bm.data.shape_keys:
    TargetService.bake_targets(bm)
HumanService.add_builtin_rig(bm, "default", import_weights=True)
for t in ("teeth", "tongue"):
    a = sorted(os.listdir(os.path.join(d, t)))[0]
    HumanService.add_mhclo_asset(os.path.join(d, t, a, a + ".mhclo"), bm, asset_type=t.capitalize(), subdiv_levels=0)
print([(o.name, o.type, len(o.data.vertices) if o.type == "MESH" else 0) for o in sc.objects])
result = {"ok": True}
