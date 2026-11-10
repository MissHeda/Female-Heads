"""Compose the head textures from the Blender bake passes (tools/bake/*.npy, written by the bake script).

Hair is painted procedurally per texel from the baked world position: pulled-back hair over the scalp
flowing to a low bun, plus the bun itself. Outputs PNGs into tools/out (converted to PAA afterwards).
usage: python -I tools/compose_textures.py
"""
import json, os, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "bake"); OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
L = json.load(open(os.path.join(B, "landmarks.json")))
ld = lambda n: np.load(os.path.join(B, n + ".npy"))[::-1]  # blender rows bottom-up -> image rows top-down
P = ld("pos")[..., :3]; N = ld("nrm")[..., :3]
covered = np.abs(P).sum(-1) > 1e-6
EZ = L["joint-l-eye"][2]; YC = L["joint-head"][1]; BUN = np.array(L["bun"])
rng = np.random.default_rng(7)

def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def strands(u, v, freq, seed):
    """1D strand noise across u (many sines with random phases), slowly wobbling along v"""
    r = np.random.default_rng(seed); s = np.zeros_like(u)
    for k in range(24):
        f = freq * r.uniform(0.5, 2.0); ph = r.uniform(0, 6.283); w = r.uniform(0.3, 1.0)
        s += w * np.sin(u * f + ph + 0.6 * np.sin(v * r.uniform(5, 25) + ph))
    s = s / np.abs(s).max(); return 0.5 + 0.5 * s

x, y, z = P[..., 0], P[..., 1], P[..., 2]
# --- hairline: height above the eye centre as a function of the angle around the vertical axis
th = np.abs(np.arctan2(x, -(y - YC)))           # 0 = front, pi = back
knots_t = np.array([0.0, 0.45, 0.85, 1.15, 1.45, 1.75, 2.2, 2.7, np.pi])
knots_h = np.array([0.062, 0.059, 0.052, 0.042, 0.032, 0.022, -0.020, -0.075, -0.088])
hl = EZ + np.interp(th, knots_t, knots_h)
jit = (strands(th * 40, z * 30, 30, 1) - 0.5) * 0.004
hair = smooth(hl - 0.002, hl + 0.006, z + jit)
ear = (np.abs(x) > 0.066) & (z < EZ + 0.02) & (z > EZ - 0.06) & (th > 1.2) & (th < 2.1)
hair *= ~ear
# --- strand pattern: angle around the front-back axis through the bun centre -> lines run front to back
u = np.arctan2(x, z - BUN[2]); v = y
st = strands(u * 1.0, v, 160, 3) * 0.6 + strands(u, v, 420, 4) * 0.4
# --- the bun: texels close to the bun centre swirl around its axis
db = np.linalg.norm(P - BUN, axis=-1)
isbun = (db < 0.05) & (y > BUN[1] - 0.012)
ub = np.arctan2(z - BUN[2], x - BUN[0]) + 18 * db
sb = strands(ub, db * 40, 90, 5) * 0.6 + strands(ub, db * 40, 260, 6) * 0.4
st = np.where(isbun, sb, st); hair = np.where(isbun, 1.0, hair)
covered |= isbun
nup = np.clip(N[..., 2], -1, 1)

def hair_rgb(base, tip):
    base = np.array(base) ** 2.2; tip = np.array(tip) ** 2.2
    t = st[..., None]
    c = base * (1 - t) + tip * t
    c *= (0.75 + 0.25 * nup[..., None] * 0.5 + 0.25)  # slightly lighter on top
    return c ** (1 / 2.2)

ao = ld("ao")[..., 0]
# --- brows: painted procedurally, an arch above each eye, tapering towards the temple
EX = abs(L["joint-l-eye"][0]); EY = L["joint-l-eye"][1]
ax = np.abs(x); t = (ax - 0.010) / 0.050                       # 0 at the inner end, 1 at the tail
arch = EZ + 0.020 + 0.007 * np.sin(np.clip(t, 0, 1) * 2.6) - 0.004 * np.clip(t - 0.8, 0, 1) * 5
half = 0.0042 * (1 - 0.65 * np.clip(t, 0, 1)) + 0.0006
front = N[..., 1] < -0.25
bstr = strands(z * 900 + ax * 600, ax * 50, 1.0, 9)
brows = smooth(half, half * 0.45, np.abs(z - arch)) * smooth(-0.05, 0.08, t) * smooth(1.08, 0.9, t) * front
brows = np.clip(brows * (0.55 + 0.6 * bstr), 0, 1) * 0.85
col_shape = P.shape
skin_spec = 0.22
for tone, base, tip in (("light", (0.10, 0.065, 0.045), (0.26, 0.17, 0.11)), ("dark", (0.035, 0.028, 0.025), (0.11, 0.085, 0.07))):
    sp = os.path.join(B, f"skin_{tone}.npy")
    if not os.path.exists(sp): continue
    skin = ld(f"skin_{tone}")[..., :3]
    bc = np.broadcast_to(np.array(base) * 1.1, col_shape).copy(); ba = brows
    if tone == "dark": bc = bc * 0.45
    col = skin * (1 - ba[..., None] * 0.9) + bc * ba[..., None] * 0.9
    edge = hair * (0.55 + 0.45 * st)          # thin strands at the hairline let skin show through
    hm = np.where(hair > 0.98, 1.0, edge)[..., None]
    col = col * (1 - hm) + hair_rgb(base, tip) * hm
    col[~covered] = col[covered].mean(0)
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, f"fh_{tone}_co.png"))
# normal map: blender bakes OpenGL (Y+), Arma wants DirectX (Y-)
n = ld("normal")[..., :3].copy(); n[..., 1] = 1 - n[..., 1]
# strand bumps on the hair
h = hair * (st - 0.5) * 0.25
n[..., 0] = np.clip(n[..., 0] + np.gradient(h, axis=1) * 6, 0, 1)
n[~covered] = (0.5, 0.5, 1.0)
Image.fromarray((n * 255).astype(np.uint8)).save(os.path.join(OUT, "fh_nohq.png"))
# smdi: R=1, G specular, B glossiness
g = np.full(hair.shape, skin_spec); g = g * (1 - hair) + (0.12 + 0.18 * st) * hair
bgl = np.full(hair.shape, 0.30); bgl = bgl * (1 - hair) + 0.55 * hair
smdi = np.stack([np.ones_like(g), g, bgl], -1)
Image.fromarray((smdi * 255).astype(np.uint8)).save(os.path.join(OUT, "fh_smdi.png"))
a = np.clip(ao, 0, 1); a[~covered] = 1
Image.fromarray((np.stack([a, a, a], -1) * 255).astype(np.uint8)).save(os.path.join(OUT, "fh_as.png"))
# preview sheet
Image.open(os.path.join(OUT, "fh_light_co.png")).resize((1024, 1024)).save(os.path.join(OUT, "_preview_co.png"))
print("ok", covered.mean())
