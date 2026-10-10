#!/usr/bin/env python3
"""
Analyse and patch the XC3S200A bitstream of the cartridge: boot ROM, PicoBlaze
program memories and other block RAMs, with explicit 22-bit CRC recalculation.

The bitstream may be embedded in a larger file (update ROM, flash dump); only the
bitstream bytes are changed, the rest of the file is copied unchanged.

Usage:
  bootrom_patch.py [options] report      <file>
  bootrom_patch.py [options] extract     <file> <out.gb>
  bootrom_patch.py [options] extract_hi  <file> <out_prefix>
  bootrom_patch.py [options] patch       <file> <new_boot.gb> <out>
  bootrom_patch.py [options] write_bram  <file> <BRAM> <data> <out>
  bootrom_patch.py [options] fixcrc      <file> <out>
  bootrom_patch.py [options] checkcrc    <file>

Options:
  --second           use the second bitstream in the file (error if there is none)
  --map B6,B2,...    boot ROM BRAMs for bits 0..7, overriding logo detection
                     (report prints the map of each bitstream)
  --include-4000     patch: also write 0x4000-0x47FF of the new image into the
                     2Kx8 data BRAM
  --mode x8|psm|x1   write_bram: x8 = 2048-byte binary (default), psm = .psm.hex
                     (1024 18-bit words, data+parity), x1 = 2048-byte binary of
                     16384 single-bit words (bit n -> byte n>>3, bit n&7)
  --force            write_bram: allow overwriting a BRAM that holds boot ROM bits

BRAM names: A0-A7 and B0-B7.  The letter is the BRAM column in bitstream order
(A = frames 350-425, B = frames 426-501), the digit the 256-bit slice in each frame.

Boot ROM detection: each boot ROM bit lives in its own 16Kx1 BRAM, and which BRAM
holds which bit changes between builds.  The bits are found by matching the
Nintendo logo at 0x104-0x133 (which any bootable ROM must contain anyway).
"""
import re
import sys

# ---------------------------------------------------------------------------
# Packets
# ---------------------------------------------------------------------------
REG_CRC, REG_FDRI, REG_CMD, REG_FLR, REG_IDCODE = 0x00, 0x03, 0x05, 0x0D, 0x0E
CMD_RCRC, CMD_DESYNC = 0x07, 0x0D
XC3S200A_IDCODE = 0x02218093   # version nibble ignored


class BitstreamError(Exception):
    pass


def be16(d, p):
    return d[p] << 8 | d[p + 1]


def packets(d, start):
    """Yield (hdr_pos, type, op, reg, data_pos, [words]) from just after the sync
    word at `start` up to and including DESYNC."""
    p = start
    while True:
        if p + 2 > len(d):
            raise BitstreamError("bitstream truncated at 0x%x" % p)
        h = be16(d, p)
        pos, p = p, p + 2
        ptype, op, reg, wc = h >> 13, (h >> 11) & 3, (h >> 5) & 0x3F, h & 0x1F
        if ptype == 2:
            wc = be16(d, p) << 16 | be16(d, p + 2)
            p += 4
        elif ptype != 1:
            raise BitstreamError("bad packet header 0x%04x at 0x%x" % (h, pos))
        if p + 2 * wc > len(d):
            raise BitstreamError("packet at 0x%x runs past end of file" % pos)
        words = [be16(d, p + 2 * i) for i in range(wc)]
        yield pos, ptype, op, reg, p, words
        p += 2 * wc
        if op == 2 and reg == REG_CMD and words == [CMD_DESYNC]:
            return


# ---------------------------------------------------------------------------
# CRC: 22-bit, polynomial x^22 + x^15 + x^12 + x^7 + 1.
#   - reset to 0 by the RCRC command (the RCRC write itself is NOT included)
#   - every later register write except to CRC is folded in as the 22-bit
#     value (reg_addr << 16) | data_word:   S = S*x + v  (mod P)
#   - header/count words are not included
#   - writing CRC compares; the running value simply continues afterwards
# ---------------------------------------------------------------------------
CRC_POLY = (1 << 15) | (1 << 12) | (1 << 7) | 1


def crc_step(s, v):
    s = (s << 1) ^ v ^ (CRC_POLY if s & (1 << 21) else 0)
    return s & 0x3FFFFF


