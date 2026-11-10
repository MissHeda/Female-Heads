"""Write the skin rvmats (Skin shader, stage layout of the vanilla A3 head materials).

usage (repo root): python -I tools/make_rvmats.py
"""
import os

D = "z\\mhfh\\addons\\heads\\data\\"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addons", "heads", "data")

UV = """    uvSource = "tex";
    class uvTransform {
        aside[] = {1, 0, 0};
        up[] = {0, 1, 0};
        dir[] = {0, 0, 0};
        pos[] = {0, 0, 0};
    };"""


def stage(n, tex):
    return f'class Stage{n} {{\n    texture = "{tex}";\n{UV}\n}};\n'


def rvmat(tone, injury):
    mc = D + "fh_injury_mc.paa" if injury else "#(argb,8,8,3)color(0,0,0,0,MC)"
    s = 'class StageTI {\n    texture = "a3\\characters_f\\heads\\data\\m_ti_ca.paa";\n};\n'
    s += """ambient[] = {2, 2, 2, 1};
diffuse[] = {0.45, 0.42, 0.4, 1};
forcedDiffuse[] = {0.2, 0.4, 0.4, 0.1};
emmisive[] = {0.8, 0.3, 0.65, 0.7};
specular[] = {0.6, 0.6, 0.6, 1};
specularPower = 30;
PixelShaderID = "Skin";
VertexShaderID = "Skin";
"""
    s += stage(1, D + "fh_nohq.paa")
    s += stage(2, mc)
    s += stage(3, D + f"fh_{tone}_co.paa")
    s += stage(4, D + "fh_as.paa")
    s += stage(5, D + "fh_smdi.paa")
    s += 'class Stage6 {\n    texture = "#(ai,64,64,1)fresnel(0.5,0.3)";\n    uvSource = "none";\n};\n'
    return s


os.makedirs(OUT, exist_ok=True)
for tone in ("light", "dark"):
    for inj in (False, True):
        name = f"fh_{tone}{'_injury' if inj else ''}.rvmat"
        open(os.path.join(OUT, name), "w", newline="\n").write(rvmat(tone, inj))
        print(name)
