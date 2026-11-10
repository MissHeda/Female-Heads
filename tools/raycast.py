"""Ray casting against triangle meshes (numpy), used to keep the head inside the vanilla head, to shape the neck
base like the reference head and to measure helmet clipping.
All points are Arma model space (x, height, depth; the face looks along -z)."""
import numpy as np

CENTRE = np.array([0.0, 0.70, -0.015])


def hits(dirs, P, F, chunk=400, origins=None):
    """distances along unit rays to every triangle hit: returns (nearest, farthest), nan where nothing is hit.
    Rays start at CENTRE, or at origins[i] when given."""
    A = P[F[:, 0]]; e1 = P[F[:, 1]] - A; e2 = P[F[:, 2]] - A
    near = np.full(len(dirs), np.nan); far = np.full(len(dirs), np.nan)
    for s in range(0, len(dirs), chunk):
        d = dirs[s:s + chunk][:, None, :]                       # (n,1,3)
        o = (origins[s:s + chunk][:, None, :] if origins is not None else CENTRE[None, None, :])
        h = np.cross(d, e2[None]); det = (e1[None] * h).sum(-1)
        ok = np.abs(det) > 1e-12; inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        t0 = o - A[None]
        u = (t0 * h).sum(-1) * inv
        q = np.cross(t0, e1[None]); v = (d * q).sum(-1) * inv
        t = (e2[None] * q).sum(-1) * inv
        m = ok & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6) & (t > 1e-4)
        any_ = m.any(1)
        near[s:s + chunk] = np.where(any_, np.min(np.where(m, t, np.inf), 1), np.nan)
        far[s:s + chunk] = np.where(any_, np.max(np.where(m, t, -np.inf), 1), np.nan)
    return near, far


def radial(points):
    d = points - CENTRE; r = np.linalg.norm(d, axis=1)
    return d / r[:, None], r


def surface_samples(P, F, n=4):
    """points spread over every triangle: returns (samples, triangle index, barycentric coordinates)"""
    bc = np.array([(i, j, n - i - j) for i in range(n + 1) for j in range(n + 1 - i)], dtype=np.float64) / n
    S = (bc[None, :, 0, None] * P[F[:, 0]][:, None] + bc[None, :, 1, None] * P[F[:, 1]][:, None] + bc[None, :, 2, None] * P[F[:, 2]][:, None])
    tri = np.repeat(np.arange(len(F)), len(bc)); bary = np.tile(bc, (len(F), 1))
    return S.reshape(-1, 3), tri, bary


def nearest(Q, S, chunk=200):
    """index of the nearest sample for every query point"""
    out = np.zeros(len(Q), dtype=np.int64)
    for s in range(0, len(Q), chunk):
        d = ((Q[s:s + chunk][:, None, :] - S[None]) ** 2).sum(-1)
        out[s:s + chunk] = d.argmin(1)
    return out
