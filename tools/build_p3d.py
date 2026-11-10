"""Write the female head MLOD (addons/heads/models/fh_head_bun.p3d) from the Blender export (tools/bake/*.npz).

- Frame: Blender (x, y back, z up, metres) -> Arma model space of a CfgHeads model (x, y up, z back):
  eye centre lands on the vanilla eye memory point, so the vanilla face RTMs drive the right regions.
- Skinning: the MakeHuman default rig's face bones are mapped onto the Arma OFP2_ManSkeleton face bones;
  bones the MakeHuman rig lacks (forehead, cheeks, chin, jowl, brows) are split off by region with soft falloffs.
- LODs 1/2/4 (visual), 10000 (shadow volume, closed), 1e15 (memory points).
- MLOD conventions (checked against BI/TFTW heads): cross(p1-p0, p2-p0) and stored normals point inwards,
  UV origin top left.
usage (repo root): python -I tools/build_p3d.py
"""
import json, os, struct
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BAKE = os.path.join(HERE, "bake")
OUT = os.path.join(HERE, "..", "addons", "heads", "models", "fh_head_bun.p3d")
PREFIX = "z\\mhfh\\addons\\heads\\"
TEX = PREFIX + "data\\fh_light_co.paa"
MAT = PREFIX + "data\\fh_light.rvmat"

L = json.load(open(os.path.join(BAKE, "landmarks.json")))
EYE = np.array(L["joint-l-eye"]); EZ, EY = EYE[2], EYE[1]
S = 1.02
ARMA_EYE = (0.705, -0.081)  # 6 mm behind the male eye: the female nose would poke out of facewear  # (y, z) of the vanilla eye-centre memory point


def to_arma(p):
    p = np.asarray(p, dtype=np.float64)
    return np.stack([S * p[..., 0], S * (p[..., 2] - EZ) + ARMA_EYE[0], S * (p[..., 1] - EY) + ARMA_EYE[1]], -1)


def nrm_to_arma(n):
    n = np.asarray(n, dtype=np.float64)
    return np.stack([n[..., 0], n[..., 2], n[..., 1]], -1)


# ---------------------------------------------------------------- skin weights
def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


DIRECT = {
    "oris01": "Face_LipLowerMiddle", "oris07.L": "Face_LipLowerLeft", "oris07.R": "Face_LipLowerRight",
    "oris05": "Face_LipUpperMiddle", "oris03.L": "Face_LipUpperLeft", "oris03.R": "Face_LipUpperRight",
    "levator06.L": "Face_NostrilLeft", "levator06.R": "Face_NostrilRight",
    "levator05.L": "Face_CheekFrontLeft", "levator05.R": "Face_CheekFrontRight",
    "orbicularis03.L": "Face_EyelidUpperLeft", "orbicularis03.R": "Face_EyelidUpperRight",
    "orbicularis04.L": "Face_EyelidLowerLeft", "orbicularis04.R": "Face_EyelidLowerRight",
    "eye.L": "L_Eye", "eye.R": "R_Eye",
    "neck03": "Neck1", "neck02": "Neck", "neck01": "Neck",
    "clavicle.L": "LeftShoulder", "clavicle.R": "RightShoulder",
}
SPINE = ("spine", "breast", "shoulder", "upperarm")
ALIAS = {"L_Eye": "EyeLeft", "R_Eye": "EyeRight"}  # second selection name the engine also looks for


