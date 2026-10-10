# Firmware versions

## Version numbering

The official releases are named after the kernel (`ezgb.dat`, not covered by this research), e.g. K1.04e. The FPGA firmware version is the kernel's last digit, so K1.02 carries FW2. This project refers to FPGA firmware only, so everything is named FW*n*:

- **FW0**: the image in the early production flash dump. It contains two bitstreams, a golden image at flash 000000 and an application image at 040000. The firmware status register reports the golden image as FW0.
- **FW1–FW5**: the update ROMs.
- **FW5 SGB beta**: the "for SGB" beta update.
- **FW5 slot B**: a second bitstream appended to both FW5 update ROMs. The updater never writes it (see [07-spi-flash.md](07-spi-flash.md)).

The update ROM in the folder `2020-01-04_FW2_K1.01` is labelled FW2, and the file is identical to the one in the K1.02 folder. By the numbering rule K1.01 should carry FW1, but there is no separate FW1 build in the archive; the table lists it under FW1 for completeness.

## Release table

Dates are taken from the folder names in the firmware archive.

| FW | Kernel | Date | Fabric (non-BRAM frames) | Boot ROM 0000–3FFF | Data 4000–47FF | PicoBlaze bank 0 | PicoBlaze bank 1 |
|---|---|---|---|---|---|---|---|
| FW0 golden | K1.00 | 2019-12-25 (dump) | — | A | A | P0-FW0 | golden |
| FW0 application | K1.00 | 2019-12-25 (dump) | rebuilt | A | A | P0-FW0 | standard |
| FW1 | K1.01 | 2020-01-04 | rebuilt | A | A | **P0-FW1** | standard |
| FW2 | K1.02 | 2020-01-07 | same file as FW1 | A | A | P0-FW1 | standard |
| FW3 | K1.03 | 2020-01-11 | rebuilt | A | A | P0-FW1 | standard |
| FW4 | K1.04e | 2020-03-10 | rebuilt | **B** | **B** | **P0-FW4** | standard |
| FW5 | K1.05RC | 2020-07-31 | rebuilt | **C** | **C** | **P0-FW5** | standard |
| FW5 slot B | (in FW5 ROMs) | 2020-07-31 | rebuilt | C | C | **P0-slotB** | standard |
| FW5 SGB beta | (SGB beta) | 2020-09-29 | rebuilt | **C′** | C | **P0-SGB** | standard |

- **Bold** marks a change from the row above it in the lineage.
- **Fabric:** "rebuilt" means a new place-and-route run, so about 370 of the 389 logic frames differ. A rebuild says nothing on its own about whether the logic changed; the two FW0 images, for example, appear to be the same design (identical configuration header and BRAM contents apart from one PicoBlaze word, near-identical resource use).
- **Boot ROM C′:** the same as C except three header bytes: SGB flag (0x146 = 03), old licensee code (0x14B = 33) and the header checksum. Those are the bytes a Super Game Boy checks before enabling SGB features.
- **Boot ROM changes:** B and C are rebuilds of the stage1 boot loader (compiled code; about 12,300 of 16,384 bytes change each time, mostly relocations). The extracted ROMs match the stage1 dumps from hardware. The only Game Boy-visible behaviour change identified so far is that FW5's stage1 also writes `$7FD3` (console type).
- **FW3:** the PicoBlaze programs, the boot ROM and the data are identical to FW1/FW2. Whatever changed in FW3 is in the FPGA fabric.

PicoBlaze program names are those of the listings in [listings/](../listings): `P0-FW0` = `bank0_FW0.psm`, `P0-FW1` = `bank0_FW1-FW3.psm`, and so on; `golden` = `bank1_FW0_golden.psm`, `standard` = `bank1.psm`.

## BRAM assignment

Which BRAM holds which content changes with every place-and-route run. Names are explained in [03-bram-layout.md](03-bram-layout.md).

