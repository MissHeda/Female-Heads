"""Texel masks for the Timberwolf head UV layout (shared by its face textures): which texels are skin, hair,
brows, lips, iris, bun... Built from the reference head (tools/ref_tftw.py): the mesh gives every texel its
position on the head, the two base textures give the hairline.
"""
import os
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref")
N = 1024


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def blur(a, r):
    return np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), dtype=np.float64) / 255


def load(name):
    return np.asarray(Image.open(os.path.join(REF, "tex", name + ".png")).convert("RGB").resize((N, N), Image.LANCZOS), dtype=np.float64) / 255


def raster():
    """per texel: position on the head (arma space), covered mask, eye mask"""
    d = np.load(os.path.join(REF, "models", "tftw_head.npz"))
    P, F, uv, eye = d["P"], d["F"], d["uv"], d["eye"]
    pos = np.zeros((N, N, 3)); cov = np.zeros((N, N), bool); iseye = np.zeros((N, N), bool)
    px = uv * N
    for f in F:
        a, b, c = px[f]
        x0, x1 = int(max(np.floor(min(a[0], b[0], c[0])) - 1, 0)), int(min(np.ceil(max(a[0], b[0], c[0])) + 1, N - 1))
        y0, y1 = int(max(np.floor(min(a[1], b[1], c[1])) - 1, 0)), int(min(np.ceil(max(a[1], b[1], c[1])) + 1, N - 1))
        if x1 < x0 or y1 < y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12: continue
        w0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / den
        w1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / den
        w2 = 1 - w0 - w1
        m = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
        if not m.any(): continue
        sub = pos[y0:y1 + 1, x0:x1 + 1]
        sub[m] = w0[m][:, None] * P[f[0]] + w1[m][:, None] * P[f[1]] + w2[m][:, None] * P[f[2]]
        cov[y0:y1 + 1, x0:x1 + 1] |= m
        if eye[f].all(): iseye[y0:y1 + 1, x0:x1 + 1] |= m
    return pos, cov, iseye


