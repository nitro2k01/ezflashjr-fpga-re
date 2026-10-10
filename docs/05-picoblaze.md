# PicoBlaze microcontroller

The FPGA contains one Xilinx PicoBlaze (KCPSM3) 8-bit soft CPU. It does everything sequential: SD card setup and transfers, ROM loading, the real-time clock, the licence check, flash writes for firmware updates and the MultiBoot decision. The Game Boy-facing logic (address decoding, MBC emulation, data paths) is in the FPGA fabric.

Commented listings of every program version are in [listings/](../listings); version differences are in [10-firmware-versions.md](10-firmware-versions.md).

## KCPSM3 in brief

- 1024 instructions of 18 bits, held in one 1K×18 block RAM. Data bits 0–15 of the BRAM hold instruction bits 0–15, parity bits hold bits 16–17.
- 16 registers (`s0`–`sF`), 64 bytes of scratchpad RAM, a 31-entry call stack, Z and C flags.
- 256 input ports and 256 output ports (`INPUT`/`OUTPUT`), one interrupt (vector 3FF).
- Every instruction takes 2 clock cycles. The core's clock frequency on this cartridge is unknown, so delays are given as instruction counts.

## Two program banks

There are two PicoBlaze BRAMs, but only one core. They are **two banks** of program memory:

- Output port **C8** selects the bank (0 = bank 0, 1 = bank 1).
- The switch happens in a short routine at 3F0 that exists in both banks. In bank 0 it reads: write 1 to C8, `LOAD s0, s0` at 3F2 and 3F3 (fetch-pipeline padding; 3F3 is the slot bank 1 uses), write 0 to C8, padding, `RETURN`. In bank 1 the instruction at 3F3 is `CALL 1B5` (the bank-1 dispatcher). So bank 0 calls 3F0, execution continues in bank 1 at 3F3, bank 1's code runs and returns to 3F4, and C8 = 0 switches back.
- Registers and scratchpad are shared. Bank 1 returns its results in scratchpad 3E/3F.
- The core resets into bank 0. Bank 1's reset code and interrupt handler never run.

Evidence for one core rather than two: bank 0 only loads ROMs when scratchpad 3E/3F hold F1/F2; no version of bank 0 ever writes 3E or writes anything but 0/1 to 3F; bank 1 writes F1/F2 there and then clears scratchpad 00–3D, deliberately leaving 3E/3F.

### Bank 0: main program

