"""Ray casting from the head centre against triangle meshes (numpy), used to keep the head inside the vanilla head
and to measure helmet clipping. All points are Arma model space (x, height, depth; the face looks along -z)."""
import numpy as np

CENTRE = np.array([0.0, 0.70, -0.015])


def hits(dirs, P, F, chunk=400):
    """distances along unit rays from CENTRE to every triangle hit: returns (nearest, farthest), nan where nothing is hit"""
    a = P[F[:, 0]] - CENTRE; e1 = P[F[:, 1]] - P[F[:, 0]]; e2 = P[F[:, 2]] - P[F[:, 0]]
    near = np.full(len(dirs), np.nan); far = np.full(len(dirs), np.nan)
    for s in range(0, len(dirs), chunk):
        d = dirs[s:s + chunk][:, None, :]                       # (n,1,3)
        h = np.cross(d, e2[None]); det = (e1[None] * h).sum(-1)
        ok = np.abs(det) > 1e-12; inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        t0 = -a[None]                                           # ray origin (0) minus triangle corner
        u = (t0 * h).sum(-1) * inv
        q = np.cross(t0, e1[None]); v = (d * q).sum(-1) * inv
        t = (e2[None] * q).sum(-1) * inv
        m = ok & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6) & (t > 1e-4)
        tt = np.where(m, t, np.nan)
        any_ = m.any(1)
        near[s:s + chunk] = np.where(any_, np.nanmin(np.where(m, t, np.inf), 1), np.nan)
        far[s:s + chunk] = np.where(any_, np.nanmax(np.where(m, t, -np.inf), 1), np.nan)
    return near, far


def radial(points):
    d = points - CENTRE; r = np.linalg.norm(d, axis=1)
    return d / r[:, None], r
