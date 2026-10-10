"""Carry annotations from one program version to another via instruction alignment."""
import difflib, pbdiff, pbreach
def addr_map(src, dst):
    a, b = pbreach.load(src), pbreach.load(dst)
    ia, ib = list(range(1024)), list(range(1024))
    na = [pbdiff.norm(a[i], a) for i in ia]; nb = [pbdiff.norm(b[i], b) for i in ib]
    sm = difflib.SequenceMatcher(None, na, nb, autojunk=False)
    m = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1):
            for d in range(i2 - i1):
                x, y = a[ia[i1 + d]], b[ib[j1 + d]]
                if tag == 'equal' or (x >> 12) == (y >> 12):
                    m[ia[i1 + d]] = ib[j1 + d]
    return m
def transfer(src, dst, N, C, H):
    m = addr_map(src, dst)
    n2 = {m[a]: v for a, v in N.items() if a in m}
    c2 = {m[a]: v for a, v in C.items() if a in m}
    h2 = {m[a]: v for a, v in H.items() if a in m}
    lost = sorted(a for a in set(N) | set(C) | set(H) if a not in m)
    return n2, c2, h2, lost
