"""New characters on the Task Force Timberwolf female head.

Every character is that head with a slightly different face shape and a face texture derived from one of the two
Timberwolf faces: other skin tone, hair, brow and eye colour, optional freckles, plus a "Tactical" variant with
their face paint. Reads the reference data written by tools/ref_tftw.py and writes
  addons/heads/data/mhfh_<id>[_tac]_co.paa, mhfh_<id>_hl_co.paa   textures (face, hands)
  addons/heads/models/mhfh_<id>.p3d                                the reshaped model (all LODs)
  addons/heads/config.cpp, model.cfg                               faces and heads
The mod needs the Timberwolf mod loaded: normal/ambient maps, hand material and base classes come from it.
usage (repo root): python -I tools/characters.py [--preview]
"""
import os, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mlod, tftw_masks, braid as braidlib
from tftw_masks import smooth, blur, N

ROOT = os.path.join(HERE, ".."); DATA = os.path.join(ROOT, "addons", "heads", "data"); MODELS = os.path.join(ROOT, "addons", "heads", "models")
OUT = os.path.join(HERE, "out"); REF = os.path.join(HERE, "ref")
TOPAA = r"D:\Steam\steamapps\common\Arma 3 Tools\ImageToPAA\ImageToPAA.exe"
SRC_P3D = os.path.join(REF, "tftw", "unbin", "A3_female_heads - UB", "Models", "female_head_bun.p3d")
PREFIX = "z\\mhfh\\addons\\heads\\"
TFTW = "\\A3_female_heads\\female_head_ICEMAN\\female_01\\"

# hair / eye colours (sRGB 0..1)
BLACK, DARKBROWN, CHESTNUT, AUBURN = (0.040, 0.036, 0.038), (0.105, 0.062, 0.042), (0.20, 0.105, 0.060), (0.27, 0.085, 0.045)
LIGHTBROWN, GINGER, BLONDE, PLATINUM = (0.34, 0.225, 0.14), (0.44, 0.215, 0.105), (0.62, 0.50, 0.33), (0.76, 0.67, 0.50)
E_BLUE, E_GREY, E_GREEN, E_HAZEL, E_BROWN, E_DARK = (0.30, 0.45, 0.62), (0.45, 0.50, 0.54), (0.33, 0.47, 0.30), (0.45, 0.36, 0.18), (0.30, 0.17, 0.08), (0.16, 0.09, 0.05)
# skin tones: mean cheek colour the face is brought to
S_PALE, S_FAIR, S_BASE, S_TAN, S_OLIVE, S_BROWN, S_DARK = (0.665, 0.505, 0.460), (0.625, 0.455, 0.405), (0.585, 0.420, 0.370), \
    (0.515, 0.350, 0.280), (0.490, 0.345, 0.265), (0.365, 0.235, 0.180), (0.300, 0.190, 0.142)

# shape: millimetres (jaw, chin, chin_fwd, nose_len, nose_up, cheek, lips, brow) and a relative nose width
CHARS = [
    dict(id="kovacs", name="Kovacs", base=1, hair=BLACK, skin=S_PALE, eyes=E_GREY, freckles=0.0,
         shape=dict(jaw=-1.8, chin=1.2, chin_fwd=0.6, nose_w=-0.07, nose_len=0.8, nose_up=0.4, cheek=1.2, lips=0.5, brow=0.0)),
    dict(id="reyes", name="Reyes", base=1, hair=DARKBROWN, skin=S_TAN, eyes=E_BROWN, freckles=0.0,
         shape=dict(jaw=1.2, chin=-0.8, chin_fwd=0.0, nose_w=0.06, nose_len=-0.4, nose_up=0.0, cheek=1.6, lips=1.2, brow=0.4)),
    dict(id="okoye", name="Okoye", base=1, hair=BLACK, skin=S_DARK, eyes=E_DARK, freckles=0.0,
         shape=dict(jaw=0.6, chin=0.4, chin_fwd=0.8, nose_w=0.12, nose_len=-1.0, nose_up=-0.2, cheek=1.0, lips=2.0, brow=0.6)),
    dict(id="walsh", name="Walsh", base=1, hair=AUBURN, skin=S_FAIR, eyes=E_GREEN, freckles=0.8,
         shape=dict(jaw=-0.8, chin=-1.0, chin_fwd=-0.4, nose_w=-0.04, nose_len=0.2, nose_up=0.8, cheek=0.2, lips=-0.3, brow=-0.3)),
    dict(id="lindqvist", name="Lindqvist", base=3, hair=PLATINUM, skin=S_PALE, eyes=E_BLUE, freckles=0.0,
         shape=dict(jaw=-1.4, chin=0.6, chin_fwd=0.2, nose_w=-0.08, nose_len=0.6, nose_up=0.6, cheek=1.4, lips=0.2, brow=0.0)),
    dict(id="fraser", name="Fraser", base=3, hair=GINGER, skin=S_FAIR, eyes=E_GREEN, freckles=1.0,
         shape=dict(jaw=0.8, chin=-0.6, chin_fwd=0.0, nose_w=0.02, nose_len=-0.2, nose_up=0.6, cheek=-0.4, lips=0.8, brow=-0.2)),
    dict(id="novak", name="Novak", base=3, hair=LIGHTBROWN, skin=S_BASE, eyes=E_HAZEL, freckles=0.0,
         shape=dict(jaw=1.6, chin=1.4, chin_fwd=0.6, nose_w=0.04, nose_len=0.4, nose_up=-0.4, cheek=0.6, lips=-0.2, brow=0.5)),
    dict(id="haddad", name="Haddad", base=3, hair=BLACK, skin=S_OLIVE, eyes=E_BROWN, freckles=0.0,
         shape=dict(jaw=-0.4, chin=0.2, chin_fwd=0.4, nose_w=0.0, nose_len=1.2, nose_up=-0.6, cheek=0.8, lips=1.0, brow=0.8)),
]


