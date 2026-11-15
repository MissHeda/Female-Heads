"""Stronger mouth movement for the Timberwolf female head.

The Timberwolf head ties its mouth area only loosely to the face bones (much of every lip vertex still follows
"head"), so the game's lip sync opens it about half as far as on a vanilla head. boost() moves weight from "head"
to the face bones around the mouth, in every LOD that has them; the face bones themselves and their shares among
each other stay as they are.
Check: python -I tools/lipboost.py [factor]   (replays the vanilla speech poses, like tools/simulate.py)
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mlod

# bones that move the mouth during speech
MOUTH = ["face_jawbone", "face_jowl", "face_chopright", "face_chopleft", "face_liplowermiddle", "face_liplowerleft",
         "face_liplowerright", "face_chin", "face_tongue", "face_cornerright", "face_cornerleft", "face_lipuppermiddle",
         "face_lipupperright", "face_lipupperleft"]
FACTOR = 2.0


def encode_weight(w):
    """weight -> selection byte (inverse of mlod.decode_weight)"""
    if w <= 0.0: return 0
    if w >= 0.995: return 1
    return int(min(255, max(3, round(2 + round((1.0 - w) * 100) * 2.55555))))


def boost(b, factor=FACTOR):
    """MLOD bytes -> MLOD bytes with the mouth bones weighted factor times as strong against "head" """
    b = bytearray(b); _, lods = mlod.read_bytes(bytes(b))
    for L in lods:
        tags = {n.lower(): (off, size) for n, off, size in L.tags if size == L.npoints + L.nfaces}
        if "head" not in tags or not any(m in tags for m in MOUTH): continue
        n = L.npoints
        head_off = tags["head"][0]
        head = mlod._WTAB[np.frombuffer(bytes(b[head_off:head_off + n]), np.uint8)].astype(np.float64)
        mouth = {m: (tags[m][0], mlod._WTAB[np.frombuffer(bytes(b[tags[m][0]:tags[m][0] + n]), np.uint8)].astype(np.float64))
                 for m in MOUTH if m in tags}
        ms = sum(w for _, w in mouth.values())
        for i in np.nonzero((ms > 0) & (head > 0))[0]:
            # the mouth bones take over (factor - 1) times their weight from "head", at most all of it
            take = min(head[i], ms[i] * (factor - 1.0))
            b[head_off + i] = encode_weight(head[i] - take)
            for off, w in mouth.values():
                if w[i] > 0: b[off + i] = encode_weight(w[i] * (1.0 + take / ms[i]))
    return bytes(b)


def lip_gaps(b):
    """lip gap (mm) of the first LOD for the vanilla speech poses, skinned like the engine (4 bones, normalized)"""
    import rtm, simulate
    _, lods = mlod.read_bytes(b); L = lods[0]
    names = list(L.selections)
    W = np.stack([L.selections[s][0] for s in names], 1)
    low = [s.lower() for s in names]
    bones = set(MOUTH) | {"head", "neck", "neck1"} | {s for s in low if s.startswith("face_") or s.startswith("eye")}
    cols = [i for i, s in enumerate(low) if s in bones]
    Ws = []
    for row in W[:, cols]:
        top = np.argsort(-row)[:4]
        d = {low[cols[j]]: row[j] for j in top if row[j] > 0}
        t = sum(d.values()) or 1; Ws.append({k: v / t for k, v in d.items()})
    P = L.points
    out = {}
    for a in ["vizem_A", "vizem_E", "vizem_F", "vizem_M", "vizem_Y"]:
        _, frames, _ = rtm.read(os.path.join(HERE, "ref", "anim", f"Heads_Anim_male_{a}.rtm"))
        out[a] = round(simulate.lip_gap(P, simulate.pose(P, Ws, frames[-1])) * 1000, 2)
    return out


if __name__ == "__main__":
    src = open(os.path.join(HERE, "ref", "tftw", "unbin", "A3_female_heads - UB", "Models", "female_head_bun.p3d"), "rb").read()
    print("original ", lip_gaps(src))
    for f in [float(x) for x in sys.argv[1:]] or [FACTOR]:
        print(f"factor {f}", lip_gaps(boost(src, f)))
