"""Annotations for PicoBlaze bank 1 (licence check / flash updater), program md5 537b0b55
(identical in every firmware from FW1 on and in the FW0 application image;
the FW0 golden image b615b8ca differs only at 1B8)."""

TITLE = r"""
;==============================================================================
; EZ-Flash Junior FPGA (XC3S200A) - PicoBlaze KCPSM3, program BANK 1
; Same program in the FW0 application image and every firmware from FW1 on. The FW0
; golden image (first bitstream in the FW0 flash dump) differs in one word:
; 1B8 = LOAD s0, 01, which enables the MultiBoot boot path described below.
;
; Commented disassembly. Re-assembles to the original 1024 words (pbasm.py).
;------------------------------------------------------------------------------
; HOW THIS BANK RUNS
;   This is the second program bank of the same core as bank 0 (see bank 0,
;   bank_call). It is only ever entered at 3F3 (CALL dispatch), right after
;   bank 0 writes 1 to port C8; registers and scratchpad are shared. The code
;   at 000 (an endless delay loop) and the interrupt handler never run in
;   normal operation, because the core always resets into bank 0.
;
;   dispatch (1B5):
;     scratch 3F = 01 -> flash_page_write (firmware update, bank-0 event 08)
;     otherwise       -> boot path: boot counter (and MultiBoot in the golden
;                        image only), then the licence check.
;
;  LICENCE CHECK (anti-clone)
;   On every boot this bank reads the FPGA's factory-programmed Device DNA and
;   checks it against licence data stored in the SPI flash block at 030000,
;   which also holds decoy records. If the check passes it leaves scratch
;   3E = F1, 3F = F2; bank 0 refuses to load ROMs otherwise. The details of the
;   check are intentionally not annotated in this release.
;
; PORTS
;   D3 out  DNA_PORT: b0 CLK, b1 SHIFT, b2 READ      D3 in  b0 = DNA bit
;   D4 out  SPI flash: b0 SCK, b1 CS (1 = idle), others 1 (idle value AF)
;   D4 in   b7 = MISO        D5 out  b7 = MOSI
;   D1 out  ICAP data byte    D2 out  ICAP control (b0 = clock strobe)
;   F1 out  flash update busy (GB status via $7FD2 = 01)
;   BF out / C0-C3 in: 512-byte table window (same as bank 0)
;   A0/A1   debug output (same as bank 0)
;
; SPI FLASH COMMANDS USED: 03 read, 02 page program, D8 64 KB erase, 05 read
;   status, 06 write enable; unreachable: 9F JEDEC ID, AB wake, 50 + 01 status
;   write (unprotect).
;
; SCRATCHPAD (bank 1 use; bank 0 clears 00-3D afterwards anyway)
;   00-02 MultiBoot address (02 = MSB)   03-05 flash address (05 = MSB)
;   06, 0A-1A, 1E-3E  licence check working storage
;   12 boot-counter byte  13 its index   1D shadow of port D4
;==============================================================================
"""

N = {
    0x000: "bank1_reset", 0x001: "bank1_idle", 0x003: "dna_idle", 0x006: "dna_read",
    0x00D: "dna_shift_loop", 0x01B: "dna_store", 0x024: "dna_clock",
    0x029: "dbg_dump_dna", 
    0x061: "dbg_putc",
    0x066: "delay_s", 0x06A: "delay_m", 0x06F: "delay_l", 0x074: "delay_xl", 0x079: "delay_xxl",
    0x07E: "spi_xfer_end", 0x083: "spi_cmd1", 0x089: "flash_unprotect",
    0x0AA: "spi_idle", 0x0AE: "spi_xfer",
    0x0BC: "flash_read_status", 0x0C3: "flash_write_enable", 0x0C9: "flash_read_id",
    0x0D9: "flash_read_start", 0x0E6: "spi_cs_toggle", 0x0EB: "flash_erase_64k",
    0x0FF: "flash_program_start", 0x10D: "flash_program_end",
    0x115: "icap_multiboot", 0x140: "icap_finish", 0x145: "icap_start",
    0x148: "icap_strobe", 0x14D: "icap_write",
    0x150: "bootcnt_find", 0x165: "bootcnt_found", 0x168: "bootcnt_erase",
    0x16D: "bootcnt_flag", 0x176: "bank1_isr", 
    0x1AC: "clear_scratch", 0x1B5: "dispatch",
    0x1BD: "boot_multiboot", 0x1C2: "boot_count_consume", 0x1CA: "boot_scan_image",
    0x1F4: "boot_scan_fail",
    0x031: "licence_fn_a", 0x043: "licence_fn_b", 0x05B: "set_ok1", 0x05E: "set_ok2",
    0x098: "licence_read", 0x179: "licence_mark_bad", 0x17C: "check_licence",
    0x1F8: "licence_check", 0x201: "licence_loop", 0x214: "licence_next",
    0x21E: "licence_result",
    0x227: "table_read",
    0x22F: "flash_page_write",
}

