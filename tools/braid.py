"""Hair worn instead of the Timberwolf bun: the parts of two styles that have depth.

  braid       a plaited braid from high on the back of the head, where the opening of a cap is, so it comes out
              through that opening and lies over the strap: gathered hair, a hair tie, three strands plaited around
              each other, a second hair tie and the loose end
  braidedbun  a bun wound from a twisted rope of hair, a spiral rising to its middle

Hair cannot move by itself in the game, so what hangs is shaped the way it would hang on someone standing
upright: it leaves the head pointing down, not out, stays close to head and neck and lies on the back. Where it
is gathered, the tie and the first centimetres belong to the head; the rest follows neck and upper spine, so it
stays on the back when the head turns instead of swinging out with it. The bun belongs to the head entirely.

mesh() builds the geometry (Arma model space: x, height, depth; the back of the head is +z), its UVs into the
atlas area the bun used, and bone weights. append() adds it to a LOD of an MLOD file (the bun faces are dropped
afterwards with mlod.rebuild). textures() gives the luminance of the hair for that atlas area.
"""
import math, os, struct
import numpy as np
import mlod

# centre lines (height, depth). The back of the head lies at depth 0.050 (height 0.80), 0.075 (0.76), 0.079 (0.73),
# 0.072 (0.69), 0.058 (0.66), the neck at 0.045 (0.62), the upper back at 0.072 (0.55).
STYLES = {
    # through the cap opening (height 0.705..0.740), over the strap below it (height 0.69..0.70, depth up to 0.084)
    "braid": dict(path=[(0.727, 0.058), (0.726, 0.072), (0.722, 0.084), (0.712, 0.095), (0.696, 0.103), (0.670, 0.103), (0.640, 0.099),
                        (0.610, 0.098), (0.582, 0.101), (0.560, 0.107), (0.540, 0.114), (0.521, 0.120)],
                  root=0.0265, w0=0.0230, w1=0.0150),
}
# where the buns sit: a point on the back of the head and the direction out of it (back and a little down)
BUN_AT = np.array([0.0, 0.668, 0.064]); BUN_OUT = np.array([0.0, -0.42, 0.91]) / math.hypot(0.42, 0.91)
TAIL = 0.048                     # length of the loose end after the lower tie
TIE = 0.010                      # length of a hair tie
PERIOD = 0.060                   # length over which one strand goes left, right and back, at half width 0.023
STEP = 0.0030                    # distance between two rings of a strand
SIDES = 9
# atlas areas in the old bun area of the 1024 atlas (pixels: x0, x1, y0, y1). A corner of the chest reaches into
# the top left of that area (up to x 811 at y 778, x 758 at y 834), so nothing of the hair lies there.
R_STRAND, R_PLAIN, R_TIE = (778, 1004, 842, 926), (778, 1004, 938, 992), (860, 1000, 796, 824)
MARGIN = 0.10                    # the strand strip holds this much more than one period


def _smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)


def _spline(pts, n=600):
    P = np.array([pts[0]] + list(pts) + [pts[-1]], dtype=np.float64); out = []
    for i in range(1, len(P) - 2):
        for t in np.linspace(0, 1, n // (len(P) - 3), endpoint=False):
            a = 2 * P[i]; b = P[i + 1] - P[i - 1]; c = 2 * P[i - 1] - 5 * P[i] + 4 * P[i + 1] - P[i + 2]; d = -P[i - 1] + 3 * P[i] - 3 * P[i + 1] + P[i + 2]
            out.append(0.5 * (a + b * t + c * t * t + d * t ** 3))
    out.append(P[-2]); return np.array(out)


class _Line:
    """the centre line by arc length: position, direction and the direction away from the body"""
    def __init__(s, path):
        C = _spline(path); s.arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]); s.C = C
        s.total = float(s.arc[-1])

    def at(s, l):
        l = min(max(l, 0.0), s.total); f = l / s.total
        y = np.interp(l, s.arc, s.C[:, 0]); z = np.interp(l, s.arc, s.C[:, 1])
        la, lb = max(l - 0.002, 0), min(l + 0.002, s.total)
        t = np.array([np.interp(lb, s.arc, s.C[:, 0]) - np.interp(la, s.arc, s.C[:, 0]), np.interp(lb, s.arc, s.C[:, 1]) - np.interp(la, s.arc, s.C[:, 1])])
        t /= np.linalg.norm(t)
        x = 0.0035 * math.sin(2.6 * f + 0.4) * _smooth(0.15, 0.6, f) - 0.0025 * _smooth(0.75, 1.0, f)   # it never hangs dead straight
        return np.array([x, y, z]), np.array([0.0, t[0], t[1]]), np.array([0.0, t[1], -t[0]])


