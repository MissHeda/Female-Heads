"""Write the female head MLOD (addons/heads/models/fh_head_bun.p3d) from the Blender export (tools/bake/*.npz).

- Frame: the export is already in Arma model space with Blender axes (x, depth, height) -> (x, height, depth).
- Skinning: the MakeHuman default rig's face bones are mapped onto the face bones of OFP2_ManSkeleton.
  The vanilla face animations are heavily exaggerated and meant for small weights (lips 0.2-0.3, lids 0.1,
  brows 0.05...), with the rest of every face vertex on Head. The caps below come from replaying the vanilla
  RTMs on a vanilla-compatible head (tools/simulate.py); with full weights the face would tear apart.
- LODs 1/2/4 (visual), 10000 (shadow volume, closed), 1e15 (memory points).
- MLOD conventions (checked against BI heads): cross(p1-p0, p2-p0) and stored normals point inwards,
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
EYE = np.array(json.load(open(os.path.join(BAKE, "landmarks.json")))["eye_l"])   # (x, depth, height)
EX, EY, EZ = EYE


def to_arma(p):
    p = np.asarray(p, dtype=np.float64)
    return np.stack([p[..., 0], p[..., 2], p[..., 1]], -1)


# ---------------------------------------------------------------- skin weights
def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# weight a face bone gets where the MakeHuman bone has full weight
CAP = {
    "Face_Jawbone": 0.87,                       # whole jaw family (jaw + its children) against Head
    "Face_LipLowerMiddle": 0.25, "Face_LipLowerLeft": 0.18, "Face_LipLowerRight": 0.18, "Face_Tongue": 0.18,
    "Face_Jowl": 0.39, "Face_ChopLeft": 0.27, "Face_ChopRight": 0.27, "Face_Chin": 0.02,
    "Face_LipUpperMiddle": 0.31, "Face_LipUpperLeft": 0.22, "Face_LipUpperRight": 0.22,
    "Face_CornerLeft": 0.07, "Face_CornerRight": 0.07, "Face_CheekSideLeft": 0.04, "Face_CheekSideRight": 0.04,
    "Face_CheekFrontLeft": 0.04, "Face_CheekFrontRight": 0.04, "Face_CheekUpperLeft": 0.07, "Face_CheekUpperRight": 0.07,
    "Face_NostrilLeft": 0.05, "Face_NostrilRight": 0.05, "Face_Forehead": 0.04,
    "Face_BrowFrontLeft": 0.07, "Face_BrowFrontRight": 0.07, "Face_BrowMiddle": 0.05,
    "Face_BrowSideLeft": 0.04, "Face_BrowSideRight": 0.04,
    "Face_EyelidUpperLeft": 0.11, "Face_EyelidUpperRight": 0.11, "Face_EyelidLowerLeft": 0.02, "Face_EyelidLowerRight": 0.02,
    "Face_Eyelids": 0.04,
}
CAP.update(json.load(open(os.path.join(HERE, "weight_caps.json"))) if os.path.exists(os.path.join(HERE, "weight_caps.json")) else {})
UPPER = {  # MakeHuman bone -> face bone that hangs on Head (Face_Hub)
    "oris05": "Face_LipUpperMiddle", "oris03.L": "Face_LipUpperLeft", "oris03.R": "Face_LipUpperRight",
    "levator06.L": "Face_NostrilLeft", "levator06.R": "Face_NostrilRight",
    "levator05.L": "Face_CheekFrontLeft", "levator05.R": "Face_CheekFrontRight",
    "orbicularis03.L": "Face_EyelidUpperLeft", "orbicularis03.R": "Face_EyelidUpperRight",
    "orbicularis04.L": "Face_EyelidLowerLeft", "orbicularis04.R": "Face_EyelidLowerRight",
}
LOWER = {"oris01": "Face_LipLowerMiddle", "oris07.L": "Face_LipLowerLeft", "oris07.R": "Face_LipLowerRight"}
SPINE = ("spine", "breast", "shoulder", "upperarm")
ALIAS = {"L_Eye": "EyeLeft", "R_Eye": "EyeRight"}  # second selection name the engine also looks for
SKIP = ("joint-", "helper-", "FH_")


def arma_weights(groups, p):
    """groups: list of (makehuman_group, weight); p: fitted position (x, depth, height) -> {arma_bone: weight}"""
    x, y, z = p
    side = "Left" if x >= 0 else "Right"; ax = abs(x)
    g = defaultdict(float)
    for n, w in groups:
        if n in ("body", "Left", "Mid", "Right", "lips", "HelperGeometry", "JointCubes") or n.startswith(SKIP): continue
        g[n] += w
    tot = sum(g.values())
    if tot <= 0: return {"Head": 1.0}
    for n in g: g[n] /= tot
    acc = defaultdict(float)
    # eyeballs follow the eye bones completely
    for n, b in (("eye.L", "L_Eye"), ("eye.R", "R_Eye")):
        if g.get(n, 0) > 0.5: return {b: 1.0}
    # --- jaw family: jaw, lower lip, tongue (all hang on Face_Jawbone)
    jaw = g.get("jaw", 0.0); low = {b: g.get(n, 0.0) for n, b in LOWER.items()}
    tongue = sum(w for n, w in g.items() if n.startswith("tongue"))
    J = jaw + sum(low.values()) + tongue
    if J > 0:
        fam = CAP["Face_Jawbone"] * J
        parts = {b: CAP[b] * w for b, w in low.items()}
        parts["Face_Tongue"] = CAP["Face_Tongue"] * tongue
        under = smooth(EZ - 0.105, EZ - 0.125, z) * smooth(EY + 0.005, EY + 0.03, y)       # under the jaw
        chop = smooth(0.030, 0.050, ax) * (1 - under)
        chin = smooth(0.022, 0.008, ax) * smooth(EZ - 0.085, EZ - 0.10, z) * smooth(EY - 0.005, EY - 0.02, y)
        parts["Face_Jowl"] = CAP["Face_Jowl"] * under * jaw
        parts["Face_Chop" + side] = CAP["Face_Chop" + side] * chop * jaw
        parts["Face_Chin"] = CAP["Face_Chin"] * chin * jaw
        s = sum(parts.values())
        if s > fam: parts = {b: w * fam / s for b, w in parts.items()}; s = fam
        for b, w in parts.items(): acc[b] += w
        acc["Face_Jawbone"] += fam - s
    # --- bones on the upper face
    for n, b in UPPER.items():
        if n in g: acc[b] += CAP[b] * g[n]
    lids = g.get("orbicularis03.L", 0) + g.get("orbicularis03.R", 0) + g.get("orbicularis04.L", 0) + g.get("orbicularis04.R", 0)
    acc["Face_Eyelids"] += CAP["Face_Eyelids"] * lids
    for s_ in ("L", "R"):
        r = g.get("risorius03." + s_, 0.0); sd = "Left" if s_ == "L" else "Right"
        far = smooth(0.042, 0.058, ax)
        acc["Face_Corner" + sd] += CAP["Face_Corner" + sd] * r * (1 - far)
        acc["Face_CheekSide" + sd] += CAP["Face_CheekSide" + sd] * r * far
        o = g.get("oculi01." + s_, 0.0)
        mid = smooth(0.014, 0.006, ax); sde = smooth(0.036, 0.050, ax) * (1 - mid)
        acc["Face_BrowMiddle"] += CAP["Face_BrowMiddle"] * o * mid
        acc["Face_BrowSide" + sd] += CAP["Face_BrowSide" + sd] * o * sde
        acc["Face_BrowFront" + sd] += CAP["Face_BrowFront" + sd] * o * (1 - mid - sde)
    # forehead and upper cheeks have no MakeHuman bone: regions on the front of the face
    headw = g.get("head", 0) + g.get("scalp", 0) + g.get("ears", 0) + sum(w for n, w in g.items() if n.startswith("special"))
    front = smooth(EY + 0.030, EY + 0.008, y)
    fore = front * smooth(EZ + 0.026, EZ + 0.038, z) * smooth(EZ + 0.062, EZ + 0.048, z) * smooth(0.062, 0.045, ax)
    cheek = smooth(EY + 0.035, EY + 0.012, y) * smooth(EZ - 0.046, EZ - 0.026, z) * smooth(EZ - 0.006, EZ - 0.016, z) \
        * smooth(0.016, 0.028, ax) * smooth(0.070, 0.056, ax)
    acc["Face_Forehead"] += CAP["Face_Forehead"] * fore * headw
    acc["Face_CheekUpper" + side] += CAP["Face_CheekUpper" + side] * cheek * headw
    # --- neck chain and torso
    n1, n2, n3 = g.get("neck01", 0), g.get("neck02", 0), g.get("neck03", 0)
    acc["Neck"] += n1 + 0.60 * n2 + 0.15 * n3
    acc["Neck1"] += 0.25 * n2 + 0.25 * n3
    neck_head = 0.15 * n2 + 0.60 * n3
    for n, w in g.items():
        if n.startswith("clavicle"):
            sd = "Left" if n.endswith(".L") else "Right"
            acc[sd + "Shoulder"] += 0.1 * w; acc["Spine3"] += 0.9 * w
        elif n.startswith(SPINE): acc["Spine3"] += w
    acc = {b: w for b, w in acc.items() if w > 0.004}
    rest = 1.0 - sum(acc.values())
    if rest > 0: acc["Head"] = acc.get("Head", 0.0) + rest
    top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
    s = sum(v for _, v in top)
    return {k: v / s for k, v in top}


# ---------------------------------------------------------------- MLOD writer
def asciiz(s):
    return s.encode("latin1") + b"\0"


def tagg(name, data):
    return b"\x01" + asciiz(name) + struct.pack("<I", len(data)) + data


def enc_w(w):
    """selection weight byte: 0 none, 1 full, otherwise 2..255 falling from almost full to almost none"""
    if w <= 0.002: return 0
    if w >= 0.998: return 1
    return min(255, max(2, int(round((1.0 - w) * 253.0)) + 2))


def lod_bytes(res, P, faces, sels, props=(), uv=True):
    """P: (n,3) arma points; faces: list of corners (point index, inward normal, (u, v)); sels: {name: per-point weights}"""
    nidx = {}; normals = []; fl = []
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


def selections(W, n, visual):
    sels = defaultdict(lambda: np.zeros(n))
    for i, w in enumerate(W):
        for b, x in w.items():
            sels[b][i] = x
            if b in ALIAS: sels[ALIAS[b]][i] = x
    sels = dict(sels)
    if visual:
        sels["personality"] = np.ones(n)
        eyes = np.maximum(sels.get("L_Eye", np.zeros(n)), sels.get("R_Eye", np.zeros(n)))
        sels["injury_head"] = (eyes == 0).astype(float)
    return sels


def visual_lod(name, res):
    V, F, UV, N, G = load(name)
    P = to_arma(V); NA = to_arma(N)
    W = [arma_weights(G[i], V[i]) for i in range(len(V))]
    faces = []
    for f, uv, nr in zip(F, UV, NA):
        p0, p1, p2 = P[f[0]], P[f[1]], P[f[2]]
        order = [0, 2, 1] if np.dot(np.cross(p1 - p0, p2 - p0), nr.mean(0)) > 0 else [0, 1, 2]   # cross product inwards
        faces.append([(int(f[k]), -nr[k], (float(uv[k][0]), 1.0 - float(uv[k][1]))) for k in order])
    return lod_bytes(res, P, faces, selections(W, len(P), True), [("LODNoShadow", "1")]), len(P), len(faces), W


def shadow_lod():
    V, F, UV, N, G = load("shadow")
    P = to_arma(V); NA = to_arma(N)
    W = [arma_weights(G[i], V[i]) for i in range(len(V))]
    faces = []; cnt = defaultdict(int)
    twice = defaultdict(int)
    for f in F: twice[frozenset(int(i) for i in f)] += 1
    for f, nr in zip(F, NA):
        if twice[frozenset(int(i) for i in f)] > 1 or len(set(int(i) for i in f)) < 3: continue   # zero-volume fins
        p0, p1, p2 = P[f[0]], P[f[1]], P[f[2]]
        f = [int(i) for i in ([f[0], f[2], f[1]] if np.dot(np.cross(p1 - p0, p2 - p0), nr.mean(0)) > 0 else f)]
        n = np.cross(P[f[1]] - P[f[0]], P[f[2]] - P[f[0]]); n = n / (np.linalg.norm(n) + 1e-12)
        faces.append([(i, n, (0.0, 0.0)) for i in f])
        for i in range(3): cnt[(min(f[i], f[(i + 1) % 3]), max(f[i], f[(i + 1) % 3]))] += 1
    open_edges = sum(1 for v in cnt.values() if v != 2)
    return lod_bytes(10000.0, P, faces, selections(W, len(P), False), (), uv=False), len(P), len(faces), open_edges


def memory_lod():
    eL = np.array([EX, EZ, EY]); eR = np.array([-EX, EZ, EY])            # arma (x, height, depth)
    pts = [eL, eR, eL + [0, 0, -0.010], eR + [0, 0, -0.010], np.array([0, EZ + 0.021, EY + 0.086]),
           np.array([0, EZ - 0.010, EY + 0.017]), np.array([0, EZ + 0.021, EY + 0.017])]
    n = len(pts)
    def sel(*idx):
        w = np.zeros(n); w[list(idx)] = 1; return w
    sels = {
        "L_eye_center": sel(0), "EyeLeft_center": sel(0), "L_Eye": sel(0), "EyeLeft": sel(0),
        "R_eye_center": sel(1), "EYERight_center": sel(1), "R_Eye": sel(1), "EyeRight": sel(1),
        "L_pupila_center": sel(2), "PupilaLeft_center": sel(2), "R_pupila_center": sel(3), "PupilaRight_center": sel(3),
        "osobnost": sel(0, 1), "Head": sel(4, 5), "pilot": sel(6),
    }
    return lod_bytes(1e15, np.array(pts), [], sels, (), uv=False), n


def main():
    blobs = []
    for name, res in (("lod1", 1.0), ("lod2", 2.0), ("lod3", 4.0)):
        b, nv, nf, W = visual_lod(name, res); blobs.append(b); print(f"LOD {res:g}: {nv} points, {nf} faces")
        if name == "lod1":
            mx = defaultdict(float); cnt = defaultdict(int)
            for w in W:
                for k, v in w.items(): mx[k] = max(mx[k], v); cnt[k] += 1
            print("  bones:", ", ".join(f"{k} {mx[k]:.2f}/{cnt[k]}" for k in sorted(mx)))
    b, nv, nf, op = shadow_lod(); blobs.append(b); print(f"shadow: {nv} points, {nf} faces, open edges {op}")
    b, nv = memory_lod(); blobs.append(b); print(f"memory: {nv} points")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(b"MLOD" + struct.pack("<II", 257, len(blobs)) + b"".join(blobs))
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
