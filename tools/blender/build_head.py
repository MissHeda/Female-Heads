"""Step 2 (Blender): build FH_head from the base human, already fitted to the Arma head space.

Fitted space = Arma model space with Blender axes (x, depth y, height z): eye centres on the vanilla eye
pivots, skull inside the vanilla skull (helmets), cut at the neck base. Parts: skin (decimated, face kept
denser), eyes, tongue, simple teeth arches, bun. UV layers: "src" (source texture UV per part) and "atlas".
Also builds FH_high (subdivided skin) as the source of the normal bake.
Run: node ~/.claude/blender-bridge/run.js tools/blender/build_head.py
"""
import bpy, bmesh, math, json, os, sys
import numpy as np
from mathutils import Vector

REPO = r"C:\Users\Heda\GitHub Repos\Female-Heads"
sys.path.insert(0, os.path.join(REPO, "tools"))
import importlib, hairline, raycast; importlib.reload(hairline); importlib.reload(raycast)

sc = bpy.data.scenes["FemaleHead"]
base = bpy.data.objects["FH_basemesh"]
EYE_X, EYE_Y, EYE_Z = 0.0325, -0.0873, 0.705      # vanilla eye bone pivots (y = depth, z = height)
CUT_Z, CUT_X = 0.476, 0.088
HAIR_T = 0.003                                    # hair thickness on the scalp
SKIN_TRIS = 13000
TEETH_TRIS = 1500
PARTS = {"skin": 0, "cavity": 1, "eye": 2, "tongue": 3, "teeth": 4, "bun": 5}

for n in ("FH_head", "FH_high"):
    if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n])


def group_points(ob, name):
    i = ob.vertex_groups[name].index
    return [ob.matrix_world @ v.co for v in ob.data.vertices if any(g.group == i for g in v.groups)]


# eye centre = centre of the left eyeball (it has to sit on the eye pivot, the eyeball rotates around it)
_eo = next(o for o in sc.objects if o.name.startswith("FH_basemesh.") and "low-poly" in o.name)
_ep = [_eo.matrix_world @ v.co for v in _eo.data.vertices if (_eo.matrix_world @ v.co).x > 0]
eye = Vector(((min(p[k] for p in _ep) + max(p[k] for p in _ep)) / 2 for k in range(3)))
head_i = base.vertex_groups["head"].index; body_i = base.vertex_groups["body"].index
head_pts = [base.matrix_world @ v.co for v in base.data.vertices
            if any(g.group == body_i for g in v.groups) and any(g.group == head_i and g.weight > 0.5 for g in v.groups)]
top = max(p.z for p in head_pts)
back = max(p.y for p in head_pts if abs(p.z - eye.z) < 0.05)
SX = EYE_X / eye.x
H0 = 0.035                                           # above this height over the eyes the cranium is squashed
K = (hairline.TOP_Z - EYE_Z - H0) / (top - eye.z - H0)
SD = min(1.0, (0.0765 - EYE_Y) / (back - eye.y))    # back of the skull inside the vanilla skull
FIT = {"sx": SX, "k": K, "sd": SD, "eye": list(eye), "top": top}
print("fit", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in FIT.items()})


def fit(co):
    """base human (world) -> fitted head space"""
    h = co.z - eye.z
    if h > H0: h = H0 + (h - H0) * K
    x, y, z = co.x * SX, EYE_Y + (co.y - eye.y) * SD, EYE_Z + h
    # the female neck is ~7 mm thinner than the vanilla one: widen it where uniform collars sit
    t = lambda e0, e1, v: max(0.0, min(1.0, (v - e0) / (e1 - e0)))
    w = t(0.625, 0.575, z) * t(-0.060, -0.040, y)
    f = 1.0 + 0.13 * w * w * (3 - 2 * w)
    return Vector((x * f, 0.008 + (y - 0.008) * f, z))


def new_obj(name, me):
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); return ob


def copy_fitted(src, name):
    me = src.data.copy(); ob = new_obj(name, me)
    for g in src.vertex_groups: ob.vertex_groups.new(name=g.name)
    M = src.matrix_world
    for v in me.vertices: v.co = fit(M @ v.co)
    return ob


