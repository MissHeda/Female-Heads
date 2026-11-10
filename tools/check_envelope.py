"""Compare the skull (without the bun) with the reference envelope of a vanilla-compatible head.

Helmets, glasses and masks are modelled around the vanilla head, so the head should not stick out of it.
tools/reference_envelope.json holds the largest radius per direction bin, measured once on a reference head.
usage (repo root): python -I tools/check_envelope.py
"""
import json, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ref = json.load(open(os.path.join(HERE, "reference_envelope.json"))); d = np.load(os.path.join(HERE, "bake", "lod1.npz"))
names = [str(n) for n in d["names"]]; V = d["V"]; bun = names.index("FH_p_bun")
isbun = np.zeros(len(V), bool)
for vi, gi, w in d["G"]:
    if int(gi) == bun and w > 0.5: isbun[int(vi)] = True
Q = np.stack([V[:, 0], V[:, 2], V[:, 1]], -1)[~isbun]              # arma (x, height, depth)
c = np.array(ref["c"]); D = Q - c; r = np.linalg.norm(D, axis=1)
el = np.degrees(np.arcsin(D[:, 1] / r)); az = np.degrees(np.arctan2(np.abs(D[:, 0]), -D[:, 2]))
out = []
for k, rr in ref["env"].items():
    e0, a0 = map(int, k.split(","))
    m = (el >= e0) & (el < e0 + 15) & (az >= a0) & (az < a0 + 20)
    if m.sum(): out.append(((r[m].max() - rr) * 1000, e0, a0))
out.sort(reverse=True)
print("sticks out most (mm, elevation, azimuth from the face):", [(round(v, 1), e, a) for v, e, a in out[:8]])
up = [v for v, e, a in out if e >= 15]
print(f"helmet zone (elevation >= 15): max {max(up):+.1f} mm, mean {np.mean(up):+.1f} mm")
print(f"top {Q[:, 1].max():.4f} (reference 0.8091), half width {np.abs(Q[:, 0]).max():.4f} (0.0892), back {Q[Q[:, 1] > 0.6][:, 2].max():.4f} (0.0795)")
