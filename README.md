# EZ-Flash Junior FPGA reverse engineering

Documentation and tools for the FPGA inside the EZ-Flash Junior Game Boy flash cartridge: the Xilinx XC3S200A bitstream, the boot ROM it contains, the PicoBlaze microcontroller programs, the SPI flash layout and the boot process, across all known firmware versions.

The main practical result is that the cartridge's boot ROM (stage1) and the PicoBlaze programs can be **extracted from and written back into** official bitstreams, with a correct configuration CRC.

## Human written preamble

Most of this documentation and reverse engineering was performed by Claude, but as the human pulling the levers I want to give some comments before I hand over to the robotic overlord. 

Back in 2021 I was working on finding a way to get the EZFlash Jr flash Game Boy flash cartridge to boot on Super Game Boy. It was an open problem how that could be solved, and the obvious, but tedious and risky solution was to replace the stage1 bootloader that lives in the FPGA. After trying to use Xilinx's own tools for a bit, and failing for various reasons (the software wouldn't install, the command needed to access the block RAM) I gave up. Every 6+ gigabyte download that didn't work, got to my nerves and I finally decided to reverse engineer the bitstream format out of spite. Nowadays we have a [prjcombine](https://codeberg.org/prjunnamed/prjcombine) but back then there was much less FPGA reverse engineering information and tooling available.

So I wanted to flip random bits until something showed up when I read back the ROM through the cartridghe edge connector. The first hurdle I had to face though was the bitstream CRC, which wasn't really documented for the Spartan-3A family. I found a reference to a CRC polynomial that might be the one Spartan-3A was using. I couldn't figure out how to calculate the exact CRC correctly, but I figured out a way of forging the CRC by calculating a old and new partial CRC and xor'ing with the stored value. Amazingly, this worked.

I then started flipping bits, until something showed up. Then I meticulously mapped out the bit patterns until I saw repetitions. I then made a special test pattern where every other bit was flipped from the original: `01010101...` then two alternating bits `00110011` then 4 alteranting bits `00001111` and so on. This kind of pattern would cut the number of times the FPGA configuration flash would have to be programmed down from n (once per bit) to log(n). With these dumps in hand I had a blackbox way of exactly mapping every bit in the stage 1 bootloader to a bit in the bitstream, as well as a way of forging the CRC. I stopped short of writing a solver that would do the reverse mapping. Because...