def apply_mod(ob, mod):
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def mark(ob, name, idx=None, w=1.0):
    g = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
    g.add(list(range(len(ob.data.vertices))) if idx is None else idx, w, "REPLACE")


def cut_skin(ob):
    me = ob.data; b = bmesh.new(); b.from_mesh(me); dl = b.verts.layers.deform.active
    bi = ob.vertex_groups["body"].index
    bmesh.ops.delete(b, geom=[v for v in b.verts if bi not in v[dl]], context="VERTS")
    # bottom: level at the front, rising towards the back of the neck like the vanilla head
    for co, no in (((0, 0, CUT_Z), (0, 0, -1)), ((0, -0.035, CUT_Z), (0, 0.70, -1)), ((CUT_X, 0, 0), (1, 0, 0)), ((-CUT_X, 0, 0), (-1, 0, 0))):
        g = b.verts[:] + b.edges[:] + b.faces[:]
        bmesh.ops.bisect_plane(b, geom=g, plane_co=co, plane_no=no, clear_outer=True)
    # keep the head component (drops arm/chest leftovers)
    seen = set(); comps = []
    for v in b.verts:
        if v in seen: continue
        st = [v]; seen.add(v); c = []
        while st:
            a = st.pop(); c.append(a)
            for e in a.link_edges:
                o = e.other_vert(a)
                if o not in seen: seen.add(o); st.append(o)
        comps.append(c)
    comps.sort(key=len)
    bmesh.ops.delete(b, geom=[v for c in comps[:-1] for v in c], context="VERTS")
    b.to_mesh(me); b.free()


def hair_volume(ob, only=None):
    """push the hair-covered scalp out by the hair thickness"""
    me = ob.data
    P = np.array([list(v.co) for v in me.vertices]); N = np.array([list(v.normal) for v in me.vertices])
    m = hairline.hair_mask(P, soft=0.010)
    ear = np.zeros(len(P)); gi = ob.vertex_groups["ears"].index if "ears" in ob.vertex_groups else -1
    inside = np.zeros(len(P))
    for v in me.vertices:
        for g in v.groups:
            if g.group == gi: ear[v.index] = g.weight
    m *= (1 - np.clip(ear * 3, 0, 1))
    if only is not None: m *= only
    for v in me.vertices:
        v.co = Vector(P[v.index] + N[v.index] * HAIR_T * m[v.index])
    return m


_vp = os.path.join(REPO, "tools", "ref", "models", "Heads_m_white_01.npz")
VAN = (np.load(_vp)["P"], np.load(_vp)["F"]) if os.path.exists(_vp) else None


def clamp_to_vanilla(ob, eye_r, margin_hair=0.0010, margin_skin=0.0003):
    """Pull everything above the neck inside the vanilla head (helmets, glasses and masks are built around it).

    Along the ray from the head centre a point may not lie beyond the outermost vanilla surface. The pull-in is
    spread over the neighbours so the surface stays smooth. Afterwards the lids are kept clear of the eyeballs,
    which sit on the vanilla eye pivots."""
    if VAN is None:
        print("no vanilla reference (tools/ref_dump.py): head NOT clamped"); return
    me = ob.data
    P = np.array([list(v.co) for v in me.vertices])                       # (x, depth, height)
    A = np.stack([P[:, 0], P[:, 2], P[:, 1]], -1)                         # arma (x, height, depth)
    ci = ob.vertex_groups["FH_p_cavity"].index
    outer = np.array([not any(g.group == ci and g.weight > 0.5 for g in v.groups) for v in me.vertices])
    sel = A[:, 1] > 0.585
    dirs, r = raycast.radial(A[sel]); _, far = raycast.hits(dirs, *VAN)
    hm = hairline.hair_mask(P[sel], soft=0.010)
    margin = margin_skin + (margin_hair - margin_skin) * hm
    ex = np.maximum(np.where(np.isnan(far), 0.0, r - (far - margin)), 0.0)
    # The lids must keep lying on the eyeballs (which sit on the vanilla eye pivots): leave the eye region as it
    # is and blend the pull-in over a wide ring around it, so no crease forms.
    de = np.linalg.norm(np.stack([np.abs(P[:, 0]) - EYE_X, P[:, 1] - EYE_Y, P[:, 2] - EYE_Z], -1), axis=1)
    keep = hairline.smooth(0.017, 0.036, de)
    full = np.zeros(len(P)); full[sel] = ex; full *= keep
    edges = np.array([e.vertices[:] for e in me.edges])
    s_ = full.copy(); cnt = np.zeros(len(P)); np.add.at(cnt, edges[:, 0], 1); np.add.at(cnt, edges[:, 1], 1)
    for _ in range(12):
        acc = np.zeros(len(P)); np.add.at(acc, edges[:, 0], s_[edges[:, 1]]); np.add.at(acc, edges[:, 1], s_[edges[:, 0]])
        s_ = np.maximum(full, 0.5 * s_ + 0.5 * acc / np.maximum(cnt, 1)) * keep
    C = np.array([raycast.CENTRE[0], raycast.CENTRE[2], raycast.CENTRE[1]])
    d = P - C; rr = np.linalg.norm(d, axis=1)
    Q = C + d * ((rr - s_) / rr)[:, None]
    for v in me.vertices: v.co = Vector(Q[v.index])
    print(f"clamped to the vanilla head: {int((full > 0.0002).sum())} of {len(P)} points pulled in, deepest {full.max() * 1000:.1f} mm")


