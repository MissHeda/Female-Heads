"""Reference data from "Task Force Timberwolf Female Characters" (Workshop 2021778690, by Iceman).

The neck base (shape and bone weights below the jaw) and the photographic hair detail of this mod follow that
head, so uniforms and helmets treat it the same way. This script reads their PBO from the Steam Workshop folder
and writes tools/ref/models/tftw_head.npz (points, triangles, bone weights) and tools/ref/tex/tftw_*.png.
usage (repo root): python -I tools/ref_tftw.py
"""
import json, os, struct, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
PBO = r"C:\SteamLibrary\steamapps\workshop\content\107410\2021778690\Addons\A3_female_heads.pbo"
NODE = r"C:\Users\Heda\Desktop\Arma stuff\debin (neu)\node.exe"
ODOL = r"C:\Users\Heda\GitHub Repos\Arma-Modding-Tools-debin\tools\debin\odol.mjs"
TOPAA = r"D:\Steam\steamapps\common\Arma 3 Tools\ImageToPAA\ImageToPAA.exe"
TMP = os.path.join(HERE, "ref", "tftw"); os.makedirs(TMP, exist_ok=True)
os.makedirs(os.path.join(HERE, "ref", "models"), exist_ok=True); os.makedirs(os.path.join(HERE, "ref", "tex"), exist_ok=True)


def entries(path):
    h = open(path, "rb"); ents = []; first = True
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
    off = h.tell(); out = {}
    for n, s in ents:
        h.seek(off); out[n.replace("/", "\\").lower()] = h.read(s); off += s
    return out


# their editable (unbinarized) models: the new characters are reshaped copies of these
UNBIN = os.path.join(os.path.dirname(os.path.dirname(PBO)), "Unbinarized - for editing.7z")
if not os.path.exists(os.path.join(TMP, "unbin", "A3_female_heads - UB", "Models", "female_head_bun.p3d")):
    os.makedirs(os.path.join(TMP, "unbin"), exist_ok=True)
    subprocess.run([r"C:\Windows\System32\tar.exe", "-xf", UNBIN, "-C", os.path.join(TMP, "unbin")], check=True)

files = entries(PBO)
want = {"models\\female_head_bun.p3d": "head.p3d"}
for i in (1, 2, 3, 4):
    want[f"female_head_iceman\\female_0{i}\\xxx_co.paa"] = f"face_0{i}.paa"
want["female_head_iceman\\female_01\\f_hl_co.paa"] = "hands_01.paa"
want["female_head_iceman\\female_03\\f_hl_co.paa"] = "hands_03.paa"
want["hair\\hair_01_co.paa"] = "hair_01.paa"            # photo of a braid (top strip) and a bun
for k, v in want.items():
    open(os.path.join(TMP, v), "wb").write(files[k])
for n in [v[:-4] for v in want.values() if v.endswith(".paa")]:
    subprocess.run([TOPAA, os.path.join(TMP, n + ".paa"), os.path.join(HERE, "ref", "tex", n + ".png")], check=True, stdout=subprocess.DEVNULL)
js = os.path.join(TMP, "head.json")
subprocess.run([NODE, os.path.join(HERE, "odump.mjs"), ODOL, os.path.join(TMP, "head.p3d"), js], check=True, stdout=subprocess.DEVNULL)
m = json.load(open(js)); L = m["lods"][0]
bones = [b[0].lower() for b in m["info"]["skeleton"]["bones"]]
P = np.array(L["positions"]) + np.array(m["info"]["boundingCenter"])
F = np.array([t for f in L["faces"] for t in ([f[:3]] if len(f) == 3 else [f[:3], [f[0], f[2], f[3]]])])
s2s = L["subSkelToSkel"]; used = sorted({s2s[i] for refs in L["boneRef"] for i, w in refs if w})
col = {b: k for k, b in enumerate(used)}
W = np.zeros((len(P), len(used)))
for vi, refs in enumerate(L["boneRef"]):
    tot = sum(w for _, w in refs) or 1
    for i, w in refs:
        if w: W[vi, col[s2s[i]]] += w / tot
names = [bones[b] for b in used]
eye = W[:, [names.index("eyeleft"), names.index("eyeright")]].sum(1) > 0.5
uv = np.array(L["uvSets"][0]).reshape(-1, 2)
np.savez(os.path.join(HERE, "ref", "models", "tftw_head.npz"), P=P, F=F, W=W, bones=np.array(names), eye=eye, uv=uv)
print(len(P), "points", len(F), "triangles", len(names), "bones ->", os.path.join("tools", "ref", "models", "tftw_head.npz"))