| FW | ROM bit 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | Data 4000 | Bank 0 | Bank 1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FW0 golden | B2 | B1 | B3 | B6 | B0 | A7 | A3 | B5 | B4 | A1 | A0 |
| FW0 application | B1 | B4 | B2 | B0 | B3 | B5 | B6 | B7 | A1 | A6 | A7 |
| FW1, FW2 | B6 | B3 | B2 | A7 | B7 | B1 | B4 | B0 | B5 | A6 | A5 |
| FW3 | B6 | B2 | B7 | B1 | A3 | B4 | A7 | B5 | B3 | A6 | A5 |
| FW4 | B6 | B2 | B1 | A4 | A3 | B4 | B5 | B0 | B3 | A0 | A1 |
| FW5 | A1 | B4 | A2 | A4 | A7 | A5 | A6 | A0 | A3 | B1 | B2 |
| FW5 slot B | A6 | A2 | A5 | A3 | A4 | A0 | A7 | A1 | B3 | B0 | B1 |
| FW5 SGB beta | A2 | B1 | B7 | A0 | A5 | A1 | A4 | B6 | A3 | A7 | A6 |

The other five BRAMs are empty (no initial contents) in every build. `bootrom_patch.py report` prints this map for any image.

## PicoBlaze changes, version by version

Labels refer to the listings; the same code has the same label in every version. Delays are instruction counts from emulating the delay routines; the core's clock is unknown. Each instruction takes 2 clock cycles.

### Bank 0 lineage

```
P0-FW0 ──► P0-FW1 (FW1–FW3) ──► P0-FW4 ──┬──► P0-FW5 ──► P0-SGB
                                         └──► P0-slotB
```

P0-slotB is built from the FW4 code, not FW5's: it has none of the MBC3 RTC code.

### FW0 → FW1 (also FW2, FW3)

One change, in `rom_load_cluster`: the wait after each cluster is shorter.

| | Call | Instructions |
|---|---|---|
| FW0 | `delay_l` | 542,602 |
| FW1 | `delay_l_half` + 2 × `delay_m` | 325,556 |

Everything else is identical, including all debug output.

### FW1 → FW4

- **Loader wait back to `delay_l`** (542,602 instructions). FW4 undoes the FW1 speed-up; a likely reason is that the shorter wait caused errors on some cards, but nothing in the code says so.
- **Debug output reduced:**
  - `table_read` no longer prints every 32-bit word it reads from the load table (4 bytes per word, so every lookup during a ROM load was printed).
  - `get_gb_sector` no longer prints the sector count.
  - The ISR no longer prints `DD` and the event byte on entry, or `44` after a sector read. Without that prefix the ISR in FW4 starts directly with the event dispatch, labelled `isr`; in FW0–FW3, FW5 and the SGB beta that part is `isr_events`.
- **No functional change otherwise.** Code after the removed lines moved up, for example the ISR from 3A3 to 395.

### FW4 → FW5

**1. MBC3 real-time clock emulation** (`main_loop`, `mbc3_rtc_update` and the `mbc3_*` labels, new code at 032–08F).

- In FW4 the main loop only copied the PCF8563 time into the Game Boy RTC window while port B9 read 01. FW5 does that copy (`rtc_publish`) on every pass, with interrupts disabled during the I2C burst.
- When B9 = 01, FW5 also runs the MBC3 emulation:
  1. Read the PCF8563 seconds register. If it changed since the last pass (scratch 37), count one elapsed second.
  2. Elapsed time is kept in scratch 33 (seconds), 34 (minutes), 35 (hours) and 36 (days, 8-bit), each wrapping at 60, 60, 24 and 256.
  3. Output ports A5–A9 get the MBC3 registers S, M, H, DL and DH: base value (input ports A5–A9) plus elapsed time, with carries between fields.
  4. A day overflow sets DH bit 0 (day counter bit 8). If bit 0 was already set, it sets DH bit 7, the MBC3 day-counter carry.
- A ROM load (event 20, `isr_events`) clears the elapsed counters.
- This matches the kernel's mapper value `$83` = MBC3+TIMER. B9 probably means "MBC3+timer mapper active" here; in FW4 it likely meant "RTC window mapped". That's an inference from the code, not verified.
- FW5 does not handle the game writing the RTC registers (see FW5 SGB beta).

