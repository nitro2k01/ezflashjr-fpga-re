# SPI flash

The FPGA configures itself from an FT25H16 SPI flash (16 Mbit = 2 MB). The same chip holds the per-cartridge licence data and a boot counter. Only PicoBlaze bank 1 accesses it at run time, by bit-banging SPI.

## Layout

From the early-production flash dump (FW0) and two dumps of the same cartridge after FW5 updates. Everything not listed is erased (FF).

| Range | Contents | Written by |
|---|---|---|
| 000000–024FFF | **Golden bitstream** (FW0 golden), sync word at 000046 | Factory |
| 030000–031FFF | **Licence block**: per-cartridge licence data and decoy records | Factory |
| 040000–064FFF | **Application bitstream**, sync word at 040046 (FW0) or 040020 (images written by the update ROMs) | Factory, then every firmware update |
| 070000–0700FF | **Boot counter**: one byte consumed per boot | PicoBlaze bank 1 on every boot |

- Each bitstream is 149,452 bytes from the sync word.
- The update ROMs write 040000 onwards, page by page: 0x20 bytes of FF padding, then the bitstream. The rest of the last 64 KB block stays erased. The golden image and the licence block are left alone. Verified by comparing dumps from before and after the FW5 update: 000000–03FFFF unchanged, 040000–0648FF equal to the corresponding part of the update ROM, FF after that.
- **FW5 slot B** (the second bitstream in both FW5 update ROMs) is not installed. The updater sends whole pages up to the end of slot A, so the last page written (064800–0648FF) also carries the first 0xD4 bytes of slot B, starting with its sync word at 06482C. Nothing reads them.
- The licence data differs between cartridges; the firmware is the same for all. See [09-licence-check.md](09-licence-check.md).

## SPI commands used

| Opcode | Command | Used for |
|---|---|---|
| `03` | Read | Boot counter, licence block, bitstream check at 040000 |
| `02` | Page program (256 bytes) | Firmware update pages, boot counter bytes |
| `D8` | 64 KB block erase | Firmware update (first page of each block), boot counter wrap |
| `05` | Read status register | Waiting for program/erase to finish |
| `06` | Write enable | Before every program/erase |

Never called: `9F` (JEDEC ID), `AB` (release from deep power-down), and `50` + `01 00 00`, which would write the status register to 00 and clear the block-protect bits.

## Boot counter

070000–0700FF holds 256 counter bytes. On every boot, bank 1:

1. Finds the first non-zero byte.
2. Programs it to `00` (consumed). In the golden image it may first program it to `01`; see [08-multiboot.md](08-multiboot.md).
3. When all 256 bytes are `00`, erases the 64 KB block and starts again at index 0.

So the counter needs one block erase every 256 boots; every other boot only programs one byte. The FW0 dump has 20 consumed bytes; later dumps of the same cartridge show 22 and 25.

In the standard images (every application image), the counter does nothing beyond counting. Its purpose there is unclear; it may only exist because the boot code is shared with the golden image, where it drives the MultiBoot fallback.

## Writing the flash from the Game Boy

The page writer in bank 1 takes any 24-bit address from the Game Boy and doesn't check it ([06-gb-interface.md](06-gb-interface.md#flash-page-write-firmware-update)). So, as far as the firmware is concerned, a Game Boy program can rewrite any part of the flash, including the golden image and the licence block. Rewriting the golden image badly would leave the cartridge unable to configure ([08-multiboot.md](08-multiboot.md#if-the-golden-image-is-damaged)); rewriting the licence block would disable ROM loading.

The flash chip itself may prevent this: the FT25H16 has block-protect bits in its status register. Whether factory cartridges have them set isn't known. The cartridge examined here had been reprogrammed externally many times, so its status register doesn't tell. The firmware never changes the status register (the unprotect sequence is unreachable), so if the factory sets protection, it stays.

Open question: reading the status register (`05`) of an untouched cartridge with an external programmer would answer it.

## Reading the flash

There is no Game Boy command that reads flash contents back. The data stays inside bank 1, which reads only the boot counter, the licence block and the first bytes at 040000. Reading the flash needs an external SPI programmer (with the FPGA held in reset or unconfigured so it doesn't drive the bus).
