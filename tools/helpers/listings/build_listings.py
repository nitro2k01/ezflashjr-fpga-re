#!/usr/bin/env python3
"""Regenerate the commented PicoBlaze listings and version diffs from firmware files.

Usage: build_listings.py <out_dir> <firmware file> [<firmware file> ...]

Pass the update ROMs (Update_FW*.gb) and/or flash dumps; every bitstream in them is
scanned and its PicoBlaze programs are extracted. Each known program (identified by
the md5 of its 1024 words) gets a listing; each listing is re-assembled with pbasm
and compared with the original words.

Labels: FW4 bank 0 is the reference. Every branch target in it has a name (either
hand-written in ann_bank0 or derived from the enclosing routine as <routine>_Lxx,
xx = offset from the routine start in FW4). Names are carried to the other versions
by instruction alignment, so the same code has the same label everywhere. Code that
only exists in one version is named in ann_versions or, failing that, after its own
enclosing routine.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))   # tools/

import bootrom_patch as bp   # noqa: E402
import kcpsm3_dis as k       # noqa: E402
import pbasm                 # noqa: E402
import pbannotate            # noqa: E402
import pbdiff                # noqa: E402
import pbreach               # noqa: E402
import pbtransfer            # noqa: E402
import ann_bank0 as A        # noqa: E402
import ann_bank1 as B        # noqa: E402
import ann_versions as V     # noqa: E402

REF0 = "45c54676"            # bank 0, FW4
REF1 = "537b0b55"            # bank 1, standard
GOLD1 = "b615b8ca"           # bank 1, FW0 golden

# Version order for the diffs (bank 0 lineage, then bank 1)
DIFFS = [("8871f4e6", "b90e8d48", "FW0", "FW1-FW3"),
         ("b90e8d48", REF0, "FW1-FW3", "FW4"),
         (REF0, "74a33101", "FW4", "FW5_slotB"),
         (REF0, "755c0dcf", "FW4", "FW5"),
         ("755c0dcf", "518780d6", "FW5", "FW5_SGB"),
         (GOLD1, REF1, "bank1_FW0_golden", "bank1")]


def phash(words):
    return hashlib.md5(str(words).encode()).hexdigest()[:8]


def collect(files):
    for f in files:
        d = bytearray(open(f, "rb").read())
        for bs in bp.find_bitstreams(d):
            an = bp.Analysis(bs)
            for n in an.picoblaze:
                w = bp.words_x18(an.data[n], an.par[n])
                pbreach.PROGRAMS.setdefault(phash(w), w)


def targets(words):
    t = set()
    for w in words:
        info = k.decode(w)[2]
        a = info.get("call", info.get("jump"))
        if a is not None:
            t.add(a)
    return t


def auto_names(words, names):
    """Name every unnamed branch target after its enclosing named label."""
    named = dict(names)
    for t in sorted(targets(words)):
        if t in named:
            continue
        enc = max((a for a in names if a <= t), default=None)
        base = names[enc] if enc is not None else "L"
        cand = "%s_L%02X" % (base, t - (enc or 0))
        while cand in named.values():
            cand += "x"
        named[t] = cand
    return named


def apply_overrides(n, overrides):
    for a, name in overrides.items():
        for other in [x for x, v in n.items() if v == name and x != a]:
            n[other] = name + ("_events" if name == "isr" else "_%03X" % other)
        n[a] = name
    return n


def emit_checked(words, names, comments, headers, title, path, entries=(0, 0x3FF)):
    pbannotate.emit(words, names, comments, headers, title, path, entries=entries)
    back = pbasm.assemble(open(path).read())
    bad = [i for i in range(1024) if back[i] != words[i]]
    print("%-28s %s" % (os.path.basename(path), "re-assembles exactly" if not bad else
                        "MISMATCH at " + " ".join("%03X" % i for i in bad[:8])))
    return not bad


def write_diffs(outdir):
    os.makedirs(os.path.join(outdir, "diffs"), exist_ok=True)

    def tgt(w):
        i = k.decode(w)[2]
        return i.get("call", i.get("jump"))

    for a, b, na, nb in DIFFS:
        if a not in pbreach.PROGRAMS or b not in pbreach.PROGRAMS:
            continue
        r, o = pbdiff.diff(a, b)
        m = pbtransfer.addr_map(a, b)
        wa, wb = pbreach.load(a), pbreach.load(b)
        blocks, cur = [], None
        for line in o:
            if line.startswith("@@"):
                cur = [line]
                blocks.append(cur)
            else:
                cur.append(line)
        keep = []
        for x in blocks:
            if all(" 00000 " in y for y in x[1:]):
                continue                                   # zero padding only
            if x[0].startswith("@@ replace"):
                olds = [y for y in x[1:] if y.startswith("  -")]
                news = [y for y in x[1:] if y.startswith("  +")]
                if len(olds) == len(news):
                    reloc = True
                    for yo, yn in zip(olds, news):
                        xo, xn = wa[int(yo.split()[1], 16)], wb[int(yn.split()[1], 16)]
                        if pbdiff._plain(xo) != pbdiff._plain(xn) or \
                                (tgt(xo) is not None and m.get(tgt(xo)) != tgt(xn)):
                            reloc = False
                            break
                    if reloc:
                        continue                           # only moved with the code
            keep.append(x)
        txt = ["; Instruction-level diff %s -> %s. Pure relocations (same instruction," % (na, nb),
               "; target moved with the code) and zero padding are left out.",
               "; Addresses: old / new.  %d change blocks" % len(keep), ""]
        for x in keep:
            txt += x + [""]
        open(os.path.join(outdir, "diffs", "%s_to_%s.diff" % (na, nb)), "w").write("\n".join(txt))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    outdir = argv[1]
    os.makedirs(outdir, exist_ok=True)
    collect(argv[2:])
    ok = True

    # bank 0 reference
    base_names = auto_names(pbreach.load(REF0), A.N) if REF0 in pbreach.PROGRAMS else None
    if base_names:
        ok &= emit_checked(pbreach.load(REF0), base_names, A.C, A.H, A.TITLE,
                           os.path.join(outdir, "bank0_FW4.psm"))
        for h, v in V.VERSIONS.items():
            if h not in pbreach.PROGRAMS:
                print("%-28s skipped (program not in the given files)" % v["file"])
                continue
            n, c, hd, _ = pbtransfer.transfer(REF0, h, base_names, A.C, A.H)
            m = pbtransfer.addr_map(REF0, h)
            for a, txt in hd.items():          # FW4 address ranges quoted in headers
                for lo, hi in ((0x1EE, 0x289),):
                    tag = "(%03X-%03X)" % (lo, hi)
                    if tag in txt and lo in m and hi in m:
                        hd[a] = txt.replace(tag, "(%03X-%03X)" % (m[lo], m[hi]))
            n = apply_overrides(n, v["names"])
            n = auto_names(pbreach.load(h), n)
            c.update(v["comments"])
            hd.update(v["headers"])
            ok &= emit_checked(pbreach.load(h), n, c, hd, V.title(v["title"]),
                               os.path.join(outdir, v["file"]))
    else:
        print("FW4 bank 0 not found: bank-0 listings need Update_FW4.gb")

    # bank 1
    for h, fname, title, comments in (
            (REF1, "bank1.psm", B.TITLE, B.C),
            (GOLD1, "bank1_FW0_golden.psm",
             B.TITLE.replace(";------------------------------------------------------------------------------\n; HOW THIS BANK RUNS",
                             V.GOLDEN_BANK1_TITLE_NOTE + ";------------------------------------------------------------------------------\n; HOW THIS BANK RUNS", 1),
             {**B.C, 0x1B8: "build constant: 01 = MultiBoot enabled (golden image)"})):
        if h in pbreach.PROGRAMS:
            names = auto_names(pbreach.load(h), B.N)
            ok &= emit_checked(pbreach.load(h), names, comments, B.H, title,
                               os.path.join(outdir, fname), entries=(0x3F3,))

    write_diffs(outdir)
    unknown = [h for h in pbreach.PROGRAMS if h not in V.VERSIONS and h not in (REF0, REF1, GOLD1)]
    if unknown:
        print("note: programs without annotations (new firmware?):", " ".join(unknown))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
