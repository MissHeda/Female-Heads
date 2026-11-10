"""Write the head rvmats.

"Super" shader with the stage layout the Timberwolf female heads and the vanilla dark-skinned heads use.
The vanilla "Skin" shader multiplies the colour map with itself and with a strong ambient term; it only works with
the very dark vanilla face textures and blows a normally exposed texture out to white.
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


def stage(n, tex, extra=""):
    return f'class Stage{n} {{\n    texture = "{tex}";\n{extra}{UV}\n}};\n'


def rvmat(tone, injury):
    mc = D + "fh_injury_mc.paa" if injury else "#(argb,8,8,3)color(0,0,0,0,MC)"
    s = 'class StageTI {\n    texture = "a3\\characters_f\\heads\\data\\m_ti_ca.paa";\n};\n'
    s += """ambient[] = {1, 1, 1, 1};
diffuse[] = {1, 1, 1, 1};
forcedDiffuse[] = {0, 0, 0, 0};
emmisive[] = {0, 0, 0, 1};
specular[] = {0.12, 0.12, 0.12, 1};
specularPower = 70;
PixelShaderID = "Super";
VertexShaderID = "Super";
"""
    s += stage(1, D + "fh_nohq.paa")
    s += stage(2, "#(argb,8,8,3)color(0.5,0.5,0.5,1,DT)")
    s += stage(3, mc)
    s += stage(4, D + "fh_as.paa")
    s += stage(5, D + "fh_smdi.paa")
    s += stage(6, "#(ai,64,64,1)fresnel(0.5,0.2)")
    s += stage(7, "a3\\data_f\\env_co.paa", '    useWorldEnvMap = "true";\n')
    return s


os.makedirs(OUT, exist_ok=True)
for tone in ("light", "dark"):
    for inj in (False, True):
        name = f"fh_{tone}{'_injury' if inj else ''}.rvmat"
        open(os.path.join(OUT, name), "w", newline="\n").write(rvmat(tone, inj))
        print(name)