H = {
    0x000: """
------------------------------------------------------------------------------
Reset entry of this bank: never executed (the core resets into bank 0).
------------------------------------------------------------------------------""",
    0x003: """
------------------------------------------------------------------------------
DEVICE DNA (Spartan-3A DNA_PORT on port D3)
dna_read: READ pulse, then SHIFT mode, clock in 57 bits (39h) through the
shift chain s3 (LSB) .. sA (MSB), store in scratch 0A-11.
------------------------------------------------------------------------------""",
    0x029: """
Unreachable: print the DNA on the debug output.""",
    0x031: """
licence_fn_a / licence_fn_b / licence_read / check_licence: licence check
helpers (not annotated in this release).""",
    0x1F8: """
licence_check: Device DNA licence check (not annotated in this release).
Result is left in scratch 3E/3F for bank 0.""",
    0x061: """
dbg_putc: send sE to the debug output (port A1) once A0 bit 2 is clear.""",
    0x066: """
------------------------------------------------------------------------------
DELAYS (instruction counts): delay_s 24, delay_m 1.1k, delay_l 27k,
delay_xl 543k, delay_xxl 27.1M.
------------------------------------------------------------------------------""",
    0x07E: """
------------------------------------------------------------------------------
SPI FLASH (bit-banged on D4/D5; scratch 1D shadows D4)
spi_idle: D4 = AF (CS high).  spi_cs_toggle: flip CS.
spi_xfer: shift s2 out (MSB first, on D5 b7) while shifting MISO (D4 b7) in.
spi_xfer_end: transfer one byte, then raise CS.
------------------------------------------------------------------------------""",
    0x083: """
Unreachable: spi_cmd1 sends sA as a one-byte command; flash_unprotect sends
AB (release from deep power-down), 50 (enable status write), then
01 00 00 (write status = 00, clears the block-protect bits).""",
    0x0BC: """
flash_read_status: RDSR (05); status in s2; CS raised afterwards.""",
    0x0C3: """
flash_write_enable: WREN (06).""",
    0x0C9: """
Unreachable: flash_read_id: JEDEC ID (9F) into sC, sB, sA.""",
    0x0D9: """
flash_read_start: READ (03) from sC:sB:sA, leaving CS low for spi_xfer.""",
    0x0EB: """
flash_erase_64k: WREN, block erase (D8) at sC:sB:sA, wait until not busy.""",
    0x0FF: """
flash_program_start: WREN, PAGE PROGRAM (02) at sC:sB:sA; CS stays low.
flash_program_end: raise CS and wait until the write is done.""",
    0x115: """
------------------------------------------------------------------------------
icap_multiboot: send the Spartan-3A MultiBoot sequence to the ICAP (D1 data,
D2 control), rebooting the FPGA from SPI flash address [02]:[01]:[00]:
  AA99        sync
  3261 xxxx   GENERAL1 = start address bits 15:0
  3281 03xx   GENERAL2 = SPI read opcode 03, address bits 23:16
  32A1 004F   MODE_REG
  30A1 000E   CMD = REBOOT
  2000        NOOP
------------------------------------------------------------------------------""",
    0x150: """
------------------------------------------------------------------------------
BOOT COUNTER at flash 070000, used on every boot in every version: the boot
path clears one byte per boot (boot_count_consume). bootcnt_find: find the
first non-zero byte in 070000-0700FF; scratch 12 = its value, 13 = its index.
If all 256 are zero: erase the 64 KB block and use index 0 with value FF.
The FW0 dump shows 20 consumed bytes. In the golden image the counter
also drives MultiBoot: FF = try the application at 040000 (and mark the byte
01); 01 = the application did not take over last time (FPGA fell back to the
golden image), so consume the byte and carry on as the golden image.
------------------------------------------------------------------------------""",
    0x16D: """
Unreachable: scratch 14 = 1 if the counter byte was FF.""",
    0x176: """
Interrupt handler for this bank (unused): debug DD.""",
    0x1AC: """
clear_scratch: zero scratchpad 00-3D (keeps 3E/3F).""",
    0x1B5: """
------------------------------------------------------------------------------
dispatch: called from bank_call (3F3) whenever bank 0 switches to this bank.
------------------------------------------------------------------------------""",
    0x1BD: """
MultiBoot path (golden image only): long delay, then if the counter byte is
fresh (FF), check that a bitstream exists at 040000 and reboot into it.
boot_count_consume (all versions): program 00 into the current counter byte,
then run the licence check.""",
    0x1CA: """
boot_scan_image: read flash from 040000; skip up to E0 bytes of FF, expect the
sync word AA 99, then look for 31 61 (the COR2 write that follows the RCRC
command) before byte F8 of the read. Found: mark the counter byte 01 and
MultiBoot to 040000. Otherwise debug 44 and continue as the golden image.""",
    0x227: """
table_read: 32-bit word s5 of the 512-byte table window (BF / C0-C3).""",
    0x22F: """
------------------------------------------------------------------------------
flash_page_write (firmware update, bank-0 event 08 with scratch 3F = 01):
  table word 00     = flash address (bits 23:0)
  table words 01-40 = 256 data bytes
If address bits 15:8 are 0, first erase the 64 KB block. Then page-program the
256 bytes. F1 = 1 while busy (the Game Boy polls it via $7FD2 = 01).
------------------------------------------------------------------------------""",
}

