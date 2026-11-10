"""Turn vanilla models (extracted with tools/pbox.py into tools/ref/models) into small npz files (points, triangles)
for the fit and the helmet check. Needs the ODOL reader of Arma-Modding-Tools (tools/odump.mjs).
usage (repo root): python -I tools/ref_dump.py
"""
import glob, json, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
NODE = r"C:\Users\Heda\Desktop\Arma stuff\debin (neu)\node.exe"
ODOL = r"C:\Users\Heda\GitHub Repos\Arma-Modding-Tools-debin\tools\debin\odol.mjs"
for p in sorted(glob.glob(os.path.join(HERE, "ref", "models", "*.p3d"))):
    js = p[:-4] + ".json"
    subprocess.run([NODE, os.path.join(HERE, "odump.mjs"), ODOL, p, js], check=True, stdout=subprocess.DEVNULL)
    m = json.load(open(js)); os.remove(js)
    L = min((l for l in m["lods"] if l["res"] < 900 and l["positions"]), key=lambda l: l["res"])
    c = np.array(m["info"]["boundingCenter"]); P = np.array(L["positions"]) + c
    F = np.array([t for f in L["faces"] for t in ([f[:3]] if len(f) == 3 else [f[:3], [f[0], f[2], f[3]]])])
    np.savez(p[:-4] + ".npz", P=P, F=F)
    print(f"{os.path.basename(p):42s} lod {L['res']:g}: {len(P)} verts, {len(F)} tris, y {P[:,1].min():.3f}..{P[:,1].max():.3f}, x +-{np.abs(P[:,0]).max():.3f}, z {P[:,2].min():.3f}..{P[:,2].max():.3f}")
