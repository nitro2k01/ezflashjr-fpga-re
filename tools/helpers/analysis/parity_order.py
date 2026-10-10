#!/usr/bin/env python3
"""Show how the parity-bit order was determined.

Usage: parity_order.py <file>

The parity bits of a RAMB16 sit at offsets 56-69 and 186-199 of each 256-bit
slice (14 per 128-bit half). Which parity bit goes where can't be checked against
the boot ROM (its BRAMs have no parity), so the order was fixed by decoding the
PicoBlaze programs: an 18-bit KCPSM3 word takes its top two bits from parity, and
only the right order makes every word a valid instruction.

For each BRAM with parity bits set, this tries the eight variants of the layout
(which half holds odd bytes, the order of the two 7-bit groups, the direction of
the 7-bit group index) and prints how many of the 1024 words decode as valid
KCPSM3 instructions. bootrom_patch.py uses the variant (swap=0, xh=0, qr=0).
"""
import itertools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import bootrom_patch as bp  # noqa: E402


def parity_offset(p, swap, xh, qr):
    q = ((8 * p) % 0x380) >> 7
    odd = p & 1
    base = (56 if odd else 186) if not swap else (186 if odd else 56)
    h = (p >> 1) & 1
    return base + 7 * (h if xh else 1 - h) + (6 - q if qr else q)


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 1
    d = bytearray(open(argv[1], "rb").read())
    for bs in bp.find_bitstreams(d):
        print("bitstream at 0x%X" % bs.sync)
        for name in bp.BRAM_NAMES:
            if not any(bs.read_parity(name)):
                continue
            data = bs.read_data(name)
            row = []
            for swap, xh, qr in itertools.product((0, 1), repeat=3):
                par = [bs._get(bs._pos(name, bp.parity_frame(p), parity_offset(p, swap, xh, qr)))
                       for p in range(2048)]
                ok = sum((w >> 12) in bp.KCPSM3_OPCODES for w in bp.words_x18(data, par))
                row.append("%d%d%d:%4d" % (swap, xh, qr, ok))
            print("  %s  %s" % (name, "  ".join(row)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
