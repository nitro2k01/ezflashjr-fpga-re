# Tools

Python 3, standard library only. Every tool that reads firmware accepts any file containing a bitstream: an update ROM (`Update_FW*.gb`), a 2 MB flash dump or a raw bitstream. Only the bitstream bytes are changed; the rest of the file is copied as is, so a patched update ROM stays an update ROM.

## bootrom_patch.py

Reads and writes the boot ROM and the other block RAMs, and recalculates the configuration CRC.

| Command | Does |
|---|---|
| `report <file>` | CRC check, boot ROM bit map (as a `--map` value), role and bit counts of all 16 BRAMs |
| `extract <file> <out.gb>` | Boot ROM 0000–3FFF plus the 2K×8 data at 4000–47FF, as a 32 KB file (rest zero) |
| `extract_hi <file> <prefix>` | Every non-boot-ROM BRAM: `<prefix>_<BRAM>.data.bin`, `.par.bin`, `.init` (`INIT_xx`/`INITP_xx` strings), and `.psm.hex` for PicoBlaze programs |
| `patch <file> <new.gb> <out>` | Write 0000–3FFF of `new.gb` into the boot ROM BRAMs |
| `write_bram <file> <BRAM> <data> <out>` | Write one BRAM; `--mode x8` (2 KB binary, default), `psm` (`.psm.hex`, data + parity), `x1` (2 KB binary of 16K single bits) |
| `fixcrc <file> <out>` | Recalculate both CRCs |
| `checkcrc <file>` | Verify both CRCs |

Options:

- `--second`: use the second bitstream in the file (FW0 flash dump: application image; FW5 update ROMs: slot B). Error if there is only one.
- `--map B6,B2,...`: the BRAMs holding ROM bits 0–7, instead of detecting them from the Nintendo logo.
- `--include-4000`: `patch` also writes 4000–47FF into the 2K×8 data BRAM.
- `--force`: let `write_bram` overwrite a boot ROM BRAM.

BRAM names (A0–A7, B0–B7) are explained in [docs/03-bram-layout.md](../docs/03-bram-layout.md).

## kcpsm3_dis.py

`kcpsm3_dis.py <prog.psm.hex>` prints a plain disassembly of a PicoBlaze program with automatic labels and cross-references (input/output ports, scratchpad addresses, callers). For a starting point on an unknown program; the commented listings in [listings/](../listings) are more useful for the known versions.

## pbasm.py

`pbasm.py <file.psm>` assembles a listing to `.psm.hex` (stdout). `pbasm.py <file.psm> <original.psm.hex>` compares the result with the original program instead. It handles the syntax of the listings in this repository: labels, `ADDRESS`, all KCPSM3 instructions, hex constants, register names `s0`–`sF`. `CONSTANT` and `NAMEREG` are not supported.

## Example: change a PicoBlaze program

```sh
python3 tools/bootrom_patch.py report Update_FW4.gb              # bank 0 is A0 in FW4
cp listings/bank0_FW4.psm my_bank0.psm                            # edit it
python3 tools/pbasm.py my_bank0.psm > my_bank0.psm.hex
python3 tools/bootrom_patch.py write_bram --mode psm Update_FW4.gb A0 my_bank0.psm.hex Update_FW4_mod.gb
python3 tools/bootrom_patch.py checkcrc Update_FW4_mod.gb
```

Which BRAM is bank 0 and which is bank 1 differs per build (table in [docs/10-firmware-versions.md](../docs/10-firmware-versions.md#bram-assignment)). `report` shows the PicoBlaze BRAMs; the bank-1 program is the one whose listing matches `bank1.psm` (compare with `pbasm.py bank1.psm <prefix>_<BRAM>.psm.hex`).

## Helper scripts

[helpers/](helpers) holds the scripts used during the research: regenerating the listings and diffs, checking the survey data, timing routines, and cross-checks against hardware dumps.