def _weights(y, along=None):
    """along: distance from where the hair is tied, None for hair that belongs to the head entirely"""
    if along is None: return {"Head": 1.0}
    head = 1.0 - _smooth(0.012, 0.075, along); spine = min(_smooth(0.615, 0.570, y), 1 - head)
    w = {"Head": head, "Spine3": spine, "Neck": max(0.0, 1 - head - spine)}
    return {k: v for k, v in w.items() if v > 0.004}


class _Mesh:
    def __init__(s): s.P = []; s.N = []; s.W = []; s.F = []; s.cen = []; s.along = None       # along: see _weights

    def ring(s, c, eu, ev, ru, rv, sides):
        idx = []
        for j in range(sides):
            th = 2 * math.pi * j / sides
            p = c + ru * math.cos(th) * eu + rv * math.sin(th) * ev
            n = math.cos(th) / ru * eu + math.sin(th) / rv * ev; n /= np.linalg.norm(n)
            idx.append(len(s.P)); s.P.append(p); s.N.append(-n); s.W.append(_weights(float(p[1]), s.along)); s.cen.append(c)
        return idx

    def point(s, p, n, c):
        s.P.append(np.asarray(p, float)); s.N.append(-np.asarray(n, float)); s.W.append(_weights(float(p[1]), s.along)); s.cen.append(np.asarray(c, float))
        return len(s.P) - 1

    def band(s, r0, r1, rect, u0, u1, span=1.0):
        """quads between two rings; u0, u1: position of the rings along the strip (0..span)"""
        n = len(r0); x0, x1, y0, y1 = rect
        uv = lambda u, j: ((x0 + u / span * (x1 - x0)) / 1024.0, (y0 + j / n * (y1 - y0)) / 1024.0)
        for j in range(n):
            j2 = (j + 1) % n
            a = (r0[j], r0[j], *uv(u0, j)); b = (r0[j2], r0[j2], *uv(u0, j + 1)); c = (r1[j2], r1[j2], *uv(u1, j + 1)); d = (r1[j], r1[j], *uv(u1, j))
            s.F.append([a, b, c]); s.F.append([a, c, d])

    def fan(s, r, tip, rect, u0, u1, span=1.0):
        n = len(r); x0, x1, y0, y1 = rect
        uv = lambda u, j: ((x0 + u / span * (x1 - x0)) / 1024.0, (y0 + j / n * (y1 - y0)) / 1024.0)
        for j in range(n):
            j2 = (j + 1) % n
            s.F.append([(r[j], r[j], *uv(u0, j)), (r[j2], r[j2], *uv(u0, j + 1)), (tip, tip, *uv(u1, j + 0.5))])

    def cap(s, r, c, axis, rect, u):
        """closes the end of a tube: a fan to its middle. axis points out of the tube. Without it the game shows
        the inside of the tube as a hole (faces are only drawn from outside)."""
        mid = s.point(c, axis, c - np.asarray(axis) * 0.004); n = len(r); x0, x1, y0, y1 = rect
        for j in range(n):
            j2 = (j + 1) % n; uu = (x0 + u * (x1 - x0)) / 1024.0
            s.F.append([(r[j], r[j], uu, (y0 + j / n * (y1 - y0)) / 1024.0), (r[j2], r[j2], uu, (y0 + (j + 1) / n * (y1 - y0)) / 1024.0),
                        (mid, mid, uu, (y0 + (j + 0.5) / n * (y1 - y0)) / 1024.0)])

    def result(s):
        P = np.array(s.P); N = np.array(s.N); cen = np.array(s.cen); out = []
        for f in s.F:                                                    # MLOD: cross(p1-p0, p2-p0) points inwards
            i0, i1, i2 = f[0][0], f[1][0], f[2][0]
            away = (P[i0] + P[i1] + P[i2]) / 3 - (cen[i0] + cen[i1] + cen[i2]) / 3
            out.append(f if np.dot(np.cross(P[i1] - P[i0], P[i2] - P[i0]), away) < 0 else [f[0], f[2], f[1]])
        return P, N, out, s.W