def build(base):
    """base: 'face_01' (dark hair) or 'face_03' (blonde). Returns dict of soft masks (0..1) in the 1024 atlas."""
    pos, cov, iseye = raster()
    tex = load(base)
    lum = tex @ np.array([0.30, 0.59, 0.11]); r, g, b = tex[..., 0], tex[..., 1], tex[..., 2]
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    vv, uu = np.mgrid[0:N, 0:N] / N
    mouth = (uu > 0.655) & (vv < 0.215) & ~iseye                      # teeth, tongue, mouth lining
    bun = cov & (z > 0.078) & (y > 0.615) & (y < 0.715) & (np.abs(x) < 0.046)
    # skin colour: clearly red-over-blue and not dark; hair is either dark (Carter) or pale and grey (Medrano)
    sat = (r - b) / np.maximum(r + g + b, 1e-3)
    def split(t):
        l_ = t @ np.array([0.30, 0.59, 0.11]); s_ = (t[..., 0] - t[..., 2]) / np.maximum(t.sum(-1), 1e-3)
        return smooth(0.35, 0.65, blur(smooth(0.20, 0.30, l_) * smooth(0.06, 0.10, s_), 2.0))
    # Every character wears the hair of the dark-haired face: it is the one whose hair can be cut out cleanly
    # (dark hair on light skin), with its soft photographed hairline. The hair itself is taken from that texture.
    hairtex = tex if base == "face_01" else load("face_01")
    hairlum = hairtex @ np.array([0.30, 0.59, 0.11])
    skinc = split(hairtex)
    region = cov & ~mouth & ~iseye & ~bun
    if base != "face_01":
        # This face has its own (blonde) hair, with a different hairline. Wherever the result shows skin, the
        # texture must be skin: keep what clearly is skin (reddish and smooth) and fill the rest from around it.
        detail = blur(np.abs(lum - blur(lum, 2.0)), 5.0)
        own = blur(smooth(0.105, 0.135, sat) * smooth(0.020, 0.011, detail) * smooth(0.18, 0.28, lum), 4.0)
        ax0 = np.abs(x)
        face0 = smooth(-0.070, -0.088, z) * smooth(0.595, 0.610, y) * smooth(0.752, 0.738, y) * smooth(0.066, 0.054, ax0) * cov
        known = ((own > 0.80) | (face0 > 0.5)) & region
        filled = tex.copy(); done = known.copy()
        for rad in (2, 4, 8, 16, 32, 64):
            k = blur(known.astype(float), rad)
            est = np.stack([blur(tex[..., i] * known, rad) for i in range(3)], -1) / np.maximum(k, 1e-3)[..., None]
            take = ~done & (k > 0.03)
            filled[take] = est[take]; done |= take
        grain = np.random.default_rng(3).normal(0, 0.006, (N, N, 1))
        soft = smooth(0.80, 0.45, blur(own, 3)) * (1 - face0)          # 1 where this texture is not clearly skin
        tex = tex * (1 - soft[..., None]) + np.clip(filled + grain, 0, 1) * soft[..., None]
        tex = np.where((region & (skinc > 0.02))[..., None], tex, load(base))
        lum = tex @ np.array([0.30, 0.59, 0.11]); r, g, b = tex[..., 0], tex[..., 1], tex[..., 2]
    # The middle of the face is never hair: lashes, nostrils and the line between the lips are dark, but not hair.
    ax_ = np.abs(x)
    faceint = smooth(-0.078, -0.090, z) * smooth(0.598, 0.610, y) * smooth(0.748, 0.736, y) * smooth(0.064, 0.054, ax_) * cov
    skin = skinc * region
    hair = (1 - skinc) * region * (1 - faceint)
    skin = np.maximum(skin, faceint)                     # ... they change with the skin around them
    hair = hair * smooth(0.30, 0.16, hairlum)             # a light pixel at the hairline is skin showing through
    hair = np.maximum(hair, bun.astype(float))
    patch_ = (vv > 0.775) & (uu < 0.30) & ~bun & ~(cov & (y < 0.57) & (z < 0.03))       # hair patch, not the chest corner next to it
    hair = np.where(patch_, 1.0, hair); skin = np.where(patch_, 0.0, skin)
    hair = np.where(~cov & ~mouth & ~iseye, 1 - skinc, hair)            # padding around the islands follows its colour
    skin = np.where(~cov & ~mouth & ~iseye, skinc, skin)
    front = z < -0.060
    # brows: dark hairs on the skin above the eyes
    eyeh = 0.705
    brow_zone = front & (y > eyeh + 0.010) & (y < eyeh + 0.034) & (np.abs(x) > 0.006) & (np.abs(x) < 0.062)
    local = blur(lum, 9)
    brows = smooth(0.03, 0.10, local - lum) * brow_zone * skin
    brows = blur(brows, 1.2)
    # lashes / closed eye line
    lash_zone = front & (np.abs(y - (eyeh - 0.004)) < 0.012) & (np.abs(np.abs(x) - 0.0325) < 0.024)
    lashes = blur(smooth(0.05, 0.14, local - lum) * lash_zone * skin, 1.0)
    # lips
    lips_zone = front & (np.abs(x) < 0.030) & (y > 0.615) & (y < 0.658)
    redness = (r - g) / np.maximum(lum, 1e-3)
    lips = blur(smooth(0.36, 0.52, redness) * lips_zone * skin, 2.0)
    # iris: inside the eye island, around its darkest spot (the pupil)
    ys, xs = np.nonzero(iseye)
    iris = np.zeros((N, N))
    if len(ys):
        sub = blur(lum, 4) + (~iseye) * 9
        cy, cx = np.unravel_index(np.argmin(sub), sub.shape)
        rr = np.hypot(vv * N - cy, uu * N - cx)
        irad = 0.036 * N
        iris = smooth(irad, irad * 0.86, rr) * smooth(irad * 0.26, irad * 0.36, rr) * iseye
    return dict(tex=tex, orig=load(base), hairtex=hairtex, hairlum=hairlum, pos=pos, cov=cov, eye=iseye, mouth=mouth, bun=bun,
                skin=np.clip(skin, 0, 1), hair=np.clip(hair, 0, 1), brows=brows, lashes=lashes, lips=lips, iris=iris, lum=lum)


if __name__ == "__main__":
    out = os.path.join(HERE, "out"); os.makedirs(out, exist_ok=True)
    for base in ("face_01", "face_03"):
        m = build(base)
        vis = m["tex"] * 0.35
        vis[..., 0] += 0.65 * m["hair"]; vis[..., 1] += 0.65 * m["skin"] * (1 - m["lips"]); vis[..., 2] += 0.9 * np.maximum(m["brows"], np.maximum(m["iris"], m["lips"]))
        Image.fromarray((np.clip(vis, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out, f"_mask_{base}.png"))
        print(base, {k: round(float(v.mean()), 3) for k, v in m.items() if k in ("skin", "hair", "brows", "lips", "iris", "lashes")})
    a = Image.open(os.path.join(out, "_mask_face_01.png")); b = Image.open(os.path.join(out, "_mask_face_03.png"))
    s = Image.new("RGB", (2048, 1024)); s.paste(a, (0, 0)); s.paste(b, (1024, 0)); s.save(os.path.join(out, "_masks.png"))
