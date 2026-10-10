#!/usr/bin/env python3
"""Compare the boot ROM extracted from bitstreams with boot ROM dumps from hardware.

Usage: stage1_check.py --dump <stage1.gb> [--dump <stage1.gb> ...] <firmware file> [...]

For every bitstream in the firmware files, the boot ROM (0000-3FFF, eight 16Kx1
BRAMs found by logo detection) and the 2Kx8 data BRAM are rebuilt with
bootrom_patch.py and compared with each dump: 0000-3FFF, 4000-47FF, and whether
4800-7FFF of the dump is all zero.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import bootrom_patch as bp  # noqa: E402


def main(argv):
    dumps, files, it = {}, [], iter(argv[1:])
    for a in it:
        if a == "--dump":
            p = next(it)
            dumps[p] = open(p, "rb").read()
        else:
            files.append(a)
    if not dumps or not files:
        print(__doc__)
        return 1
    for f in files:
        d = bytearray(open(f, "rb").read())
        for bs in bp.find_bitstreams(d):
            an = bp.Analysis(bs)
            rom = bytearray(0x4000)
            for bit, name in enumerate(an.rom_map):
                for a, v in enumerate(an.data[name]):
                    rom[a] |= v << bit
            x8 = bp.bits_to_bytes(an.data[an.x8[0]]) if an.x8 else None
            print("%s @0x%X" % (os.path.basename(f), bs.sync))
            for p, s in dumps.items():
                lo = s[:0x4000] == bytes(rom)
                mid = x8 is not None and s[0x4000:0x4800] == x8
                hi = not any(s[0x4800:0x8000])
                if lo:
                    print("    == %s  (4000-47FF %s, 4800-7FFF zero: %s)"
                          % (p, "matches" if mid else "differs", hi))
            if not any(s[:0x4000] == bytes(rom) for s in dumps.values()):
                best = max(dumps, key=lambda p: sum(a == b for a, b in zip(dumps[p], rom)))
                same = sum(a == b for a, b in zip(dumps[best], rom))
                print("    no matching dump (closest: %s, %d/16384 bytes equal)" % (best, same))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