def mesh(style="braid"):
    """-> points (n,3), inward normals (n,3), faces [[(point, normal, u, v) x3]], weights [{bone: weight}]"""
    if style in BUNS: return BUNS[style]()
    S = STYLES[style]; line = _Line(S["path"]); m = _Mesh(); X = np.array([1.0, 0.0, 0.0]); root = S["root"]

    def tube(l0, l1, n, ru, rv, rect, sides=12, u=(0.0, 1.0)):
        rings = []
        for k in range(n):
            f = k / (n - 1); l = l0 + (l1 - l0) * f
            c, t, no = line.at(l); m.along = max(0.0, l - root)
            rings.append(m.ring(c, X, no, ru(f), rv(f), sides))
            if k: m.band(rings[-2], rings[-1], rect, u[0] + (u[1] - u[0]) * (k - 1) / (n - 1), u[0] + (u[1] - u[0]) * f)
        return rings

    def tie(l, r):
        """a hair tie: a short sleeve, its rims pulled into the hair, closed at both ends"""
        rings = []
        m.along = max(0.0, l - root)
        for k, (o, sc) in enumerate(((-0.5, 0.88), (-0.30, 1.08), (0.30, 1.08), (0.5, 0.88))):
            c, t, no = line.at(l + o * TIE)
            rings.append(m.ring(c, X, no, r * sc, r * sc * 0.86, 12))
            if k: m.band(rings[-2], rings[-1], R_TIE, k - 1.0, float(k), span=3.0)
        c, t, no = line.at(l - 0.5 * TIE); m.cap(rings[0], c, -t, R_TIE, 0.5)
        c, t, no = line.at(l + 0.5 * TIE); m.cap(rings[-1], c, t, R_TIE, 0.5)

    if root is not None:
        # Gathered hair coming out of the head. All the hair of the head runs together here and lies on top of each
        # other, so it stands up from the head as a low mound (some 45 mm wide and 25 mm high where it leaves the
        # head) up to the tie. Flat at the head: it has to fit the opening of a cap.
        flat = 0.42
        mound = lambda f: 0.0300 - 0.0140 * _smooth(0.012, root, f * (root + 0.002)) ** 0.8
        rings = tube(0.0, root + 0.002, 10, mound, lambda f: (flat + (0.86 - flat) * f * f) * mound(f), R_PLAIN, sides=14, u=(0.0, 0.45))
        c, t, no = line.at(root + 0.002); m.cap(rings[-1], c, t, R_PLAIN, 0.45)
        tie(root, 0.0168)

    # three strands plaited around each other: seen from behind a strand comes in from one edge, crosses over the
    # middle, goes under the next strand and comes back from the other edge
    la = root + TIE * 0.5
    lb = line.total - TAIL - TIE * 0.5
    width = lambda l: S["w0"] + (S["w1"] - S["w0"]) * _smooth(la, lb, l) ** 0.8
    K = int(round((lb - la) / STEP)) + 1
    ls = np.linspace(la, lb, K); ph = np.zeros(K)
    for k in range(1, K): ph[k] = ph[k - 1] + 2 * math.pi * (ls[k] - ls[k - 1]) / (PERIOD * width(0.5 * (ls[k] + ls[k - 1])) / 0.023)

    def strand_pos(l, phi):
        c, t, no = line.at(l); w = width(l)
        env = _smooth(la - 0.002, la + 0.006, l) * _smooth(lb + 0.001, lb - 0.010, l)   # the strands come out of the ties
        return c + X * (0.50 * w * env * math.sin(phi)) + no * (-0.30 * w * env * math.sin(2 * phi)), no, w

    for i in range(3):
        rings = []
        for k in range(K):
            phi = ph[k] + 2 * math.pi * i / 3; l = ls[k]; m.along = l - root
            dphi = 2 * math.pi * 0.001 / (PERIOD * width(l) / 0.023)
            p, no, w = strand_pos(l, phi)
            t = strand_pos(l + 0.001, phi + dphi)[0] - strand_pos(l - 0.001, phi - dphi)[0]; t /= np.linalg.norm(t)
            eu = np.cross(t, no); eu /= np.linalg.norm(eu); ev = np.cross(eu, t); ev /= np.linalg.norm(ev)
            if np.dot(ev, no) < 0: ev = -ev
            rings.append(m.ring(p, eu, ev, 0.52 * w, 0.40 * w, SIDES))
            if k in (0, K - 1): m.cap(rings[-1], p, -t if k == 0 else t, R_STRAND, 0.9)
            if k:
                u0 = (ph[k - 1] + 2 * math.pi * i / 3) / (2 * math.pi) % 1.0
                m.band(rings[-2], rings[-1], R_STRAND, u0, u0 + (ph[k] - ph[k - 1]) / (2 * math.pi), span=1.0 + MARGIN)
    tie(lb, S["w1"] * 0.90)
    # the loose end: swells a little below the tie, then thins out to a point
    n = 11; l0 = lb + TIE * 0.3; rings = []
    for k in range(n):
        f = k / (n - 1); l = l0 + (line.total - 0.004 - l0) * f
        c, t, no = line.at(l); m.along = l - root
        r = S["w1"] * (0.78 + 0.34 * math.sin(math.pi * min(f / 0.55, 1.0)) * (1 - f)) * (1 - 0.72 * _smooth(0.35, 1.0, f))
        rings.append(m.ring(c + no * 0.0015 * f, X, no, r, r * 0.80, 12))
        if k == 0: m.cap(rings[-1], c, -t, R_PLAIN, 0.5)
        if k: m.band(rings[-2], rings[-1], R_PLAIN, 0.50 + 0.45 * (k - 1) / (n - 1), 0.50 + 0.45 * f)
    c, t, no = line.at(line.total)
    tip = m.point(c + no * 0.002, t, c)
    m.fan(rings[-1], tip, R_PLAIN, 0.95, 1.0)
    return m.result()


