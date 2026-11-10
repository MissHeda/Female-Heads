"""Minimal MLOD (P3DM 0x1c/0x100) reader/patcher: points, normals, faces, named selections, resolutions.

Keeps the raw file bytes; patch() only overwrites point positions (and optionally the normal vectors), so
topology, UVs, selections, skin weights, proxies and every other tag stay byte-identical.
Coordinates are Arma model space (x right, y up, z forward).
"""
import struct
import numpy as np

NUL = 0


def decode_weight(b):
    """selection byte -> weight (same rule as ArmaToolbox)"""
    if b == 0: return 0.0
    if b == 2 or b == 1: return 1.0
    if b > 2: return 1.0 - round((b - 2) / 2.55555) * 0.01
    return -round(b / 2.55555) * 0.01


_WTAB = np.array([decode_weight(b if b < 128 else b - 256) for b in range(256)], dtype=np.float32)


class Lod:
    pass


def _asciiz(b, pos):
    e = b.index(b"\0", pos)
    return b[pos:e].decode("latin-1"), e + 1


def read(path, want_selections=True):
    return read_bytes(open(path, "rb").read(), want_selections)


def read_bytes(data, want_selections=True):
    b = bytearray(data)
    assert b[:4] == b"MLOD", "not MLOD"
    nl = struct.unpack_from("<I", b, 8)[0]
    pos = 12; lods = []
    for li in range(nl):
        L = Lod(); L.index = li; L.start = pos
        assert b[pos:pos + 4] == b"P3DM", f"bad lod sig at {pos}"
        hs, ver, npt, nnm, nfc, flags = struct.unpack_from("<6I", b, pos + 4); pos += 28
        L.npoints, L.nnormals, L.nfaces = npt, nnm, nfc
        L.points_off = pos
        raw = np.frombuffer(bytes(b[pos:pos + npt * 16]), dtype=np.float32).reshape(npt, 4)
        L.points = raw[:, :3].astype(np.float64).copy()
        L.point_flags = np.frombuffer(bytes(b[pos:pos + npt * 16]), dtype=np.uint32).reshape(npt, 4)[:, 3].copy()
        pos += npt * 16
        L.normals_off = pos
        L.normals = np.frombuffer(bytes(b[pos:pos + nnm * 12]), dtype=np.float32).reshape(nnm, 3).astype(np.float64).copy()
        pos += nnm * 12
        fn = np.zeros(nfc, dtype=np.int32); fv = np.zeros((nfc, 4), dtype=np.int64); fnr = np.zeros((nfc, 4), dtype=np.int64)
        fuv = np.zeros((nfc, 4, 2), dtype=np.float32); ftex = []; fmat = []; fflags = np.zeros(nfc, dtype=np.uint32)
        for f in range(nfc):
            n = struct.unpack_from("<I", b, pos)[0]
            rec = struct.unpack_from("<" + "iiff" * 4, b, pos + 4)
            fn[f] = n
            fv[f] = rec[0::4]; fnr[f] = rec[1::4]; fuv[f, :, 0] = rec[2::4]; fuv[f, :, 1] = rec[3::4]
            fflags[f] = struct.unpack_from("<I", b, pos + 68)[0]
            pos += 72
            t, pos = _asciiz(b, pos); m, pos = _asciiz(b, pos)
            ftex.append(t); fmat.append(m)
        L.face_n, L.face_v, L.face_nrm, L.face_uv, L.face_flags = fn, fv, fnr, fuv, fflags
        L.face_tex, L.face_mat = ftex, fmat
        assert b[pos:pos + 4] == b"TAGG", f"no TAGG at {pos}"
        pos += 4
        L.selections = {}; L.tags = []
        while True:
            active = b[pos]; pos += 1
            name, pos = _asciiz(b, pos)
            size = struct.unpack_from("<I", b, pos)[0]; pos += 4
            data_off = pos
            L.tags.append((name, data_off, size))
            if want_selections and active and name and not name.startswith("#") and size == npt + nfc:
                pw = _WTAB[np.frombuffer(bytes(b[data_off:data_off + npt]), dtype=np.uint8)]
                fw = np.frombuffer(bytes(b[data_off + npt:data_off + npt + nfc]), dtype=np.uint8) != 0
                L.selections[name] = (pw, fw)
            pos += size
            if name == "#EndOfFile#": break
        L.res = struct.unpack_from("<f", b, pos)[0]; pos += 4
        L.end = pos
        lods.append(L)
    return b, lods