def lerp(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


def sine_noise(p, freq, seed, n=14, spread=(0.5, 2.0)):
    r = np.random.default_rng(seed); s = np.zeros(p.shape[:-1])
    for _ in range(n):
        d = r.normal(size=3); d /= np.linalg.norm(d)
        s += np.sin((p @ d) * freq * r.uniform(*spread) + r.uniform(0, 6.283))
    return s / n ** 0.5


# ------------------------------------------------------------------ textures
_M = {}


def masks(base):
    if base not in _M:
        m = tftw_masks.build(f"face_0{base}")
        m["tac"] = tftw_masks.load(f"face_0{base + 1}")
        _M[base] = m
    return _M[base]


def face_texture(ch, tactical=False, braid=False):
    m = masks(ch["base"]); tex = m["tex"]; lum = m["lum"]; pos = m["pos"]
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]; ax = np.abs(x)
    skin, hair = m["skin"], m["hair"]
    # --- skin: bring the cheek colour to the target, a little more contrast on dark skin so it keeps its shape
    cheek = (skin > 0.9) & (z < -0.085) & (y > 0.655) & (y < 0.69) & (ax > 0.022) & (ax < 0.05)
    mean = tex[cheek].mean(0); target = np.array(ch["skin"])
    dark = float(np.clip((0.585 - target[0]) / 0.34, 0, 1))
    g = 1.0 + 0.30 * dark
    sk = target * np.clip(tex / mean, 0, 3) ** g
    lipc = sk * np.array([1.0, 0.86, 0.88]) * (1 - 0.18 * dark)                 # lips stay a touch redder / darker
    sk = lerp(sk, lipc, m["lips"] * 0.6)
    if ch["freckles"]:
        fr = sine_noise(pos, 2300.0, 14, 16) * 0.6 + sine_noise(pos, 1100.0, 15, 10) * 0.4
        fmask = smooth(0.95, 1.5, fr) * np.exp(-((y - 0.683) / 0.030) ** 2) * smooth(0.075, 0.045, ax) * (z < -0.06) * skin
        sk = lerp(sk, sk * np.array([0.74, 0.58, 0.47]), fmask * 0.7 * ch["freckles"])
    out = lerp(tex, sk, skin)
    # --- hair: keep the photographed strands, change the colour
    # (the hair is the dark-haired face's for every character, see tftw_masks)
    hlum = m["hairlum"]
    ht = np.array(ch["hair"])
    light = float(np.clip((ht.max() - 0.25) / 0.45, 0, 1))                # light hair shows less contrast between strands
    # dark hair: only its highlights reach the target colour; light hair: its average does
    hl = hlum[hair > 0.9]; hmean = float(np.percentile(hl, 85 - 40 * light))
    def recolour(l):
        rel = np.clip(l / max(hmean, 1e-3), 0.15, 1.6 - 0.45 * light)
        return np.minimum(ht * (rel ** (0.80 - 0.30 * light))[..., None], 0.94)
    out = lerp(out, np.clip(recolour(hlum), 0, 1), hair)
    if braid:                                            # the braid photo goes where the bun's texture was
        for (x0, x1, y0, y1), row in zip(braidlib.ROWS, braidlib.braid_strip()):
            row = row / max(float(np.percentile(row, 85)), 1e-3) * hmean
            out[y0:y1, x0:x1] = np.clip(recolour(row), 0, 1)
            out[y0 - 3:y0, x0:x1] = out[y0, x0:x1]; out[y1:y1 + 3, x0:x1] = out[y1 - 1, x0:x1]
    # --- brows follow the hair (never lighter than a mid brown), lashes stay dark
    bc = np.minimum(ht * 0.75, np.array([0.30, 0.20, 0.13])) + 0.015
    out = lerp(out, np.broadcast_to(bc, out.shape) * (0.75 + 0.5 * (lum / np.maximum(blur(lum, 9), 1e-3))[..., None]).clip(0, 1.5), np.clip(m["brows"] * 0.9, 0, 1))
    # --- iris
    il = lum[m["iris"] > 0.5]; imean = float(il.mean()) if len(il) else 0.3
    ic = np.array(ch["eyes"])[None, None, :] * np.clip(lum / imean, 0.2, 2.5)[..., None]
    out = lerp(out, np.clip(ic, 0, 1), m["iris"] * 0.88)
    if tactical:                                         # their face paint, laid over the new face
        diff = np.abs(m["tac"] - m["orig"]).max(-1)
        a = blur(smooth(0.035, 0.11, diff), 1.0) * (1 - m["eye"]) * (1 - m["mouth"])
        paint = m["tac"] * (0.92 - 0.25 * dark)
        out = lerp(out, paint, a)
    return np.clip(out, 0, 1), (mean, target, g)