def _bun_frame():
    """axes of a bun: across, up along the head, out of the head"""
    e1 = np.array([1.0, 0.0, 0.0]); e2 = np.cross(BUN_OUT, e1); return e1, e2 / np.linalg.norm(e2), BUN_OUT


def _bun_base(m, radius, height):
    """the hair below a bun: a low dome on the head, so nothing shows through between the turns"""
    e1, e2, n = _bun_frame(); rings = []; steps = 6
    for k in range(steps):
        f = k / steps; r = radius * math.cos(f * math.pi / 2); c = BUN_AT + n * (height * math.sin(f * math.pi / 2) - 0.010)      # its rim lies inside the head
        rings.append(m.ring(c, e1, e2, r, r, 16))
        for i in rings[-1]: m.cen[i] = BUN_AT - n * 0.02
        if k: m.band(rings[-2], rings[-1], R_PLAIN, 0.05 + 0.35 * (k - 1) / steps, 0.05 + 0.35 * k / steps)
    top = m.point(BUN_AT + n * (height - 0.010), n, BUN_AT - n * 0.02)
    m.fan(rings[-1], top, R_PLAIN, 0.40, 0.45)


def _braided_bun():
    """a bun wound from a rope of two strands twisted around each other. The rope starts under the bun at the
    nape, runs once around its rim and then winds in to the middle, rising as it goes; the whole lies on the
    curve of the head, so it stands off nowhere and looks round from every side."""
    m = _Mesh(); e1, e2, n = _bun_frame()
    TURNS, R0, A, RS, PITCH, ROUND = 2.5, 0.0275, 0.0060, 0.0074, 0.028, 0.085      # ROUND: radius of the head below it
    _bun_base(m, R0 + 0.004, 0.027)
    def centre(q):                                       # q: 0 at the start of the rope .. 1 in the middle
        th = -0.5 * math.pi + 2 * math.pi * TURNS * q
        rho = R0 * (1 - 0.93 * _smooth(0.34, 1.0, q) ** 0.9)                          # the first turn is a circle
        lift = 0.0045 + 0.0185 * _smooth(0.25, 1.0, q) ** 0.9 - rho * rho / (2 * ROUND)
        lift -= 0.017 * _smooth(0.09, 0.0, q) + 0.004 * _smooth(0.95, 1.0, q)          # both ends tucked in
        return BUN_AT + rho * (math.cos(th) * e1 + math.sin(th) * e2) + lift * n
    qs = np.linspace(0, 1, 2400); C = np.array([centre(q) for q in qs])
    arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]); total = float(arc[-1])
    K = int(round(total / STEP)) + 1
    for i in range(2):
        rings = []
        for k in range(K):
            l = total * k / (K - 1); q = float(np.interp(l, arc, qs)); c = centre(q)
            t = centre(min(q + 1e-3, 1.0)) - centre(max(q - 1e-3, 0.0)); t /= np.linalg.norm(t)
            up = n - np.dot(n, t) * t; up /= np.linalg.norm(up); side = np.cross(t, up)
            psi = 2 * math.pi * l / PITCH + math.pi * i
            env = _smooth(0.0, 0.012, l) * _smooth(total, total - 0.010, l)
            p = c + A * env * (math.cos(psi) * side + math.sin(psi) * up)
            dpsi = 2 * math.pi * 0.001 / PITCH
            ts = t * 0.001 + A * env * dpsi * (-math.sin(psi) * side + math.cos(psi) * up); ts /= np.linalg.norm(ts)
            ev = up - np.dot(up, ts) * ts; ev /= np.linalg.norm(ev); eu = np.cross(ts, ev)
            rings.append(m.ring(p, eu, ev, RS * (0.6 + 0.4 * env), RS * 0.90 * (0.6 + 0.4 * env), SIDES))
            if k in (0, K - 1): m.cap(rings[-1], p, -ts if k == 0 else ts, R_STRAND, 0.4)
            if k:
                # the strip shows a strand coming up, lying on top and going under once in half its length
                lp = total * (k - 1) / (K - 1); u0 = ((2 * math.pi * lp / PITCH + math.pi * i) / (2 * math.pi) + 0.5) % 1.0 / 2
                m.band(rings[-2], rings[-1], R_STRAND, u0, u0 + (l - lp) / PITCH / 2, span=1.0 + MARGIN)
    return m.result()


