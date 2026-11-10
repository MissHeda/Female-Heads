import struct, sys, os, re
def entries(path):
    h=open(path,'rb'); ents=[]; first=True
    def asciiz():
        s=bytearray()
        while (c:=h.read(1)) and c!=b"\0": s+=c
        return bytes(s)
    while True:
        name=asciiz(); pack,orig,res,ts,size=struct.unpack("<5I",h.read(20))
        if first and not name and pack==0x56657273:
            while asciiz(): pass
            first=False; continue
        first=False
        if not name: break
        ents.append((name.decode("latin-1"),size))
    return h, h.tell(), ents
pbo, pat, out = sys.argv[1], re.compile(sys.argv[2], re.I), sys.argv[3]
h, off, ents = entries(pbo); os.makedirs(out, exist_ok=True)
for n,s in ents:
    if pat.search(n):
        h.seek(off); open(os.path.join(out, n.replace("\\","_").replace("/","_")),'wb').write(h.read(s)); print(n,s)
    off+=s
