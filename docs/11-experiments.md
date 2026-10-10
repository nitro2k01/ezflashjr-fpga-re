# Hardware experiments and open questions

Most of this research is static analysis. This page lists what was checked on real cartridges, and what is still open.

## Done

### Bit-address survey

The first mapping of bitstream bits to boot ROM bits came from hardware. Starting from the FW4 bitstream, 19 survey bitstreams were made. Survey *s* flipped every bit in the first 72 frames of BRAM column A whose bit address within the region (byte offset and bit number) had bit *s* set, with the CRC fixed. Each was loaded on the cartridge and the boot ROM read back and XORed with the original. Together the 19 XOR images give each changed ROM bit's source address.

- 72 of column A's 76 frames were surveyed, so the result covers ROM bits 3 and 4 (the column-A bits in FW4) at 0000–3EFF: 32,256 bits, no collisions.
- The formula in [03-bram-layout.md](03-bram-layout.md) reproduces all 32,256 (`tools/helpers/survey/survey_verify.py`).
- Some bits were left out of the survey as suspected control bits. They turned out to be parity bits.

### Boot ROM dumps

The boot ROM was read from cartridges running FW1, FW2, FW3, FW4 and FW5. For every firmware, the ROM rebuilt from the bitstream matches the dump at 0000–47FF, and the dump reads zero at 4800–7FFF (`tools/helpers/analysis/stage1_check.py`). This also confirms that a 1 in the bitstream is a 1 in the ROM.

### Flash dumps around an update

An early-production cartridge (FW0) was dumped, updated to FW5 with the official update ROM, and dumped again ([07-spi-flash.md](07-spi-flash.md)):

- Only 040000 onwards changed; the golden image and the licence block were untouched.
- The update installs slot A of the update ROM. Slot B is not written.
- The boot counter kept advancing (20, then 22, then 25 consumed bytes in successive dumps).

The first update attempt left two bytes wrong (04FFFF and 05FFFF read `80` instead of `00`). The cartridge then ran FW0 from the golden image, as the boot counter logic predicts ([08-multiboot.md](08-multiboot.md#when-the-application-image-is-bad)). A second write of the same image was clean.

## Open questions

| Question | How it could be answered |
|---|---|
| Are the flash block-protect bits set on factory cartridges? | Read the flash status register (`05`) of an untouched cartridge with an external programmer, before writing anything to it. |
| Can an empty BRAM be made to appear at 4800–7FFF? | Write a pattern into each empty BRAM (`bootrom_patch.py write_bram --mode x8`), load the image, and read 4800–7FFF. Safe to try in the application slot. |
| What do ports B9 and BB mean exactly, and is BB `$7FBB`? | Write `$7FBB = 11` before a ROM load and compare load times; watch the debug output. |
| Where is the debug output? | Probe the test pads for serial data while booting. The PicoBlaze sends licence flags and `DD`/event bytes, so there is plenty of traffic. |
| What is FW5 slot B for? | Install it in the application slot and read the heartbeat on the debug output. It looks like a diagnostic build. |
| What do `$7F31`/`$7F32`, `$7FC3`, `$7FD3` and `$7FD4` do? | They act in the fabric; experiments on the Game Boy side or fabric analysis. |
| What clock does the PicoBlaze run at? | Time a known delay (for example the ROM-load wait) with a logic analyser on the SD clock or the debug output. |

## Safety notes for experiments

- Keep a full flash dump, including the licence block at 030000–031FFF, before changing anything.
- Test modified bitstreams in the application slot (040000) and leave the golden image alone. If an application image fails to configure, the golden image (FW0) runs again, immediately or at the next power-up; a bad golden image needs an external programmer.
- A bitstream that passes its CRC check but doesn't work in the application slot will be started on every boot. Have an external programmer ready.
