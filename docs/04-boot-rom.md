# Boot ROM (stage1)

When the Game Boy powers up with the cartridge inserted, it runs a small boot loader ("stage1") stored inside the FPGA bitstream. Stage1 finds the kernel file `ezgb.dat` on the SD card and has the FPGA load it, then starts it. This page covers where stage1 lives and how to replace it.

## What the Game Boy sees

| Address | Contents | Source |
|---|---|---|
| 0000–3FFF | Stage1 code, a normal Game Boy ROM with header title `BOOTLOADER` | Eight 16K×1 block RAMs, one per data bit |
| 4000–47FF | 512 bytes of code (4000–41FF), then zeros | One 2K×8 block RAM |
| 4800–7FFF | All zero | No BRAM contents (see below) |

Verified by extracting the ROM from every bitstream and comparing it with boot ROM dumps read from cartridges running FW1 to FW5 (`tools/helpers/analysis/stage1_check.py`). All three areas match exactly. The FW0 images contain the same stage1 as FW1–FW3.

Whether one of the five empty BRAMs could be made to appear at 4800–7FFF (by writing contents into it) is untested. Nothing in the bitstream analysis says how the boot ROM address decoder is wired.

## The code at 4000

The 2K×8 BRAM holds the part of stage1 that has to run from WRAM, because the cartridge's ROM area changes under it during the hand-off. In FW4, stage1 copies 0x150 bytes from 4000 to D100 and calls D100. That code:

1. Writes `$7F36 = 03` (start the ROM load) and waits on the status at `$A000`.
2. Writes `$7F36 = 00` and `$7FC0 = 00` (unmap).
3. Sets the bank registers (`$2000 = 01`, `$3000 = 00`).
4. Writes `$7F31 = 00`, `$7F32 = 80`.
5. Calls 0100, the entry point of the loaded kernel.

The rest of the 512 bytes includes the routine that uploads the load table (`$7F36 = 01`). Each register write is wrapped in the unlock/lock sequence; see [06-gb-interface.md](06-gb-interface.md).

## What stage1 does

The register sequence was first documented by daid (see the README for credits). In short:

1. (FW5 only) Write the console type (initial value of register A) to `$7FD3`.
2. Read the partition table and FAT through the SD sector interface (`$7F30`, `$7FB0`–`$7FB4`) and find `ezgb.dat`.
3. Build the 512-byte load table (fragment list, file size, sectors per cluster) and upload it with `$7F36 = 01`.
4. Run the hand-off code above from WRAM.

## Versions

Stage1 has three builds plus one header variant (letters as in [10-firmware-versions.md](10-firmware-versions.md)):

| Build | Firmware | Notes |
|---|---|---|
| A | FW0–FW3 | |
| B | FW4 | Rebuilt; most bytes move |
| C | FW5, FW5 slot B | Adds the `$7FD3` write |
| C′ | FW5 SGB beta | C with the header's SGB flag (0146 = 03), old licensee code (014B = 33) and header checksum changed, so a Super Game Boy enables SGB features |

B and C are recompiles: about 12,300 of the 16,384 bytes change each time, mostly because code moved. The 4000 data changes along with them.

## Replacing stage1

`tools/bootrom_patch.py` reads and writes the boot ROM inside any file that contains a bitstream (update ROM, flash dump, raw bitstream) and recalculates the bitstream CRC.

```sh
# Which BRAM holds which ROM bit, CRC status, other BRAM contents
python3 tools/bootrom_patch.py report Update_FW4.gb

# Extract 0000-47FF as a 32 KB .gb file (4800-7FFF zero-filled)
python3 tools/bootrom_patch.py extract Update_FW4.gb stage1.gb

# Write a new 0000-3FFF (and with --include-4000 also 4000-47FF)
python3 tools/bootrom_patch.py patch --include-4000 Update_FW4.gb my_stage1.gb Update_FW4_patched.gb

# Check both CRCs of a file
python3 tools/bootrom_patch.py checkcrc Update_FW4_patched.gb
```

- **Size:** 16 KB at 0000–3FFF plus 2 KB at 4000–47FF. A replacement that relies on 4800–7FFF won't work.
- **Logo:** the tool finds the ROM BRAMs by matching the Nintendo logo at 0104–0133 in the *original* image. Pass `--map` (as printed by `report`) if the image you're patching no longer has a recognisable stage1.
- **Files with two bitstreams:** use `--second` to select the second one (FW0 flash dump: the application image; FW5 update ROMs: slot B).
- **Writing it to the cartridge** is up to you. Writing the application slot at flash 040000 with an external SPI programmer is the safe route: the golden image at 000000 stays intact, and if the new image fails its CRC check the golden image runs again, immediately or at the next power-up ([08-multiboot.md](08-multiboot.md#when-the-application-image-is-bad)). If the patched image passes the CRC check but your stage1 doesn't work, the cartridge still boots that image, so you need the programmer to recover.

The same tool can write any BRAM directly (`write_bram`), for example a modified PicoBlaze program assembled from the listings (`--mode psm`). See [tools/README.md](../tools/README.md).
