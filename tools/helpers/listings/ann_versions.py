"""Per-version titles and extra annotations.

Bank 0: FW4 is the reference (ann_bank0). Names, comments and headers are carried to
the other versions by instruction alignment (pbtransfer); this file adds titles,
names for code that only exists in a given version, and version-specific notes.
Bank 1: the standard program (FW0 application, FW1 and later) is the reference
(ann_bank1); the FW0 golden variant differs in one word.
"""

import ann_bank0 as A

_ARCH = A.TITLE.split(";------------------------------------------------------------------------------\n; ARCHITECTURE")[1]


def title(lines):
    head = ";==============================================================================\n"
    head += "\n".join("; " + l if l else ";" for l in lines) + "\n"
    head += ";\n; Commented disassembly. Re-assembles to the original 1024 words (pbasm.py).\n"
    head += "; Labels, comments and section headers are shared with the FW4 listing and\n"
    head += "; were carried over by instruction alignment; code that only exists in this\n"
    head += "; version is annotated separately.\n"
    return head + ";------------------------------------------------------------------------------\n; ARCHITECTURE" + _ARCH


MAIN_LOOP_RTC = """
------------------------------------------------------------------------------
MAIN LOOP (FW5 and FW5 SGB beta): every pass copies the PCF8563 time into the
Game Boy RTC window (rtc_publish, now unconditional). When B9 = 01 it also runs
an MBC3 real-time-clock emulation (mbc3_rtc_update):
  - read the PCF8563 seconds; when they change, count one elapsed second in
    scratch 33 (s, 0-59), 34 (min, 0-59), 35 (h, 0-23), 36 (days, 8-bit)
  - output A5-A9 = MBC3 registers S, M, H, DL, DH = base value (input ports
    A5-A9) + elapsed time, with carries; a day overflow sets DH bit 0, or
    DH bit 7 (day-counter carry) if bit 0 was already set
The elapsed counters are reset by a ROM load (event 20) and, in FW5 SGB beta,
when the game writes an MBC3 RTC register. B9 probably means "MBC3 + timer
mapper active" here (the kernel selects mapper $83 = MBC3+TIMER).
------------------------------------------------------------------------------"""

RTC_EMU_COMMENTS = {
    0x032: "start at PCF8563 register 2", 0x033: "no interrupts during the I2C burst",
    0x034: "time -> GB RTC window", 0x036: "MBC3 timer active?",
    0x039: "PCF8563 seconds", 0x03A: "read it", 0x03B: "last seen seconds value",
    0x03C: "unchanged: nothing to do", 0x03E: "remember it",
    0x03F: "elapsed seconds", 0x040: "59?", 0x042: "+1 s",
    0x045: "wrap seconds", 0x047: "elapsed minutes", 0x04A: "+1 min",
    0x04D: "wrap minutes", 0x04F: "elapsed hours", 0x050: "23?", 0x052: "+1 h",
    0x055: "wrap hours", 0x057: "elapsed days", 0x058: "+1 day",
    0x05A: "S: base + elapsed", 0x05F: "mod 60, carry in s3", 0x063: "MBC3 S",
    0x064: "M: base + elapsed + carry", 0x06E: "MBC3 M",
    0x06F: "H: base + elapsed + carry", 0x075: "mod 24", 0x079: "MBC3 H",
    0x07A: "DL: base + elapsed days", 0x07D: "overflow?", 0x07E: "+ carry from hours",
    0x081: "MBC3 DL (wrapped)", 0x082: "DH", 0x083: "day bit 8 already set?",
    0x085: "yes: set day-counter carry (b7)", 0x088: "no: set day bit 8",
    0x08B: "MBC3 DL", 0x08C: "DH unchanged", 0x08E: "pause, then repeat",
}

RTC_EMU_NAMES = {
    0x032: "main_loop", 0x036: "mbc3_rtc_update", 0x045: "mbc3_wrap_s", 0x04D: "mbc3_wrap_m",
    0x055: "mbc3_wrap_h", 0x05A: "mbc3_compose", 0x063: "mbc3_out_s", 0x06E: "mbc3_out_m",
    0x079: "mbc3_out_h", 0x081: "mbc3_day_overflow", 0x088: "mbc3_day_bit8",
    0x08B: "mbc3_no_overflow", 0x343: "isr",
}

ISR_DEBUG = """
------------------------------------------------------------------------------
ISR entry (FW0-FW3): debug DD, then the event byte, then dispatch on B5
(see isr_events). The sector-read path also prints 44 when done.
------------------------------------------------------------------------------"""