**2. Port-BB loader option** (`rom_load_go`, `rom_load_cluster`). At the start of a ROM load, port BB is copied into scratch 2B. If it reads 11, the per-cluster `delay_l` wait is skipped (`rom_load_next`). Input ports B0–B4 mirror `$7FB0`–`$7FB4`, so BB is probably `$7FBB`. Neither stage1 nor the update ROMs write it, and it's not in either protocol document. Not tested on hardware.

**3. `rtc_init` changed.** FW4 stopped the clock (control 1 = 20) and set CLKOUT = 80 on every boot before checking the clock-integrity flag. FW5 only writes control 1 = 00 (run). It still resets the date to 00-01-01 00:00:00 when the flag shows the clock lost power.

**4. Debug output.** `DD` and the event byte on ISR entry are back. Setting the RTC (event 10) prints `AA`. The `99` + card address output in `sd_xfer_start` is gone.

**5. Dead code removed.** The unreachable `old_*` routines (1EE–289 in FW4, 156 words) that drove ports E4–E7 are gone. Nothing called them in any earlier version.

### FW4 → FW5 slot B

- **Debug heartbeat** (`debug_heartbeat`): after every pass of the main loop, send `EE` and then input ports AC, AB, AF, AE, A9 and A8 to the debug output. Ports AB, AC, AE and AF don't appear in any other version.
- **Port-BB loader option**, as in FW5.
- **The `99` + card address output is removed**, as in FW5.
- Nothing else: no MBC3 RTC code, and `rtc_init` is FW4's. This looks like a diagnostic build. The updater never installs it.

### FW5 → FW5 SGB beta

**The game can now set the emulated MBC3 clock.** In FW5, a game writing the MBC3 RTC registers had no effect on the emulated clock. The SGB beta's ISR checks port B8 before the normal dispatch and three more B5 values after it:

| Register written | Event | Action |
|---|---|---|
| DL | B8 = 01 | copy input A8 to output A8, clear elapsed days |
| DH | B8 = 02 | copy input A9 to output A9 |
| S | B5 = 04 | copy A5 to A5, clear elapsed seconds |
| M | B5 = 02 | copy A6 to A6, clear elapsed minutes |
| H | B5 = 01 | copy A7 to A7, clear elapsed hours |

- Labels: `isr_dh_write`, `isr_s_write`, `isr_m_write`, `isr_h_write`.
- When B8 is 01 or 02, the B5 events aren't handled in the same interrupt.
- The rest of the program is identical to FW5. The "for SGB" part of this release is otherwise only the boot ROM header (row C′ above).

### Bank 1

Bank 1 is identical in the FW0 application image and every later firmware. The FW0 golden image differs in one word:

| | 1B8 | Effect |
|---|---|---|
| golden | `LOAD s0, 01` | MultiBoot path enabled: the golden image reboots into the application at 040000 |
| standard | `LOAD s0, 02` | MultiBoot path skipped |

Both run the boot counter, the licence check and the flash page writer. See [08-multiboot.md](08-multiboot.md).

## Unchanged in every version

- **SD card setup:** CMD0, CMD8, CMD55 + ACMD41 (always requesting high capacity), CMD2, CMD3, CMD7, CMD16 (512), CMD55 + ACMD6 (4-bit bus). In `sd_acmd41`, an `OR` that should set the high-capacity bit only for version-2 cards is overwritten by the next instruction, so the bit is always set.
- **Sector transfers:** always multi-block (CMD18 or CMD25) followed by CMD12.
- **ROM loader:** walks the {file sector offset, LBA} pairs, one cluster per CMD18, requires load-table word 7D = 1, and only runs when bank 1's licence check passed.
- **Unreachable code:** a single-block write (CMD24), pulses on ports E9 and F2; in bank 1, a JEDEC ID read, a flash unprotect sequence and a DNA debug dump.
