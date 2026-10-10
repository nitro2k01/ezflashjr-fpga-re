#!/usr/bin/env python3
"""Print the configuration packets of every bitstream in a file.

Usage: bitstream_info.py [-v] <file> [<file> ...]

For each bitstream (update ROM, flash dump or plain .bin): file offset, register
writes with their values, the FDRI word count and both CRC checks. -v also lists
NOOPs. Register names follow UG332 (Extended Spartan-3A).
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import bootrom_patch as bp  # noqa: E402

REG = ["CRC", "FAR_MAJ", "FAR_MIN", "FDRI", "FDRO", "CMD", "CTL", "MASK", "STAT", "LOUT",
       "COR1", "COR2", "PWRDWN", "FLR", "IDCODE", "SNOWPLOW", "HC_OPT", "R17", "CSBO",
       "GENERAL1", "GENERAL2", "MODE_REG", "PU_GWE", "PU_GTS", "MFWR", "CCLK_FREQ",
       "SEU_OPT", "EXP_SIGN", "RDBK_SIGN", "R29", "R30", "R31"]
CMDS = {0: "NULL", 1: "WCFG", 3: "LFRM", 5: "START", 7: "RCRC", 0xA: "GRESTORE",
        0xB: "SHUTDOWN", 0xD: "DESYNC", 0xE: "REBOOT"}


def show(d, verbose):
    streams = bp.find_bitstreams(d)
    if not streams:
        print("  no bitstream found")
    for bs in streams:
        md5 = hashlib.md5(bytes(d[bs.sync:bs.end])).hexdigest()[:8]
        print("  bitstream: sync word at 0x%X, ends at 0x%X, md5 %s" % (bs.sync, bs.end, md5))
        calc = {dp: c for dp, _, c in bs.crc_walk()}
        for pos, ptype, op, reg, dp, words in bp.packets(d, bs.sync + 2):
            if op == 0:
                if verbose:
                    print("    %06X  NOOP" % pos)
                continue
            name = REG[reg]
            if ptype == 2 or len(words) > 4:
                val = "%d words" % len(words)
            elif reg == bp.REG_CMD:
                val = "%04X %s" % (words[0], CMDS.get(words[0], "?"))
            elif reg == bp.REG_CRC:
                stored = words[0] << 16 | words[1]
                c = calc.get(dp)
                val = "%06X  (calculated %s)" % (stored, "%06X" % c if c is not None else "?")
            else:
                val = " ".join("%04X" % w for w in words)
            print("    %06X  %s %-9s %s" % (pos, "W" if op == 2 else "R", name, val))


def main(argv):
    verbose = "-v" in argv
    files = [a for a in argv[1:] if a != "-v"]
    if not files:
        print(__doc__)
        return 1
    for f in files:
        print(f)
        show(bytearray(open(f, "rb").read()), verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
