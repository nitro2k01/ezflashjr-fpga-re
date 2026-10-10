# Hardware overview

The cartridge is built around a Xilinx Spartan-3A FPGA that sits between the Game Boy cartridge bus and everything else.

| Part | Role | Notes |
|---|---|---|
| **XC3S200A** (Spartan-3A) | Cartridge logic, boot ROM, SD controller, MBC emulation, PicoBlaze CPU | IDCODE 0x02218093; 540 configuration frames of 138 16-bit words; 16 block RAMs |
| **FT25H16** SPI flash (16 Mbit, 2 MB) | FPGA configuration (golden and application bitstreams), licence data, boot counter | Configures the FPGA in Master SPI mode; also read and written at run time by the PicoBlaze |
| **PCF8563** RTC | Real-time clock | I2C address 0x51; bit-banged by the PicoBlaze |
| microSD card | Game storage | Driven by an SD host controller inside the FPGA (native SD bus, 4-bit, DMA) |
| PSRAM/flash (one parallel-bus chip) | Holds the loaded game ROM | The FPGA writes it during ROM loading; the PicoBlaze only tells the hardware where data goes |
| SRAM | Save RAM (64 banks of 8 KB visible to the Game Boy) | Not analysed here |

## Inside the FPGA

What the FPGA design contains, as far as it is visible in the bitstream and the PicoBlaze code:

- **Boot ROM**: 16 KB at Game Boy 0000–3FFF, built from eight 16K×1 block RAMs, plus 2 KB of data at 4000–47FF from a 2K×8 block RAM. This is the "stage1" boot loader the Game Boy runs at power-on. See [04-boot-rom.md](04-boot-rom.md).
- **PicoBlaze (KCPSM3) microcontroller** with two 1K-word program banks. It runs SD card setup and transfers, ROM loading, the RTC, the licence check, firmware updates and MultiBoot. See [05-picoblaze.md](05-picoblaze.md).
- **SD host controller with DMA**. Its register layout and command format match the open-source OpenCores `sd_card_controller` (inferred from the code; the controller itself is in the fabric).
- **Register interface for the Game Boy** at `$7F00`–`$7FFF` (unlock sequence, then write-only registers) and mappable windows at `$A000`–`$BFFF`. See [06-gb-interface.md](06-gb-interface.md).
- **MBC emulation** (MBC1, MBC2, MBC3, MBC5, …) in fabric logic, with an MBC3 RTC emulated by the PicoBlaze from FW5 on.
- **Device DNA port** (the Spartan-3A's factory-programmed unique ID) and **ICAP** (internal configuration access), both used by PicoBlaze bank 1.

## Debug output

Both PicoBlaze banks send status bytes through output port A1, waiting while bit 2 of input port A0 is set. The bytes are progress markers (`B0`, `EE`, `99`, `AA`, `55`, `DD`, …) and data (licence flags at boot, sector numbers, event bytes). This looks like a serial debug channel, perhaps a UART on a test pad. Not located on hardware yet.
