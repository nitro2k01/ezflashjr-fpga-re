# Bitstream format and CRC

The XC3S200A uses the "Extended Spartan-3A" configuration format described in Xilinx UG332 (chapter 17). This page covers what you need to locate data in a bitstream and to patch it.

## Packets

The bitstream starts with FF padding, the sync word `AA 99`, then a stream of 16-bit packets (big-endian).

| Header bits | Field |
|---|---|
| 15:13 | type: `001` = type 1, `010` = type 2 |
| 12:11 | opcode: `00` NOOP, `01` read, `10` write |
| 10:5 | register address |
| 4:0 | word count (type 1); unused for type 2 |

A type-2 header is followed by two words holding a 32-bit word count (upper 4 bits zero), then that many data words.

All official bitstreams have the same packet sequence:

| Register | Value | Meaning |
|---|---|---|
| CMD | 0007 | RCRC: reset CRC |
| COR2 | 89EE | bit 15 RESET_ON_ERR = 1 (retry from address 0 on CRC error) |
| CCLK_FREQ | 3C0F | configuration clock setting |
| FLR | 0089 | frame length = 0x89 + 1 = 138 words |
| COR1 | 2F08 | |
| IDCODE | 0221 8093 | XC3S200A |
| MASK, CTL, PWRDWN, HC_OPT, PU_GWE, PU_GTS, MODE_REG, GENERAL1/2, SEU_OPT, EXP_SIGN | … | GENERAL1/2 = 0: no MultiBoot address in the header |
| FAR_MAJ | 0000 0000 | start at frame address 0 |
| CMD | 0001 | WCFG |
| FDRI | type 2, 74,658 words | 541 frames × 138 words (540 frames plus one trailing pad frame) |
| CRC | 2 words | first CRC check |
| CMD | 000A, 0003, 0005 | GRESTORE, LFRM, START |
| MASK, CTL | | |
| CRC | 2 words | second CRC check |
| CMD | 000D | DESYNC |

## Frames

FDRI data is a sequence of frames, each 138 words (2,208 bits), starting at frame address 0 and incrementing. Frame numbers below are positions in the FDRI data (0–540). Bits are numbered MSB-first from the start of the FDRI data.

The block RAM contents sit in two columns of 76 frames each: frames 350–425 (column A) and 426–501 (column B). See [03-bram-layout.md](03-bram-layout.md).

## CRC

The configuration CRC is 22 bits, as UG332 states. UG332 doesn't give the algorithm; this is what matches every official bitstream (verified on all 10 bitstreams in the archive, 8 of them distinct, both CRC values each):

- Polynomial x²² + x¹⁵ + x¹² + x⁷ + 1.
- Each register write contributes the 22-bit value `(register << 16) | data_word`, folded in as `S = S·x + value (mod P)`:

  ```
  S = ((S << 1) ^ value ^ (P_low if S & 0x200000 else 0)) & 0x3FFFFF
  P_low = (1<<15) | (1<<12) | (1<<7) | 1
  ```
- **RCRC resets S to 0, and the RCRC write itself is not included.** Including it is the cause of the "magic constant" needed by earlier attempts (0x15A683 for these bitstreams).
- Writes to the CRC register are compared, not folded in, and the running value continues after a check.
- Packet header words and type-2 count words are not included.
- Type-2 data words use the register of the type-2 header (FDRI = 3).

The stored CRC value is written as two words: `00 hi`, `lo lo`, i.e. 0x00XXYYZZ.

`tools/bootrom_patch.py` recalculates both CRCs after every patch (`fixcrc`, `checkcrc`).

## Configuration behaviour that matters here

From UG332, relevant to MultiBoot and recovery (see [08-multiboot.md](08-multiboot.md)):

- Power-up configuration always starts at flash address 0.
- The configuration watchdog allows 64K CCLK cycles (about 65 ms at the initial ~1 MHz) to find the sync word, then retries from address 0; after three retries the FPGA halts with INIT_B low.
- With RESET_ON_ERR set, a CRC error also retries from address 0, with the same retry limit.
- The XC3S200A has no bitstream encryption.