def arma_weights(groups, p):
    """groups: list of (mh_name, weight); p: Blender-space position -> {arma_bone: weight}"""
    x, y, z = p
    side = "Left" if x >= 0 else "Right"
    ax = abs(x)
    acc = defaultdict(float)
    for g, w in groups:
        if g in ("body", "Left", "Mid", "Right", "FH_bunmark", "lips") or g.startswith(("joint-", "helper-")):
            continue
        if g in DIRECT:
            acc[DIRECT[g]] += w
        elif g.startswith("tongue"):
            acc["Face_Tongue"] += w
        elif g.startswith(SPINE):
            acc["Spine3"] += w
        elif g == "jaw":
            dz = z - (EZ - 0.088)                      # chin height
            chin = smooth(0.026, 0.010, ax) * smooth(-0.02, -0.005, -(y - EY + 0.0))  # front, centre
            chin *= smooth(0.035, 0.0, abs(dz))
            jowl = smooth(-0.005, 0.02, y - EY) * smooth(EZ - 0.07, EZ - 0.10, z)     # under the jaw
            chop = smooth(0.03, 0.05, ax) * (1 - jowl)
            rest = max(0.0, 1 - chin - jowl - chop)
            acc["Face_Chin"] += w * chin
            acc["Face_Jowl"] += w * jowl
            acc["Face_Chop" + side] += w * chop
            acc["Face_Jawbone"] += w * rest
        elif g.startswith("risorius03"):
            far = smooth(0.045, 0.06, ax)
            acc["Face_Corner" + side] += w * (1 - far)
            acc["Face_CheekSide" + side] += w * far
        elif g.startswith("oculi01"):
            mid = smooth(0.013, 0.006, ax)
            sd = smooth(0.035, 0.05, ax) * (1 - mid)
            acc["Face_BrowMiddle"] += w * mid
            acc["Face_BrowSide" + side] += w * sd
            acc["Face_BrowFront" + side] += w * (1 - mid - sd)
        else:  # head, scalp, ears, special*, unknown -> Head, with forehead / upper cheek split off
            front = smooth(-0.07, -0.095, y)
            fore = front * smooth(EZ + 0.028, EZ + 0.040, z) * smooth(EZ + 0.075, EZ + 0.060, z) * smooth(0.06, 0.04, ax)
            cheek = smooth(-0.065, -0.09, y) * smooth(EZ - 0.045, EZ - 0.025, z) * smooth(EZ - 0.003, EZ - 0.015, z) \
                * smooth(0.018, 0.03, ax) * smooth(0.068, 0.055, ax)
            acc["Face_Forehead"] += w * fore
            acc["Face_CheekUpper" + side] += w * cheek
            acc["Head"] += w * max(0.0, 1 - fore - cheek)
    # face bones only act on the face; stray small weights on the sides and back go to Head
    if y > EY + 0.045:
        for k in [k for k in acc if k.startswith(("Face_Nostril", "Face_Lip", "Face_Brow", "Face_Eyelid", "Face_CheekFront", "Face_Forehead"))]:
            acc["Head"] += acc.pop(k)
    if not acc:
        acc["Head"] = 1.0
    top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
    top = [(k, v) for k, v in top if v > 0.02] or [("Head", 1.0)]
    s = sum(v for _, v in top)
    return {k: v / s for k, v in top}


# ---------------------------------------------------------------- MLOD writer
def asciiz(s):
    return s.encode("latin1") + b"\0"


def tagg(name, data):
    return b"\x01" + asciiz(name) + struct.pack("<I", len(data)) + data


def enc_w(w):
    if w <= 0.0: return 0
    if w >= 0.995: return 1
    return min(255, max(3, int(round((1 - w) * 100 * 2.55555)) + 2))


def lod_bytes(res, P, faces, sels, props=(), uv=True):
    """P: (n,3) arma points; faces: list of (corners[(pi, normal_xyz_inward, (u,v))]); sels: {name: per-point weights}"""
    nidx = {}; normals = []
    fl = []
    for f in faces:
        cs = []
        for pi, n, t in f:
            k = tuple(np.round(n, 5))
            if k not in nidx: nidx[k] = len(normals); normals.append(n)
            cs.append((pi, nidx[k], t))
        fl.append(cs)
    out = bytearray(b"P3DM") + struct.pack("<6I", 28, 256, len(P), len(normals), len(fl), 0)
    for p in P: out += struct.pack("<fffI", p[0], p[1], p[2], 0)
    for n in normals: out += struct.pack("<fff", *n)
    uvset = bytearray(struct.pack("<I", 0))
    for cs in fl:
        out += struct.pack("<I", len(cs))
        for pi, ni, (u, v) in cs:
            out += struct.pack("<IIff", pi, ni, u, v); uvset += struct.pack("<ff", u, v)
        for _ in range(4 - len(cs)): out += struct.pack("<IIff", 0, 0, 0, 0)
        out += struct.pack("<I", 0)
        out += asciiz(TEX if uv else "") + asciiz(MAT if uv else "")
    out += b"TAGG"
    for k, v in props:
        out += tagg("#Property#", k.encode().ljust(64, b"\0") + v.encode().ljust(64, b"\0"))
    if uv:
        out += tagg("#UVSet#", bytes(uvset))
    for name, w in sels.items():
        pw = bytes(enc_w(x) for x in w)
        fw = bytes(1 if all(w[pi] > 0 for pi, _, _ in cs) else 0 for cs in fl)
        out += tagg(name, pw + fw)
    out += tagg("#EndOfFile#", b"")
    out += struct.pack("<f", res)
    return bytes(out)


def load(name):
    d = np.load(os.path.join(BAKE, name + ".npz"))
    names = [str(n) for n in d["names"]]
    G = defaultdict(list)
    for vi, gi, w in d["G"]:
        G[int(vi)].append((names[int(gi)], float(w)))
    return d["V"], d["F"], d["UV"], d["N"], G