# ---------------------------------------------------------------- skin
skin = copy_fitted(base, "FH_head"); cut_skin(skin)
skin.modifiers.clear(); skin.parent = None
me = skin.data
# source UV layer
src = me.uv_layers[0]; src.name = "src"
# mouth cavity = the UV island(s) whose centre lies inside the head behind the lips
b = bmesh.new(); b.from_mesh(me); uvl = b.loops.layers.uv.active
par = list(range(len(b.faces)))
def find(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
for e in b.edges:
    if len(e.link_faces) != 2: continue
    fa, fb = e.link_faces
    ok = True
    for v in e.verts:
        ua = next(l[uvl].uv for l in fa.loops if l.vert == v); ub = next(l[uvl].uv for l in fb.loops if l.vert == v)
        if (ua - ub).length > 1e-5: ok = False
    if ok: par[find(fa.index)] = find(fb.index)
isl = {}
for f in b.faces: isl.setdefault(find(f.index), []).append(f)
cav = set()
for fs in isl.values():
    vs = {v for f in fs for v in f.verts}
    c = sum((v.co for v in vs), Vector()) / len(vs)
    r = max((v.co - c).length for v in vs)
    mouth = abs(c.x) < 0.012 and EYE_Y + 0.004 < c.y < EYE_Y + 0.085 and EYE_Z - 0.10 < c.z < EYE_Z - 0.035 and r < 0.075
    socket = (Vector((abs(c.x), c.y, c.z)) - Vector((EYE_X, EYE_Y, EYE_Z))).length < 0.012 and r < 0.03
    if mouth or socket:
        cav |= {v.index for v in vs}
b.free()
print("cavity verts", len(cav), "islands", len(isl))
mark(skin, "FH_p_cavity", sorted(cav))

# one smooth subdivision is the common base of the model and of the normal-bake source
sub = skin.modifiers.new("sub", "SUBSURF"); sub.levels = 1; apply_mod(skin, sub)
me = skin.data
hair_volume(skin)
_eo2 = [fit(_eo.matrix_world @ v.co) for v in _eo.data.vertices if (_eo.matrix_world @ v.co).x > 0]
EYE_R0 = (max(p.z for p in _eo2) - min(p.z for p in _eo2)) / 2
clamp_to_vanilla(skin, EYE_R0)
high = new_obj("FH_high", me.copy())
for g in skin.vertex_groups: high.vertex_groups.new(name=g.name)
sub = high.modifiers.new("sub", "SUBSURF"); sub.levels = 1; apply_mod(high, sub)
for p in high.data.polygons: p.use_smooth = True

# decimate: keep the face dense, thin out scalp, neck and cavity
P = np.array([list(v.co) for v in me.vertices])
facey = hairline.smooth(-0.045, -0.075, P[:, 1]) * hairline.smooth(EYE_Z - 0.125, EYE_Z - 0.10, P[:, 2]) * hairline.smooth(EYE_Z + 0.065, EYE_Z + 0.045, P[:, 2])
ears_i = skin.vertex_groups["ears"].index; cav_i = skin.vertex_groups["FH_p_cavity"].index
dg = skin.vertex_groups.new(name="FH_dec")
for v in me.vertices:
    w = 0.8 - 0.3 * float(facey[v.index])
    if any(g.group == ears_i and g.weight > 0.3 for g in v.groups): w = min(w, 0.55)
    if any(g.group == cav_i and g.weight > 0.5 for g in v.groups): w = 1.0
    dg.add([v.index], w, "REPLACE")
tris0 = sum(len(p.vertices) - 2 for p in me.polygons)
d = skin.modifiers.new("dec", "DECIMATE"); d.ratio = SKIN_TRIS / tris0; d.use_symmetry = True; d.symmetry_axis = "X"
d.vertex_group = "FH_dec"; d.vertex_group_factor = 1.0
apply_mod(skin, d)
# marker groups were interpolated by the subdivision: make them crisp again
g_ = skin.vertex_groups["FH_p_cavity"]
for v in skin.data.vertices:
    w = max([x.weight for x in v.groups if x.group == cav_i] or [0.0])
    if w > 0.5: g_.add([v.index], 1.0, "REPLACE")
    elif w > 0: g_.remove([v.index])
mark(skin, "FH_p_skin")
print("skin tris", tris0, "->", sum(len(p.vertices) - 2 for p in skin.data.polygons))

parts = [skin]

# ---------------------------------------------------------------- eyes, tongue
def asset(sub):
    return next(o for o in sc.objects if o.name.startswith("FH_basemesh.") and sub in o.name)

eyes = copy_fitted(asset("low-poly"), "FH_tmp_eyes"); eyes.modifiers.clear(); eyes.parent = None
for v in eyes.data.vertices:
    mark(eyes, "eye.L" if v.co.x > 0 else "eye.R", [v.index])
# centre every eyeball on its pivot (it rotates around it)
for sgn in (1, -1):
    idx = [v.index for v in eyes.data.vertices if v.co.x * sgn > 0]
    c = sum((eyes.data.vertices[i].co for i in idx), Vector()) / len(idx)
    bb = [min(eyes.data.vertices[i].co[k] for i in idx) for k in range(3)], [max(eyes.data.vertices[i].co[k] for i in idx) for k in range(3)]
    c = Vector(((bb[0][k] + bb[1][k]) / 2 for k in range(3)))
    off = Vector((EYE_X * sgn, EYE_Y, EYE_Z)) - c
    for i in idx: eyes.data.vertices[i].co += off
    EYE_MEAN = sum((eyes.data.vertices[i].co - Vector((EYE_X * sgn, EYE_Y, EYE_Z))).length for i in idx) / len(idx)
EYE_R = EYE_R0                                        # eyeball radius (half its height), the lids lie on it
sub = eyes.modifiers.new("sub", "SUBSURF"); sub.levels = 1; apply_mod(eyes, sub)
for sgn in (1, -1):                                   # subdivision shrinks a coarse ball: restore its mean radius
    c = Vector((EYE_X * sgn, EYE_Y, EYE_Z))
    vs = [v for v in eyes.data.vertices if v.co.x * sgn > 0]
    mean = sum((v.co - c).length for v in vs) / len(vs)
    for v in vs: v.co = c + (v.co - c) * (EYE_MEAN / mean)
for p in eyes.data.polygons: p.use_smooth = True
eyes.data.uv_layers[0].name = "src"; mark(eyes, "FH_p_eye"); parts.append(eyes)

tongue = copy_fitted(asset("tongue"), "FH_tmp_tongue"); tongue.modifiers.clear(); tongue.parent = None
tongue.data.uv_layers[0].name = "src"; mark(tongue, "FH_p_tongue"); parts.append(tongue)

# ---------------------------------------------------------------- teeth: the MakeHuman teeth, thinned out
tb = asset("teeth"); M = tb.matrix_world
ji = tb.vertex_groups["jaw"].index
TP = np.array([list(fit(M @ v.co)) for v in tb.data.vertices])
low = np.array([any(g.group == ji and g.weight > 0.5 for g in v.groups) for v in tb.data.vertices])
zmid = (TP[low][:, 2].max() + TP[~low][:, 2].min()) / 2          # where the teeth meet = the mouth line
teeth = copy_fitted(tb, "FH_tmp_teeth"); teeth.modifiers.clear(); teeth.parent = None
d = teeth.modifiers.new("dec", "DECIMATE"); d.ratio = TEETH_TRIS / sum(len(p.vertices) - 2 for p in teeth.data.polygons); apply_mod(teeth, d)
for p in teeth.data.polygons: p.use_smooth = True
teeth.data.uv_layers[0].name = "src"; mark(teeth, "FH_p_teeth"); parts.append(teeth)

# ---------------------------------------------------------------- bun
SP = np.array([list(v.co) for v in skin.data.vertices])
# Low bun at the nape: the vanilla helmets end at height 0.64-0.66 at the back, the bun stays below that.
bz = EYE_Z - 0.094
m = (np.abs(SP[:, 2] - bz) < 0.010) & (np.abs(SP[:, 0]) < 0.02)
backy = SP[m, 1].max()
RX, RY, RZ = 0.031, 0.018, 0.0215
bb = bmesh.new(); buv = bb.loops.layers.uv.new("src")
bmesh.ops.create_uvsphere(bb, u_segments=32, v_segments=16, radius=1.0)
for v in bb.verts:
    x, y, z = v.co                                   # unit sphere, pole along z
    px, py, pz = x, z, y                             # pole along depth (y)
    rad = math.hypot(px, pz); ang = math.atan2(pz, px)
    groove = 0.055 * math.sin(2 * ang + 9.0 * rad) * min(1.0, rad * 2.5) * (1 if py > -0.2 else 0.3)
    dent = -0.10 * math.exp(-(rad / 0.22) ** 2) if py > 0 else 0.0   # the centre of the coil
    s = 1.0 + groove + dent
    v.co = Vector((px * RX * s, py * RY * (1.0 if py > 0 else 0.7) * s, pz * RZ * s))
for f in bb.faces:
    f.smooth = True
    for l in f.loops:
        c = l.vert.co
        l[buv].uv = (0.5 + 0.48 * c.x / RX / 1.06, 0.5 + 0.48 * c.z / RZ / 1.06)
bmesh.ops.recalc_face_normals(bb, faces=bb.faces[:])
bme = bpy.data.meshes.new("FH_bun"); bb.to_mesh(bme); bb.free()
bun = new_obj("FH_tmp_bun", bme)
for v in bme.vertices: v.co += Vector((0, backy + RY * 0.33, bz))
mark(bun, "head"); mark(bun, "FH_p_bun"); parts.append(bun)
BUN = [0.0, backy + RY * 0.33, bz]

# ---------------------------------------------------------------- join + atlas
for o in sc.objects: o.select_set(False)
for p in parts: p.select_set(True)
bpy.context.view_layer.objects.active = skin
with bpy.context.temp_override(active_object=skin, object=skin, selected_editable_objects=parts, selected_objects=parts):
    bpy.ops.object.join()
head = skin; me = head.data
for p in me.polygons: p.use_smooth = True
print("uv layers", [u.name for u in me.uv_layers])
at = me.uv_layers.new(name="atlas")
srcl = me.uv_layers["src"]
for i, l in enumerate(srcl.data): at.data[i].uv = l.uv

def part_of_vert():
    out = {}
    gid = {head.vertex_groups["FH_p_" + n].index: n for n in PARTS if ("FH_p_" + n) in head.vertex_groups}
    for v in me.vertices:
        ps = [gid[g.group] for g in v.groups if g.group in gid and g.weight > 0.5]
        out[v.index] = "cavity" if "cavity" in ps else (ps[0] if ps else "skin")
    return out
pv = part_of_vert()
# part id as a face-corner colour attribute (read by the bake)
col = me.color_attributes.new("fh_part", "FLOAT_COLOR", "CORNER")
earl = me.color_attributes.new("fh_ear", "FLOAT_COLOR", "CORNER")
ears_i = head.vertex_groups["ears"].index
earw = {v.index: max([g.weight for g in v.groups if g.group == ears_i] or [0.0]) for v in me.vertices}
fpart = []
for p in me.polygons:
    ps = [pv[v] for v in p.vertices]
    part = "cavity" if all(x == "cavity" for x in ps) else next((x for x in ps if x != "cavity"), "skin")
    fpart.append(part)
    for li in p.loop_indices:
        col.data[li].color = (PARTS[part] / 10.0, 0, 0, 1)
        e = earw[me.loops[li].vertex_index]
        earl.data[li].color = (e, e, e, 1)

# scale the atlas islands per part, then pack without rotation
b = bmesh.new(); b.from_mesh(me); uvl = b.loops.layers.uv["atlas"]; b.faces.ensure_lookup_table()
par = list(range(len(b.faces)))
for e in b.edges:
    if len(e.link_faces) != 2: continue
    fa, fb = e.link_faces
    if all((next(l[uvl].uv for l in fa.loops if l.vert == v) - next(l[uvl].uv for l in fb.loops if l.vert == v)).length < 1e-5 for v in e.verts):
        par[find(fa.index)] = find(fb.index)
isl = {}
for f in b.faces: isl.setdefault(find(f.index), []).append(f)
def area3(fs): return sum(f.calc_area() for f in fs)
def areauv(fs):
    a = 0.0
    for f in fs:
        u = [l[uvl].uv for l in f.loops]
        for i in range(1, len(u) - 1): a += abs((u[i] - u[0]).cross(u[i + 1] - u[0])) / 2
    return a
SCALE = {"skin": 1.0, "cavity": 0.32, "eye": 1.9, "tongue": 0.5, "teeth": 0.5, "bun": 0.95}
for fs in isl.values():
    part = fpart[fs[0].index]
    a3, au = area3(fs), areauv(fs)
    if au < 1e-12: continue
    s = math.sqrt(a3 / au) * SCALE[part]              # uniform texel density, then the part factor
    # hair-only skin islands (back of the head) need less
    if part == "skin":
        c = sum((v.co for f in fs for v in f.verts), Vector()) / sum(len(f.verts) for f in fs)
        if c.z < 0.585: s *= 0.62                      # neck and chest: mostly under the collar
        elif hairline.hair_mask(np.array([list(c)]))[0] > 0.9 and len(fs) < 0.2 * len(b.faces): s *= 0.7
    cu = sum((l[uvl].uv for f in fs for l in f.loops), Vector((0, 0))) / sum(len(f.loops) for f in fs)
    for f in fs:
        for l in f.loops: l[uvl].uv = cu + (l[uvl].uv - cu) * s
b.to_mesh(me); b.free()
me.uv_layers.active = me.uv_layers["atlas"]
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == "VIEW_3D"); region = next(r for r in area.regions if r.type == "WINDOW")
for o in sc.objects: o.select_set(False)
head.select_set(True); bpy.context.view_layer.objects.active = head
with bpy.context.temp_override(window=win, area=area, region=region, screen=win.screen, active_object=head, object=head):
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=False, margin=0.006)
    bpy.ops.object.mode_set(mode="OBJECT")
me.uv_layers.active = me.uv_layers["atlas"]

L = {"eye_l": [EYE_X, EYE_Y, EYE_Z], "eye_r": float(EYE_R), "mouth_z": float(zmid), "bun": BUN, "bun_r": [RX, RY, RZ], "fit": FIT, "parts": PARTS,
     "hair_t": HAIR_T}
os.makedirs(os.path.join(REPO, "tools", "bake"), exist_ok=True)
json.dump(L, open(os.path.join(REPO, "tools", "bake", "landmarks.json"), "w"), indent=1)
P = np.array([list(v.co) for v in me.vertices])
print("FH_head verts", len(me.vertices), "tris", sum(len(p.vertices) - 2 for p in me.polygons),
      "bounds", P.min(0).round(4), P.max(0).round(4))
base.hide_render = True; base.hide_set(True); high.hide_render = True; high.hide_set(True)
for o in sc.objects:
    if o.name.startswith("FH_basemesh."): o.hide_render = True; o.hide_set(True)
result = {"ok": True}
