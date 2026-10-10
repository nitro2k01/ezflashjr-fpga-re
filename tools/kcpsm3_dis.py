#!/usr/bin/env python3
"""
Minimal PicoBlaze (KCPSM3) disassembler.

Usage: kcpsm3_dis.py <prog.psm.hex>      (one 18-bit hex word per line, 1024 lines)

Output: listing with auto labels, plus cross-references of I/O ports,
scratchpad addresses and call targets.
"""
import sys
from collections import defaultdict

ALU = {0x00: "LOAD", 0x0A: "AND", 0x0C: "OR", 0x0E: "XOR", 0x12: "TEST",
       0x14: "COMPARE", 0x18: "ADD", 0x1A: "ADDCY", 0x1C: "SUB", 0x1E: "SUBCY"}
SHIFT = {0x06: "SL0", 0x07: "SL1", 0x04: "SLX", 0x00: "SLA", 0x02: "RL",
         0x0E: "SR0", 0x0F: "SR1", 0x0A: "SRX", 0x08: "SRA", 0x0C: "RR"}
COND = ["Z", "NZ", "C", "NC"]


def decode(w):
    """Return (mnemonic, operands, info) where info has keys for xrefs."""
    op, x, y, kk, aaa = w >> 12, (w >> 8) & 15, (w >> 4) & 15, w & 0xFF, w & 0x3FF
    sx, sy = "s%X" % x, "s%X" % y
    base = op & ~1
    if base in ALU:
        return ALU[base], "%s, %s" % (sx, sy if op & 1 else "%02X" % kk), {}
    if base == 0x04:
        return "INPUT", "%s, %s" % (sx, "(%s)" % sy if op & 1 else "%02X" % kk), \
            ({} if op & 1 else {"in": kk})
    if base == 0x2C:
        return "OUTPUT", "%s, %s" % (sx, "(%s)" % sy if op & 1 else "%02X" % kk), \
            ({} if op & 1 else {"out": kk})
    if base == 0x06:
        return "FETCH", "%s, %s" % (sx, "(%s)" % sy if op & 1 else "%02X" % (kk & 63)), \
            ({} if op & 1 else {"ram": kk & 63})
    if base == 0x2E:
        return "STORE", "%s, %s" % (sx, "(%s)" % sy if op & 1 else "%02X" % (kk & 63)), \
            ({} if op & 1 else {"ram": kk & 63})
    if op == 0x20:
        return SHIFT.get(kk & 0x0F, "SHIFT?%X" % (kk & 0x0F)), sx, {}
    cond = COND[(w >> 10) & 3]
    if base in (0x30, 0x34):
        name = "CALL" if base == 0x30 else "JUMP"
        return name, ("%s, " % cond if op & 1 else "") + "%03X" % aaa, \
            {"call" if name == "CALL" else "jump": aaa, "cond": bool(op & 1)}
    if base == 0x2A:
        return "RETURN", cond if op & 1 else "", {"ret": True, "cond": bool(op & 1)}
    if op == 0x38:
        return "RETURNI", "ENABLE" if w & 1 else "DISABLE", {"ret": True}
    if op == 0x3C:
        return ("ENABLE" if w & 1 else "DISABLE") + " INTERRUPT", "", {}
    return "DB", "%05X" % w, {}


def main(path):
    words = [int(l, 16) for l in open(path) if l.strip()]
    dec = [decode(w) for w in words]
    labels = {}
    xin, xout, xram, callers = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for a, (m, o, info) in enumerate(dec):
        if "call" in info:
            labels.setdefault(info["call"], "sub_%03X" % info["call"])
            callers[info["call"]].append(a)
        if "jump" in info:
            labels.setdefault(info["jump"], "L_%03X" % info["jump"])
        if "in" in info:
            xin[info["in"]].append(a)
        if "out" in info:
            xout[info["out"]].append(a)
        if "ram" in info:
            xram[info["ram"]].append(a)
    labels[0x3FF] = "int_vector"
    # trim trailing zero (unused) words but keep the interrupt vector
    last = max(i for i, w in enumerate(words[:0x3FF]) if w) if any(words[:0x3FF]) else 0
    out = []
    for a, (m, o, info) in enumerate(dec):
        if last < a < 0x3FF:
            continue
        if a in labels:
            out.append("\n%s:" % labels[a])
        tgt = info.get("call", info.get("jump"))
        ops = o
        if tgt is not None:
            ops = o.replace("%03X" % tgt, labels[tgt])
        out.append("  %03X  %05X   %-18s %s" % (a, words[a], m, ops))
    out.append("\n; (0x%03X-0x3FE: all zero, unused)" % (last + 1))
    out.append("\n; ---- cross references ----")
    for title, xr in (("INPUT port", xin), ("OUTPUT port", xout), ("scratchpad", xram)):
        for k in sorted(xr):
            out.append("; %-12s %02X : %s" % (title, k, " ".join("%03X" % a for a in xr[k])))
    for k in sorted(callers):
        out.append("; called %-6s %s <- %s" % ("", labels[k], " ".join("%03X" % a for a in callers[k])))
    print("\n".join(out))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
