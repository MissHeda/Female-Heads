"""Hair layout shared by the Blender build (hair volume) and the texture composer (hair painting).

Coordinates are the fitted head space used in Blender: x right-left, y depth (face at -y), z up; the eye
centres sit at (+-0.0325, -0.0873, 0.705), exactly on the vanilla eye bone pivots.
"""
import numpy as np

EYE_Z = 0.705
CENTRE_Y = -0.012          # vertical axis of the skull
TOP_Z = 0.8055             # skull top without hair (vanilla skull top is 0.809)

# hairline: height above the eye centre as a function of the angle around the vertical axis (0 front, pi back)
_T = np.array([0.00, 0.40, 0.75, 1.00, 1.20, 1.36, 1.50, 1.68, 1.88, 2.05, 2.25, 2.60, np.pi])
_H = np.array([0.047, 0.046, 0.042, 0.034, 0.020, 0.010, 0.016, 0.022, 0.014, -0.014, -0.052, -0.088, -0.098])


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def strands(u, v, freq, seed, n=24):
    """1D strand noise across u (sum of sines with random phases), slowly wobbling along v, range 0..1"""
    r = np.random.default_rng(seed); s = np.zeros_like(u, dtype=np.float64)
    for _ in range(n):
        f = freq * r.uniform(0.5, 2.0); ph = r.uniform(0, 6.283); w = r.uniform(0.3, 1.0)
        s += w * np.sin(u * f + ph + 0.6 * np.sin(v * r.uniform(5, 25) + ph))
    return 0.5 + 0.5 * s / (np.abs(s).max() + 1e-9)


def theta(P):
    return np.abs(np.arctan2(P[..., 0], -(P[..., 1] - CENTRE_Y)))


def hairline_height(P):
    t = theta(P)
    # smoothed piecewise curve: average over a small angle window so the line has no corners
    return EYE_Z + sum(np.interp(t + d, _T, _H) for d in (-0.08, -0.04, 0.0, 0.04, 0.08)) / 5.0


def hair_mask(P, soft=0.006, jitter=None):
    """0..1 hair coverage of the scalp at the points P; jitter (same shape, metres) frays the edge"""
    z = P[..., 2] + (jitter if jitter is not None else 0.0)
    hl = hairline_height(P)
    return smooth(hl - soft * 0.4, hl + soft, z)
