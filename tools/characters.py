"""New characters on the Task Force Timberwolf female head.

Every character is that head with a slightly different face shape and a face texture derived from one of the two
Timberwolf faces: other skin tone, hair, brow and eye colour, optional freckles, plus a "Tactical" variant with
the Timberwolf face paint. Reads the reference data written by tools/ref_tftw.py and writes
  addons/heads/data/mhfh_<id>[_braid][_tac]_co.paa, mhfh_<id>_hl_co.paa   textures (face, arms and legs)
  addons/heads/models/mhfh_<id>[_braid].p3d                                the reshaped model (all LODs)
  addons/heads/config.cpp, model.cfg                                       faces and heads
The mod needs the Timberwolf mod loaded: normal/ambient maps and base classes come from it.
usage (repo root): python -I tools/characters.py [--preview]
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mlod, tftw_masks, braid as braidlib, shadow
from tftw_masks import smooth, blur, blurf, N

ROOT = os.path.join(HERE, ".."); DATA = os.path.join(ROOT, "addons", "heads", "data"); MODELS = os.path.join(ROOT, "addons", "heads", "models")
OUT = os.path.join(HERE, "out"); REF = os.path.join(HERE, "ref")
TOPAA = r"D:\Steam\steamapps\common\Arma 3 Tools\ImageToPAA\ImageToPAA.exe"
SRC_P3D = os.path.join(REF, "tftw", "unbin", "A3_female_heads - UB", "Models", "female_head_bun.p3d")
PREFIX = "z\\mhfh\\addons\\heads\\"
TFTW = "\\A3_female_heads\\female_head_ICEMAN\\female_01\\"

# hair / eye colours (sRGB 0..1)
BLACK, DARKBROWN, CHESTNUT, AUBURN = (0.040, 0.036, 0.038), (0.105, 0.062, 0.042), (0.20, 0.105, 0.060), (0.27, 0.085, 0.045)
LIGHTBROWN, GINGER, BLONDE, PLATINUM = (0.34, 0.225, 0.14), (0.44, 0.215, 0.105), (0.62, 0.50, 0.33), (0.76, 0.67, 0.50)
# eye colours: (tint, brightness) of the iris against the grey of the photographed one, which keeps its light and
# dark. The game shows colours far more saturated than the texture has them: the clearly blue eyes of the
# Timberwolf face are (0.95, 1.01, 1.08) on this scale, her brown ones (1.15, 0.94, 0.89).
E_BLUE, E_GREY, E_GREEN = ((0.93, 1.00, 1.09), 1.00), ((0.97, 1.00, 1.03), 1.00), ((0.96, 1.04, 0.93), 0.92)
E_HAZEL, E_BROWN, E_DARK = ((1.09, 1.00, 0.86), 0.88), ((1.15, 0.95, 0.87), 0.78), ((1.11, 0.97, 0.89), 0.52)
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


# ------------------------------------------------------------------ face paint
def paint_layer(m):
    """The Timberwolf face paint taken off their painted face: -> (how thick it lies 0..1, its colour).
    Their painted texture is their skin with paint over it: painted = skin * (1 - a) + paint * a. The paint is a
    mix of two colours (olive and black), so for every texel a and the mix can be solved from the three colour
    channels. Laid over another skin with the same a, the result is their paint exactly as it is: thick where it
    is thick, the skin showing where it is thin, and nothing of their skin tone in it."""
    if "paint" in m: return m["paint"]
    tac, orig = m["tac"], m["orig"]; d = tac - orig
    on = m["cov"] & ~m["eye"] & ~m["mouth"]
    strong = on & (np.abs(d).max(-1) > 0.22) & (orig @ np.array([0.30, 0.59, 0.11]) > 0.3)
    px = tac[strong]; l = px @ np.array([0.30, 0.59, 0.11])
    black = px[l < np.percentile(l, 15)].mean(0); olive = px[l > np.percentile(l, 65)].mean(0)
    u = black[None, None, :] - orig; v = (olive - black)[None, None, :]
    uu = (u * u).sum(-1); uv = (u * v).sum(-1); vv = float((v * v).sum()); ud = (u * d).sum(-1); vd = (v * d).sum(-1)
    det = np.maximum(uu * vv - uv * uv, 1e-9)
    a = np.clip((ud * vv - vd * uv) / det, 0, 1); b = np.clip((vd * uu - ud * uv) / det, 0, None)
    b = np.minimum(b, a * 1.15)                                        # the mix stays between black and a bit beyond olive
    a = np.clip(np.where(uu > 1e-6, ((d - b[..., None] * v) * u).sum(-1) / np.maximum(uu, 1e-6), 0), 0, 1)   # a again with that mix
    paint = black + (b / np.maximum(a, 1e-3))[..., None] * v
    rest = d - (a[..., None] * u + b[..., None] * v)                   # brush marks the two colours do not explain
    a = a * smooth(0.04, 0.10, a) * on                                 # no haze where there is no paint
    paint = np.clip(paint + rest * smooth(0.3, 0.7, a)[..., None], 0, 1)
    print(f"face paint: olive {olive.round(3)}, black {black.round(3)}, not explained {float(np.abs(rest[strong]).mean()):.3f}")
    # Two changes to their pattern. The upper forehead is nearly bare on one side: more olive there, as strokes
    # running the way theirs do. And the ears carry a lot of paint: nearly half of it comes off.
    pos = m["pos"]; x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    thick = (a > 0.85) & m["cov"]; l = paint @ np.array([0.30, 0.59, 0.11])
    olive_thick = np.median(paint[thick & (l > np.percentile(l[thick], 55))], 0)
    across = np.array([0.90, -0.44, 0.0]); along = np.array([0.44, 0.90, 0.0])
    q = np.stack([pos @ across, (pos @ along) * 0.30, z * 0.5], -1)
    strokes = sine_noise(q, 330.0, 5, 10, (0.6, 1.6)) + 0.12 * sine_noise(pos, 700.0, 6, 8)
    zone = smooth(0.744, 0.756, y) * smooth(-0.055, -0.075, z) * smooth(0.070, 0.058, np.abs(x)) * m["cov"]
    more = zone * smooth(-0.45, 0.05, strokes) * 0.90
    # their colour: the paint next to it carried on, olive where there is none near
    near = blurf(a, 14); cont = np.stack([blurf(paint[..., i] * a, 14) for i in range(3)], -1) / np.maximum(near, 1e-3)[..., None]
    colour = lerp(np.broadcast_to(olive_thick, paint.shape), cont, smooth(0.05, 0.25, near)) * (1 + 0.04 * sine_noise(q, 900.0, 7, 8))[..., None]
    paint = lerp(paint, np.clip(colour, 0, 1), np.clip((more - a) / np.maximum(more, 1e-3), 0, 1))
    a = np.maximum(a, more)
    ear = np.zeros(a.shape); ear[:140, :230] = 1.0                    # the ears have their own corner of the texture
    a = a * (1 - 0.45 * ear)
    m["paint"] = (a, paint); return m["paint"]


# ------------------------------------------------------------------ hair towards the braid
BUN_AT, BRAID_AT = (0.665, 0.080), (0.727, 0.078)       # (height, depth): where the bun sat, where the braid starts


def hair_to_braid(m, hlum):
    """The photographed hair runs to the bun. For the braid it has to run to the start of the braid, 6 cm higher.
    The hair is laid out flat (around the head, down the head) and changed there:
      1. the spot the bun covered (photographed dark, with a rim) is filled with the hair around it, mirrored at
         its edge, so the strands go on to the middle; below the middle the hair from above is used upside down,
         because there is next to no hair under the bun that could run up to it;
      2. every texel takes the hair that lies a bit further down: by the full distance at the start of the braid,
         by nothing at the hairline. So the hair above still comes down to the braid and the hair below runs up."""
    pos, cov = m["pos"], m["cov"]; x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    RHO, CY, R1 = 0.085, 0.700, 0.047
    th = np.arctan2(x, z); s = th * RHO; t = np.arctan2(np.hypot(x, z), y - CY) * RHO
    tb = math.atan2(BUN_AT[1], BUN_AT[0] - CY) * RHO; tr = math.atan2(BRAID_AT[1], BRAID_AT[0] - CY) * RHO
    head = cov & ~m["bun"] & (np.abs(th) < 2.0)
    k = np.clip(1 - (s / 0.11) ** 2 - ((t - tr) / np.where(t < tr, 0.085, 0.125)) ** 2, 0, 1) ** 2 * head
    G = 0.00025; S0 = -0.18; W, H = int(0.36 / G), int(0.27 / G)
    src = head & (m["hair"] > 0.5)
    gi = np.clip(((s - S0) / G).astype(int), 0, W - 1); gj = np.clip((t / G).astype(int), 0, H - 1)
    A = np.zeros((H, W)); K = np.zeros((H, W)); A[gj[src], gi[src]] = hlum[src]; K[gj[src], gi[src]] = 1
    flat = A.copy(); done = K > 0
    for rad in (1, 2, 4, 8, 16, 32):                     # cells no texel fell into, and a rim beyond the hairline
        kk = blur(K, rad); take = ~done & (kk > 0.03)
        flat[take] = (blur(A, rad) / np.maximum(kk, 1e-3))[take]; done |= take

    def sample(F, fs, ft):                               # fs, ft in metres
        fi = (fs - S0) / G - 0.5; fj = ft / G - 0.5
        i0 = np.clip(np.floor(fi).astype(int), 0, W - 2); j0 = np.clip(np.floor(fj).astype(int), 0, H - 2)
        a = np.clip(fi - i0, 0, 1); b = np.clip(fj - j0, 0, 1)
        return F[j0, i0] * (1 - a) * (1 - b) + F[j0, i0 + 1] * a * (1 - b) + F[j0 + 1, i0] * (1 - a) * b + F[j0 + 1, i0 + 1] * a * b

    # 1. the spot of the bun
    gs = S0 + (np.arange(W) + 0.5) * G; gt = (np.arange(H) + 0.5) * G
    ds, dt = np.meshgrid(gs, gt - tb); r = np.maximum(np.hypot(ds, dt), 1e-5)
    inside = r < R1 + 0.003
    f = np.where(inside, (2 * (R1 + 0.003) - r) / r, 1.0)
    F1 = np.where(inside, sample(flat, ds * f, tb + dt * f), flat)                    # mirrored at the edge
    up = sample(F1, ds, tb - np.abs(dt))                                               # the upper half, upside down
    F2 = F1 + (up - F1) * (dt > 0) * smooth(R1 + 0.018, R1 + 0.005, r)
    ring = (r > R1 + 0.015) & (r < R1 + 0.045) & (dt < 0) & (np.abs(ds) < 0.05)
    level = float(np.median(F2[ring]))                                                 # no dark halo where the bun sat
    F2 = F2 * (1 + (np.clip(level / np.maximum(blur(F2, 28), 1e-3), 0.5, 3.0) - 1) * smooth(R1 + 0.040, R1 + 0.012, r))
    # 2. everything a bit further up
    w = smooth(0.0, 0.03, k) * head
    spot = smooth(R1 + 0.045, R1 + 0.030, np.hypot(s, t - tb)) * head                 # the repaired spot shows even where nothing moves
    w = np.maximum(w, spot)
    res = hlum * (1 - w) + sample(F2, s, t + (tb - tr) * k) * w
    # 3. The hair around the bun was photographed in its shadow: bring it to the brightness of the hair above
    ref = head & (m["hair"] > 0.9) & (np.abs(s) < 0.05) & (t > tr - 0.075) & (t < tr - 0.035)
    level = float(np.median(hlum[ref])); sigma = float((hlum - blurf(hlum, 3))[ref].std()) / level
    res = res * (1 + (np.clip(level / np.maximum(blurf(res, 22), 1e-3), 0.6, 2.5) - 1) * 0.8 * smooth(0.0, 0.25, k))
    # 4. Fine strands are drawn over the photo hair where it does not run to the braid after all that:
    #   - right around the start of the braid, as a part of the picture only and in patches. Wide rays all the way
    #     round look like a star, which hair never does;
    #   - below the start of the braid, down to the nape and behind the ears, nearly all of the picture. That hair
    #     is the little there was under the bun, stretched to several times its length: flat, with stray lights
    #     running anywhere. Those are taken out (only light and dark of the area stay) and strands drawn instead.
    # They do not run dead straight to one point: their direction wanders with the place.
    rr = np.hypot(s, t - tr); near = head & ((rr < 0.07) | (k > 0.001))
    pn = pos[near]; r_ = rr[near]
    # (by a few millimetres sideways at any distance: hair pulled into a braid is taut, not wavy)
    bend = np.minimum(0.30, 0.005 / np.maximum(r_, 0.01))
    phi = np.arctan2(t - tr, s)[near] + bend * (sine_noise(pn, 45.0, 21, 6, (0.6, 1.6)) + 0.3 * sine_noise(pn, 140.0, 22, 6))
    rng = np.random.default_rng(8); n = np.zeros(r_.shape); tot = np.zeros(r_.shape)
    for mm in np.unique(np.round(np.exp(rng.uniform(math.log(22), math.log(420), 90))).astype(int)):
        fade = smooth(1300.0, 650.0, mm / (2 * math.pi * np.maximum(r_, 1e-3)))        # no strands thinner than the texels
        amp = mm ** -0.2 * fade
        n += amp * np.sin(mm * phi + rng.uniform(0, 6.283) + rng.uniform(0.4, 1.4) * np.sin(r_ * rng.uniform(25, 70) + rng.uniform(0, 6.283)))
        tot += amp ** 2 / 2
    n /= np.sqrt(np.maximum(tot, 1e-6))
    below = (smooth(tr - 0.006, tr + 0.022, t) * smooth(0.0, 0.10, k))[near] * 0.9
    local = np.maximum(blurf(res, 6), 1e-3)[near]                                      # light and dark of the photo stay
    drawn = local * np.clip(1 + (1.1 + 0.5 * below) * sigma * n, 0.4, 1.9)
    patchy = 0.25 + 0.30 * smooth(-0.8, 0.8, sine_noise(pn, 70.0, 23, 8, (0.6, 1.6)))
    wd = np.maximum(smooth(0.062, 0.028, r_) * patchy, below)
    res[near] = res[near] * (1 - wd) + drawn * wd
    return res


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
    # (the photo is of dark hair: its darkest strands stay dark in any colour, so light hair keeps less of them)
    # and those it keeps fade in softly and turn warmer instead of grey)
    def recolour(l, floor=0.15 + 0.42 * light):
        rel = l / max(hmean, 1e-3); top = 1.6 - 0.45 * light
        soft = np.where(rel < 1, floor + (1 - floor) * np.clip(rel, 0, 1) ** 0.8, np.minimum(rel, top))
        rel = np.clip(rel, floor, top) * (1 - light) + soft * light
        warm = 1 + light * np.array([-0.10, 0.0, 0.20])
        return np.minimum(ht * rel[..., None] ** ((0.80 - 0.30 * light) * warm), 0.94)
    if braid: hlum = hair_to_braid(m, hlum)              # the hair runs to the start of the braid, not to the bun
    out = lerp(out, np.clip(recolour(hlum), 0, 1), hair)
    if braid:                                            # the braid's hair goes where the bun's texture was
        strips, tie = braidlib.textures()
        for (x0, x1, y0, y1), row in strips:
            # on dark hair only the highlights of the head reach the hair colour: the braid is as dark as the rest
            c = np.clip(recolour(row * hmean * (0.62 + 0.38 * light), floor=0.2), 0, 1)
            out[y0:y1, x0:x1] = c
            out[y0 - 3:y0, x0:x1] = c[-3:]; out[y1:y1 + 3, x0:x1] = c[:3]          # the strip closes around the strand
            out[y0 - 3:y1 + 3, x0 - 3:x0] = out[y0 - 3:y1 + 3, x0:x0 + 1]; out[y0 - 3:y1 + 3, x1:x1 + 3] = out[y0 - 3:y1 + 3, x1 - 1:x1]
        x0, x1, y0, y1 = tie
        out[y0 - 3:y1 + 3, x0 - 3:x1 + 3] = np.array([0.050, 0.046, 0.050]) + np.random.default_rng(2).normal(0, 0.006, (y1 - y0 + 6, x1 - x0 + 6, 1))
    # --- brows follow the hair (never lighter than a mid brown), lashes stay dark
    bc = np.minimum(ht * 0.75, np.array([0.30, 0.20, 0.13])) + 0.015
    out = lerp(out, np.broadcast_to(bc, out.shape) * (0.75 + 0.5 * (lum / np.maximum(blur(lum, 9), 1e-3))[..., None]).clip(0, 1.5), np.clip(m["brows"] * 0.9, 0, 1))
    # --- iris
    # --- iris: the photographed iris keeps its brightness and structure, only its tint changes
    tint, bright = ch["eyes"]
    ic = lum[..., None] * np.array(tint)[None, None, :] * bright
    out = lerp(out, np.clip(ic, 0, 1), m["iris"] * 0.92)
    # the skin at the lower edge, where the neck meets the body: the arms get this tone
    edge = m["cov"] & (y < 0.575) & (skin > 0.9) & (hair < 0.05)
    neck = out[edge].mean(0)
    if tactical:                                         # the Timberwolf face paint, laid over the new face
        a, paint = paint_layer(m)
        out = lerp(out, paint, a * (1 - hair))
    return np.clip(out, 0, 1), (neck, g)


def hands_texture(ch, skinfit):
    neck, g = skinfit
    h = np.asarray(Image.open(os.path.join(REF, "tex", f"hands_0{ch['base']}.png")).convert("RGB"), dtype=np.float64) / 255
    hm = h.reshape(-1, 3); hm = hm[hm.sum(1) > 0.6].mean(0)              # skin mean (ignore dark background)
    return np.clip(neck * np.clip(h / hm, 0, 3) ** g, 0, 1)


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


_SRC = []


def write_model(ch, braid=False):
    if not _SRC: _SRC.append(bytes(shadow.fix(open(SRC_P3D, "rb").read(), verbose=True)))
    b, lods = mlod.read_bytes(_SRC[0])
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
# arms and legs: the same shader and settings as the face, so they have the same tone where they meet
# (the game's own material for them is the "Skin" shader, which turns the same texture clearly more orange)
RVMAT_HL = RVMAT.replace("m_ti_ca.paa", "hl_ti_ca.paa").replace("A3_female_heads\\Models\\xxx_nohq.paa", "a3\\characters_f\\heads\\data\\hl_muscular_nohq.paa") \
    .replace("A3_female_heads\\Models\\xxx_as.paa", "a3\\characters_f\\heads\\data\\hl_muscular_as.paa")
assert RVMAT_HL.count("hl_") == 3


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
            # the face worn instead while the headgear leaves no room for the braid (addons/hair)
            bun = f'            mhfh_bunFace = "mhfh_{c["id"]}{"_tac" if tac else ""}";\n' if v else ""
            faces += f'''        class {cls}: B_female_bun_01 {{
            author = "Miss Heda";
            displayName = "{c["name"]}{" (" + label + ")" if label else ""}";
            head = "mhfh_{c["id"]}{v}";
            texture = "{D}{cls}_co.paa";
            material = "{D}mhfh_face.rvmat";
            materialWounded1 = "{D}mhfh_face.rvmat";
            materialWounded2 = "{D}mhfh_face.rvmat";
            textureHL = "{D}mhfh_{c["id"]}_hl_co.paa";
            materialHL = "{D}mhfh_hl.rvmat";
            textureHL2 = "{D}mhfh_{c["id"]}_hl_co.paa";
            materialHL2 = "{D}mhfh_hl.rvmat";
{bun}        }};
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
    open(os.path.join(DATA, "mhfh_hl.rvmat"), "w", newline="\n").write(RVMAT_HL)
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
