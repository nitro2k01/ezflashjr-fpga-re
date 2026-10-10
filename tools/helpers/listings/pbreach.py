import kcpsm3_dis as k
# Programs are registered by the build script (key = short md5 of the words).
PROGRAMS = {}
def load(h): return list(PROGRAMS[h])
def reach(w, entries=(0,0x3ff)):
    seen=set(); todo=list(entries)
    while todo:
        a=todo.pop()
        while a not in seen and 0<=a<1024:
            seen.add(a); op=w[a]>>12; t=w[a]&0x3ff
            if op==0x34: todo.append(t); break
            if op in (0x35,0x30,0x31): todo.append(t)
            if op in (0x2A,0x38): break
            a+=1
    return seen
def dead_ranges(w):
    s=reach(w); last=max(i for i in range(0x3ff) if w[i])
    r=[];st=None
    for a in range(last+1):
        d=a not in s
        if d and st is None: st=a
        if not d and st is not None: r.append((st,a-1)); st=None
    if st is not None: r.append((st,last))
    return r
