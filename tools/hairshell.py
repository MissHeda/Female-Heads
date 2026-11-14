"""Hair with volume: a layer of hair over the skull instead of hair that is only painted on it.

The Timberwolf head has its hair as a picture on the bare skull, which shows as soon as something with real
depth (a braid) lies on it. shell() builds the hair as its own surface: the part of the skull that carries hair,
made four times as fine, lifted off the skull by the thickness hair has there (nothing at the hairline, most
over the top and back of the head) and shaped into the shallow ridges of strands combed back. It keeps the UVs of
the skull, so it shows the same hair picture, and it is closed all round because it comes down to the skin at
the hairline. The skull faces it covers completely are reported so they can be dropped.

Headgear is made for the bare skull: this layer goes through it. It is for styles that change to the bun under
any headgear.
"""
import math
import numpy as np

THICK = 0.0090          # the layer over the skull, away from the hairline
TOP = 0.0040            # more of it over the top of the head
RIDGE = 0.0034          # height of the strand ridges
BONES = ("Head", "Neck", "Neck1", "Spine3", "LeftShoulder", "RightShoulder")


def _smooth(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def _sample(img, uv):
    n = img.shape[0]
    x = np.clip(uv[..., 0] * n - 0.5, 0, n - 1.001); y = np.clip(uv[..., 1] * n - 0.5, 0, n - 1.001)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); a = x - x0; b = y - y0
    return img[y0, x0] * (1 - a) * (1 - b) + img[y0, x0 + 1] * a * (1 - b) + img[y0 + 1, x0] * (1 - a) * b + img[y0 + 1, x0 + 1] * a * b


def _lift(p, hair, seed):
    """how far a point of the layer stands off the skull. hair: 0 at the hairline .. 1 well inside the hair"""
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    inside = _smooth(0.0, 1.0, hair)
    h = (THICK + TOP * _smooth(0.735, 0.790, y)) * inside ** 0.7
    # strands combed back: they run from the front hairline over the top and along the sides to the back of the
    # head, so across them the surface goes up and down. Seen from the front that is the angle around the head.
    ang = np.arctan2(x, y - 0.700)
    r = np.random.default_rng(seed); ridges = np.zeros(h.shape)
    for k in (7, 11, 16, 23):
        ridges += (1.0 / k ** 0.5) * np.sin(k * ang + r.uniform(0, 6.283) + 0.6 * np.sin(z * r.uniform(30, 60) + r.uniform(0, 6.283)))
    return h + RIDGE * 0.9 * ridges / 1.2 * inside * _smooth(-0.02, 0.01, z)      # the ridges fade towards the front hairline


