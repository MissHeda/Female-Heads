import bpy, os
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.locationservice import LocationService
bm=bpy.data.objects['FH_basemesh']; d=LocationService.get_user_data()
have=[o.name for o in bpy.context.scene.objects]
for t in ('teeth','tongue'):
    a=sorted(os.listdir(os.path.join(d,t)))[0]
    if not any(t in n.lower() or a in n for n in have):
        HumanService.add_mhclo_asset(os.path.join(d,t,a,a+'.mhclo'), bm, asset_type=t.capitalize(), subdiv_levels=0)
for o in bpy.context.scene.objects:
    if o.type=='MESH': print(o.name, len(o.data.vertices), len(o.data.polygons), [g.name for g in o.vertex_groups][:6], [m.type for m in o.modifiers])
result={}
