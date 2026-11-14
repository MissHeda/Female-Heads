"""Repairs for the shadow volumes of the Timberwolf head (LOD 10000 and the one for first person), which cause dark
streaks on the neck in game.

Three things are wrong with it:
  - three triangles exist twice, back to back (below both ears and at the chin). Such a fin has no volume and
    throws a thin streak of shadow;
  - below the jaw its points are weighted to other bones than the visible surface next to them, so the volume
    comes through the neck as soon as the head turns;
  - some of its points lie outside the visible surface (most of them at the lower edge on the chest).
fix() removes the fins, copies the bone weights of the nearest visible point for everything below the jaw and
moves every point that is not clearly inside the head to a few millimetres below the surface.
"""
import os, sys
from collections import defaultdict
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mlod

INSET = 0.004           # depth below the visible surface a shadow point is moved to
REWEIGHT_BELOW = 0.625  # height below which the weights of the visible surface are taken over


def _closest(p, A, B, C):
    """closest point on any of the triangles A, B, C (n,3) to p -> (triangle index, point)"""
    ab = B - A; ac = C - A; ap = p - A
    d1 = (ab * ap).sum(1); d2 = (ac * ap).sum(1)
    bp = p - B; d3 = (ab * bp).sum(1); d4 = (ac * bp).sum(1)
    cp = p - C; d5 = (ab * cp).sum(1); d6 = (ac * cp).sum(1)
    va = d3 * d6 - d5 * d4; vb = d5 * d2 - d1 * d6; vc = d1 * d4 - d3 * d2
    den = va + vb + vc; den = np.where(np.abs(den) < 1e-18, 1e-18, den)
    Q = A + ab * (vb / den)[:, None] + ac * (vc / den)[:, None]
    nz = lambda a: np.where(np.abs(a) < 1e-18, 1e-18, a)
    m = (vc <= 0) & (d1 >= 0) & (d3 <= 0); Q[m] = (A + ab * (d1 / nz(d1 - d3))[:, None])[m]
    m = (vb <= 0) & (d2 >= 0) & (d6 <= 0); Q[m] = (A + ac * (d2 / nz(d2 - d6))[:, None])[m]
    m = (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0); Q[m] = (B + (C - B) * ((d4 - d3) / nz((d4 - d3) + (d5 - d6)))[:, None])[m]
    m = (d1 <= 0) & (d2 <= 0); Q[m] = A[m]
    m = (d3 >= 0) & (d4 <= d3); Q[m] = B[m]
    m = (d6 >= 0) & (d5 <= d6); Q[m] = C[m]
    i = int(np.argmin(np.linalg.norm(Q - p, axis=1)))
    return i, Q[i]


def _winding(Q, A, B, C):
    """generalised winding number of the points Q in the triangle soup (works with the open neck)"""
    a = A[None] - Q[:, None]; b = B[None] - Q[:, None]; c = C[None] - Q[:, None]
    la, lb, lc = np.linalg.norm(a, axis=2), np.linalg.norm(b, axis=2), np.linalg.norm(c, axis=2)
    num = (a * np.cross(b, c)).sum(2)
    den = la * lb * lc + (a * b).sum(2) * lc + (b * c).sum(2) * la + (c * a).sum(2) * lb
    return (2 * np.arctan2(num, den)).sum(1) / (4 * np.pi)


def is_shadow(L):
    """the shadow volume, and the one used for the own shadow in first person (resolution 1.9e16)"""
    return L.nfaces > 0 and (10000 <= L.res < 11000 or 1.85e16 < L.res < 1.95e16)


def fix(b, verbose=False):
    """b: MLOD bytes of the head -> copy with every shadow volume repaired"""
    _, lods = mlod.read_bytes(bytes(b))
    for index in [L.index for L in lods if is_shadow(L)]: b = _fix_lod(b, index, verbose)
    return b


def _fix_lod(b, index, verbose):
    b = bytearray(b); _, lods = mlod.read_bytes(bytes(b))
    V = lods[0]; S = lods[index]
    # --- weights and positions
    bun = V.selections["Bun"][0] > 0 if "Bun" in V.selections else np.zeros(V.npoints, bool)
    T, _f = mlod.triangles(V); T = T[~bun[T].any(1)]
    VP = V.points; A, B, C = VP[T[:, 0]], VP[T[:, 1]], VP[T[:, 2]]
    inward = np.cross(B - A, C - A); inward /= np.maximum(np.linalg.norm(inward, axis=1), 1e-12)[:, None]
    P = S.points.copy(); w = np.abs(_winding(P, A, B, C))
    near = np.zeros(S.npoints, np.int64); moved = 0
    for i, p in enumerate(P):
        t, q = _closest(p, A, B, C)
        near[i] = T[t][int(np.argmin(np.linalg.norm(VP[T[t]] - q, axis=1)))]
        depth = np.linalg.norm(p - q) * (1 if w[i] > 0.75 else -1)
        if depth < INSET and (w[i] < 0.75 or p[1] < 0.66):
            P[i] = q + inward[t] * INSET; moved += 1
    b = mlod.patch(b, lods, {S.index: P})
    low = S.points[:, 1] < REWEIGHT_BELOW
    vtags = {n: o for n, o, s in V.tags if s == V.npoints + V.nfaces}
    fv = S.face_v[:, :3]
    for name, off, size in S.tags:
        if size != S.npoints + S.nfaces or name.startswith("#"): continue
        pb = np.frombuffer(bytes(b[off:off + S.npoints]), np.uint8).copy()
        src = np.frombuffer(bytes(b[vtags[name]:vtags[name] + V.npoints]), np.uint8) if name in vtags else np.zeros(V.npoints, np.uint8)
        pb[low] = src[near[low]]
        b[off:off + S.npoints] = pb.tobytes()
        b[off + S.npoints:off + size] = (pb[fv] != 0).all(1).astype(np.uint8).tobytes()
    # --- fins: faces that exist twice with opposite winding
    seen = defaultdict(list)
    for f in range(S.nfaces): seen[tuple(sorted(int(v) for v in fv[f]))].append(f)
    keep = np.ones(S.nfaces, bool)
    for fs in seen.values():
        if len(fs) > 1: keep[fs] = False
    _, lods = mlod.read_bytes(bytes(b))
    b = mlod.rebuild(b, lods, faces={S.index: (keep, np.arange(S.npoints))})
    if verbose:
        _, lods = mlod.read_bytes(bytes(b)); S2 = lods[S.index]; edges = defaultdict(int)
        for f in S2.face_v[:, :3]:
            for k in range(3): edges[tuple(sorted((int(f[k]), int(f[(k + 1) % 3]))))] += 1
        print(f"shadow volume {S.res:g}: {int((~keep).sum())} fin faces removed, {moved} points moved inside, {int(low.sum())} points re-weighted;"
              f" {S2.npoints} points, {S2.nfaces} faces, edges not shared by two faces: {sum(1 for k in edges.values() if k != 2)}")
    return b


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref", "tftw", "unbin", "A3_female_heads - UB", "Models", "female_head_bun.p3d")
    fix(open(src, "rb").read(), verbose=True)