BUNS = {"braidedbun": _braided_bun}


def _enc(w):
    if w <= 0.004: return 0
    if w >= 0.996: return 1
    return min(255, max(3, int(round((1 - w) * 100 * 2.55555)) + 2))


def append(b, li, P, N, faces, weights, tex, mat, like):
    """copy of the MLOD bytes with the geometry added to LOD li. Selections that are not bones take the membership
    of the point `like` (a point of the part this geometry replaces)."""
    _, lods = mlod.read_bytes(bytes(b)); L = lods[li]
    npt, nnm, nfc = L.npoints, L.nnormals, L.nfaces
    out = bytearray(b[:L.start])
    hdr = bytearray(b[L.start:L.start + 28])
    struct.pack_into("<I", hdr, 12, npt + len(P)); struct.pack_into("<I", hdr, 16, nnm + len(N)); struct.pack_into("<I", hdr, 20, nfc + len(faces))
    out += hdr + b[L.points_off:L.points_off + npt * 16] + b"".join(struct.pack("<fffI", p[0], p[1], p[2], 0) for p in P)
    out += b[L.normals_off:L.normals_off + nnm * 12] + b"".join(struct.pack("<fff", *n) for n in N)
    offs = mlod._face_offsets(b, L)
    out += b[offs[0]:offs[nfc]]
    for f in faces:
        rec = struct.pack("<I", 3)
        for pi, ni, u, v in f: rec += struct.pack("<iiff", pi + npt, ni + nnm, u, v)
        rec += struct.pack("<iiff", 0, 0, 0, 0) + struct.pack("<I", 0) + tex.encode("latin-1") + b"\0" + mat.encode("latin-1") + b"\0"
        out += rec
    out += b[offs[nfc]:offs[nfc] + 4]                                   # "TAGG"
    ncorner = int(L.face_n.sum()); bones = {k for w in weights for k in w}
    for name, data_off, size in L.tags:
        start = data_off - 4 - len(name.encode("latin-1")) - 2
        head = bytearray(b[start:data_off]); data = bytes(b[data_off:data_off + size])
        if name == "#UVSet#" and size == 4 + ncorner * 8:
            first = struct.unpack_from("<I", data, 0)[0] == 0
            data += b"".join(struct.pack("<ff", (u if first else 0.0), (v if first else 0.0)) for f in faces for _, _, u, v in f)
        elif size == npt + nfc and name != "#EndOfFile#":
            pb, fb = data[:npt], data[npt:]
            if name in bones: newp = bytes(_enc(w.get(name, 0.0)) for w in weights)
            else: newp = bytes([pb[like]]) * len(P)
            newf = bytes(1 if all(newp[pi] for pi, _, _, _ in f) else 0 for f in faces)
            data = pb + newp + fb + newf
        struct.pack_into("<I", head, len(head) - 4, len(data))
        out += head + data
    out += b[L.end - 4:L.end] + b[L.end:]
    return out