ISR_FW5 = """
------------------------------------------------------------------------------
ISR (FW5): debug DD, then the event byte, then dispatch on B5
  80 read sectors, 40 write sectors, 20 ROM load (also clears the MBC3
  elapsed counters), 10 set RTC (debug AA), 08 flash page write (bank 1)
------------------------------------------------------------------------------"""

ISR_SGB = """
------------------------------------------------------------------------------
ISR (FW5 SGB beta): as FW5, plus game writes to the MBC3 RTC registers:
  B8 = 01: DL written -> copy input A8 to output A8, clear elapsed days
  B8 = 02: DH written -> copy input A9 to output A9
  B5 = 04: S written  -> copy A5, clear elapsed seconds
  B5 = 02: M written  -> copy A6, clear elapsed minutes
  B5 = 01: H written  -> copy A7, clear elapsed hours
(B8 is checked first; when it is 01 or 02 the B5 events are not handled in
the same interrupt.)
------------------------------------------------------------------------------"""

RTC_INIT_FW5 = """
rtc_init (FW5 and FW5 SGB beta): control 1 = 00 (run); no longer stops the
clock or sets CLKOUT on every boot. If the VL (clock integrity) flag is set:
reset the clock to year 00, month 01, weekday 03, day 01, 00:00:00."""

XFER_NODEBUG = """
sd_xfer_start: DMA address 0, block size 512, enable data events, then send
the command with an R1 response. (No 99 + address debug output in this
version.)"""

ROMLOAD_BB = """
------------------------------------------------------------------------------
rom_load (event 20, Game Boy $7F36 = 03): as in FW4, with one addition:
port BB is sampled into scratch 2B at the start, and the per-cluster wait
(delay_l) is skipped when it reads 11. BB probably mirrors $7FBB; its meaning
is not known.
------------------------------------------------------------------------------"""

ROMLOAD_FW1 = """
------------------------------------------------------------------------------
rom_load (event 20, Game Boy $7F36 = 03): see FW4. In FW1-FW3 the per-cluster
wait is delay_l_half + 2 x delay_m (about 325k instructions) instead of
delay_l (543k) in FW0 and FW4.
------------------------------------------------------------------------------"""

HEARTBEAT = """
------------------------------------------------------------------------------
Debug heartbeat (FW5 slot B only): after every main-loop pause, send EE and
then input ports AC, AB, AF, AE, A9, A8 to the debug output.
------------------------------------------------------------------------------"""

