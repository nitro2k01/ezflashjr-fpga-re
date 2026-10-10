#!/usr/bin/env python3
"""Check the BRAM bit-mapping formula against the hardware bit-address survey.

Usage: survey_verify.py <Update_FW4.gb> [<survey dir>]   (default: data/ next to this script)

<survey dir> holds boot-0.gb.xor ... boot-18.gb.xor: the boot ROM read from the
cartridge after loading survey bitstream s, XORed with the original boot ROM.
Survey bitstream s flipped, in the surveyed region, every bit whose region bit
address has bit s set: runs 0-2 select by the bit number within the byte
(masks AA, CC, F0), runs 3-18 by the byte offset from the region start. The 19
XOR files together therefore spell out, for every ROM bit that changed, the
address of its source bit.

The script converts each index back to a bit position in the file and compares it
with the position the formula in bootrom_patch.py predicts (data_frame /
data_offset plus the boot ROM BRAM map found by logo detection).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import bootrom_patch as bp  # noqa: E402

# Survey region, as used by the original survey generator (analimage.py): 72
# frames of 276 bytes starting at REGION_BASE in a copy of the FW4 bitstream
# whose sync word sat at file offset 0x20 (SURVEY_SYNC).
# Bytes 224-275 of each frame and the bits cleared in ROWMASK were not flipped.
REGION_BASE = 0x179DE      # column A (frame 350) + 80 bits; ROM bits 3 and 4 in FW4
SURVEY_SYNC = 0x20
RUNS = 19



def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__)
        return 1
    if len(argv) == 2:
        argv = argv + [os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")]
    d = bytearray(open(argv[1], "rb").read())
    xors = [open(os.path.join(argv[2], "boot-%d.gb.xor" % s), "rb").read() for s in range(RUNS)]
    bs = bp.find_bitstreams(d)[0]
    an = bp.Analysis(bs)
    fdri_bit = bs.fdri * 8
    ok = bad = 0
    for addr in range(0x4000):
        for bit in range(8):
            code = 0
            for s in range(RUNS):
                if xors[s][addr] >> bit & 1:
                    code |= 1 << s
            if not code:
                continue
            surveyed = (bs.sync - SURVEY_SYNC + REGION_BASE + (code >> 3)) * 8 + 7 - (code & 7)
            name = an.rom_map[bit]
            col, slc = name[0], int(name[1])
            predicted = fdri_bit + (bp.BRAM_COLUMNS[col] + bp.data_frame(addr)) * bs.fbits \
                + bp.SLICE_BIT0 + bp.SLICE_BITS * slc + bp.data_offset(addr)
            if surveyed == predicted:
                ok += 1
            else:
                bad += 1
                if bad <= 10:
                    print("mismatch: ROM %04X bit %d  survey bit %d  formula bit %d"
                          % (addr, bit, surveyed, predicted))
    print("ROM bits located by the survey: %d   agree with formula: %d   disagree: %d"
          % (ok + bad, ok, bad))
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
