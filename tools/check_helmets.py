"""Does the head poke through vanilla headgear, and does it stay inside the vanilla head?

For every head point a ray from the head centre is cast against vanilla headgear (tools/ref/models/*.npz, made
by tools/ref_dump.py from the game files). A point shows through when it lies beyond the outermost surface of the
headgear along that ray. The vanilla head is the baseline: headgear is modelled around it, so whatever shows on
the vanilla head (ears under a cap, the face) is by design; only points that show MORE than vanilla count.
usage (repo root): python -I tools/check_helmets.py [lod1|<npz>]
"""
import glob, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import raycast

REF = os.path.join(HERE, "ref", "models")


def own_head(name="lod1"):
    d = np.load(os.path.join(HERE, "bake", name + ".npz"))
    names = [str(n) for n in d["names"]]; V = d["V"]
    part = {}
    for vi, gi, w in d["G"]:
        n = names[int(gi)]
        if n.startswith("FH_p_") and w > 0.5: part[int(vi)] = n[5:]
    P = np.stack([V[:, 0], V[:, 2], V[:, 1]], -1)
    kind = np.array([part.get(i, "skin") for i in range(len(P))])
    return P, d["F"], kind


def report(tag, P, sel, helmets, van):
    """points beyond the outer headgear surface, not counting directions where the vanilla head shows too"""
    dirs, r = raycast.radial(P[sel]); _, vfar = raycast.hits(dirs, *van)
    print(f"{tag}: {sel.sum()} points")
    worst = 0.0
    for hn, (HP, HF) in helmets.items():
        _, far = raycast.hits(dirs, HP, HF)
        cov = ~np.isnan(far)
        vanilla_shows = cov & ~np.isnan(vfar) & (vfar > far + 0.0005)
        out = cov & ~vanilla_shows & (r > far + 0.0005)
        deep = float((r - far)[out].max() * 1000) if out.any() else 0.0
        clear = float(np.percentile((far - r)[cov & ~vanilla_shows], 5) * 1000) if (cov & ~vanilla_shows).any() else float("nan")
        worst = max(worst, deep)
        print(f"   {hn:34s} covered {int(cov.sum()):5d}  showing through {int(out.sum()):4d}  deepest {deep:5.1f} mm  tight spots (5%) {clear:5.1f} mm of air")
    return worst


def main():
    helmets = {}
    for p in sorted(glob.glob(os.path.join(REF, "*.npz"))):
        n = os.path.basename(p)[:-4]
        if n.startswith("Heads_"): continue
        d = np.load(p); helmets[n.split("_", 1)[1]] = (d["P"], d["F"])
    van = np.load(os.path.join(REF, "Heads_m_white_01.npz"))
    VP = van["P"]
    vn = (VP, van["F"])
    P, F, kind = own_head(sys.argv[1] if len(sys.argv) > 1 else "lod1")
    up = P[:, 1] > 0.60
    w1 = report("own head, skin + hair", P, up & (kind == "skin"), helmets, vn)
    w2 = report("own head, bun", P, kind == "bun", helmets, vn)
    print(f"worst case: skin/hair {w1:.1f} mm, bun {w2:.1f} mm through any headgear")
    # inside the vanilla head? (outermost vanilla surface along the same ray)
    sel = up & (kind == "skin")
    dirs, r = raycast.radial(P[sel]); _, far = raycast.hits(dirs, VP, van["F"])
    ex = (r - far) * 1000; ok = ~np.isnan(ex)
    hz = ok & (P[sel][:, 1] > 0.725)
    print(f"against the vanilla head: helmet zone (above the brows) max {np.nanmax(ex[hz]):+.1f} mm, "
          f"whole head max {np.nanmax(ex[ok]):+.1f} mm, points outside by > 1 mm: {(ex[ok] > 1).sum()} of {ok.sum()}")


if __name__ == "__main__":
    main()
