# Helper scripts

Scripts used to produce and check the results in this repository. They import the main tools from `tools/`, so run them from anywhere in the repository tree as shown.

## listings/: regenerate the commented listings

```sh
python3 tools/helpers/listings/build_listings.py <out_dir> <firmware files...>
```

Pass the update ROMs and the FW0 flash dump (all files of the official firmware archive). It extracts every PicoBlaze program, identifies each by the md5 of its 1024 words, writes a commented listing per known program, re-assembles each listing and compares it with the original words, and writes the version diffs to `<out_dir>/diffs/`. Output for the full archive is what is in [listings/](../../listings).

| File | Role |
|---|---|
| `build_listings.py` | Driver |
| `ann_bank0.py` | Names, comments and section headers for bank 0, written against FW4 (the reference) |
| `ann_bank1.py` | Names, comments and headers for bank 1 |
| `ann_versions.py` | Per-version titles and the annotations for code that only exists in some versions |
| `pbtransfer.py` | Carries labels and comments from FW4 to the other versions by aligning identical instructions, so the same code gets the same label everywhere |
| `pbannotate.py` | Writes a listing (marks unreachable code, collapses unused zero areas) |
| `pbreach.py` | Reachability analysis from the reset vector, interrupt vector and bank entry |
| `pbdiff.py` | Instruction-level diff with relocation filtering |

Labels not named by hand are derived from the enclosing routine: `<routine>_Lxx`, where xx is the offset from the routine's start in FW4.

## survey/: check the bit-mapping formula against the hardware survey

```sh
python3 tools/helpers/survey/survey_verify.py Update_FW4.gb
```

Decodes the 19 survey XOR images (see [docs/11-experiments.md](../../docs/11-experiments.md#bit-address-survey)) into a source bit address for each ROM bit and compares it with the formula. The survey was made from the FW4 bitstream; the script accepts `Update_FW4.gb` or any other file containing that bitstream. The 19 XOR images are in `survey/data/` (each is a survey boot ROM read XORed with the original, so it contains only the flipped bits, no ROM content).

## analysis/

| Script | Use |
|---|---|
| `bitstream_info.py [-v] <file>` | Packet-by-packet dump of each bitstream: register writes, FDRI size, stored and calculated CRCs |
| `parity_order.py <file>` | Tries the eight possible parity-bit orders on the PicoBlaze BRAMs; only the one used by `bootrom_patch.py` decodes all 1024 words as valid instructions |
| `stage1_check.py --dump <stage1.gb> ... <files>` | Compares the boot ROM rebuilt from each bitstream with boot ROM dumps read from hardware |
| `pbemu.py <listing.psm> <routine> ...` | Runs routines in a small KCPSM3 emulator (no I/O) and counts instructions; used for the delay figures |