def hands_texture(ch, skinfit):
    mean, target, g = skinfit
    h = np.asarray(Image.open(os.path.join(REF, "tex", f"hands_0{ch['base']}.png")).convert("RGB"), dtype=np.float64) / 255
    hm = h.reshape(-1, 3); hm = hm[hm.sum(1) > 0.6].mean(0)              # hand skin mean (ignore dark background)
    return np.clip(target * np.clip(h / hm, 0, 3) ** g, 0, 1)


def save_paa(arr, name):
    os.makedirs(OUT, exist_ok=True); os.makedirs(DATA, exist_ok=True)
    png = os.path.join(OUT, name + ".png")
    Image.fromarray((arr * 255 + 0.5).astype(np.uint8)).save(png)
    subprocess.run([TOPAA, png, os.path.join(DATA, name + ".paa")], check=True, stdout=subprocess.DEVNULL)


# ------------------------------------------------------------------ face shape
EYE = np.array([0.0325, 0.705, -0.0873])


def morph(P, s):
    """P: (n,3) arma points -> reshaped points. Neck, skull, ears and the eye region stay as they are."""
    P = np.asarray(P, dtype=np.float64); x, y, z = P[:, 0], P[:, 1], P[:, 2]; ax = np.abs(x); sg = np.sign(x)
    de = np.linalg.norm(np.stack([ax - EYE[0], y - EYE[1], z - EYE[2]], -1), axis=1)
    base = smooth(-0.035, -0.065, z) * smooth(0.016, 0.028, de) * smooth(0.585, 0.600, y)
    mm = 1e-3
    d = np.zeros_like(P)
    w = smooth(0.668, 0.640, y) * smooth(0.010, 0.034, ax) * base
    d[:, 0] += sg * s["jaw"] * mm * w
    w = smooth(0.628, 0.604, y) * smooth(0.036, 0.016, ax) * base
    d[:, 1] -= s["chin"] * mm * w; d[:, 2] -= s["chin_fwd"] * mm * w
    nb = np.exp(-(x / 0.016) ** 2) * smooth(0.650, 0.662, y) * smooth(0.715, 0.700, y) * smooth(-0.098, -0.112, z)
    d[:, 0] += x * s["nose_w"] * nb; d[:, 2] -= s["nose_len"] * mm * nb
    d[:, 1] += s["nose_up"] * mm * nb * smooth(0.690, 0.665, y)
    cb = np.exp(-((ax - 0.046) / 0.016) ** 2) * np.exp(-((y - 0.672) / 0.018) ** 2) * base
    d[:, 0] += sg * s["cheek"] * mm * cb; d[:, 2] -= 0.4 * s["cheek"] * mm * cb
    lb = np.exp(-(x / 0.022) ** 2) * np.exp(-((y - 0.637) / 0.010) ** 2) * smooth(-0.095, -0.105, z)
    d[:, 2] -= s["lips"] * mm * lb
    bb = np.exp(-((y - 0.728) / 0.010) ** 2) * smooth(0.008, 0.020, ax) * smooth(0.062, 0.045, ax) * smooth(-0.080, -0.095, z)
    d[:, 2] -= s["brow"] * mm * bb
    return P + d


