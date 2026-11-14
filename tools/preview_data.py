"""Take the binarized models out of the built PBO and turn them into small npz files for the preview render and the
animation check (tools/check/<model>.npz with points, triangles, UVs; tools/check/<model>.json for simulate.py).
usage (repo root, after hemtt build): python -I tools/preview_data.py
"""
import json, os, struct, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
PBO = os.path.join(HERE, "..", ".hemttout", "build", "addons", "mhfh_heads.pbo")
NODE = r"C:\Users\Heda\Desktop\Arma stuff\debin (neu)\node.exe"
ODOL = r"C:\Users\Heda\GitHub Repos\Arma-Modding-Tools-debin\tools\debin\odol.mjs"
OUT = os.path.join(HERE, "check"); os.makedirs(OUT, exist_ok=True)

h = open(PBO, "rb"); ents = []; first = True
def asciiz():
    s = bytearray()
    while (c := h.read(1)) and c != b"\0": s += c
    return bytes(s)
while True:
    name = asciiz(); pack, orig, res, ts, size = struct.unpack("<5I", h.read(20))
    if first and not name and pack == 0x56657273:
        while asciiz(): pass
        first = False; continue
    first = False
    if not name: break
    ents.append((name.decode("latin-1"), size))
off = h.tell()
for n, s in ents:
    if n.lower().endswith(".p3d"):
        base = os.path.splitext(os.path.basename(n.replace("\\", "/")))[0]
        h.seek(off); p = os.path.join(OUT, base + ".p3d"); open(p, "wb").write(h.read(s))
        js = os.path.join(OUT, base + ".json")
        subprocess.run([NODE, os.path.join(HERE, "odump.mjs"), ODOL, p, js], check=True, stdout=subprocess.DEVNULL)
        m = json.load(open(js)); L = m["lods"][0]
        P = np.array(L["positions"]) + np.array(m["info"]["boundingCenter"])
        F = np.array([t for f in L["faces"] for t in ([f[:3]] if len(f) == 3 else [f[:3], [f[0], f[2], f[3]]])])
        uv = np.array(L["uvSets"][0]).reshape(-1, 2)
        np.savez(os.path.join(OUT, base + ".npz"), P=P, F=F, uv=uv)
        sk = m["info"]["skeleton"]
        print(f"{base:26s} {len(P):5d} verts {len(F):5d} tris  skeleton {sk.get('name')!r} {len(sk.get('bones', []))} bones")
        os.remove(p)
    off += s