I found an easier way of solving the original problem. What I call the [SGB Enabler](https://blog.gg8.se/wordpress/2021/08/19/nitro2k01s-sgb-enabler-for-ez-flash-jr/) which instead sends the same commands that the SGB would send, but from the "kernel", which avoids the risk of bricking. I then let that previous work rest because, while it was cool and took a lot of effort, it didn't seem too useful any more.

Step forward to today. We now have powerful AI that can do amazing things when it's not busy outputting slop. I asked to finish off the job, and it wrote the solver, and figured out the BRAM layout in the bitstream. It informed that some of the other BRAM blocks had data in them as well. I asked it to extract that data, and not only did it extract it, but it also informed me that there was PicoBlaze code in there. PicoBlaze is a tiny RISC CPU specialized for FPGAs. After that I basically let Claude cook. In the end it diassembled and analyzed the code and figured out what it does on the EZFlash Jr. 

Some (human-selected) highlights of this work:

- **bootrom_patch.py** Can extract or inject the stage 1 bootloader from any of the FW update ROMs from EZFlash, or into a raw bitstream dump. (Caution: it's easy to effectively brick your cartridge if you manage to put a stage 1 ROM there that can't load ezgb.dat.)
- **The fact that the PicoBlaze core exists.** This core is used for SD card access, realtime clock (RTC), firmware update process and one more thing, see below. As such, improving RTC accuracy or SD card communication reliability without reverse engineering the "sea of gates" is on the table. This can also bring some clarity of the exact meaning of some of the commands that the GB can send to the FPGA. A full (AI commented) disassembly of the PicoBlaze program is provided.
- **The PicoBlaze core is also used for copy protection.** It checks a hash of a serial number in the FPGA against a license region in the SPI configuration flash. I strongly suspect some EZFlash Jr cartridges that are "bricked" became that way because this region of flash got corrupted. With an understanding of the licence works, this region could be regenerated if ot gor corrupted, or the check could be completely removed... However, that portion of the code is deliberately obfuscated for now.

Since the research is AI generated it may get finer details wrong, and you should be careful about what assumptions you make. It's provded "as-is" with the hopes that it's better than nothing.

I'd also like to point to [lukesau's ezgb project](https://github.com/lukesau/ezgb) which also tackles reverse engineering the EZFlash Jr but with a broader scope, including building a modded kernel ROM.

Finally, I leave the mic to Claude:

## Findings

- **Bitstream and CRC.** The Spartan-3A configuration CRC is computed exactly (22-bit, x²²+x¹⁵+x¹²+x⁷+1; the RCRC command resets it and is not itself included). No magic constants needed. → [02-bitstream.md](docs/02-bitstream.md)
- **Block RAM bit mapping.** A closed-form mapping from every block RAM data and parity bit to its position in the bitstream, verified against hardware. A 1 in the bitstream is a 1 in the RAM. → [03-bram-layout.md](docs/03-bram-layout.md)
- **Boot ROM.** 16 KB at 0000–3FFF in eight 16K×1 BRAMs (one per data bit) plus 2 KB at 4000–47FF, located automatically through the Nintendo logo. Which BRAM holds which bit changes with every build. → [04-boot-rom.md](docs/04-boot-rom.md)
- **PicoBlaze.** One KCPSM3 core with two switchable 1K program banks: bank 0 runs the SD card, ROM loading and the RTC; bank 1 runs the boot counter, MultiBoot, the licence check and flash writes. Commented, re-assemblable listings of every version, with consistent labels. → [05-picoblaze.md](docs/05-picoblaze.md), [listings/](listings)
- **Game Boy interface.** How `$7Fxx` register writes become PicoBlaze events, including the flash page-write command used by firmware updates and an undocumented loader option (`$7FBB`). → [06-gb-interface.md](docs/06-gb-interface.md)
- **SPI flash and boot.** Golden image at 000000, application image at 040000, per-cartridge licence block at 030000, boot counter at 070000. The golden image hands over to the application image by MultiBoot and takes over again if the application image fails. → [07-spi-flash.md](docs/07-spi-flash.md), [08-multiboot.md](docs/08-multiboot.md)
- **Licence check.** Ties each cartridge's licence block to its FPGA's factory Device DNA and gates ROM loading. Described at a high level only. → [09-licence-check.md](docs/09-licence-check.md)
- **Versions.** What changed in each firmware release: boot ROM, PicoBlaze code, BRAM placement. → [10-firmware-versions.md](docs/10-firmware-versions.md)

## Documentation

| File | Topic |
|---|---|
| [01-hardware.md](docs/01-hardware.md) | Components and what the FPGA design contains |
| [02-bitstream.md](docs/02-bitstream.md) | Packet format, frames, CRC algorithm |
| [03-bram-layout.md](docs/03-bram-layout.md) | Block RAM naming, bit mapping formula, parity bits |
| [04-boot-rom.md](docs/04-boot-rom.md) | Stage1: location, contents, how to replace it |
| [05-picoblaze.md](docs/05-picoblaze.md) | The KCPSM3 core, the two banks, peripherals, debug output |
| [06-gb-interface.md](docs/06-gb-interface.md) | Game Boy registers and the PicoBlaze events behind them |
| [07-spi-flash.md](docs/07-spi-flash.md) | Flash layout, commands, boot counter, write protection |
| [08-multiboot.md](docs/08-multiboot.md) | Boot sequence, MultiBoot, fallback, failure modes |
| [09-licence-check.md](docs/09-licence-check.md) | What the licence check does (high level) |
| [10-firmware-versions.md](docs/10-firmware-versions.md) | Release table, BRAM assignment, per-version changes |
| [11-experiments.md](docs/11-experiments.md) | Hardware experiments done, open questions |

**Certainty.** The docs separate what was verified (on hardware, or by an exact check such as re-assembly or CRC match) from what was read from code, and mark inferences as "probably", "inferred" or "presumably". Numbers in hex are written without prefix where the context is clear (addresses, ports, opcodes); Game Boy registers use `$`.

**Firmware names.** The FPGA firmware version is the last digit of the kernel version: K1.02 carries FW2. FW0 is the factory firmware of early cartridges. Details in [10-firmware-versions.md](docs/10-firmware-versions.md).

## Repository layout

```
docs/            topic documentation (above)
listings/        commented PicoBlaze disassembly of every program version
  diffs/         instruction-level diffs between consecutive versions
tools/           main tools: bitstream patcher, PicoBlaze disassembler and assembler
  helpers/        helper scripts used during the research and to regenerate the listings
```

## Quick start

Python 3, standard library only (tested with Python 3.13). The tools take any file that contains a bitstream: an official update ROM (`Update_FW*.gb`), a flash dump or a raw bitstream.

```sh
# What's in this firmware: CRC status, boot ROM bit map, role of each BRAM
python3 tools/bootrom_patch.py report Update_FW4.gb

# Extract the boot ROM, and the PicoBlaze programs and other BRAMs
python3 tools/bootrom_patch.py extract Update_FW4.gb stage1.gb
python3 tools/bootrom_patch.py extract_hi Update_FW4.gb fw4      # fw4_A0.psm.hex, fw4_A0.init, ...

# Replace the boot ROM (CRC is recalculated)
python3 tools/bootrom_patch.py patch --include-4000 Update_FW4.gb my_stage1.gb patched.gb

# Assemble an edited listing and write it into the PicoBlaze bank 0 BRAM (A0 in FW4)
python3 tools/pbasm.py listings/bank0_FW4.psm > bank0.psm.hex
python3 tools/bootrom_patch.py write_bram --mode psm Update_FW4.gb A0 bank0.psm.hex patched.gb
```

More in [tools/README.md](tools/README.md). Read [11-experiments.md](docs/11-experiments.md#safety-notes-for-experiments) before writing anything to a cartridge: keep a full flash backup (including the licence block), test in the application slot, and have an external SPI programmer at hand.

## What is not included

- **No firmware files.** No bitstreams, update ROMs, boot ROM images or flash dumps are included, original or patched. The tools work on files you supply; the official update ROMs are distributed by the manufacturer.
- **No licence-check details.** The algorithm, its parameters and the licence data layout are not documented, and there are no tools for licence data. See [09-licence-check.md](docs/09-licence-check.md).

## Credits

- **daid**, for the original notes on the cartridge's Game Boy-side protocol and stage1/kernel loading sequence, which this work builds on.
- Xilinx UG332 (*Spartan-3 Generation Configuration User Guide*) for the configuration format, and the OpenCores `sd_card_controller` project, whose register layout matches the cartridge's SD host controller.

Research and write-up: Claude AI.

## Disclaimer

Not affiliated with or endorsed by the manufacturer of the EZ-Flash Junior, Nintendo or AMD/Xilinx. Names are used only to identify the hardware. Modifying your cartridge's flash can leave it unusable without an external programmer; you do so at your own risk.
