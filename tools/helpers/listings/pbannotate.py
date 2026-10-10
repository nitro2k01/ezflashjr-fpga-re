"""Emit a commented, re-assemblable KCPSM3 listing from program words + annotations."""
import kcpsm3_dis as k
import pbreach

SHIFT = {0x06: "SL0", 0x07: "SL1", 0x04: "SLX", 0x00: "SLA", 0x02: "RL",
         0x0E: "SR0", 0x0F: "SR1", 0x0A: "SRX", 0x08: "SRA", 0x0C: "RR"}
ALU = {0x00: "LOAD", 0x0A: "AND", 0x0C: "OR", 0x0E: "XOR", 0x12: "TEST",
       0x14: "COMPARE", 0x18: "ADD", 0x1A: "ADDCY", 0x1C: "SUB", 0x1E: "SUBCY"}
COND = ["Z", "NZ", "C", "NC"]


def fmt(w, label_of):
    op, x, y, kk, aaa = w >> 12, (w >> 8) & 15, (w >> 4) & 15, w & 0xFF, w & 0x3FF
    sx, sy = "s%X" % x, "s%X" % y
    b = op & ~1
    if b in ALU:
        return "%-8s %s, %s" % (ALU[b], sx, sy if op & 1 else "%02X" % kk)
    if b in (0x04, 0x2C, 0x06, 0x2E):
        name = {0x04: "INPUT", 0x2C: "OUTPUT", 0x06: "FETCH", 0x2E: "STORE"}[b]
        return "%-8s %s, %s" % (name, sx, "(%s)" % sy if op & 1 else "%02X" % kk)
    if op == 0x20:
        return "%-8s %s" % (SHIFT[kk & 15], sx)
    if b in (0x30, 0x34):
        name = "CALL" if b == 0x30 else "JUMP"
        t = label_of(aaa)
        return "%-8s %s" % (name, ("%s, %s" % (COND[(w >> 10) & 3], t)) if op & 1 else t)
    if b == 0x2A:
        return "RETURN" + (" %s" % COND[(w >> 10) & 3] if op & 1 else "")
    if op == 0x38:
        return "RETURNI  " + ("ENABLE" if w & 1 else "DISABLE")
    if op == 0x3C:
        return ("ENABLE" if w & 1 else "DISABLE") + " INTERRUPT"
    raise ValueError("cannot format %05X" % w)


def emit(words, names, comments, headers, title, out, entries=(0, 0x3FF)):
    """names: addr->label, comments: addr->str, headers: addr->multiline str."""
    reach = pbreach.reach(words, entries)
    # every jump/call target needs a label
    targets = set()
    for w in words:
        m, o, info = k.decode(w)
        t = info.get("call", info.get("jump"))
        if t is not None:
            targets.add(t)
    labels = dict(names)
    for t in targets:
        labels.setdefault(t, "L_%03X" % t)

    def label_of(a):
        return labels[a]

    # collapse unreachable zero-padding runs (>= 8 words) into ADDRESS directives
    skip = set()
    a = 0
    while a < 1024:
        if words[a] == 0 and a not in reach and a not in labels:
            b = a
            while b < 1024 and words[b] == 0 and b not in reach and b not in labels:
                b += 1
            if b - a >= 8:
                skip.update(range(a, b))
            a = b
        else:
            a += 1
    lines = [title.rstrip(), ""]
    gap = False
    for a in range(1024):
        if a in skip:
            gap = True
            continue
        if gap or a == 0:
            lines.append("")
            lines.append("            ADDRESS %03X" % a)
            gap = False
        if a in headers:
            lines.append("")
            for h in headers[a].strip("\n").splitlines():
                lines.append(("; " + h).rstrip())
        if a in labels:
            lines.append("%s:" % labels[a])
        ins = fmt(words[a], label_of)
        c = comments.get(a, "")
        dead = "" if a in reach else "[unreachable] "
        lines.append(("            %-30s ; %03X  %s%s" % (ins, a, dead, c)).rstrip())
    open(out, "w").write("\n".join(lines) + "\n")