def triangles(L, corners=False):
    """(T, face_of_tri) fan triangulation of the faces; corners=True also returns the face corner of every triangle vertex"""
    tris = []; fo = []; cs = []
    for f in range(L.nfaces):
        n = L.face_n[f]; v = L.face_v[f]
        tris.append((v[0], v[1], v[2])); fo.append(f); cs.append((0, 1, 2))
        if n == 4: tris.append((v[0], v[2], v[3])); fo.append(f); cs.append((0, 2, 3))
    T, F = np.array(tris, dtype=np.int64).reshape(-1, 3), np.array(fo, dtype=np.int64)
    return (T, F, np.array(cs, dtype=np.int64).reshape(-1, 3)) if corners else (T, F)


def face_normals(L, P):
    """unnormalized geometric face normals (2x area) for points P, in the file's winding"""
    v = np.clip(L.face_v, 0, len(P) - 1)
    p0, p1, p2, p3 = P[v[:, 0]], P[v[:, 1]], P[v[:, 2]], P[v[:, 3]]
    tri = np.cross(p1 - p0, p2 - p0)
    quad = np.cross(p2 - p0, p3 - p1)
    return np.where((L.face_n == 4)[:, None], quad, tri)


def normal_accum(L, P):
    """per normal-index accumulated (area weighted) face normals for points P"""
    fnrm = face_normals(L, P)
    acc = np.zeros((L.nnormals, 3))
    for k in range(4):
        use = k < L.face_n
        np.add.at(acc, L.face_nrm[use, k], fnrm[use])
    return acc


def updated_normals(L, P_old, P_new):
    """rotate every stored normal by the rotation that takes its recomputed old direction to the new one"""
    a = normal_accum(L, P_old); c = normal_accum(L, P_new)
    na = np.linalg.norm(a, axis=1); nc = np.linalg.norm(c, axis=1)
    ok = (na > 1e-12) & (nc > 1e-12)
    a = np.where(ok[:, None], a / np.maximum(na, 1e-12)[:, None], 0); c = np.where(ok[:, None], c / np.maximum(nc, 1e-12)[:, None], 0)
    N = L.normals.copy(); out = N.copy()
    for i in np.nonzero(ok)[0]:
        u, v = a[i], c[i]
        w = np.cross(u, v); s = np.linalg.norm(w); cth = float(np.dot(u, v))
        if s < 1e-9: continue
        k = w / s; n = N[i]
        out[i] = n * cth + np.cross(k, n) * s + k * np.dot(k, n) * (1 - cth)   # Rodrigues
    return out


def patch(b, lods, new_points, new_normals=None):
    """new_points / new_normals: {lod_index: array}; returns patched bytearray copy"""
    b = bytearray(b)
    for li, P in new_points.items():
        L = lods[li]; P = np.asarray(P, dtype=np.float32)
        assert P.shape == (L.npoints, 3)
        raw = np.frombuffer(bytes(b[L.points_off:L.points_off + L.npoints * 16]), dtype=np.float32).reshape(L.npoints, 4).copy()
        raw[:, :3] = P
        b[L.points_off:L.points_off + L.npoints * 16] = raw.tobytes()
    for li, N in (new_normals or {}).items():
        L = lods[li]; N = np.asarray(N, dtype=np.float32)
        assert N.shape == (L.nnormals, 3)
        b[L.normals_off:L.normals_off + L.nnormals * 12] = N.tobytes()
    return b


def rewrite_face_paths(b, lods, fn):
    """copy of the file with every face texture / material string replaced by fn(old) (latin-1 str -> str);
    MLOD has no offsets, so the face records can change length"""
    out = bytearray(b[:lods[0].start]) if lods else bytearray(b)
    for L in lods:
        fstart = L.normals_off + L.nnormals * 12
        out += b[L.start:fstart]
        pos = fstart
        for f in range(L.nfaces):
            out += b[pos:pos + 72]; pos += 72
            for _ in range(2):
                e = b.index(b"\0", pos); s = bytes(b[pos:e]).decode("latin-1")
                out += fn(s).encode("latin-1") + b"\0"; pos = e + 1
        out += b[pos:L.end]
    if lods: out += b[lods[-1].end:]
    return out


def _face_offsets(b, L):
    """byte offset of every face record of L (records have variable length: two strings each)"""
    offs = np.zeros(L.nfaces + 1, np.int64); pos = L.normals_off + L.nnormals * 12
    for f in range(L.nfaces):
        offs[f] = pos; pos += 72
        pos = b.index(b"\0", pos) + 1; pos = b.index(b"\0", pos) + 1
    offs[L.nfaces] = pos
    return offs