def write_model(ch, braid=False):
    b, lods = mlod.read(SRC_P3D)
    newp, newn = {}, {}
    for L in lods:
        if L.npoints == 0 or L.res > 9e14: continue          # empty and memory LODs stay
        Pn = morph(L.points, ch["shape"])
        newp[L.index] = Pn; newn[L.index] = mlod.updated_normals(L, L.points, Pn)
    b = mlod.patch(b, lods, newp, newn)
    name = f"mhfh_{ch['id']}{'_braid' if braid else ''}"
    tex = PREFIX + f"data\\{name}_co.paa"; mat = PREFIX + "data\\mhfh_face.rvmat"
    if braid:                                            # take the bun off the first LOD and hang the braid there
        _, lods2 = mlod.read_bytes(bytes(b)); L = lods2[0]
        bun = L.selections["Bun"][0] > 0; like = int(np.nonzero(bun)[0][0])
        fv = np.clip(L.face_v, 0, L.npoints - 1)
        isbun = np.array([bun[fv[f, :L.face_n[f]]].all() for f in range(L.nfaces)])
        # the braid goes in first (it needs a bun point as its pattern), then the bun faces come off
        P, N, faces, weights = braidlib.braid_mesh()
        b = braidlib.append(b, 0, P, N, faces, weights, tex, mat, like)
        _, lods3 = mlod.read_bytes(bytes(b)); L3 = lods3[0]
        keep = np.ones(L3.nfaces, bool); keep[:len(isbun)] = ~isbun
        b = mlod.rebuild(b, lods3, faces={0: (keep, np.arange(L3.npoints))})
    _, lods2 = mlod.read_bytes(bytes(b))
    b = mlod.rewrite_face_paths(b, lods2, lambda s: (tex if s.lower().endswith(".paa") else mat if s.lower().endswith(".rvmat") else s))
    os.makedirs(MODELS, exist_ok=True)
    open(os.path.join(MODELS, name + ".p3d"), "wb").write(bytes(b))


# ------------------------------------------------------------------ config
RVMAT = '''class StageTI {
    texture = "a3\\characters_f\\heads\\data\\m_ti_ca.paa";
};
ambient[] = {1, 1, 1, 1};
diffuse[] = {1, 1, 1, 1};
forcedDiffuse[] = {0, 0, 0, 0};
emmisive[] = {0, 0, 0, 1};
specular[] = {0.12, 0.12, 0.12, 1};
specularPower = 70;
PixelShaderID = "Super";
VertexShaderID = "Super";
''' + "".join(f'''class Stage{n} {{
    texture = "{t}";
{e}    uvSource = "tex";
    class uvTransform {{
        aside[] = {{1, 0, 0}};
        up[] = {{0, 1, 0}};
        dir[] = {{0, 0, 0}};
        pos[] = {{0, 0, 0}};
    }};
}};
''' for n, t, e in ((1, "A3_female_heads\\Models\\xxx_nohq.paa", ""), (2, "#(argb,8,8,3)color(0.5,0.5,0.5,1,DT)", ""),
                    (3, "#(argb,8,8,3)color(0,0,0,0,MC)", ""), (4, "A3_female_heads\\Models\\xxx_as.paa", ""),
                    (5, "#(argb,8,8,3)color(0,0,0.5,1,SMDI)", ""), (6, "#(ai,64,64,1)fresnel(0.5,0.2)", ""),
                    (7, "a3\\data_f\\env_co.paa", '    useWorldEnvMap = "true";\n')))


