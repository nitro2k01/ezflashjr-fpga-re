# Licence check

The cartridge has a copy-protection check that ties each cartridge's flash contents to its FPGA. This page describes what the check does and how it fits into the rest of the system. The algorithm, its parameters and the layout of the licence data are deliberately left out of this release, and the listings don't annotate them.

## What it does

- **When:** on every boot, in PicoBlaze bank 1, after the boot counter (and in the golden image, after the MultiBoot decision). See [08-multiboot.md](08-multiboot.md).
- **Inputs:**
  - The FPGA's **Device DNA**, read through the Spartan-3A DNA_PORT primitive. The DNA is a 57-bit identifier programmed by Xilinx at the factory. It is read-only and differs between individual chips.
  - The **licence block** in the SPI flash at 030000–031FFF. It holds the licence data for this cartridge and a number of decoy records.
- **Result:** two scratchpad bytes, 3E and 3F. They read F1 and F2 when the check passed. Bank 1 leaves them there when it returns to bank 0.
- **Effect:** bank 0's ROM loader (event 20, `$7F36 = 03`) returns immediately unless 3E/3F are F1/F2. Nothing else is gated: SD sector access, the RTC and flash page writes work either way. Since stage1 starts the kernel through the ROM loader, a cartridge that fails the check can't get past stage1 (inferred from the code).

The licence flags are also printed on the debug output at boot and at the start of every ROM load.

## Firmware versus licence data

- **The firmware is the same for every cartridge.** All update ROMs and bitstreams in this research are generic; any of them can be installed on any cartridge.
- **The licence block is per cartridge.** It's written at the factory and no update ROM touches it.
- **What binds them is the Device DNA.** The licence block is only valid together with the FPGA it was made for. Copying a complete flash image to another cartridge therefore gives a cartridge that configures and runs stage1 but fails the check (inferred from the design, not tested).
- **Bank 1 hasn't changed since FW0.** The check is the same in every firmware version.

## Practical consequences

- Keep a backup of your cartridge's licence block (030000–031FFF) before experimenting with the flash. It can't be regenerated from public information, and a cartridge without a valid one can't load ROMs.
- Erasing the whole flash, or writing a flash image taken from another cartridge, loses it.
- Modifying the boot ROM or bank 0 doesn't affect the check. The check runs in bank 1 against the original licence block, and bank 0 only reads its result.
- After a flash page write, scratchpad 3F holds `01` (the request flag), so ROM loading stays disabled until the next boot even on a licensed cartridge ([06-gb-interface.md](06-gb-interface.md#flash-page-write-firmware-update)).

## Scope of this release

The listings show the check's code as disassembled instructions, as they do for everything else, but label its routines only generically (`licence_check`, `licence_fn_a`, …) and don't explain them. No tools for reading, generating or modifying licence data are included.