def visual_lod(name, res, shadow=False):
    V, F, UV, N, G = load(name)
    keep = np.ones(len(V), bool)
    if shadow:  # shadow volume: skin + bun only, holes closed
        for vi, gs in G.items():
            if any(g.startswith(("eye.", "tongue")) for g, _ in gs): keep[vi] = False
        teeth = [vi for vi, gs in G.items() if set(g for g, _ in gs) <= {"head", "jaw"} and V[vi][1] < EY + 0.04
                 and abs(V[vi][0]) < 0.03 and EZ - 0.08 < V[vi][2] < EZ - 0.03 and V[vi][1] > EY - 0.0]
        keep[teeth] = False
    P = to_arma(V)
    W = [arma_weights(G[i], V[i]) for i in range(len(V))]
    faces = []
    for f, uv, nr in zip(F, UV, N):
        if not keep[f].all(): continue
        p0, p1, p2 = P[f[0]], P[f[1]], P[f[2]]
        nA = nrm_to_arma(nr)
        outward = nA.mean(0)
        order = [0, 1, 2]
        if np.dot(np.cross(p1 - p0, p2 - p0), outward) > 0:  # make the cross product point inwards
            order = [0, 2, 1]
        faces.append([(int(f[k]), -nA[k], (float(uv[k][0]), 1.0 - float(uv[k][1]))) for k in order])
    if shadow:
        faces = close_holes(P, faces)
    # drop unused points (shadow), reindex
    used = sorted({c[0] for f in faces for c in f}); remap = {o: i for i, o in enumerate(used)}
    P2 = P[used]
    faces = [[(remap[pi], n, t) for pi, n, t in f] for f in faces]
    sels = defaultdict(lambda: np.zeros(len(P2)))
    for o, i in remap.items():
        for b, w in W[o].items():
            sels[b][i] = w
            if b in ALIAS: sels[ALIAS[b]][i] = w
    sels = dict(sels)
    if not shadow:
        allv = np.ones(len(P2))
        sels["personality"] = allv
        eyes = np.maximum(sels.get("L_Eye", 0), sels.get("R_Eye", 0)) if "L_Eye" in sels else np.zeros(len(P2))
        sels["injury_head"] = (eyes == 0).astype(float)
    props = [("LODNoShadow", "1")] if not shadow else []
    return lod_bytes(res, P2, faces, sels, props, uv=not shadow), len(P2), len(faces)


def close_holes(P, faces):
    """fan-fill every boundary loop around its centroid (new points appended to P via a global list)"""
    global SHADOW_EXTRA
    edges = defaultdict(int); dir_ = {}
    for f in faces:
        for i in range(3):
            a, b = f[i][0], f[(i + 1) % 3][0]
            edges[(min(a, b), max(a, b))] += 1; dir_[(a, b)] = True
    bnd = [(a, b) for (a, b) in dir_ if edges[(min(a, b), max(a, b))] == 1]
    nxt = defaultdict(list)
    for a, b in bnd: nxt[b].append(a)  # reverse direction for the cap
    seen = set(); loops = []
    for a, b in bnd:
        if (b, a) in seen: continue
        loop = [b]; cur = a; seen.add((b, a))
        start = b
        while cur != start and len(loop) < 10000:
            loop.append(cur)
            cand = [c for c in nxt[cur] if (cur, c) not in seen]
            if not cand: break
            seen.add((cur, cand[0])); cur = cand[0]
        loops.append(loop)
    global P_SHADOW
    extra = []
    base = len(P)
    newfaces = list(faces)
    for loop in loops:
        if len(loop) < 3: continue
        c = P[loop].mean(0); ci = base + len(extra); extra.append(c)
        for i in range(len(loop)):
            a, b = loop[i], loop[(i + 1) % len(loop)]
            tri = [a, b, ci]
            pa, pb = (P[a], P[b])
            newfaces.append([(a, np.zeros(3), (0, 0)), (b, np.zeros(3), (0, 0)), (ci, np.zeros(3), (0, 0))])
    P_SHADOW.extend(extra)
    return newfaces


P_SHADOW = []


def shadow_lod():
    global P_SHADOW
    V, F, UV, N, G = load("shadow")
    P_SHADOW = []
    # build via visual_lod machinery, then append fan centres
    import types
    data = visual_lod_shadow(V, F, UV, N, G)
    return data