VERSIONS = {
    "8871f4e6": {
        "file": "bank0_FW0.psm",
        "title": ["EZ-Flash Junior FPGA (XC3S200A) - PicoBlaze KCPSM3, program BANK 0",
                  "Firmware FW0 (golden and application images share this bank 0)."],
        "names": {0x3A1: "isr"},
        "comments": {0x3A1: "debug DD", 0x3A4: "debug: event byte", 0x3AC: "debug 44: read done",
                     0x29C: "debug: every table word read (4 bytes)", 0x2DA: "debug: sector count"},
        "headers": {0x3A1: ISR_DEBUG, 0x3A3: "isr_events: dispatch on B5."},
    },
    "b90e8d48": {
        "file": "bank0_FW1-FW3.psm",
        "title": ["EZ-Flash Junior FPGA (XC3S200A) - PicoBlaze KCPSM3, program BANK 0",
                  "Firmware FW1, FW2 and FW3 (identical bank 0 in all three)."],
        "names": {0x3A3: "isr"},
        "comments": {0x1D4: "shorter wait than FW0/FW4 (~325k instr total)", 0x1D5: "", 0x1D6: "",
                     0x3A3: "debug DD", 0x3A6: "debug: event byte", 0x3AE: "debug 44: read done",
                     0x29E: "debug: every table word read (4 bytes)", 0x2DC: "debug: sector count"},
        "headers": {0x1A7: ROMLOAD_FW1, 0x3A3: ISR_DEBUG, 0x3A5: "isr_events: dispatch on B5."},
    },
    "74a33101": {
        "file": "bank0_FW5_slotB.psm",
        "title": ["EZ-Flash Junior FPGA (XC3S200A) - PicoBlaze KCPSM3, program BANK 0",
                  "FW5 slot B: the second bitstream in both FW5 update ROMs (identical in",
                  "both, never written to flash by the updater). Code base: FW4 plus a",
                  "debug heartbeat and the port-BB loader option of FW5.",
                  "Extra ports: AB, AC, AE, AF, A8, A9 in (heartbeat dump), BB in (loader",
                  "option). Scratch 2B = sampled BB."],
        "names": {0x03A: "debug_heartbeat", 0x1E4: "rom_load_next"},
        "comments": {0x03A: "heartbeat marker EE", 0x03C: "port AC", 0x03F: "port AB",
                     0x042: "port AF", 0x045: "port AE", 0x048: "port A9", 0x04B: "port A8",
                     0x1C8: "sample port BB", 0x1E0: "BB = 11: skip the per-cluster wait"},
        "headers": {0x03A: HEARTBEAT, 0x19F: XFER_NODEBUG, 0x1B1: ROMLOAD_BB},
    },
    "755c0dcf": {
        "file": "bank0_FW5.psm",
        "title": ["EZ-Flash Junior FPGA (XC3S200A) - PicoBlaze KCPSM3, program BANK 0",
                  "Firmware FW5 (slot A of the FW5 update ROM, the image that is installed).",
                  "Extra ports: A5-A9 in = MBC3 RTC base values S, M, H, DL, DH;",
                  "A5-A9 out = emulated MBC3 RTC registers; BB in = loader option.",
                  "Scratch 33-36 = elapsed s/min/h/days, 37 = last PCF8563 seconds,",
                  "2B = sampled BB. The E4-E7 dead code of earlier versions is gone."],
        "names": {**RTC_EMU_NAMES, 0x225: "rom_load_next"},
        "comments": {**RTC_EMU_COMMENTS, **{0x209: "sample port BB",
                                            0x221: "BB = 11: skip the per-cluster wait",
                                            0x343: "debug DD", 0x346: "debug: event byte",
                                            0x359: "clear MBC3 elapsed counters",
                                            0x361: "debug AA"}},
        "headers": {0x032: MAIN_LOOP_RTC, 0x036: "mbc3_rtc_update: see the main loop header above.",
                    0x345: "isr_events: dispatch on B5 (see the ISR header above).",
                    0x343: ISR_FW5, 0x31B: RTC_INIT_FW5, 0x1E0: XFER_NODEBUG, 0x1F2: ROMLOAD_BB},
    },
    "518780d6": {
        "file": "bank0_FW5_SGB.psm",
        "title": ["EZ-Flash Junior FPGA (XC3S200A) - PicoBlaze KCPSM3, program BANK 0",
                  "Firmware FW5 SGB beta (slot A of the FW5 SGB update ROM).",
                  "Extra ports as FW5, plus B8 in = MBC3 day register written",
                  "(01 = DL, 02 = DH)."],
        "names": {**RTC_EMU_NAMES, 0x225: "rom_load_next", 0x34D: "isr_dh_write",
                  0x378: "isr_s_write", 0x37F: "isr_m_write", 0x386: "isr_h_write"},
        "comments": {**RTC_EMU_COMMENTS, **{0x209: "sample port BB",
                                            0x221: "BB = 11: skip the per-cluster wait",
                                            0x343: "debug DD", 0x345: "MBC3 day register written?",
                                            0x346: "DL", 0x348: "base DL from the game",
                                            0x34A: "clear elapsed days", 0x34D: "DH",
                                            0x34F: "base DH from the game",
                                            0x353: "debug: event byte",
                                            0x366: "clear MBC3 elapsed counters",
                                            0x36E: "debug AA", 0x378: "S written",
                                            0x37A: "base S from the game", 0x37C: "clear elapsed seconds",
                                            0x37F: "M written", 0x381: "base M", 0x383: "clear elapsed minutes",
                                            0x386: "H written", 0x388: "base H", 0x38A: "clear elapsed hours"}},
        "headers": {0x032: MAIN_LOOP_RTC, 0x036: "mbc3_rtc_update: see the main loop header above.",
                    0x352: "isr_events: dispatch on B5 (see the ISR header above).",
                    0x343: ISR_SGB, 0x31B: RTC_INIT_FW5, 0x1E0: XFER_NODEBUG, 0x1F2: ROMLOAD_BB},
    },
}

GOLDEN_BANK1_TITLE_NOTE = (
    "; THIS FILE: FW0 golden image (first bitstream in the FW0 flash dump).\n"
    "; Identical to the standard bank 1 except 1B8 = LOAD s0, 01, which enables\n"
    "; the MultiBoot path (boot_multiboot) into the application image at 040000.\n")
