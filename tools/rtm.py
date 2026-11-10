"""Reader for binarized Arma 3 animations (BMTR v5), used to replay the vanilla face animations on the head offline.

read(path) -> (bone_names, frames); frames[f][bone] = (quat xyzw, pos xyz).
A bone transform maps a rest-pose model-space point p to q*p + pos (absolute, not hierarchical).
"""
import struct
import numpy as np


def lzo1x(src, pos, out_len):
    """LZO1X stream decoder (port of the decoder in Arma-Modding-Tools tools/debin/odol.mjs)"""
    out = bytearray(out_len); ip = pos; op = 0; state = 0

    def literals(n):
        nonlocal ip, op
        out[op:op + n] = src[ip:ip + n]; op += n; ip += n

    def back(dist, ln):
        nonlocal op
        fr = op - dist
        if dist < 1 or fr < 0: raise ValueError("LZO lookbehind overrun")
        for _ in range(ln):
            out[op] = out[fr]; op += 1; fr += 1

    def ext(base):
        nonlocal ip
        n = 0
        while src[ip] == 0: n += 255; ip += 1
        n += src[ip]; ip += 1
        return base + n

    def tail(s):
        nonlocal state
        if s: literals(s)
        state = s

    def le16():
        nonlocal ip
        v = src[ip] | (src[ip + 1] << 8); ip += 2; return v

    if src[ip] > 17:
        n = src[ip] - 17; ip += 1; literals(n); state = n if n < 4 else 4
    while True:
        t = src[ip]; ip += 1
        if t < 16:
            if state == 0:
                literals(3 + t if (t & 15) else ext(18)); state = 4
            elif state < 4:
                d = 1 + (t >> 2) + (src[ip] << 2); ip += 1; back(d, 2); tail(t & 3)
            else:
                d = 2049 + (t >> 2) + (src[ip] << 2); ip += 1; back(d, 3); tail(t & 3)
        elif t < 32:
            ln = 2 + (t & 7) if (t & 7) else ext(9); v = le16(); dist = 16384 + ((t & 8) << 11) + (v >> 2)
            if dist == 16384:
                if op != out_len: raise ValueError(f"LZO output underrun {op}/{out_len}")
                return bytes(out), ip
            back(dist, ln); tail(v & 3)
        elif t < 64:
            ln = 2 + (t & 31) if (t & 31) else ext(33); v = le16()
            back(1 + (v >> 2), ln); tail(v & 3)
        else:
            d = 1 + ((t >> 2) & 7) + (src[ip] << 3); ip += 1
            back(d, 3 + ((t >> 5) & 1) if t < 128 else 5 + ((t >> 5) & 3)); tail(t & 3)


def _array(b, o, elem):
    """v5 array: u32 count, u8 flag (2 = LZO), data"""
    n = struct.unpack_from("<I", b, o)[0]; o += 4
    flag = b[o]; o += 1
    size = n * elem
    if flag == 2:
        data, o = lzo1x(b, o, size)
    else:
        data = b[o:o + size]; o += size
    return n, data, o


def read(path):
    b = open(path, "rb").read()
    assert b[:4] == b"BMTR", "not a binarized RTM"
    ver = struct.unpack_from("<I", b, 4)[0]
    assert ver == 5, f"BMTR version {ver} not supported"
    o = 8 + 1 + 12
    nframes, _generic, nbones, nbones2 = struct.unpack_from("<4I", b, o); o += 16
    names = []
    for _ in range(nbones):
        e = b.index(b"\0", o); names.append(b[o:e].decode("latin1").lower()); o = e + 1
    nprops = struct.unpack_from("<I", b, o)[0]; o += 4
    for _ in range(nprops):
        o += 4
        for _ in range(2): o = b.index(b"\0", o) + 1
    o += 4                                 # unknown, 0 in every face animation
    _n, times, o = _array(b, o, 4)         # frame times
    frames = []
    for _ in range(nframes):
        n, data, o = _array(b, o, 14)
        raw = np.frombuffer(data, dtype="<i2").reshape(n, 7)
        quat = raw[:, :4].astype(np.float64) / 16384.0
        pos = np.frombuffer(raw[:, 4:].astype("<i2").tobytes(), dtype="<f2").reshape(n, 3).astype(np.float64)
        frames.append({names[i]: (quat[i], pos[i]) for i in range(n)})
    return names, frames, np.frombuffer(times, dtype="<f4")


def rotate(q, p):
    """rotate points p (n,3) by quaternion q = (x, y, z, w)"""
    x, y, z, w = q
    u = np.array([x, y, z]); p = np.asarray(p, dtype=np.float64)
    return p + 2 * np.cross(u, np.cross(u, p) + w * p)


if __name__ == "__main__":
    import sys
    names, frames, times = read(sys.argv[1])
    print(len(names), "bones", len(frames), "frames", times[:5])
    for n in names:
        q, p = frames[0][n]
        if n.startswith("face_") or n in ("head", "neck", "neck1", "eyeleft", "eyeright", "pelvis"):
            ang = 2 * np.degrees(np.arccos(min(1, abs(q[3]))))
            print(f"{n:24s} rot {ang:6.2f} deg  q=({q[0]:+.3f},{q[1]:+.3f},{q[2]:+.3f},{q[3]:+.3f})  pos=({p[0]:+.4f},{p[1]:+.4f},{p[2]:+.4f})")
