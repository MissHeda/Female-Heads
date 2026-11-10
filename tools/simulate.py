"""Replay vanilla face animations (binarized RTMs) on a binarized head, offline.

Reads the head as the engine gets it (ODOL dumped to JSON by tools/odump.mjs: normalized bone weights, at most
four per vertex) and skins it with the bone transforms of an RTM frame: v' = sum_b w_b * (R_b v + t_b).
RTM transforms live in the engine frame, which is the model frame turned 180 degrees around the vertical axis
(x and z negated), with the quaternion conjugated. Checked against A3\anims_f_data\skeleton\SkeletonPivots.p3d:
with this convention the rotation axes of dead.rtm pass within 0.4 mm of the bone pivots.
usage (repo root): python -I tools/simulate.py <head.json> <anim dir> [out.npz]
"""
import json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtm


def load_head(path, lod=0):
    m = json.load(open(path)); L = m["lods"][lod]
    bones = [b[0].lower() for b in m["info"]["skeleton"]["bones"]]
    c = np.array(m["info"]["boundingCenter"])
    P = np.array(L["positions"]) + c
    F = np.array([t for f in L["faces"] for t in ([f[:3]] if len(f) == 3 else [f[:3], [f[0], f[2], f[3]]])])
    uv = np.array(L["uvSets"][0]).reshape(-1, 2) if L["uvSets"] and len(L["uvSets"][0]) == 2 * len(P) else None
    s2s = L["subSkelToSkel"]
    W = []
    for refs in L["boneRef"]:
        tot = sum(w for _, w in refs) or 1
        W.append({bones[s2s[i]]: w / tot for i, w in refs if w})
    return P, F, uv, W, bones


def bone_matrix(q, t):
    """model-space 3x3 + translation of an RTM bone transform"""
    qq = (q[0], -q[1], q[2], q[3])
    R = np.array([rtm.rotate(qq, e) for e in np.eye(3)]).T
    return R, np.array([-t[0], t[1], -t[2]])


def pose(P, W, frame):
    out = np.zeros_like(P)
    mats = {b: bone_matrix(q, t) for b, (q, t) in frame.items()}
    I = (np.eye(3), np.zeros(3))
    for i, (p, w) in enumerate(zip(P, W)):
        acc = np.zeros(3); tot = 0.0
        for b, wt in w.items():
            R, t = mats.get(b, I); acc += wt * (R @ p + t); tot += wt
        out[i] = acc / tot if tot else p
    return out


def lip_gap(P, Pd):
    """vertical opening between the lips at the middle of the mouth (m), measured on the deformed head"""
    m = (np.abs(P[:, 0]) < 0.006) & (P[:, 2] < -0.095) & (P[:, 1] > 0.61) & (P[:, 1] < 0.67)
    if m.sum() < 4: return float("nan")
    d = (Pd - P)[m, 1]; y = P[m, 1]
    up = d[y > np.median(y)]; lo = d[y <= np.median(y)]
    return float(up.mean() - lo.mean())


ANIMS = ["vizem_A", "vizem_E", "vizem_F", "vizem_I", "vizem_M", "vizem_V", "vizem_Y", "hurt", "dead", "unconscious", "danger", "safe"]


def run(head_json, anim_dir, out=None, quiet=False):
    P, F, uv, W, bones = load_head(head_json)
    used = sorted({b for w in W for b in w})
    res = {"P": P, "F": F, "uv": uv if uv is not None else np.zeros((len(P), 2))}
    rows = []
    for a in ANIMS:
        f = os.path.join(anim_dir, f"Heads_Anim_male_{a}.rtm")
        if not os.path.exists(f): continue
        names, frames, times = rtm.read(f)
        Pd = pose(P, W, frames[-1])
        d = np.linalg.norm(Pd - P, axis=1)
        # stretch: edge length ratio after/before, worst edges show tearing
        e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        l0 = np.linalg.norm(P[e[:, 0]] - P[e[:, 1]], axis=1); l1 = np.linalg.norm(Pd[e[:, 0]] - Pd[e[:, 1]], axis=1)
        ok = l0 > 1e-5; ratio = l1[ok] / l0[ok]
        rows.append((a, d.max() * 1000, lip_gap(P, Pd) * 1000, np.percentile(ratio, 99.5), ratio.max(), float((d > 0.0005).mean())))
        res[a] = Pd
    if not quiet:
        print(f"{len(P)} verts, {len(used)} bones used")
        print("anim          max move mm   lip gap mm   stretch p99.5   stretch max   moving share")
        for r in rows: print(f"{r[0]:12s} {r[1]:10.1f} {r[2]:12.1f} {r[3]:13.2f} {r[4]:13.2f} {r[5]:12.2f}")
    if out: np.savez(out, **res)
    return rows, res


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
