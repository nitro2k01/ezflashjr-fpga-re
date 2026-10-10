#!/usr/bin/env python3
"""Small KCPSM3 (PicoBlaze-3) emulator for timing and testing individual routines.

Usage: pbemu.py <program> <routine> [<routine> ...]

<program> is a listing (.psm, assembled with tools/pbasm.py) or a .psm.hex file
(1024 lines of 18-bit hex words, as written by bootrom_patch.py extract_hi).
<routine> is a hex address or, for a .psm listing, a label. Each routine is called
with all registers and scratchpad zero, and the number of instructions executed
until it returns is printed. INPUT reads 00, OUTPUT is ignored, so this is only
meaningful for routines that don't wait on hardware (delay loops, arithmetic).
One KCPSM3 instruction takes 2 clock cycles.

As a module: run(words, pc, regs=None, scratch=None, inp=None, out=None)
returns (instruction count, registers, scratchpad, flags).
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

SHIFT = {0x06: "SL0", 0x07: "SL1", 0x04: "SLX", 0x00: "SLA", 0x02: "RL",
         0x0E: "SR0", 0x0F: "SR1", 0x0A: "SRX", 0x08: "SRA", 0x0C: "RR"}


class Timeout(Exception):
    pass


def run(w, pc, regs=None, scratch=None, inp=None, out=None, maxsteps=10 ** 9):
    r = list(regs or [0] * 16)
    sp = list(scratch or [0] * 64)
    inp = inp or (lambda port: 0)
    out = out or (lambda port, val: None)
    z = c = 0
    ie = 0
    stack = []
    n = 0
    while n < maxsteps:
        i = w[pc]
        op, x, y, kk, aaa = i >> 12, (i >> 8) & 15, (i >> 4) & 15, i & 0xFF, i & 0x3FF
        v = r[y] if op & 1 else kk
        b = op & ~1
        n += 1
        cond = [z, not z, c, not c][(i >> 10) & 3]
        nxt = pc + 1
        if b == 0x00:
            r[x] = v
        elif b == 0x0A:
            r[x] &= v; z = r[x] == 0; c = 0
        elif b == 0x0C:
            r[x] |= v; z = r[x] == 0; c = 0
        elif b == 0x0E:
            r[x] ^= v; z = r[x] == 0; c = 0
        elif b == 0x12:
            t = r[x] & v; z = t == 0; c = bin(t).count("1") & 1
        elif b == 0x14:
            c = r[x] < v; z = r[x] == v
        elif b in (0x18, 0x1A):
            t = r[x] + v + (c if b == 0x1A else 0); c = t > 255; r[x] = t & 255
            z = r[x] == 0
        elif b in (0x1C, 0x1E):
            t = r[x] - v - (c if b == 0x1E else 0); c = t < 0; r[x] = t & 255
            z = r[x] == 0
        elif b == 0x04:
            r[x] = inp(v) & 255
        elif b == 0x2C:
            out(v, r[x])
        elif b == 0x06:
            r[x] = sp[v & 63]
        elif b == 0x2E:
            sp[v & 63] = r[x]
        elif op == 0x20:
            s, vx = SHIFT[kk & 15], r[x]
            if s.startswith("SL") or s == "RL":
                fill = {"SL0": 0, "SL1": 1, "SLX": vx & 1, "SLA": c, "RL": vx >> 7}[s]
                c = vx >> 7; r[x] = ((vx << 1) | fill) & 255
            else:
                fill = {"SR0": 0, "SR1": 1, "SRX": vx >> 7, "SRA": c, "RR": vx & 1}[s]
                c = vx & 1; r[x] = (vx >> 1) | (fill << 7)
            z = r[x] == 0
        elif op == 0x34 or (op == 0x35 and cond):
            nxt = aaa
        elif op == 0x30 or (op == 0x31 and cond):
            stack.append(pc + 1); nxt = aaa
        elif op == 0x2A or (op == 0x2B and cond):
            if not stack:
                return n, r, sp, (z, c)
            nxt = stack.pop()
        elif op == 0x3C:
            ie = kk & 1
        elif op == 0x38:
            raise ValueError("RETURNI outside an interrupt at %03X" % pc)
        elif op not in (0x35, 0x31, 0x2B):
            raise ValueError("invalid instruction %05X at %03X" % (i, pc))
        pc = nxt & 0x3FF
    raise Timeout("no return after %d instructions" % maxsteps)


def load(path):
    text = open(path).read()
    if path.endswith(".hex"):
        return [int(t, 16) for t in text.split()], {}
    import pbasm
    labels, addr = {}, 0
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        m = re.match(r"([A-Za-z_]\w*):\s*(.*)", line)
        if m:
            labels[m.group(1)] = addr
            line = m.group(2).strip()
        if not line:
            continue
        if line.upper().startswith("ADDRESS"):
            addr = int(line.split()[1], 16)
        else:
            addr += 1
    return pbasm.assemble(text), labels


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    words, labels = load(argv[1])
    for name in argv[2:]:
        pc = labels[name] if name in labels else int(name, 16)
        n = run(words, pc)[0]
        print("%-16s %03X  %12d instructions  (%d clock cycles)" % (name, pc, n, 2 * n))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