def _fibres(w, h, seed, drift=1.0):
    """hair running along x: fine streaks that differ across y, repeat in x and y -> (h, w) around 1.0"""
    r = np.random.default_rng(seed)
    u = (np.arange(w) + 0.5) / w; v = (np.arange(h) + 0.5) / h
    out = np.zeros((h, w))
    for n in range(2, 34):
        amp = r.uniform(0.5, 1.0) / n ** 0.55
        ph = r.uniform(0, 6.283) + drift * r.uniform(0.3, 1.1) * np.sin(2 * math.pi * (u * r.integers(1, 3) + r.uniform()))
        out += amp * np.sin(2 * math.pi * n * v[:, None] + ph[None, :])
    out /= out.std()
    return 1.0 + 0.20 * np.clip(out, -2.2, 2.2)


def textures():
    """-> [(rect, luminance (h, w))] for the plaited strands and the plain hair, and the rect of the hair tie.
    Luminance is relative: 1.0 is the colour of the hair."""
    x0, x1, y0, y1 = R_STRAND; w, h = x1 - x0, y1 - y0
    u = (np.arange(w) + 0.5) / w * (1.0 + MARGIN) % 1.0; v = (np.arange(h) + 0.5) / h
    hair = _fibres(int(round(w / (1.0 + MARGIN))), h, 5)
    hair = hair[:, (np.arange(w) % hair.shape[1])]
    q = (2 * u) % 1.0                                  # each strand shows twice per period: 0.5..1 is the visible part
    sm = lambda e0, e1, x: (lambda t: t * t * (3 - 2 * t))(np.clip((x - e0) / (e1 - e0), 0, 1))
    along = np.where(q >= 0.5, 1.0 - 0.62 * sm(0.80, 1.0, q) - 0.22 * sm(0.62, 0.5, q), 0.42)   # dives under the next strand
    out_facing = np.sin(2 * math.pi * v)                # 1 on the side facing away from the braid's middle plane
    around = 0.58 + 0.42 * np.clip(out_facing, -0.2, 1) ** 1
    sheen = 0.30 * np.exp(-((q - 0.70) / 0.085) ** 2)[None, :] * np.clip(out_facing, 0, 1)[:, None] ** 2
    strand = hair * (along[None, :] * around[:, None] + sheen)
    x0, x1, y0, y1 = R_PLAIN; w, h = x1 - x0, y1 - y0; v = (np.arange(h) + 0.5) / h
    plain = _fibres(w, h, 9, drift=0.6) * (0.74 + 0.26 * np.sin(2 * math.pi * v))[:, None]
    return [(R_STRAND, strand), (R_PLAIN, plain)], R_TIE