C = {
    0x000: "", 0x001: "endless delay", 0x004: "DNA_PORT idle",
    0x006: "READ = 1", 0x008: "clock: load the DNA into the shift register",
    0x009: "SHIFT = 1", 0x00C: "57 bits", 0x00D: "DNA bit", 0x00E: "carry = bit",
    0x00F: "shift into s3 .. sA", 0x017: "clock next bit", 0x01B: "DNA bits 7:0",
    0x022: "most significant DNA byte",
    
    
    
    
    0x061: "debug TX busy?", 0x064: "send byte",
    0x089: "AB: release from deep power-down", 0x08B: "50: enable write status register",
    0x091: "01: write status", 0x093: "= 00", 0x095: "",
    
    
    
    0x0AA: "CS high, SCK high", 0x0AE: "8 bits", 0x0B0: "MOSI = s2 b7", 0x0B1: "SCK edge",
    0x0B4: "MISO", 0x0B5: "carry = MISO", 0x0B6: "shift in", 0x0B7: "SCK edge",
    0x0BD: "CS low", 0x0C0: "RDSR", 0x0C1: "", 0x0C7: "WREN", 0x0CD: "JEDEC ID",
    0x0DA: "CS low", 0x0DD: "READ", 0x0DF: "address", 0x0EB: "WREN",
    0x0F0: "BLOCK ERASE 64 KB", 0x0F8: "CS high", 0x0FB: "busy?",
    0x0FF: "WREN", 0x104: "PAGE PROGRAM", 0x10E: "CS high", 0x111: "busy?",
    0x116: "sync AA99", 0x11A: "GENERAL1 (type-1 write, reg 13)", 0x11E: "address bits 15:8",
    0x120: "address bits 7:0", 0x122: "GENERAL2 (reg 14)", 0x126: "SPI opcode 03 (read)",
    0x128: "address bits 23:16", 0x12A: "MODE_REG (reg 15)", 0x12E: "",
    0x132: "CMD (reg 05)", 0x136: "", 0x138: "000E = REBOOT", 0x13A: "NOOP",
    0x141: "", 0x14D: "data byte",
    0x150: "070000", 0x154: "READ", 0x157: "non-zero = unused/partly used",
    0x15F: "all 256 used: erase the block", 0x160: "value FF", 0x165: "value",
    0x166: "index",
    
    
    
    
    0x1B5: "update request?", 0x1B7: "-> program a flash page",
    0x1B8: "build constant: 02 = no MultiBoot (01 in the FW0 golden image)",
    0x1BB: "locate the boot counter (no MultiBoot)", 0x1BF: "counter byte",
    0x1C0: "FF = fresh: try the application image",
    0x1C2: "070000 + index", 0x1C6: "program 00: byte consumed",
    0x1CA: "040000", 0x1CF: "skip FF bytes", 0x1D3: "up to E0", 0x1D6: "sync AA",
    0x1D8: "", 0x1D9: "sync 99", 0x1DF: "31", 0x1E2: "61",
    0x1E9: "program 01: attempt marked", 0x1EC: "MultiBoot address 040000",
    0x1F2: "", 0x1F3: "reboot (does not return)", 0x1F5: "debug 44",
    
    
    
    
    
    
    
    
    0x22F: "busy", 0x232: "word 00: flash address", 0x236: "address bits 15:8 = 0?",
    0x23B: "yes: erase the 64 KB block first", 0x23F: "PAGE PROGRAM at the address",
    0x240: "words 01..40", 0x245: "send the four bytes of the word",
    0x24E: "256 bytes", 0x250: "finish and wait", 0x252: "not busy",
    0x3F0: "", 0x3F1: "(bank 1 already selected)", 0x3F2: "", 0x3F3: "entry point from bank 0",
    0x3F5: "back to bank 0", 0x3F6: "", 0x3F7: "",
}
