# Game Boy interface

This page connects the Game Boy-side registers to what the FPGA does with them. The Game Boy side was documented first by daid and in a register summary built from disassembling stage1 and the kernel; this research adds the PicoBlaze side: which register writes become PicoBlaze events, what the PicoBlaze does with them, and a few registers and events that aren't in those notes.

Sources are marked as in the rest of the docs: **code** = read from the PicoBlaze or Game Boy code in this research, **notes** = from the earlier protocol notes, **inferred** = a reasonable reading that hasn't been checked on hardware.

## Register access

| Write | Function | Source |
|---|---|---|
| `$E1`→`$7F00`, `$E2`→`$7F10`, `$E3`→`$7F20` | Unlock the registers | notes, code |
| `$E4`→`$7FF0` | Lock | notes, code |

The registers at `$7F00`–`$7FFF` are write-only. Data comes back through windows mapped at `$A000`–`$BFFF`. Stage1, the kernel and the update ROMs generally unlock before and lock after each register write.

## Registers

| Register | Function | PicoBlaze side |
|---|---|---|
| `$7F30` | `$A000` window: `00` none, `01` SD sector buffer (4 × 512 bytes), `03` SD status (`E1` busy) | Sector buffer = DMA address 0 |
| `$7FB0`–`$7FB3` | Sector number (LBA), little-endian | Input ports B0–B3 |
| `$7FB4` | Sector count 1–4, bit 7 = write. Writing it starts the transfer | Input port B4; event 80 (read) or 40 (write) |
| `$7FBB` | **Not in the notes.** Loader option: `11` = skip the wait after each cluster (FW5 and later) | Input port BB, inferred from B0–B4 |
| `$7F36` | `01` = `$A000` takes the 512-byte load table, `03` = start the ROM load and map its status, `00` = unmap | Table via ports BF/C0–C3; `03` raises event 20; status probably from port EF |
| `$7F37`, `$7FC1`–`$7FC4`, `$7FD4` | Mapper type, ROM and SRAM bank masks, header checksum, unknown | Not seen by the PicoBlaze (fabric) |
| `$7FC0` | SRAM-area window: `00` none, `02` set before table uploads, `03` SRAM, `04` firmware version, `05` **flash page write**, `06` RTC | `05` raises event 08 (code: update ROMs); `04` is presumably answered by the fabric |
| `$7FD0` | `01` = set the RTC from the values written in the RTC window | Event 10; bytes read via F0/B6 |
| `$7FD2` | `01` = map the flash-write status at `$A000` (non-zero = busy), `00` = unmap | Output port F1 (bank 1) |
| `$7FD3` | Console type, written by stage1 from FW5 on | Not seen by the PicoBlaze |
| `$7F31`, `$7F32` | Written after loads (stage1 `00`/`80`, kernel `00`/`00`). Unknown | Not seen by the PicoBlaze |
| `$7FE0` | `80` = reset and start the loaded ROM | Not seen by the PicoBlaze |

"Not seen by the PicoBlaze" means no PicoBlaze program reads a port that corresponds to it; those registers act in the fabric, if at all.

## Events seen by the PicoBlaze

Each Game Boy command interrupts the PicoBlaze. The interrupt handler in bank 0 reads input port B5 and handles one event:

| B5 | Trigger | Action |
|---|---|---|
| `80` | `$7FB4 = n` | Wait for the card, CMD18 for n sectors into the sector buffer, CMD12 |
| `40` | `$7FB4 = n \| 80` | Wait for the card, CMD25 for n sectors from the sector buffer, CMD12 |
| `20` | `$7F36 = 03` | ROM load (only if the licence check passed; see [09-licence-check.md](09-licence-check.md)) |
| `10` | `$7FD0 = 01` | Copy the 7 bytes the Game Boy wrote (seconds … year) into the PCF8563 |
| `08` | `$7FC0 = 05` | Switch to bank 1 and program one flash page (below) |

The FW5 SGB beta adds MBC3 RTC register writes (game-side writes, not `$7Fxx` registers):

| Port | Value | Register written by the game |
|---|---|---|
| B5 | `04`, `02`, `01` | S, M, H |
| B8 | `01`, `02` | DL, DH |

In FW5 and later, input ports A5–A9 give the MBC3 RTC base values (S, M, H, DL, DH) and output ports A5–A9 the emulated registers; port B9 = `01` enables the emulation. How these map to Game Boy addresses is in the fabric; see [10-firmware-versions.md](10-firmware-versions.md#fw4--fw5).

## RTC window

With `$7FC0 = 06`, the window shows PCF8563 registers 02–08 (seconds, minutes, hours, day, weekday, month, year; BCD) at `$Ax08`–`$Ax0E` (notes; the register-to-address correspondence is inferred from the order). The PicoBlaze keeps the window updated: it reads registers 02–08 over I2C and writes them out with ports ED (index 02–08) and EE (data). Up to FW4 this only happens while port B9 reads `01`; from FW5 on, on every main-loop pass.

To set the clock, the Game Boy writes the new values into the window and then `$7FD0 = 01`. The PicoBlaze selects each byte with port F0 (index 02–08), reads it from port B6 and writes it to the PCF8563.

## Flash page write (firmware update)

The update ROMs program the configuration flash one 256-byte page at a time. Their sequence, read from the FW5 update ROM:

1. `$7FC0 = 02`, `$7F36 = 01`, copy the page record to `$A000`, `$7F36 = 00`, `$7FC0 = 00`.
   - Bytes 0–3: the flash address (32-bit little-endian, bits 23:0 used).
   - Bytes 4–259: the 256 data bytes, in order.
2. `$7FC0 = 05`: the PicoBlaze gets event 08 and runs bank 1's page writer.
3. From WRAM: `$7FD2 = 01`, poll `$A000` until it reads `00`, `$7FD2 = 00`.
4. `$7FC0 = 00`.

The page writer erases the 64 KB block first when address bits 15:8 are zero, i.e. when writing the first page of a block, then page-programs the 256 bytes. It doesn't restrict the address. The only limit on what can be written comes from the flash chip's own write protection (see [07-spi-flash.md](07-spi-flash.md)).

Side effect (code, not tested): bank 0 marks the request by writing `01` to scratchpad 3F, which also holds half of the licence result. After any flash page write, ROM loading stays disabled until the FPGA is configured again (power-up).

There is no command to read the flash back to the Game Boy. Bank 1 only reads the flash during boot.

## Not covered

- What the fabric does with `$7F31`/`$7F32`, `$7FC3`, `$7FD3` and `$7FD4`.
- The mapping of the MBC3 RTC registers and the ports AB, AC, AE, AF that the FW5 slot B heartbeat prints.
- Whether `$7FBB` is really where port BB comes from. Nothing writes it, so it hasn't been tried.