def rebuild(b, lods, drop=(), faces=None):
    """copy of the file without the LODs in drop and with faces[lod_index] = (keep mask, point remap) applied: kept
    faces get their vertex indices remapped, points no kept face uses are removed; per-face and per-point tag data
    (#UVSet#, selections, #Mass#, #SharpEdges#) follows; normals stay as they are"""
    faces = faces or {}
    out = bytearray(b[:lods[0].start]); n = 0
    for L in lods:
        if L.index in drop: continue
        n += 1
        if L.index not in faces:
            out += b[L.start:L.end]; continue
        keep, remap = faces[L.index]
        offs = _face_offsets(b, L)
        fv = remap[np.clip(L.face_v, 0, L.npoints - 1)]
        used = np.zeros(L.npoints, bool)
        for k in range(4): used[fv[keep & (L.face_n > k), k]] = True
        new_idx = np.cumsum(used) - 1
        hdr = bytearray(b[L.start:L.start + 28])
        struct.pack_into("<I", hdr, 12, int(used.sum())); struct.pack_into("<I", hdr, 20, int(keep.sum()))
        pts = np.frombuffer(bytes(b[L.points_off:L.points_off + L.npoints * 16]), np.uint8).reshape(L.npoints, 16)
        out += hdr + pts[used].tobytes() + b[L.normals_off:offs[0]]
        for f in np.nonzero(keep)[0]:
            rec = bytearray(b[offs[f]:offs[f + 1]])
            for k in range(L.face_n[f]): struct.pack_into("<i", rec, 4 + 16 * k, int(new_idx[fv[f, k]]))
            out += rec
        tpos = offs[L.nfaces]; out += b[tpos:tpos + 4]           # "TAGG"
        ncorner = int(L.face_n.sum())
        for name, data_off, size in L.tags:
            start = data_off - 4 - len(name.encode("latin-1")) - 2  # active byte + name + NUL + size
            head = bytearray(b[start:data_off]); data = bytes(b[data_off:data_off + size])
            if name == "#UVSet#" and size == 4 + ncorner * 8:
                uv = np.frombuffer(data[4:], np.float32).reshape(-1, 2)
                data = data[:4] + uv[np.repeat(keep, L.face_n)].tobytes()
            elif name == "#Mass#" and size == L.npoints * 4:
                data = np.frombuffer(data, np.float32)[used].tobytes()
            elif name == "#SharpEdges#":
                e = np.frombuffer(data, np.uint32).reshape(-1, 2).astype(np.int64)
                e = remap[np.clip(e, 0, L.npoints - 1)]; ok = used[e].all(1)
                data = new_idx[e[ok]].astype(np.uint32).tobytes()
            elif size == L.npoints + L.nfaces and name != "#EndOfFile#":   # selections, #Hidden#, #Lock#, ...
                pb = np.frombuffer(data[:L.npoints], np.uint8); fb = np.frombuffer(data[L.npoints:], np.uint8)
                data = pb[used].tobytes() + fb[keep].tobytes()
            else:
                assert name in ("#EndOfFile#", "#Property#", "#UVSet#") or not name.startswith("#"), f"tag {name} not handled"
            struct.pack_into("<I", head, len(head) - 4, len(data))
            out += head + data
        out += b[L.end - 4:L.end]                                 # resolution
    out += b[lods[-1].end:]
    struct.pack_into("<I", out, 8, n)
    return out


def clean_shadow(b, lods, male_lods):
    """undo what a previous binarize did to the shadow LODs of a debinarized model, so binarize processes them once:
    shadow volumes (10000..10999) get their split points welded again (groups by the male positions; the points of a
    group get their mean position) and lose the zero-area edge quads binarize inserted; the shadow buffer LODs
    (11000..11999) binarize generated from them are dropped (binarize generates them again). Returns new bytes."""
    newp, faces, drop = {}, {}, set()
    for L, M in zip(lods, male_lods):
        if 11000 <= L.res < 12000: drop.add(L.index); continue
        if not (10000 <= L.res < 11000) or not L.nfaces: continue
        assert M.npoints == L.npoints and M.nfaces == L.nfaces, "male and female shadow LODs differ"
        q = np.round(M.points / 1e-5).astype(np.int64)
        prox = np.zeros(L.npoints, bool)                         # proxy triangles stay separate (equipment and
        for name, (pw, fw) in L.selections.items():             # backpack sit on the same three spots)
            if name.lower().startswith("proxy:"): prox |= pw != 0
        q = np.concatenate([q, np.where(prox, np.arange(L.npoints), -1)[:, None]], 1)
        _, first, key = np.unique(q, axis=0, return_index=True, return_inverse=True)
        key = key.ravel(); remap = first[key]
        P = L.points.copy()
        mean = np.zeros((len(first), 3)); np.add.at(mean, key, P); mean /= np.bincount(key)[:, None]
        newp[L.index] = mean[key]
        area = np.linalg.norm(face_normals(M, M.points), axis=1)
        rv = remap[np.clip(L.face_v, 0, L.npoints - 1)]
        uniq = np.array([len(set(rv[f, :L.face_n[f]])) == L.face_n[f] for f in range(L.nfaces)])
        faces[L.index] = (uniq & (area > 1e-12), remap)
    return rebuild(patch(b, lods, newp), lods, drop, faces)


def res_name(r):
    return f"{r:g}"