def write_config():
    D = "\\" + PREFIX + "data\\"
    heads = "".join(f'''    class mhfh_{c["id"]}{v}: bun_female_bun_01 {{
        model = "\\{PREFIX}models\\mhfh_{c["id"]}{v}.p3d";
    }};
''' for c in CHARS for v in ("", "_braid"))
    faces = ""
    for c in CHARS:
        for v, tac in (("", False), ("", True), ("_braid", False), ("_braid", True)):
            cls = f'mhfh_{c["id"]}{v}{"_tac" if tac else ""}'
            label = ", ".join(([] if not v else ["Braid"]) + ([] if not tac else ["Tactical"]))
            faces += f'''        class {cls}: B_female_bun_01 {{
            author = "Miss Heda";
            displayName = "{c["name"]}{" (" + label + ")" if label else ""}";
            head = "mhfh_{c["id"]}{v}";
            texture = "{D}{cls}_co.paa";
            material = "{D}mhfh_face.rvmat";
            materialWounded1 = "{D}mhfh_face.rvmat";
            materialWounded2 = "{D}mhfh_face.rvmat";
            textureHL = "{D}mhfh_{c["id"]}_hl_co.paa";
            textureHL2 = "{D}mhfh_{c["id"]}_hl_co.paa";
        }};
'''
    cfg = f'''// Generated by tools/characters.py
class CfgPatches {{
    class mhfh_heads {{
        name = "MH Female Heads - Heads";
        author = "Miss Heda";
        units[] = {{}};
        weapons[] = {{}};
        requiredVersion = 2.18;
        requiredAddons[] = {{"mhfh_main", "A3_Characters_F", "A3_Characters_F_Heads", "female3_ICEMAN"}};
    }};
}};

// New characters on the Task Force Timberwolf female head: reshaped copies of that model with new face textures.
class CfgHeads {{
    class bun_female_bun_01;
{heads}}};

class CfgFaces {{
    class Default;
    class Man_A3: Default {{
        class B_female_bun_01;
{faces}    }};
}};
'''
    open(os.path.join(ROOT, "addons", "heads", "config.cpp"), "w", newline="\n").write(cfg)
    open(os.path.join(DATA, "mhfh_face.rvmat"), "w", newline="\n").write(RVMAT)
    # model.cfg: the skeleton comes from the BI sample (kept as it is in the file), the model classes are ours.
    # Without a matching class a model is binarized without skeleton and the face does not animate.
    mc = os.path.join(ROOT, "addons", "heads", "model.cfg"); s = open(mc, encoding="utf8").read()
    s = s[:s.index("class CfgModels")] + '''class CfgModels
{
	class Default
	{
		sectionsInherit = "";
		sections[] = {};
		skeletonName = "";
	};
	class ArmaMan: Default
	{
		htMin = 60;
		htMax = 1800;
		afMax = 30;
		mfMax = 0;
		mFact = 1;
		tBody = 37;
		sections[] =
		{
			"osobnost","Head_Injury","Body_Injury","l_leg_injury","l_arm_injury","r_arm_injury","r_leg_injury","injury_body","injury_legs","injury_hands",
			"clan","clan_sign","Camo","CamoB","Camo1","Camo2","personality","hl","injury_head","insignia","ghillie_hide"
		};
		skeletonName = "OFP2_ManSkeleton";
	};
''' + "".join(f"\tclass mhfh_{c['id']}{v}: ArmaMan {{}};\n" for c in CHARS for v in ("", "_braid")) + "};\n"
    open(mc, "w", encoding="utf8", newline="\n").write(s)


def main():
    for c in CHARS:
        t, fit = face_texture(c); save_paa(t, f"mhfh_{c['id']}_co")
        save_paa(face_texture(c, tactical=True)[0], f"mhfh_{c['id']}_tac_co")
        save_paa(face_texture(c, braid=True)[0], f"mhfh_{c['id']}_braid_co")
        save_paa(face_texture(c, tactical=True, braid=True)[0], f"mhfh_{c['id']}_braid_tac_co")
        save_paa(hands_texture(c, fit), f"mhfh_{c['id']}_hl_co")
        write_model(c); write_model(c, braid=True)
        print(c["name"], "done")
    write_config()
    # reshaped reference points for previews and checks
    d = np.load(os.path.join(REF, "models", "tftw_head.npz"))
    np.savez(os.path.join(OUT, "chars.npz"), F=d["F"], uv=d["uv"], ids=np.array([c["id"] for c in CHARS]),
             **{c["id"]: morph(d["P"], c["shape"]) for c in CHARS}, base=d["P"])


if __name__ == "__main__":
    main()
