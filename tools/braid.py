"""The braid variant: a short braid hanging from the back of the head instead of the bun.

braid_mesh() builds the geometry (Arma model space: x, height, depth; the back of the head is +z), its UVs into
the atlas area the bun used, and bone weights. append() adds it to a LOD of an MLOD file (the bun faces are
dropped before with mlod.rebuild). braid_strip() gives the photographed braid for that atlas area.
"""
import math, os, struct
import numpy as np
from PIL import Image
import mlod

HERE = os.path.dirname(os.path.abspath(__file__))
# centre line (height, depth): starts inside the hair at the back of the head, hangs down clear of the neck and
# ends above the collar, where the uniform's back comes out
PATH = [(0.684, 0.056), (0.675, 0.072), (0.658, 0.079), (0.630, 0.078), (0.600, 0.083), (0.572, 0.094), (0.550, 0.103)]
A, B = 0.0185, 0.0115            # half width, half thickness
SIDES, STEP, PERIOD = 10, 0.0055, 0.029
# two rows in the old bun area of the 1024 atlas (pixels: x0, x1, y0, y1): first and second half of the braid
ROWS = ((778, 1004, 792, 872), (778, 1004, 884, 964))


def _smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)


def _spline(pts, n=400):
    P = np.array([pts[0]] + list(pts) + [pts[-1]], dtype=np.float64); out = []
    for i in range(1, len(P) - 2):
        for t in np.linspace(0, 1, n // (len(P) - 3), endpoint=False):
            a = 2 * P[i]; b = P[i + 1] - P[i - 1]; c = 2 * P[i - 1] - 5 * P[i] + 4 * P[i + 1] - P[i + 2]; d = -P[i - 1] + 3 * P[i] - 3 * P[i + 1] + P[i + 2]
            out.append(0.5 * (a + b * t + c * t * t + d * t ** 3))
    out.append(P[-2]); return np.array(out)


def braid_mesh():
    """-> points (n,3), inward normals (n,3), faces [[(point, normal, u, v) x3]], weights [{bone: weight}]"""
    C = _spline(PATH); seg = np.linalg.norm(np.diff(C, axis=0), axis=1); arc = np.concatenate([[0], np.cumsum(seg)])
    total = arc[-1]; K = int(round(total / STEP)) | 1                 # odd: one ring sits exactly in the middle
    rings = []; pts = []; nrm = []; wts = []
    for k in range(K):
        l = total * k / (K - 1); s = l / total
        y = np.interp(l, arc, C[:, 0]); z = np.interp(l, arc, C[:, 1])
        y2 = np.interp(min(l + 0.002, total), arc, C[:, 0]); z2 = np.interp(min(l + 0.002, total), arc, C[:, 1])
        y1 = np.interp(max(l - 0.002, 0), arc, C[:, 0]); z1 = np.interp(max(l - 0.002, 0), arc, C[:, 1])
        t = np.array([y2 - y1, z2 - z1]); t /= np.linalg.norm(t)
        nout = np.array([0.0, t[1], -t[0]])                           # away from the body
        sc = (0.80 + 0.20 * _smooth(0.0, 0.10, s)) * (1.0 - 0.52 * _smooth(0.72, 1.0, s))
        a = A * sc * (1 + 0.07 * math.cos(4 * math.pi * l / PERIOD)); b = B * sc
        cx = 0.0012 * math.sin(2 * math.pi * l / PERIOD) * sc
        ring = []
        for j in range(SIDES):
            th = 2 * math.pi * j / SIDES
            p = np.array([cx + a * math.cos(th), y, z]) + b * math.sin(th) * nout
            n = np.array([math.cos(th) / a, 0, 0]) + math.sin(th) / b * nout; n /= np.linalg.norm(n)
            ring.append(len(pts)); pts.append(p); nrm.append(-n)
            head = _smooth(0.618, 0.650, y); spine = _smooth(0.590, 0.560, y)
            w = {"Head": head, "Spine3": spine, "Neck": max(0.0, 1 - head - spine)}
            wts.append({k_: v for k_, v in w.items() if v > 0.004})
        rings.append((ring, s))
    tip = len(pts); y, z = C[-1]; pts.append(np.array([0.0, y - 0.004, z + 0.001])); nrm.append(np.array([0.0, 1.0, 0.0])); wts.append(dict(wts[-1]))

    def uv(s, j):
        row = ROWS[0] if s <= 0.5 + 1e-9 else ROWS[1]
        f = (s / 0.5) if s <= 0.5 + 1e-9 else ((s - 0.5) / 0.5)
        return row, f, 0.5 - 0.5 * math.cos(2 * math.pi * j / SIDES)

    def corner(i, s, j, row=None):
        r, f, v = uv(s, j)
        if row is not None:                                            # middle ring seen from the second half
            r = row; f = 0.0
        return (i, i, (r[0] + f * (r[1] - r[0])) / 1024.0, (r[2] + v * (r[3] - r[2])) / 1024.0)

    faces = []
    for k in range(K - 1):
        (r0, s0), (r1, s1) = rings[k], rings[k + 1]
        second = s1 > 0.5 + 1e-9
        for j in range(SIDES):
            j2 = (j + 1) % SIDES
            c00 = corner(r0[j], s0, j, ROWS[1] if second and s0 <= 0.5 + 1e-9 else None)
            c01 = corner(r0[j2], s0, j + 1, ROWS[1] if second and s0 <= 0.5 + 1e-9 else None)
            c10 = corner(r1[j], s1, j); c11 = corner(r1[j2], s1, j + 1)
            faces.append([c00, c01, c11]); faces.append([c00, c11, c10])
    last = rings[-1][0]
    for j in range(SIDES):
        j2 = (j + 1) % SIDES
        faces.append([corner(last[j], 1.0, j), corner(last[j2], 1.0, j + 1), (tip, tip, ROWS[1][1] / 1024.0, (ROWS[1][2] + ROWS[1][3]) / 2048.0)])
    P = np.array(pts); N = np.array(nrm)
    cen = {i: np.array([0.0, np.interp(total * s, arc, C[:, 0]), np.interp(total * s, arc, C[:, 1])]) for ring, s in rings for i in ring}
    cen[tip] = np.array([0.0, C[-1, 0], C[-1, 1]])
    fixed = []
    for f in faces:                                                    # MLOD: cross(p1-p0, p2-p0) points inwards
        p0, p1, p2 = P[f[0][0]], P[f[1][0]], P[f[2][0]]
        out = (p0 + p1 + p2) / 3 - (cen[f[0][0]] + cen[f[1][0]] + cen[f[2][0]]) / 3
        fixed.append(f if np.dot(np.cross(p1 - p0, p2 - p0), out) < 0 else [f[0], f[2], f[1]])
    return P, N, fixed, wts


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


def braid_strip():
    """the braid photo as two rows of luminance (first half, second half of the braid), sized like ROWS"""
    im = Image.open(os.path.join(HERE, "ref", "tex", "hair_01.png")).convert("RGB")
    w, h = im.size; s = w / 1024.0
    total = sum(math.hypot(PATH[i + 1][0] - PATH[i][0], PATH[i + 1][1] - PATH[i][1]) for i in range(len(PATH) - 1))
    px = int(total / 0.00031 * s)                                        # the photo shows about 0.31 mm per texel
    strip = im.crop((int(6 * s), int(6 * s), int(6 * s) + px, int(101 * s)))
    rows = []
    for k, (x0, x1, y0, y1) in enumerate(ROWS):
        half = strip.crop((k * strip.size[0] // 2, 0, (k + 1) * strip.size[0] // 2, strip.size[1])).resize((x1 - x0, y1 - y0), Image.LANCZOS)
        rows.append(np.asarray(half, dtype=np.float64) / 255 @ np.array([0.30, 0.59, 0.11]))
    return rows