def visual_lod_shadow(V, F, UV, N, G):
    keep = np.ones(len(V), bool)
    for vi, gs in G.items():
        names = set(g for g, _ in gs)
        if any(g.startswith(("eye.", "tongue")) for g in names): keep[vi] = False
    P = to_arma(V)
    W = [arma_weights(G[i], V[i]) for i in range(len(V))]
    tris = []
    for f, nr in zip(F, N):
        if not keep[f].all(): continue
        p0, p1, p2 = P[f[0]], P[f[1]], P[f[2]]
        if np.dot(np.cross(p1 - p0, p2 - p0), nrm_to_arma(nr).mean(0)) > 0: f = [f[0], f[2], f[1]]
        tris.append([int(i) for i in f])
    # keep the largest connected skin component + bun (drop teeth fragments)
    adj = defaultdict(set)
    for t in tris:
        for a in t:
            adj[a].update(t)
    comp = {}; cid = 0
    for s in adj:
        if s in comp: continue
        st = [s]; comp[s] = cid
        while st:
            a = st.pop()
            for b in adj[a]:
                if b not in comp: comp[b] = cid; st.append(b)
        cid += 1
    sizes = defaultdict(int)
    for a, c in comp.items(): sizes[c] += 1
    big = {c for c, n in sizes.items() if n > 40}
    tris = [t for t in tris if comp[t[0]] in big]
    # boundary loops (edges used once) -> fan caps, oriented like the rest (inward cross product)
    cnt = defaultdict(int)
    for t in tris:
        for i in range(3): cnt[(min(t[i], t[(i + 1) % 3]), max(t[i], t[(i + 1) % 3]))] += 1
    half = {}
    for t in tris:
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            if cnt[(min(a, b), max(a, b))] == 1: half[b] = a  # cap edge runs reversed: b -> a
    Pl = list(P); Wl = list(W)
    while half:
        s = next(iter(half)); loop = [s]; cur = half.pop(s)
        while cur != s and cur in half:
            loop.append(cur); cur = half.pop(cur)
        if len(loop) < 3: continue
        c = np.mean([Pl[i] for i in loop], 0); ci = len(Pl); Pl.append(c)
        Wl.append(Wl[loop[0]])
        for i in range(len(loop)):
            tris.append([loop[i], loop[(i + 1) % len(loop)], ci])
    P = np.array(Pl)
    used = sorted({i for t in tris for i in t}); remap = {o: i for i, o in enumerate(used)}
    P2 = P[used]; tris = [[remap[i] for i in t] for t in tris]
    faces = []
    for t in tris:
        p0, p1, p2 = P2[t]
        n = np.cross(p1 - p0, p2 - p0); n = n / (np.linalg.norm(n) + 1e-12)
        faces.append([(i, n, (0.0, 0.0)) for i in t])
    sels = defaultdict(lambda: np.zeros(len(P2)))
    for o, i in remap.items():
        for b, w in Wl[o].items():
            sels[b][i] = w
            if b in ALIAS: sels[ALIAS[b]][i] = w
    # closed check
    cnt = defaultdict(int)
    for t in tris:
        for i in range(3): cnt[(min(t[i], t[(i + 1) % 3]), max(t[i], t[(i + 1) % 3]))] += 1
    open_edges = sum(1 for v in cnt.values() if v != 2)
    return lod_bytes(10000.0, P2, faces, dict(sels), (), uv=False), len(P2), len(faces), open_edges


def memory_lod():
    eyeL = to_arma(np.array(L["joint-l-eye"])); eyeR = to_arma(np.array(L["joint-r-eye"]))
    pupL = eyeL + [0, 0, -0.011]; pupR = eyeR + [0, 0, -0.011]
    mid = (eyeL + eyeR) / 2
    pts = [eyeL, eyeR, pupL, pupR, mid + [0, 0.02, 0.017], mid + [0, -0.012, -0.03], mid + [0, 0.021, -0.0]]
    # 0 eyeL 1 eyeR 2 pupL 3 pupR 4 head(back) 5 head(front) 6 pilot
    n = len(pts)
    def sel(*idx):
        w = np.zeros(n); w[list(idx)] = 1; return w
    sels = {
        "L_eye_center": sel(0), "EyeLeft_center": sel(0), "L_Eye": sel(0), "EyeLeft": sel(0),
        "R_eye_center": sel(1), "EYERight_center": sel(1), "R_Eye": sel(1), "EyeRight": sel(1),
        "L_pupila_center": sel(2), "PupilaLeft_center": sel(2),
        "R_pupila_center": sel(3), "PupilaRight_center": sel(3),
        "osobnost": sel(0, 1), "Head": sel(4, 5), "pilot": sel(6),
    }
    return lod_bytes(1e15, np.array(pts), [], sels, (), uv=False), n


def main():
    blobs = []
    for name, res in (("lod1", 1.0), ("lod2", 2.0), ("lod3", 4.0)):
        b, nv, nf = visual_lod(name, res); blobs.append(b); print(f"LOD {res:g}: {nv} points, {nf} faces")
    V, F, UV, N, G = load("shadow")
    b, nv, nf, op = visual_lod_shadow(V, F, UV, N, G); blobs.append(b)
    print(f"shadow: {nv} points, {nf} faces, open edges {op}")
    b, nv = memory_lod(); blobs.append(b); print(f"memory: {nv} points")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(b"MLOD" + struct.pack("<II", 257, len(blobs)) + b"".join(blobs))
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
