"""Compose the head textures from the data passes baked in Blender (tools/bake/*.npy, see tools/blender/bake.py).

Every texel knows its part, its source-texture UV and its position on the head, so the colour comes straight
from the CC0 source images (no blurry re-bake) and everything else is painted in head space:
pulled-back hair flowing into the bun, brows, lash line, lips, teeth, plus normal, specular, AO and wound maps.
Outputs PNGs into tools/out (converted to PAA by tools/make_paa.ps1).
usage (repo root): python -I tools/compose_textures.py [--detail tools/out/detail_<tone>.png]
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hairline
from hairline import smooth

B = os.path.join(HERE, "bake"); OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
MPFB = os.path.join(os.environ["APPDATA"], "Blender Foundation", "Blender", "5.2", "extensions", ".user", "user_default", "mpfb", "data")
L = json.load(open(os.path.join(B, "landmarks.json")))
PART = L["parts"]; EYE = np.array(L["eye_l"]); BUN = np.array(L["bun"]); MOUTH_Z = L["mouth_z"]
TONES = {
    "light": dict(skin=("young_caucasian_female", "young_lightskinned_female_diffuse.png"), eye="green_eye.png",
                  hair=((0.085, 0.052, 0.035), (0.30, 0.20, 0.125)), lip=(0.70, 0.36, 0.37), lipk=0.42, eyesat=0.55),
    "dark": dict(skin=("young_african_female", "young_darkskinned_female_diffuse.png"), eye="brown_eye.png",
                 hair=((0.030, 0.024, 0.022), (0.12, 0.095, 0.08)), lip=(0.45, 0.20, 0.21), lipk=0.30, freckle=0.0),
}

ld = lambda n: np.load(os.path.join(B, n + ".npy"))[::-1].astype(np.float64)   # image rows top-down
P = ld("pos"); N = ld("nrm"); SRC = ld("src"); EAR = ld("ear")[..., 0]; AO = ld("ao")[..., 0]; NB = ld("normal")
R = P.shape[0]
part = np.rint(SRC[..., 2] * 10).astype(int)
part[np.abs(P).sum(-1) < 1e-6] = 9                         # texels no face covers
covered = part < 9
is_ = {k: (part == v) for k, v in PART.items()}
x, y, z = P[..., 0], P[..., 1], P[..., 2]
nlen = np.linalg.norm(N, axis=-1, keepdims=True); N = N / np.maximum(nlen, 1e-9)
PX_PER_M = 4600.0


def srgb(img):
    return np.asarray(Image.open(img).convert("RGB"), dtype=np.float64) / 255.0


def sample(img, uv):
    """bilinear lookup, uv origin bottom left"""
    h, w = img.shape[:2]
    u = np.clip(uv[..., 0] * w - 0.5, 0, w - 1.001); v = np.clip((1 - uv[..., 1]) * h - 0.5, 0, h - 1.001)
    u0 = np.floor(u).astype(int); v0 = np.floor(v).astype(int); fu = (u - u0)[..., None]; fv = (v - v0)[..., None]
    return (img[v0, u0] * (1 - fu) + img[v0, u0 + 1] * fu) * (1 - fv) + (img[v0 + 1, u0] * (1 - fu) + img[v0 + 1, u0 + 1] * fu) * fv


def ring_strands(psi, rho, seed, nmin, nmax, count):
    """strand pattern that is periodic in the angle psi (integer frequencies), fading where it would alias"""
    r = np.random.default_rng(seed); s = np.zeros_like(psi); tot = 0.0
    for n in np.unique(r.integers(nmin, nmax, count)):
        w = r.uniform(0.4, 1.0)
        px = 2 * np.pi * rho * PX_PER_M / n               # pixels per wave
        s += w * np.sin(n * psi + r.uniform(0, 6.283)) * smooth(4.0, 9.0, px); tot += w
    return s / (tot ** 0.5 * 0.9)


def sine_noise(p, freq, seed, n=10, spread=(0.6, 1.6)):
    r = np.random.default_rng(seed); s = np.zeros(p.shape[:-1])
    for _ in range(n):
        d = r.normal(size=3); d /= np.linalg.norm(d)
        s += np.sin((p @ d) * freq * r.uniform(*spread) + r.uniform(0, 6.283))
    return s / n ** 0.5


def lerp(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


# ------------------------------------------------------------------ hair layout (shared by all tones)
skinp = is_["skin"]
# across-strand coordinate: angle around the axis from the bun to the top of the forehead
axis = np.array([0.0, -0.110, 0.700]) - BUN   # front pole on the nose bridge: hair runs straight back from the hairline; axis /= np.linalg.norm(axis)
e1 = np.array([1.0, 0, 0]); e2 = np.cross(axis, e1)
d = P - BUN
psi = np.arctan2(d @ e1, d @ e2); rho = np.linalg.norm(d - (d @ axis)[..., None] * axis, axis=-1)
fine = ring_strands(psi, rho, 3, 60, 620, 70)             # single strands
clump = ring_strands(psi, rho, 4, 6, 40, 14)              # locks
along = sine_noise(P, 55.0, 5, 6)
irr = sine_noise(P, 700.0, 8, 24, (0.3, 3.0))             # irregular, so the edge is not a comb
jit = (clump * 0.4 + irr * 0.6) * 0.0022
hair = hairline.hair_mask(P, soft=0.009, jitter=jit) * (1 - np.clip(EAR * 4, 0, 1)) * skinp
# wispy edge: single strands reach a little past the solid hair
edge = np.clip(hair * (0.72 + 0.22 * (fine * 0.5 + 0.5) + 0.22 * (irr * 0.5 + 0.5)), 0, 1)
hair_a = np.where(hair > 0.97, 1.0, smooth(0.15, 0.85, edge))
# bun: coil pattern in its own disc UV
bu = SRC[..., 0] - 0.5; bv = SRC[..., 1] - 0.5
brad = np.hypot(bu, bv) / 0.48 * 1.06; bang = np.arctan2(bv, bu)
bphase = bang + 4.5 * brad
bfine = ring_strands(bphase, np.maximum(brad, 0.05) * 0.034, 6, 30, 300, 60)
bclump = ring_strands(bphase, np.maximum(brad, 0.05) * 0.034, 7, 2, 14, 8)
bun = is_["bun"]
fine = np.where(bun, bfine, fine); clump = np.where(bun, bclump, clump)
hair_a = np.where(bun, 1.0, hair_a)
strand = np.clip(0.5 + 0.30 * fine + 0.22 * clump + 0.05 * along, 0, 1)
_root = np.where(bun, 1.0, smooth(0.0, 0.014, z - hairline.hairline_height(P)))
hair_h = (0.35 * fine + 0.30 * clump) * hair_a * (0.35 + 0.65 * _root)   # height field for the normal map, calmer at the hairline

# ------------------------------------------------------------------ face features in head space
front = smooth(-0.15, -0.55, N[..., 1])                      # facing forward
ax = np.abs(x)
# brows: an arch over each eye, thick at the nose, thin at the temple
t = (ax - 0.010) / 0.048
arch = EYE[2] + 0.0200 + 0.0065 * np.sin(np.clip(t, 0, 1) * 2.4) - 0.005 * np.clip(t - 0.75, 0, 1) * 4
half = 0.0045 * (1 - 0.62 * np.clip(t, 0, 1)) + 0.0006
bst = np.clip(sine_noise(P * np.array([0.45, 1.0, 1.0]), 2600.0, 9, 30, (0.5, 1.8)) * 0.5 + 0.5, 0, 1)   # hairs lying sideways
brow = smooth(half, half * 0.25, np.abs(z - arch)) * smooth(-0.10, 0.12, t) * smooth(1.08, 0.86, t) * front * skinp
brow = np.clip(brow * (0.80 + 0.30 * bst), 0, 1)
# lash line: skin right at the eyeball, darker on the upper lid
ec = np.stack([np.sign(x) * EYE[0], np.full_like(x, EYE[1]), np.full_like(x, EYE[2])], -1)
de = np.linalg.norm(P - ec, axis=-1) - L["eye_r"]
infront = smooth(EYE[1] + 0.004, EYE[1] - 0.004, y) * smooth(0.021, 0.016, np.abs(ax - EYE[0]))
rim = smooth(0.0016, 0.0003, np.abs(de)) * skinp * infront
upper = smooth(-0.001, 0.003, z - EYE[2])
lash = rim * (0.80 * upper + 0.12 * (1 - upper))
shadow = smooth(0.007, 0.001, np.abs(de)) * upper * skinp * infront * 0.10
# lips
lipm = np.exp(-(((x / 0.0225) ** 2 + ((z - MOUTH_Z) / 0.0075) ** 2) ** 2.0)) * front * skinp
# cheeks
blush = np.exp(-(((ax - 0.045) / 0.022) ** 2 + ((z - (EYE[2] - 0.035)) / 0.018) ** 2)) * front * skinp
mottle = sine_noise(P, 260.0, 11, 12) * 0.5 + sine_noise(P, 900.0, 12, 12) * 0.5
pores = sine_noise(P, 4200.0, 13, 40, (0.35, 2.6))
fr = sine_noise(P, 2300.0, 14, 16) * 0.6 + sine_noise(P, 1100.0, 15, 10) * 0.4
freckle = smooth(1.05, 1.55, fr) * np.exp(-((z - (EYE[2] - 0.022)) / 0.030) ** 2) * smooth(0.075, 0.045, ax) * front * skinp
undereye = np.exp(-(((ax - EYE[0]) / 0.016) ** 2 + ((z - (EYE[2] - 0.016)) / 0.007) ** 2)) * front * skinp
nosetip = np.exp(-((x / 0.012) ** 2 + ((z - (EYE[2] - 0.040)) / 0.012) ** 2)) * front * skinp

# teeth: procedural strip (u along the arch, v across gum -> edge -> inside)
tu, tv = SRC[..., 0], SRC[..., 1]
band = np.where(tv < 0.15, tv, tv - 0.16) / 0.14
tooth = tu * 14.0; gap = np.abs(tooth - np.rint(tooth))
enamel = np.array([0.84, 0.81, 0.73]); gum = np.array([0.58, 0.27, 0.28])
tcol = lerp(np.broadcast_to(gum, P.shape), np.broadcast_to(enamel, P.shape), smooth(0.10, 0.22, band) * smooth(1.0, 0.80, band))
tcol = tcol * (1 - 0.45 * smooth(0.05, 0.0, gap) * smooth(0.12, 0.3, band))[..., None]
tcol = tcol * (0.88 + 0.12 * np.cos((tooth - np.floor(tooth) - 0.5) * 2.2))[..., None]
tcol = tcol * np.where(band > 0.76, 0.55, 1.0)[..., None]


def compose(tone, cfg, detail=None):
    skin_img = srgb(os.path.join(MPFB, "skins", cfg["skin"][0], cfg["skin"][1]))
    eye_img = srgb(os.path.join(MPFB, "eyes", "materials", cfg["eye"]))
    tongue_img = srgb(os.path.join(MPFB, "tongue", "tongue01", "tongue01_diffuse.png"))
    col = sample(skin_img, SRC)
    if detail is not None:
        col = np.where(skinp[..., None], detail, col)
    sk = skinp[..., None]
    # the source skin has scalp stubble: near and above the hairline use plain forehead skin instead
    fh = skinp & (np.abs(x) < 0.03) & (z > EYE[2] + 0.030) & (z < EYE[2] + 0.045) & (y < -0.06)
    plain = col[fh].mean(0)
    hl_ = hairline.hairline_height(P)
    scalp = smooth(hl_ - 0.030, hl_ - 0.012, z) * smooth(0.55, 0.95, hairline.theta(P)) * skinp
    col = lerp(col, np.broadcast_to(plain, P.shape), scalp * 0.9)
    # skin life: mottling, blush, pores
    col = np.where(sk, col * (1 + 0.035 * mottle[..., None] * np.array([1.0, 0.7, 0.6])) * (1 + 0.010 * pores[..., None]), col)
    # the full-body source skin is soft at this size: sharpen it, then add what a face has
    g = np.asarray(Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), dtype=np.float64) / 255
    col = np.where(sk, np.clip(col + (col - g) * 0.9, 0, 1), col)
    col = lerp(col, col * np.array([1.06, 0.90, 0.90]), blush * 0.55)
    col = lerp(col, col * np.array([1.05, 0.92, 0.92]), nosetip * 0.35)
    col = lerp(col, col * np.array([0.93, 0.90, 0.93]), undereye * 0.12)
    col = lerp(col, col * np.array([0.74, 0.60, 0.50]), freckle * cfg.get("freckle", 0.55))
    col = np.where(sk, col * (0.72 + 0.28 * np.clip(AO, 0, 1)[..., None] ** 0.8), col)
    col = lerp(col, col * 0.6 + np.array(cfg["lip"]) * 0.4, lipm * cfg["lipk"])
    col = lerp(col, col * np.array([0.62, 0.52, 0.50]), shadow)
    base, tip = np.array(cfg["hair"][0]), np.array(cfg["hair"][1])
    col = lerp(col, np.broadcast_to(base * 0.9, P.shape), lash)
    col = lerp(col, np.broadcast_to(base * 1.25, P.shape), brow * 0.85)
    # parts with their own source image
    ey = sample(eye_img, SRC); gy = ey.mean(-1, keepdims=True)
    ey = (gy + (ey - gy) * cfg.get("eyesat", 0.7)) * np.array([0.93, 0.92, 0.92])       # calmer iris, off-white sclera
    col = np.where(is_["eye"][..., None], ey, col)
    col = np.where(is_["tongue"][..., None], sample(tongue_img, SRC) * 0.9, col)
    col = np.where(is_["teeth"][..., None], tcol, col)
    col = np.where(is_["cavity"][..., None], col * 0.75, col)
    # hair: dark roots and locks, lighter single strands, a broad sheen where the skull faces up/back
    hc = lerp(np.broadcast_to(base, P.shape), np.broadcast_to(tip, P.shape), strand ** 1.6)
    sheen = smooth(0.35, 0.95, N[..., 2]) * 0.22 + smooth(0.2, 0.9, N[..., 1]) * 0.10
    hc = hc * (0.85 + sheen[..., None] * (0.6 + 0.8 * strand[..., None]))
    hc = lerp(np.broadcast_to(base, P.shape), hc, smooth(0.5, 1.0, hair_a))        # thin edge strands stay dark
    root = smooth(0.0, 0.012, z - hairline.hairline_height(P))            # slightly see-through at the roots
    ha = hair_a * np.where(bun, 1.0, 0.80 + 0.20 * root)
    col = lerp(col, hc, ha)
    col = np.where(covered[..., None], col, col[covered].mean(0))
    Image.fromarray((np.clip(col, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, f"fh_{tone}_co.png"))


def others():
    lips = lipm; eyes = is_["eye"]
    # ---- normal map (OpenGL in, DirectX out)
    n = NB.copy()
    flat = ~(skinp | is_["cavity"]); n[flat] = (0.5, 0.5, 1.0)
    n = lerp(n, np.broadcast_to(np.array([0.5, 0.5, 1.0]), n.shape), hair_a * 0.85)    # hair: only the strand relief
    h = hair_h * 0.55 + (pores * 0.045 + mottle * 0.02) * skinp * (1 - hair_a) + lips * 0.10 * np.sin(x * 2400) * 0.5
    h = h + is_["teeth"] * (-0.25 * smooth(0.06, 0.0, gap))
    dhx = np.gradient(h, axis=1); dhy = np.gradient(h, axis=0)
    k = 3.2
    n[..., 0] = np.clip(n[..., 0] - 0.5 * k * dhx, 0, 1)
    n[..., 1] = np.clip(n[..., 1] + 0.5 * k * dhy, 0, 1)
    n[..., 1] = 1 - n[..., 1]
    n[~covered] = (0.5, 0.5, 1.0)
    Image.fromarray((n * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, "fh_nohq.png"))
    # ---- smdi: R = 1, G specular, B glossiness
    tz = np.exp(-((x / 0.018) ** 2)) * front * 0.06               # nose and forehead a touch shinier
    g = (0.26 + tz + 0.03 * mottle) * skinp
    bl = 0.34 * skinp
    g = g * (1 - lips) + 0.40 * lips; bl = bl * (1 - lips) + 0.50 * lips
    g = g * (1 - hair_a) + (0.16 + 0.26 * strand) * hair_a; bl = bl * (1 - hair_a) + 0.58 * hair_a
    for m, gs, bs in ((eyes, 0.9, 0.92), (is_["teeth"], 0.6, 0.7), (is_["tongue"], 0.55, 0.6), (is_["cavity"], 0.35, 0.5)):
        g = np.where(m, gs, g); bl = np.where(m, bs, bl)
    smdi = np.stack([np.ones_like(g), g, bl], -1); smdi[~covered] = (1, 0.26, 0.34)
    Image.fromarray((np.clip(smdi, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, "fh_smdi.png"))
    # ---- ambient shadow
    a = np.clip(AO * 1.08, 0, 1); a = np.where(eyes, np.maximum(a, 0.85), a); a[~covered] = 1
    Image.fromarray((np.stack([a, a, a], -1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, "fh_as.png"))
    # ---- wound macro map (blended over the skin by its alpha): blood on brow, cheek, nose and lip
    spots = [((0.030, -0.105, EYE[2] + 0.030), 0.020), ((-0.045, -0.085, EYE[2] - 0.035), 0.024),
             ((0.004, -0.120, EYE[2] - 0.040), 0.012), ((-0.012, -0.105, MOUTH_Z - 0.004), 0.011), ((0.060, -0.040, EYE[2] + 0.010), 0.02)]
    ns = sine_noise(P, 420.0, 21, 12) * 0.5 + sine_noise(P, 1500.0, 22, 12) * 0.5
    al = np.zeros_like(x)
    for c, r in spots:
        dd = np.linalg.norm(P - np.array(c), axis=-1)
        al = np.maximum(al, smooth(1.0, 0.35, dd / r + 0.35 * ns))
    drip = smooth(0.004, 0.0, np.abs(x - 0.030 - 0.004 * np.sin(z * 300))) * smooth(EYE[2] + 0.03, EYE[2] + 0.02, z) * smooth(EYE[2] - 0.02, EYE[2] + 0.01, z) * 0.8
    al = np.clip(np.maximum(al, drip) * skinp * (1 - hair_a * 0.6), 0, 1) * 0.92
    blood = np.broadcast_to(np.array([0.30, 0.025, 0.02]), P.shape) * (0.75 + 0.35 * ns[..., None])
    bruise = smooth(0.03, 0.0, np.linalg.norm(P - np.array([-0.045, -0.085, EYE[2] - 0.030]), axis=-1)) * skinp * 0.35
    rgb = lerp(np.broadcast_to(np.array([0.33, 0.16, 0.26]), P.shape), blood, np.clip(al * 3, 0, 1))
    mc = np.concatenate([np.clip(rgb, 0, 1), np.maximum(al, bruise)[..., None]], -1)
    Image.fromarray((mc * 255 + 0.5).astype(np.uint8), "RGBA").save(os.path.join(OUT, "fh_injury_mc.png"))


if __name__ == "__main__":
    only = [a for a in sys.argv[1:] if a in TONES]
    for tone, cfg in TONES.items():
        if only and tone not in only: continue
        dp = os.path.join(OUT, f"detail_{tone}.png")
        compose(tone, cfg, srgb(dp) if os.path.exists(dp) and "--no-detail" not in sys.argv else None)
    others()
    Image.open(os.path.join(OUT, "fh_light_co.png")).resize((1024, 1024), Image.LANCZOS).save(os.path.join(OUT, "_preview_co.png"))
    print("ok, covered", round(float(covered.mean()), 3))
