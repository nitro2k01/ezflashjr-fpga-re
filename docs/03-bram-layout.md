# Block RAM layout

The XC3S200A has 16 block RAMs (RAMB16, 16 Kbit data + 2 Kbit parity each), in two columns of eight. This page gives the exact mapping between bitstream bits and RAM bits, which is what makes patching the boot ROM and the PicoBlaze programs possible.

## Naming

This project names the BRAMs **A0–A7** and **B0–B7**:

- **Letter**: the column, in bitstream order. Column A is frames 350–425, column B frames 426–501.
- **Digit**: the 256-bit slice within each frame that belongs to that BRAM (0–7).

These are not Xilinx site names (`RAMB16_X#Y#`). Column A is probably the left column (X0), since column addresses increase left to right; the slice-to-Y mapping hasn't been checked.

## Frame layout

Each BRAM column is 76 frames. In every frame of a BRAM column:

| Bits from frame start | Contents |
|---|---|
| 0–79 | 5 words not used for BRAM content |
| 80 + 256·s … 80 + 256·s + 255 | slice for BRAM s (s = 0–7) |
| 2128–2207 | rest of the frame |

## Data bits

A RAMB16's data bits are numbered as in Xilinx `INIT_xx` strings: in ×1 mode the address is the bit number; in ×N mode, word a bit k is data bit `N·a + k`. For data bit n (0–16383):

```
frame  = 4 · (n // 0x380) + ((n >> 5) & 3)              (0–75, within the column)
q = (n % 0x380) >> 7    h = (n >> 4) & 1    g = (n >> 2) & 3    j = n & 3
offset = 249 − 70·g + (10 if g ≥ 2 else 0) − 14·j − 7·h + q   (0–255, within the slice)

bit position in FDRI data = (column_first_frame + frame) · 2208 + 80 + 256·slice + offset
```

Bit positions are MSB-first: bit p is `byte p // 8`, mask `0x80 >> (p % 8)`.

## Parity bits

Parity bit p (0–2047) belongs to data byte p and sits in the same frame:

```
frame  = frame of data bit 8p
offset = (56 if p is odd else 186) + 7 · (1 − ((p >> 1) & 1)) + q(8p)
```

Each 128-bit half of a slice holds 14 parity bits at offsets 56–69 or 186–199; offsets 126–129 are unused.

On this design the parity bits only matter for the PicoBlaze programs (1K×18 mode, where they hold instruction bits 16–17). There is no hardware parity: they are just extra data bits. The boot ROM BRAMs (16K×1) and the 2K×8 data BRAM have no parity port, and their parity bits are all zero.

## Polarity

A 1 in the bitstream is a 1 in the RAM. Verified for all 131,072 bits of 0000–3FFF and the 16,384 bits at 4000–47FF by comparing the extracted ROM with boot ROM dumps from hardware, for every firmware version with a dump.

## How the mapping was found

1. **Bit-address survey (on hardware).** Flip every bitstream bit in the BRAM region whose bit address has address bit *k* set, load the bitstream, read the boot ROM and XOR it with the original. One run per address bit gives each ROM bit's source bit address in log₂(n) runs instead of n. 19 runs over the first 72 frames of column A located 32,256 ROM bits (bits 3 and 4 of FW4 at 0000–3EFF) with no collisions. See [11-experiments.md](11-experiments.md#bit-address-survey).
2. **Formula fit.** The survey results were fitted to the formula above; `tools/helpers/survey/survey_verify.py` checks it against all 32,256 survey results.
3. **Extension by content.** The same formula, applied to the other column and slices, reproduces all eight ROM bit-planes exactly. The parity-bit order was pinned down by decoding the PicoBlaze programs, which only decode to valid instructions (1024 of 1024) with the order above.

Some bits that the survey excluded as "control bits" are parity bits (offsets 58–69 and 186–197). Why flipping them disturbed a larger area during the survey wasn't determined.

## Which BRAM holds what

The assignment changes with every place-and-route run; see the table in [10-firmware-versions.md](10-firmware-versions.md#bram-assignment). In every build:

| Contents | BRAMs | Mode |
|---|---|---|
| Boot ROM, one per data bit | 8 | 16K×1 |
| PicoBlaze bank 0 and bank 1 | 2 | 1K×18 |
| Data at Game Boy 4000–47FF | 1 | 2K×8 |
| Empty (no initial contents) | 5 | — |

"Empty" means no initial contents. An empty BRAM could still be used as RAM by the design; the SD sector buffer and the load-table window are candidates.

## Automatic detection

`bootrom_patch.py` finds the boot ROM BRAMs by matching the Nintendo logo at 0104–0133: for each ROM bit, exactly one BRAM matches the logo's bit pattern. The PicoBlaze BRAMs are the ones whose contents decode as valid KCPSM3 code (with parity bits set). The data BRAM is the remaining non-empty BRAM without parity bits.