# ---------------------------------------------------------------------------
# Block RAM layout (XC3S200A: 2 BRAM columns x 8 RAMB16)
#
# A BRAM column is 76 frames of 138 words.  Each frame carries, starting 5 words
# (80 bits) in, eight 256-bit slices, one per BRAM.  A RAMB16 has 16384 data bits
# and 2048 parity bits, numbered like INIT_xx / INITP_xx: in x1 mode the address is
# the data bit index, in xN mode word a, bit k is data bit N*a + k, and parity
# bit p belongs to data byte p.
# ---------------------------------------------------------------------------
BRAM_COLUMNS = {"A": 350, "B": 426}
SLICE_BIT0 = 80
SLICE_BITS = 256
BRAM_NAMES = ["%s%d" % (c, i) for c in "AB" for i in range(8)]


def data_frame(n):
    return 4 * (n // 0x380) + ((n >> 5) & 3)


def data_offset(n):
    q = (n % 0x380) >> 7
    h = (n >> 4) & 1
    g = (n >> 2) & 3
    j = n & 3
    return 249 - 70 * g + (10 if g >= 2 else 0) - 14 * j - 7 * h + q


def parity_frame(p):
    return data_frame(8 * p)


def parity_offset(p):
    q = ((8 * p) % 0x380) >> 7
    return (56 if p & 1 else 186) + 7 * (1 - ((p >> 1) & 1)) + q


class Bitstream:
    """One bitstream inside file buffer `d` (a bytearray), starting at `sync`
    (offset of the AA 99 sync word)."""

    def __init__(self, d, sync):
        self.d, self.sync = d, sync
        self.fbits = self.fdri = self.idcode = None
        self.fdri_words = 0
        self.crcs = []
        last = None
        for pk in packets(d, sync + 2):
            pos, ptype, op, reg, dp, words = pk
            last = pk
            if op != 2:
                continue
            if reg == REG_FLR:
                self.fbits = (words[0] + 1) * 16
            elif reg == REG_IDCODE and len(words) == 2:
                self.idcode = words[0] << 16 | words[1]
            elif reg == REG_FDRI and len(words) > 1:
                self.fdri, self.fdri_words = dp, len(words)
            elif reg == REG_CRC:
                self.crcs.append(dp)
        self.end = last[4] + 2 * len(last[5])
        if self.fdri is None or self.fbits is None:
            raise BitstreamError("no FLR/FDRI in bitstream at 0x%x" % sync)

    @property
    def frames(self):
        return self.fdri_words * 16 // self.fbits

    def check_device(self):
        if self.idcode is None or (self.idcode & 0x0FFFFFFF) != (XC3S200A_IDCODE & 0x0FFFFFFF):
            raise BitstreamError("IDCODE %s is not an XC3S200A; BRAM layout unknown"
                                 % (hex(self.idcode) if self.idcode is not None else "missing"))
        if self.fbits != 138 * 16:
            raise BitstreamError("unexpected frame length %d bits" % self.fbits)

    # -- CRC --
    def crc_walk(self, fix=False):
        out, s = [], 0
        for pos, ptype, op, reg, dp, words in packets(self.d, self.sync + 2):
            if op != 2:
                continue
            if reg == REG_CRC:
                stored = words[0] << 16 | words[1]
                out.append((dp, stored, s))
                if fix:
                    self.d[dp:dp + 4] = s.to_bytes(4, "big")
                continue
            for w in words:
                s = crc_step(s, reg << 16 | w)
            if reg == REG_CMD and words == [CMD_RCRC]:
                s = 0
        return out

    # -- BRAM bit access --
    def _pos(self, name, frame, off):
        col, idx = name[0], int(name[1])
        p = (BRAM_COLUMNS[col] + frame) * self.fbits + SLICE_BIT0 + idx * SLICE_BITS + off
        return self.fdri + p // 8, 0x80 >> (p % 8)

    def _get(self, pos):
        return 1 if self.d[pos[0]] & pos[1] else 0

    def _set(self, pos, v):
        if v:
            self.d[pos[0]] |= pos[1]
        else:
            self.d[pos[0]] &= ~pos[1] & 0xFF

    def read_data(self, name):
        return [self._get(self._pos(name, data_frame(n), data_offset(n))) for n in range(16384)]

    def read_parity(self, name):
        return [self._get(self._pos(name, parity_frame(p), parity_offset(p))) for p in range(2048)]

    def write_data(self, name, bits):
        for n, v in enumerate(bits):
            self._set(self._pos(name, data_frame(n), data_offset(n)), v)

    def write_parity(self, name, bits):
        for p, v in enumerate(bits):
            self._set(self._pos(name, parity_frame(p), parity_offset(p)), v)


def find_bitstreams(d):
    """Return list of Bitstream objects for every valid bitstream in d."""
    found, pos = [], 0
    for m in re.finditer(rb"\xff\xff\xaa\x99", bytes(d)):
        sync = m.start() + 2
        if sync < pos:
            continue
        try:
            bs = Bitstream(d, sync)
        except BitstreamError:
            continue
        found.append(bs)
        pos = bs.end
    return found


def select_bitstream(d, second=False):
    streams = find_bitstreams(d)
    if not streams:
        raise BitstreamError("no valid bitstream found")
    if second:
        if len(streams) < 2:
            raise BitstreamError("--second given, but the file contains only one valid bitstream")
        bs = streams[1]
    else:
        bs = streams[0]
    bs.check_device()
    return bs


# ---------------------------------------------------------------------------
# Content analysis
# ---------------------------------------------------------------------------
NINTENDO_LOGO = bytes.fromhex(
    "CEED6666CC0D000B03730083000C000D0008111F8889000EDCCC6EE6DDDDD999BBBB67636E0EECCCDDDC999FBBB9333E")
ROM_SIZE = 0x4000
X8_BASE = 0x4000      # 2Kx8 data BRAM appears at 0x4000-0x47FF of the boot ROM area

KCPSM3_OPCODES = {0x00, 0x01, 0x04, 0x05, 0x06, 0x07, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
                  0x12, 0x13, 0x14, 0x15, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F,
                  0x20, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x34, 0x35,
                  0x38, 0x3C}


def bits_to_bytes(bits, width=8):
    return bytes(sum(bits[width * i + k] << k for k in range(8)) for i in range(len(bits) // width))


def bytes_to_bits(data, nbits):
    return [(data[n >> 3] >> (n & 7)) & 1 if (n >> 3) < len(data) else 0 for n in range(nbits)]


def words_x18(data, par):
    return [sum(data[16 * w + k] << k for k in range(16)) | par[2 * w] << 16 | par[2 * w + 1] << 17
            for w in range(1024)]


def parse_map(s):
    names = [x.strip().upper() for x in s.split(",")]
    if len(names) != 8 or any(n not in BRAM_NAMES for n in names) or len(set(names)) != 8:
        raise BitstreamError("--map needs 8 distinct BRAM names for bits 0..7, e.g. B6,B2,B1,A4,A3,B4,B5,B0")
    return names


class Analysis:
    def __init__(self, bs, rom_map=None):
        self.bs = bs
        self.data = {n: bs.read_data(n) for n in BRAM_NAMES}
        self.par = {n: bs.read_parity(n) for n in BRAM_NAMES}
        self.rom_map = rom_map or self._detect_rom()
        self.role = {}
        for b, n in enumerate(self.rom_map):
            self.role[n] = "boot ROM bit %d (16Kx1)" % b
        self.picoblaze, self.x8 = [], []
        for n in BRAM_NAMES:
            if n in self.role:
                continue
            d, p = self.data[n], self.par[n]
            if not any(d) and not any(p):
                self.role[n] = "empty"
            elif any(p) and all((w >> 12) in KCPSM3_OPCODES for w in words_x18(d, p)):
                self.role[n] = "PicoBlaze (KCPSM3) program, 1Kx18"
                self.picoblaze.append(n)
            elif not any(p):
                self.role[n] = "data, no parity (2Kx8?)"
                self.x8.append(n)
            else:
                self.role[n] = "unknown (uses parity bits)"

    def _detect_rom(self):
        rom_map = []
        for b in range(8):
            want = [(NINTENDO_LOGO[i] >> b) & 1 for i in range(48)]
            hits = [n for n in BRAM_NAMES if self.data[n][0x104:0x134] == want]
            if len(hits) != 1:
                raise BitstreamError(
                    "boot ROM bit %d: %s BRAM(s) match the Nintendo logo; use --map"
                    % (b, len(hits) and ",".join(hits) or "no"))
            rom_map.append(hits[0])
        if len(set(rom_map)) != 8:
            raise BitstreamError("logo detection gave overlapping BRAMs %s; use --map" % ",".join(rom_map))
        return rom_map

    def rom(self):
        out = bytearray(ROM_SIZE)
        for b, n in enumerate(self.rom_map):
            d = self.data[n]
            for a in range(ROM_SIZE):
                out[a] |= d[a] << b
        return bytes(out)

    def x8_bram(self):
        return self.x8[0] if len(self.x8) == 1 else None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_report(d, bs, an):
    print("Bitstream: sync at 0x%x, ends at 0x%x (%d bytes)" % (bs.sync, bs.end, bs.end - bs.sync))
    print("  IDCODE 0x%08X, %d frames x %d words, FDRI data at 0x%x"
          % (bs.idcode, bs.frames, bs.fbits // 16, bs.fdri))
    for dp, stored, calc in bs.crc_walk():
        print("  CRC @0x%x stored %06x calculated %06x %s"
              % (dp, stored, calc, "OK" if stored == calc else "MISMATCH"))
    others = find_bitstreams(d)
    if len(others) > 1:
        print("  file contains %d bitstreams at %s" % (len(others), ", ".join("0x%x" % o.sync for o in others)))
    print("\nBoot ROM bit map (bits 0..7): --map %s" % ",".join(an.rom_map))
    rom = an.rom()
    title = bytes(c for c in rom[0x134:0x143] if 32 <= c < 127).decode()
    print("  entry @0x100: %s   title: %r   logo ok: %s"
          % (rom[0x100:0x104].hex(" "), title, rom[0x104:0x134] == NINTENDO_LOGO))
    print("\nBRAM  data/par bits  role")
    for n in BRAM_NAMES:
        extra = ""
        if n in an.picoblaze:
            w = words_x18(an.data[n], an.par[n])
            last = max((i for i in range(0x3FF) if w[i]), default=0)
            extra = "  [reset %05X, vector @3FF %05X, code up to 0x%03X]" % (w[0], w[0x3FF], last)
        if n == an.x8_bram():
            extra = "  [appears at 0x%04X-0x%04X]" % (X8_BASE, X8_BASE + 0x7FF)
        print("  %s  %5d/%4d      %s%s" % (n, sum(an.data[n]), sum(an.par[n]), an.role[n], extra))


def cmd_extract(an, out):
    img = bytearray(0x8000)
    img[:ROM_SIZE] = an.rom()
    x8 = an.x8_bram()
    if x8:
        img[X8_BASE:X8_BASE + 0x800] = bits_to_bytes(an.data[x8])
    else:
        print("note: no unique 2Kx8 data BRAM found; 0x4000-0x7FFF left zero")
    open(out, "wb").write(img)
    print("wrote 32 KiB image (0x0000-0x3FFF boot ROM%s)" % (", 0x4000-0x47FF from %s" % x8 if x8 else ""))


def init_strings(bits, prefix):
    lines = []
    for k in range(len(bits) // 256):
        v = 0
        for i in range(256):
            v |= bits[256 * k + i] << i
        lines.append("%s_%02X = 256'h%064X" % (prefix, k, v))
    return lines


def cmd_extract_hi(an, prefix):
    for n in BRAM_NAMES:
        if n in an.rom_map:
            continue
        data, par = an.data[n], an.par[n]
        base = "%s_%s" % (prefix, n)
        open(base + ".data.bin", "wb").write(bits_to_bytes(data))
        open(base + ".par.bin", "wb").write(bits_to_bytes(par))
        with open(base + ".init", "w") as f:
            f.write("\n".join(init_strings(data, "INIT") + init_strings(par, "INITP")) + "\n")
        if n in an.picoblaze:
            with open(base + ".psm.hex", "w") as f:
                f.write("\n".join("%05X" % w for w in words_x18(data, par)) + "\n")
        print("%s: %s" % (n, an.role[n]))


def cmd_patch(bs, an, new, include_4000):
    if len(new) < 0x134 or new[0x104:0x134] != NINTENDO_LOGO:
        print("warning: new image has no Nintendo logo at 0x104; it will not boot on a Game Boy,\n"
              "         and later runs will need --map %s" % ",".join(an.rom_map))
    rom = bytes(new[:ROM_SIZE]) + b"\xff" * max(0, ROM_SIZE - len(new))
    for b, n in enumerate(an.rom_map):
        bs.write_data(n, [(rom[a] >> b) & 1 for a in range(ROM_SIZE)])
    if include_4000:
        x8 = an.x8_bram()
        if not x8:
            raise BitstreamError("--include-4000: no unique 2Kx8 data BRAM in this bitstream")
        bs.write_data(x8, bytes_to_bits(new[X8_BASE:X8_BASE + 0x800], 16384))
        print("wrote 0x4000-0x47FF into %s" % x8)
    elif len(new) > ROM_SIZE and any(new[X8_BASE:X8_BASE + 0x800]):
        print("note: 0x4000-0x47FF of the new image was not written (use --include-4000)")


def cmd_write_bram(bs, an, name, payload, mode, force):
    name = name.upper()
    if name not in BRAM_NAMES:
        raise BitstreamError("unknown BRAM %r (A0-A7, B0-B7)" % name)
    if name in an.rom_map and not force:
        raise BitstreamError("%s holds boot ROM bit %d; use --force to overwrite"
                             % (name, an.rom_map.index(name)))
    if mode in ("x8", "x1"):
        if len(payload) > 2048:
            raise BitstreamError("payload is %d bytes, max 2048" % len(payload))
        bs.write_data(name, bytes_to_bits(payload, 16384))
    elif mode == "psm":
        words = [int(l, 16) for l in payload.decode().split() if l.strip()]
        if len(words) > 1024:
            raise BitstreamError("psm file has %d words, max 1024" % len(words))
        words += [0] * (1024 - len(words))
        bs.write_data(name, [(words[n >> 4] >> (n & 15)) & 1 for n in range(16384)])
        bs.write_parity(name, [(words[p >> 1] >> (16 + (p & 1))) & 1 for p in range(2048)])
    else:
        raise BitstreamError("unknown mode %r" % mode)
    print("wrote %s (%s mode), previously: %s" % (name, mode, an.role[name]))


def main(argv):
    opts = {"second": False, "map": None, "include_4000": False, "mode": "x8", "force": False}
    args = []
    it = iter(argv[1:])
    for a in it:
        if a == "--second":
            opts["second"] = True
        elif a == "--map":
            opts["map"] = parse_map(next(it))
        elif a.startswith("--map="):
            opts["map"] = parse_map(a[6:])
        elif a == "--include-4000":
            opts["include_4000"] = True
        elif a == "--mode":
            opts["mode"] = next(it)
        elif a.startswith("--mode="):
            opts["mode"] = a[7:]
        elif a == "--force":
            opts["force"] = True
        elif a.startswith("--"):
            raise BitstreamError("unknown option %s" % a)
        else:
            args.append(a)
    if len(args) < 2:
        print(__doc__)
        return 1
    cmd, src = args[0], args[1]
    need = {"report": 2, "extract": 3, "extract_hi": 3, "patch": 4, "write_bram": 5,
            "fixcrc": 3, "checkcrc": 2}
    if cmd not in need or len(args) != need[cmd]:
        print(__doc__)
        return 1

    d = bytearray(open(src, "rb").read())
    bs = select_bitstream(d, opts["second"])

    if cmd == "checkcrc":
        ok = True
        for dp, stored, calc in bs.crc_walk():
            print("CRC @0x%x stored %06x calculated %06x %s"
                  % (dp, stored, calc, "OK" if stored == calc else "MISMATCH"))
            ok &= stored == calc
        return 0 if ok else 2
    if cmd == "fixcrc":
        bs.crc_walk(fix=True)
        open(args[2], "wb").write(d)
        return 0

    an = Analysis(bs, opts["map"])
    if cmd == "report":
        cmd_report(d, bs, an)
    elif cmd == "extract":
        cmd_extract(an, args[2])
    elif cmd == "extract_hi":
        cmd_extract_hi(an, args[2])
    elif cmd in ("patch", "write_bram"):
        if cmd == "patch":
            cmd_patch(bs, an, open(args[2], "rb").read(), opts["include_4000"])
            out = args[3]
        else:
            cmd_write_bram(bs, an, args[2], open(args[3], "rb").read(), opts["mode"], opts["force"])
            out = args[4]
        bs.crc_walk(fix=True)
        open(out, "wb").write(d)
        print("CRCs updated, wrote %s" % out)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except BitstreamError as e:
        print("error: %s" % e, file=sys.stderr)
        sys.exit(1)
