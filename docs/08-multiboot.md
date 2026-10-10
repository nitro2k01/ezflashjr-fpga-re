# Boot sequence and MultiBoot

The flash holds two bitstreams: a **golden image** at 000000 that is never updated, and an **application image** at 040000 that firmware updates replace. The golden image decides at boot whether to hand over to the application image. This page describes how, and what happens when something goes wrong.

## Normal boot

1. **Power-up.** The FPGA configures in Master SPI mode, always from flash address 000000: the golden image. Configuration completes fully (all frames, CRC check, startup) before anything else happens. The golden image is a complete working firmware (FW0).
2. **Golden image, PicoBlaze bank 0** starts and immediately calls bank 1's boot path.
3. **Golden image, bank 1:**
   1. Waits about 27 million instructions (`delay_xxl`).
   2. Finds the current boot counter byte at 070000 ([07-spi-flash.md](07-spi-flash.md#boot-counter)).
   3. If the byte is `FF` (fresh): reads 040000 and checks that a bitstream starts there: up to E0 bytes of FF, the sync word `AA 99`, then the COR2 write `31 61` (which follows the RCRC command) before byte F8 of the read. If so, programs the counter byte to `01` and triggers MultiBoot to 040000 through the ICAP.
4. **MultiBoot.** The ICAP sequence below makes the FPGA reconfigure itself from 040000. The golden design is discarded.
5. **Application image, bank 1:** finds the counter byte (now `01`), programs it to `00`, runs the licence check, returns to bank 0, which brings up the SD card and the RTC. The cartridge is now running the installed firmware.

The switch is not part of the configuration packet stream: the golden bitstream contains no MultiBoot address (GENERAL1/2 = 0). The jump is made at run time by the golden design's PicoBlaze writing configuration commands into the ICAP.

### ICAP sequence

Sent one byte at a time through ports D1 (data) and D2 (control):

| Words | Meaning |
|---|---|
| `AA99` | Sync |
| `3261 xxxx` | GENERAL1 = MultiBoot address bits 15:0 (`0000`) |
| `3281 03xx` | GENERAL2 = SPI read opcode `03`, address bits 23:16 (`04`) |
| `32A1 004F` | MODE_REG: NEW_MODE = 1, BOOTMODE = 001 (Master SPI) |
| `30A1 000E` | CMD = REBOOT |
| `2000` | NOOP |

With NEW_MODE = 1 and SPI mode, UG332 says fallback is not supported and the configuration watchdog doesn't apply. That may be why the golden image checks the start of the application image itself before jumping.

## When the application image is bad

If the application image fails to configure (for example a CRC error), one of two things happens. UG332 isn't clear which applies with this MODE_REG setting:

- **Fallback:** every bitstream has COR2 RESET_ON_ERR set, so the FPGA reconfigures from 000000 and the golden image boots again right away.
- **Halt:** the FPGA stops with INIT_B low, and the golden image boots at the next power-up.

The boot counter handles both cases the same way:

1. The golden image boots and finds the counter byte it marked `01`. The application image never consumed it, so it must have failed.
2. The golden image programs the byte to `00` and carries on as itself: licence check, SD card, RTC. The cartridge runs FW0, which is enough to run an update ROM again.
3. At the next power-up the next counter byte is `FF`, so the golden image tries the application image again.

Observed on hardware: after an FW5 update in which two bytes were programmed wrong (bit 7 left set at 04FFFF and 05FFFF), the cartridge came up running FW0. A second, clean write of the same image fixed it. Which of the two paths above led to FW0 wasn't recorded.

If 040000 holds no bitstream at all (erased), the golden image doesn't try to jump: it sends debug byte `44` and continues as FW0.

UG332 limits fallback to three failed attempts per power cycle. The golden image tries the application image at most once per power-up, so a bad application image never reaches that limit.

## Only the golden image does MultiBoot

Bank 1 is the same program in every image except for one word at 1B8, a build constant: `01` in the golden image, `02` in all application images. Only `01` takes the MultiBoot path. An application image therefore never reboots into anything, wherever it sits in the flash: written to 000000, it would configure at power-up and run as itself (from the code).

## If the golden image is damaged

At power-up the FPGA only ever reads from 000000. It does not search the flash for another bitstream.

- **No sync word** (erased or overwritten at the start): the configuration watchdog expires after 64K configuration clocks and the FPGA retries from 000000. After three retries it stops with INIT_B low.
- **CRC error** (corrupted somewhere in the frames): RESET_ON_ERR retries from 000000, with the same limit.
- **Valid but wrong** (a bitstream that passes its CRC but doesn't work, for example a patched image with a broken stage1): the FPGA configures and runs it.

In the first two cases the cartridge is dead until the flash is reprogrammed with an external programmer. Nothing on the Game Boy side can help, because the Game Boy interface itself is part of the bitstream. This is why the flash's write protection matters ([07-spi-flash.md](07-spi-flash.md#writing-the-flash-from-the-game-boy)).
