import sys, difflib
import kcpsm3_dis as k
import pbreach
def load(h): return pbreach.load(h)
def _plain(w):
    m,o,info=k.decode(w)
    if 'call' in info or 'jump' in info: o=o.rsplit(' ',1)[0] if ',' in o else ''
    return m+' '+o
def norm(w, ws=None):
    m,o,info=k.decode(w)
    s=_plain(w)
    t=info.get('call',info.get('jump'))
    if ws is not None and t is not None:
        s+=' ->['+'|'.join(_plain(x) for x in ws[t:t+8])+']'
    return s
def body(ws):
    last=max(i for i in range(0x3ff) if ws[i])
    return list(range(last+1))+[0x3ff]
def diff(ha,hb,ctx=0):
    a,b=load(ha),load(hb); ia,ib=body(a),body(b)
    na=[norm(a[i],a) for i in ia]; nb=[norm(b[i],b) for i in ib]
    sm=difflib.SequenceMatcher(None,na,nb,autojunk=False)
    out=[]
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal': continue
        out.append('@@ %s  old %03X-%03X  new %03X-%03X'%(tag,ia[i1] if i1<len(ia) else 0x400,ia[i2-1] if i2>i1 else ia[i1-1],ib[j1] if j1<len(ib) else 0x400, ib[j2-1] if j2>j1 else ib[j1-1]))
        for i in range(i1,i2): out.append('  - %03X %05X  %s'%(ia[i],a[ia[i]],' '.join(k.decode(a[ia[i]])[:2])))
        for j in range(j1,j2): out.append('  + %03X %05X  %s'%(ib[j],b[ib[j]],' '.join(k.decode(b[ib[j]])[:2])))
    return sm.ratio(), out