- **Reset:** call bank 1 (boot path: boot counter, MultiBoot in the golden image, licence check), bring up the SD card, initialise the RTC, enable interrupts, enter the main loop.
- **Main loop:** keep the Game Boy's RTC window up to date from the PCF8563 (from FW5 also the MBC3 RTC emulation), with a pause (`delay_l`) between passes.
- **Interrupt handler:** one event per interrupt, read from input port B5. See the event table in [06-gb-interface.md](06-gb-interface.md#events-seen-by-the-picoblaze).

### Bank 1: boot, licence and flash

- **Boot path** (bank 0 enters with scratchpad 3F = 0): boot counter in flash, MultiBoot (golden image only), then the licence check. See [08-multiboot.md](08-multiboot.md) and [09-licence-check.md](09-licence-check.md).
- **Flash page write** (bank 0 enters with 3F = 1, on event 08): program one 256-byte page of the SPI flash. See [07-spi-flash.md](07-spi-flash.md).

## Peripherals

| Peripheral | How the PicoBlaze reaches it |
|---|---|
| SD host controller (with DMA) | A Wishbone-style bridge: ports 70–73 carry 32-bit data, `OUTPUT`/`INPUT` with an indexed port number select the controller register. The register layout and command-word format are consistent with the OpenCores `sd_card_controller`. DMA address 0 is the start of the sector buffer the Game Boy sees at `$A000`. |
| Load table | 512 bytes written by the Game Boy. Port BF selects a 32-bit word, C0–C3 return it. |
| PCF8563 RTC | Bit-banged I2C on ports EC (out) and EB (in), with clock stretching. |
| Game Boy RTC window | ED (index), EE (data) to publish the time; F0/B6 to read what the Game Boy wrote. |
| SPI flash | Bit-banged on D4/D5 (out) and D4 bit 7 (in), bank 1 only. |
| Device DNA | DNA_PORT on D3 (bank 1). |
| ICAP | D1 (data byte), D2 (control), bank 1. Used only for MultiBoot. |
| Debug output | A1 (byte out), A0 bit 2 (busy). See below. |

The full port tables are in the listing headers ([bank0_FW4.psm](../listings/bank0_FW4.psm), [bank1.psm](../listings/bank1.psm)).

## SD card handling

Unchanged in every version:

- **Initialisation:** CMD0, CMD8, CMD55 + ACMD41 (up to 255 attempts), CMD2, CMD3, CMD7, CMD16 (512-byte blocks), CMD55 + ACMD6 (4-bit bus). The SD clock starts slow (divider 0x48) for card identification.
- **High capacity:** ACMD41 always requests high capacity. The code that should set that bit only for version-2 cards is overwritten by the next instruction. This is probably harmless: the card's reply decides whether card addresses are converted to bytes (standard capacity) or used as block numbers.
- **Transfers:** always multi-block (CMD18 read, CMD25 write) followed by CMD12, after waiting for the card's "tran" state with CMD13.
- **ROM loading** follows the load table: for each cluster, tell the destination logic the file sector (ports E0–E3), translate it to a card address with the `{file sector offset, LBA}` pairs, read the cluster with CMD18 (the same DMA transfer as a sector read; the fabric presumably routes it into cartridge memory), CMD12, then wait. Port EF is 1 while loading, probably the source of the load status the Game Boy polls.

## Debug output

Both banks send bytes to output port A1, waiting while bit 2 of input port A0 is set. They are progress markers and data:

| Bytes | Meaning |
|---|---|
| licence flags | 3E and 3F after boot and at the start of every ROM load |
| `DD` + event | ISR entry (not in FW4 and FW5 slot B) |
| `44` | bank 0: after a sector read (FW0–FW3 only); bank 1: no bitstream found at 040000 (golden image) |
| `99` + card address | `sd_xfer_start` (FW0–FW4) |
| `AA` | set RTC (FW5) |
| `EE` | end of initialisation (all versions) |
| `EE` + ports | heartbeat after every main-loop pass (FW5 slot B only) |

This looks like a serial debug channel, probably a UART going to a test pad. It hasn't been located on the hardware.

## Unreachable code

Every version carries some code that nothing calls: a single-block SD write (CMD24), pulses on ports E9 and F2, and up to FW4 (and in FW5 slot B) a block of about 156 words (1EE–289 in FW4) that drives a 24-bit address on ports E4–E6 with a control port E7, probably a memory copy or clear from an earlier design. Bank 1 has a JEDEC ID read, a flash unprotect sequence and a Device DNA debug dump that are also never called. The listings mark every unreachable instruction.

## Working with the code

| Task | Tool |
|---|---|
| Extract a program from a firmware file | `bootrom_patch.py extract_hi` writes `<prefix>_<BRAM>.psm.hex` for each PicoBlaze BRAM |
| Disassemble | `kcpsm3_dis.py prog.psm.hex` (auto labels, port and scratchpad cross-references) |
| Assemble a listing | `pbasm.py listing.psm > prog.psm.hex`, or `pbasm.py listing.psm original.psm.hex` to compare with the original |
| Write a program back | `bootrom_patch.py write_bram --mode psm file BRAM prog.psm.hex out` |
| Time a routine | `tools/helpers/analysis/pbemu.py listing.psm delay_l` |
| Regenerate the listings and diffs | `tools/helpers/listings/build_listings.py` |

Nobody has run a modified PicoBlaze program on the cartridge yet. The mechanics are the same as for the boot ROM, so it should work, but an error in bank 1 can stop the cartridge from booting or from loading ROMs.
