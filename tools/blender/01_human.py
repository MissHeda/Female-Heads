import bpy, os
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.locationservice import LocationService
# own scene so Mia's scene stays untouched
sc = bpy.data.scenes.get("FemaleHead") or bpy.data.scenes.new("FemaleHead")
bpy.context.window.scene = sc
for o in list(sc.objects): bpy.data.objects.remove(o)
macro = {"gender":0.0,"age":0.52,"muscle":0.55,"weight":0.45,"proportions":0.85,"height":0.5,
         "cupsize":0.5,"firmness":0.5,"race":{"asian":0.15,"caucasian":0.7,"african":0.15}}
bm = HumanService.create_human(macro_detail_dict=macro, feet_on_ground=True)
bm.name = "FH_basemesh"
d = LocationService.get_user_data()
HumanService.add_mhclo_asset(os.path.join(d,"eyes","low-poly","low-poly.mhclo"), bm, asset_type="Eyes", subdiv_levels=0)
for t,a in (("eyebrows","eyebrow001"),("eyelashes","eyelashes01")):
    HumanService.add_mhclo_asset(os.path.join(d,t,a,a+".mhclo"), bm, asset_type=t.capitalize(), subdiv_levels=0)
HumanService.set_character_skin(os.path.join(d,"skins","young_caucasian_female","young_caucasian_female.mhmat"), bm)
objs=[(o.name,o.type,len(o.data.vertices) if o.type=='MESH' else 0) for o in sc.objects]
print(objs, [g.name for g in bm.vertex_groups][:80])
result={'ok':True}
