#!/usr/bin/env python3
"""Small KCPSM3 assembler for the syntax used by the listings in listings/.

Usage: pbasm.py <file.psm>                      print 1024 words as .psm.hex
       pbasm.py <file.psm> <reference.psm.hex>  compare with the original words

Supports labels, ADDRESS, all KCPSM3 instructions with hex constants and the
s0-sF register names. CONSTANT and NAMEREG directives are not supported.
Unused locations assemble to 00000. The .psm.hex output can be written into a
bitstream with: bootrom_patch.py write_bram --mode psm <file> <BRAM> <hex> <out>
"""
import re
import sys

ALU = {"LOAD": 0x00, "AND": 0x0A, "OR": 0x0C, "XOR": 0x0E, "TEST": 0x12, "COMPARE": 0x14,
       "ADD": 0x18, "ADDCY": 0x1A, "SUB": 0x1C, "SUBCY": 0x1E}
SHIFT = {"SL0": 0x06, "SL1": 0x07, "SLX": 0x04, "SLA": 0x00, "RL": 0x02,
         "SR0": 0x0E, "SR1": 0x0F, "SRX": 0x0A, "SRA": 0x08, "RR": 0x0C}
COND = {"Z": 0, "NZ": 1, "C": 2, "NC": 3}


def reg(t):
    m = re.fullmatch(r"s([0-9A-Fa-f])", t)
    if not m:
        raise ValueError("bad register %r" % t)
    return int(m.group(1), 16)


def assemble(text):
    lines = []
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if line:
            lines.append(line)
    # pass 1: labels
    labels, addr = {}, 0
    for line in lines:
        m = re.match(r"([A-Za-z_]\w*):\s*(.*)", line)
        if m:
            labels[m.group(1)] = addr
            line = m.group(2)
        if not line:
            continue
        if line.upper().startswith("ADDRESS"):
            addr = int(line.split()[1], 16)
        else:
            addr += 1
    # pass 2
    words, addr = [0] * 1024, 0
    for line in lines:
        m = re.match(r"([A-Za-z_]\w*):\s*(.*)", line)
        if m:
            line = m.group(2)
        if not line:
            continue
        parts = line.replace(",", " , ").split()
        op = parts[0].upper()
        args = [p for p in parts[1:] if p != ","]
        if op == "ADDRESS":
            addr = int(args[0], 16)
            continue

        def target(t):
            return labels[t] if t in labels else int(t, 16)

        if op in ALU:
            x = reg(args[0])
            if re.fullmatch(r"s[0-9A-Fa-f]", args[1]):
                w = (ALU[op] + 1) << 12 | x << 8 | reg(args[1]) << 4
            else:
                w = ALU[op] << 12 | x << 8 | int(args[1], 16)
        elif op in ("INPUT", "OUTPUT", "FETCH", "STORE"):
            base = {"INPUT": 0x04, "OUTPUT": 0x2C, "FETCH": 0x06, "STORE": 0x2E}[op]
            x = reg(args[0])
            if args[1].startswith("("):
                w = (base + 1) << 12 | x << 8 | reg(args[1].strip("()")) << 4
            else:
                w = base << 12 | x << 8 | int(args[1], 16)
        elif op in SHIFT:
            w = 0x20 << 12 | reg(args[0]) << 8 | SHIFT[op]
        elif op in ("JUMP", "CALL"):
            base = 0x34 if op == "JUMP" else 0x30
            if len(args) == 2:
                w = (base + 1) << 12 | COND[args[0].upper()] << 10 | target(args[1])
            else:
                w = base << 12 | target(args[0])
        elif op == "RETURN":
            w = (0x2B << 12 | COND[args[0].upper()] << 10) if args else 0x2A << 12
        elif op == "RETURNI":
            w = 0x38 << 12 | (1 if args[0].upper() == "ENABLE" else 0)
        elif op in ("ENABLE", "DISABLE"):
            w = 0x3C << 12 | (1 if op == "ENABLE" else 0)
        else:
            raise ValueError("unknown instruction %r" % line)
        words[addr] = w
        addr += 1
    return words


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        sys.exit(1)
    words = assemble(open(sys.argv[1]).read())
    if len(sys.argv) > 2:
        ref = [int(l, 16) for l in open(sys.argv[2]) if l.strip()]
        bad = [i for i in range(1024) if words[i] != ref[i]]
        print("%s: %d/1024 words match%s" % (sys.argv[1], 1024 - len(bad),
              "" if not bad else "; first mismatches at " + " ".join("%03X" % i for i in bad[:10])))
        sys.exit(1 if bad else 0)
    print("\n".join("%05X" % w for w in words))