def shell(L, hair_soft, seed=3):
    """L: the first LOD of the head (mlod.Lod), hair_soft: (n, n) blurred hair mask of the face atlas.
    -> points, inward normals, faces [[(point, normal, u, v) x3]], weights [{bone: weight}], covered (nfaces bool)"""
    P = L.points; bun = L.selections["Bun"][0] > 0 if "Bun" in L.selections else np.zeros(L.npoints, bool)
    # triangles of the skull with their corner UVs
    T = []; U = []; F = []
    for f in range(L.nfaces):
        n = int(L.face_n[f]); v = L.face_v[f, :n]; uv = L.face_uv[f, :n]
        for a, b, c in (((0, 1, 2),) if n == 3 else ((0, 1, 2), (0, 2, 3))):
            T.append((int(v[a]), int(v[b]), int(v[c]))); U.append((uv[a], uv[b], uv[c])); F.append(f)
    T = np.array(T); U = np.array(U, dtype=np.float64); F = np.array(F)
    # hair at every point: 0 at the hairline and outside, 1 inside
    val = np.zeros(L.npoints); cnt = np.zeros(L.npoints)
    s = _sample(hair_soft, U)
    for k in range(3): np.add.at(val, T[:, k], s[:, k]); np.add.at(cnt, T[:, k], 1)
    val = _smooth(0.72, 1.0, val / np.maximum(cnt, 1)); val[bun] = 0
    # The layer may only rise where the picture shows hair. A point lifts the faces around it, so it only counts as
    # hair as far as all its neighbours do: the rise then lies inside the hair, and skin at the hairline and in the
    # parting stays on the skull.
    near = val.copy()
    for a, b in ((0, 1), (1, 2), (2, 0)):
        np.minimum.at(near, T[:, a], val[T[:, b]]); np.minimum.at(near, T[:, b], val[T[:, a]])
    val = near
    take = (val[T] > 0).any(1) & ~bun[T].any(1)
    # outward direction at every point (MLOD: cross(p1-p0, p2-p0) points inwards)
    out = np.zeros((L.npoints, 3)); fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    for k in range(3): np.add.at(out, T[:, k], -fn)
    out /= np.maximum(np.linalg.norm(out, axis=1), 1e-12)[:, None]
    # every triangle becomes four; the points in the middle of the edges are shared
    pts = {}; base = []; dirs = []; hairv = []; wsrc = []
    def point(i):
        if ("v", i) not in pts:
            pts[("v", i)] = len(base); base.append(P[i]); dirs.append(out[i]); hairv.append(val[i]); wsrc.append((i, i))
        return pts[("v", i)]
    def mid(i, j, uv):
        key = ("e", min(i, j), max(i, j))
        if key not in pts:
            d = out[i] + out[j]; d /= max(np.linalg.norm(d), 1e-12)
            hv = 0.0 if (val[i] == 0 or val[j] == 0) else (val[i] + val[j]) / 2
            pts[key] = len(base); base.append((P[i] + P[j]) / 2); dirs.append(d); hairv.append(hv); wsrc.append((i, j))
        return pts[key]
    faces = []
    for t, uv in zip(T[take], U[take]):
        a, b, c = (point(int(i)) for i in t); ua, ub, uc = uv
        ab = mid(int(t[0]), int(t[1]), (ua + ub) / 2); bc = mid(int(t[1]), int(t[2]), (ub + uc) / 2); ca = mid(int(t[2]), int(t[0]), (uc + ua) / 2)
        uab, ubc, uca = (ua + ub) / 2, (ub + uc) / 2, (uc + ua) / 2
        for tri in (((a, ua), (ab, uab), (ca, uca)), ((ab, uab), (b, ub), (bc, ubc)), ((ca, uca), (bc, ubc), (c, uc)), ((ab, uab), (bc, ubc), (ca, uca))):
            faces.append([(i, i, float(u[0]), float(u[1])) for i, u in tri])
    base = np.array(base); dirs = np.array(dirs); hairv = np.array(hairv)
    Q = base + dirs * np.maximum(_lift(base, hairv, seed), 0.0)[:, None] * (hairv > 0)[:, None]
    # smooth normals of the layer (stored pointing inwards, like the rest of the file)
    N = np.zeros_like(Q); I = np.array([[c[0] for c in f] for f in faces])
    fnq = np.cross(Q[I[:, 1]] - Q[I[:, 0]], Q[I[:, 2]] - Q[I[:, 0]])
    for k in range(3): np.add.at(N, I[:, k], fnq)
    N /= np.maximum(np.linalg.norm(N, axis=1), 1e-12)[:, None]
    # bone weights of the skull below
    sel = {b: L.selections[b][0] for b in list(BONES) + [n for n in L.selections if n.startswith("Face_")] if b in L.selections}
    weights = []
    for i, j in wsrc:
        w = {b: float(pw[i] + pw[j]) / 2 for b, pw in sel.items() if pw[i] + pw[j] > 0.008}
        tot = sum(w.values()) or 1.0
        weights.append({b: v / tot for b, v in w.items()} if w else {"Head": 1.0})
    # skull faces that lie completely under a good layer of hair are not seen any more
    deep = np.zeros(L.npoints, bool); deep[val > 0.75] = True
    covered = np.zeros(L.nfaces, bool)
    for f in range(L.nfaces):
        v = L.face_v[f, :int(L.face_n[f])]; covered[f] = bool(deep[v].all())
    return Q, N, faces, weights, covered
