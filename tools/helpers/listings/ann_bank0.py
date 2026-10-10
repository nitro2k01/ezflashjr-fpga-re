"""Annotations for PicoBlaze bank 0 (main program), firmware FW4 (program md5 45c54676)."""

TITLE = r"""
;==============================================================================
; EZ-Flash Junior FPGA (XC3S200A) - PicoBlaze KCPSM3, program BANK 0
; Firmware FW4 (reference listing: all labels and comments start here)
;
; Commented disassembly. Re-assembles to the original 1024 words (checked with
; pbasm.py). Interpretation is from static analysis of the code plus the Game
; Boy-side protocol notes; anything marked "probably" is inference.
;------------------------------------------------------------------------------
; ARCHITECTURE
;   One KCPSM3 core runs from two 1K-word program BRAMs (bank 0 = this file,
;   bank 1 = the updater/licence code). Output port C8 selects the bank; the
;   switch happens inside the routine at 3F0, which exists at the same address
;   in both banks (see bank_call). Registers and the 64-byte scratchpad are
;   shared, which is how bank 1 hands results back (scratchpad 3E/3F).
;
;   The core resets into bank 0. Bank 1 is entered twice:
;     - at boot (3F = 0): licence check against the Device DNA; on success
;       bank 1 leaves 3E=F1, 3F=F2, which unlocks ROM loading here.
;     - on event 08 (3F = 1): program one 256-byte page of the SPI config flash
;       (firmware update).
;
; FUNCTIONS IN THIS BANK
;   - SD card bring-up and sector transfers through an SD host controller with
;     DMA, reached over a Wishbone-style bridge (ports 70-73 + indexed port).
;     Register layout and command-word format are consistent with the
;     OpenCores sd_card_controller (Marek Czerski).
;   - ROM loading from the SD card (cluster by cluster, from the 512-byte
;     load table written by the Game Boy at $7F36=1).
;   - PCF8563 real-time clock over bit-banged I2C: init, continuous readout
;     into the Game Boy RTC window, and setting the time.
;
; SD CONTROLLER REGISTERS (Wishbone address = port number used with (sE))
;   00 argument          04 command (index<<8 | flags)   08-14 response
;   18 data timeout?     1C bus width (1 = 4-bit)        20 cmd timeout?
;   24 clock divider     28 software reset               34 cmd event status
;   38 cmd event enable  3C data event status            40 data event enable
;   44 block size - 1    48 block count - 1              60 DMA address
;   Command flags (low byte): b1:0 response (01 = 48-bit, 10 = 136-bit),
;   b2 busy check, b3 CRC check, b4 index check, b5 read data, b6 write data.
;   Routine sd_cmd takes "sB" flags: b0 response, b1 long, b2 CRC check,
;   b3 busy, b4 index check (15 = R1, 1D = R1b, 07 = R2, 01 = R3).
;
; INPUT PORTS                               OUTPUT PORTS
;   00-7F (sE) Wishbone ack, b1:0 != 0        00-7F (sE) Wishbone write strobe
;   70-73  Wishbone read data (70 = LSB)      70-73  Wishbone write data (70 = LSB)
;   A0     debug TX status, b2 = busy         A1     debug byte out
;   B0-B3  sector number ($7FB0-$7FB3)        BF     load-table word index
;   B4     sector count ($7FB4)               C8     program bank select (1 = bank 1)
;   B5     event flags (see isr)              E0-E3  ROM-load destination (file sector)
;   B6     RTC byte written by the GB         EC     I2C out: b0 SCL, b1 SDA (1 = release)
;   B9     01 while the RTC window is mapped  ED/EE  RTC window index / data
;   C0-C3  load-table word (C0 = b31:24)      EF     ROM load busy (1 = loading)
;   EB     I2C in: b0 SCL, b1 SDA             F0     index of RTC byte to fetch on B6
;   (A2, A3, B7, E4-E7, E9, F2 are only used by unreachable code)
;
; SCRATCHPAD
;   00 ACMD41 retry counter        01 02 = SD v2 card (CMD8 echo ok)
;   02-05 last response (02 = b31:24 .. 05 = b7:0)
;   06 01 = high-capacity card (block addressing)
;   13-16 CID response (first word)    17-18 RCA
;   19 data phase of next command: 01 read, 02 write
;   1A-1D DMA address (1A = MSB)       1E-1F block size - 1 (01FF)
;   20 block count - 1                 2A/31 sectors per cluster (lo/hi)
;   2C-2F current file sector during ROM load (2F = LSB)
;   3B load-table page (00 = words 00-7F)   3D last data event status
;   3E/3F licence flags (F1/F2 = licensed, written by bank 1)
;   3F also: 01 = "flash page write requested" when entering bank 1
;==============================================================================
"""

N = {
    0x000: "reset", 0x018: "init_acmd41", 0x032: "main_loop", 0x039: "main_idle",
    0x042: "clear_scratch", 0x04B: "sd_cmd0", 0x04E: "sd_cmd8", 0x053: "sd_wait_ready",
    0x058: "acmd41_retry", 0x067: "acmd41_ready", 0x073: "acmd41_sdsc", 0x076: "acmd41_done",
    0x078: "sd_cmd55", 0x079: "sd_cmd_rca", 0x07D: "sd_cmd13", 0x07F: "sd_acmd41",
    0x088: "sd_cmd_arg_hi", 0x08C: "sd_cmd2", 0x08F: "sd_cmd3", 0x092: "sd_cmd7",
    0x097: "sd_acmd6", 0x09C: "sd_cmd16", 0x0A1: "sd_cmd_noarg", 0x0A3: "sd_cmd_arg16",
    0x0A7: "sdc_init_regs", 0x0B5: "sdc_reset_on", 0x0B8: "sdc_reg20_clear",
    0x0C1: "sdc_reg18_clear", 0x0C3: "sdc_set_clkdiv", 0x0C9: "sdc_reset_off",
    0x0CB: "sdc_reg38_clear", 0x0CD: "sdc_reg34_clear", 0x0CF: "sdc_reg40_set",
    0x0D2: "sdc_reg40_clear", 0x0D4: "sdc_reg3C_clear", 0x0D6: "sdc_bus4",
    0x0D8: "wb_write_1", 0x0DC: "sdc_bus1", 0x0DE: "wb_write_0", 0x0E2: "wb_clear_hi",
    0x0E7: "sd_cmd", 0x100: "sd_cmd_data", 0x118: "sd_cmd_issue", 0x122: "sd_cmd_wait",
    0x129: "sd_cmd_done", 0x132: "sd_data_wait", 0x13E: "sd_cmd_ret",
    0x13F: "sd_get_resp", 0x14B: "sd_save_cid", 0x155: "dbg_putc", 0x15A: "wb_write",
    0x15C: "wb_wait_ack", 0x160: "delay_tiny", 0x164: "delay_11", 0x168: "delay_s",
    0x16D: "delay_m", 0x172: "delay_l", 0x177: "delay_l_half", 0x17C: "delay_xl",
    0x181: "sd_read_multi", 0x183: "sd_xfer_dir", 0x186: "sd_write_single",
    0x189: "sd_write_multi", 0x18B: "sd_xfer_start", 0x1A3: "sd_cmd12",
    0x1A7: "rom_load", 0x1BC: "rom_load_go", 0x1C2: "rom_load_file", 0x1C9: "rom_load_cluster",
    0x1EE: "old_wait_b7", 0x1FD: "old_bus_fill", 0x211: "old_get_33",
    0x216: "old_step", 0x234: "old_copy_a", 0x24A: "old_copy_b", 0x263: "old_copy_c",
    0x28A: "table_page", 0x294: "table_read", 0x29D: "map_sector",
    0x2BF: "lba_to_addr", 0x2CA: "get_gb_sector", 0x2D3: "old_pulse_e9",
    0x2DC: "i2c_idle", 0x2E0: "i2c_start", 0x2E7: "i2c_stop", 0x2ED: "i2c_write_byte",
    0x2F7: "i2c_read_byte", 0x2FC: "i2c_ack", 0x2FD: "i2c_clock", 0x302: "i2c_nack",
    0x304: "i2c_get_ack", 0x307: "i2c_scl_low", 0x30B: "i2c_scl_high",
    0x311: "i2c_sda_low", 0x314: "i2c_sda_high", 0x317: "i2c_read_bit",
    0x321: "i2c_delay5", 0x322: "i2c_delay4", 0x324: "i2c_delay2", 0x327: "i2c_delay1",
    0x32B: "rtc_write0", 0x32C: "rtc_write", 0x33D: "rtc_select_read",
    0x34F: "rtc_read", 0x355: "rtc_publish", 0x35E: "rtc_set_from_gb",
    0x367: "rtc_init", 0x38D: "sd_wait_tran", 0x395: "isr", 0x3B2: "isr_exit",
    0x3F0: "bank_call",
}

H = {
    0x000: """
------------------------------------------------------------------------------
RESET: run the bank-1 boot code (licence check), print the licence flags,
bring up the SD card (CMD0, CMD8, ACMD41, CMD2, CMD3, CMD7, CMD16, ACMD6 4-bit),
initialise the RTC, then enter the main loop with interrupts enabled.
------------------------------------------------------------------------------""",
    0x032: """
------------------------------------------------------------------------------
MAIN LOOP: while the Game Boy has the RTC window mapped (B9 = 01), keep copying
the PCF8563 time into it. All Game Boy commands arrive as interrupts (isr).
------------------------------------------------------------------------------""",
    0x03B: """
Unreachable: pulse output port F2.""",
    0x042: """
clear_scratch: zero scratchpad 00-3D (3E/3F, the licence flags, survive).""",
    0x04B: """
------------------------------------------------------------------------------
SD COMMAND WRAPPERS. Each loads sC = command index, sB = response flags,
s7-sA = argument (s7 = LSB) and falls into sd_cmd.
------------------------------------------------------------------------------
sd_cmd0: GO_IDLE_STATE, no response.""",
    0x04E: """
sd_cmd8: SEND_IF_COND, argument 000001AA (2.7-3.6 V, check pattern AA), R7.""",
    0x053: """
sd_wait_ready: repeat CMD55 + ACMD41 until the card reports power-up done
(OCR bit 31), at most 255 tries. Sets scratch 06 = 01 for a high-capacity card
(OCR bit 30, CCS); debug byte 82 = SDHC/SDXC, 88 = SDSC or timeout.""",
    0x078: """
sd_cmd55: APP_CMD with the card's RCA (R1).""",
    0x07D: """
sd_cmd13: SEND_STATUS with RCA (R1).""",
    0x07F: """
sd_acmd41: SD_SEND_OP_COND, argument 40300000 (HCS + 3.2-3.4 V), R3.
The OR at 085 is overwritten by the LOAD at 086, so HCS is always set.""",
    0x08C: """
sd_cmd2: ALL_SEND_CID, R2 (136-bit).""",
    0x08F: """
sd_cmd3: SEND_RELATIVE_ADDR, R6.""",
    0x092: """
sd_cmd7: SELECT_CARD with RCA, R1.""",
    0x097: """
sd_acmd6: SET_BUS_WIDTH, argument 2 (4-bit). Sent after CMD55.""",
    0x09C: """
sd_cmd16: SET_BLOCKLEN, argument s1:s0 (called with 0200).""",
    0x0A7: """
------------------------------------------------------------------------------
sdc_init_regs: initial SD host controller setup: clear timeouts and event
enables/status, 1-bit bus, pulse software reset, clock divider 48 (slow
clock for card identification).
------------------------------------------------------------------------------""",
    0x0D8: """
wb_write_1 / wb_write_0: write 00000001 / 00000000 to Wishbone register sE.""",
    0x0E2: """
wb_clear_hi: zero the upper three staging bytes (ports 71-73); sD = 0.""",
    0x0E7: """
------------------------------------------------------------------------------
sd_cmd: send SD command.
  in: sC = index, sB = flags (see header), s7-sA = argument (s7 = LSB),
      scratch 19 = data phase (01 read, 02 write, 00 none),
      1A-1D = DMA address, 1E-1F = block size - 1, 20 = block count - 1.
Builds the controller's command word in s0, programs the data registers if a
data phase is requested, issues the command, waits for the command event,
then (for data commands) waits for the data event.
------------------------------------------------------------------------------""",
    0x13F: """
sd_get_resp: read response register 08 into scratch 02-05 (02 = MSB).""",
    0x14B: """
sd_save_cid: read the response and copy it to scratch 13-16.""",
    0x155: """
------------------------------------------------------------------------------
dbg_putc: send sF to the debug output (port A1) once A0 bit 2 is clear.
Probably a UART or similar; the codes it sends are progress markers.
------------------------------------------------------------------------------""",
    0x15A: """
wb_write: write the 32-bit value staged in ports 70-73 to Wishbone register
sE (the port number is the register address), then wait for the ack.
wb_wait_ack: wait until reading register sE returns b1:0 != 0 (also used on
its own to start a register read; data then appears on input ports 70-73).""",
    0x160: """
------------------------------------------------------------------------------
DELAYS (nested countdown loops; instruction counts measured by emulation):
  delay_s  ~1.1k instr   delay_m ~27k   delay_l ~543k   delay_l_half ~271k
------------------------------------------------------------------------------""",
    0x181: """
------------------------------------------------------------------------------
SECTOR TRANSFERS. In: s7-sA = card address, scratch 20 = block count - 1.
DMA address = 0, i.e. the start of the 2 KB sector buffer the Game Boy sees
at $A000 ($7F30 = 01).
sd_read_multi:  CMD18 READ_MULTIPLE_BLOCK
sd_write_multi: CMD25 WRITE_MULTIPLE_BLOCK
sd_write_single: CMD24 (only reachable via fall-through, unused)
------------------------------------------------------------------------------""",
    0x18B: """
sd_xfer_start: DMA address 0, block size 512, enable data events, then send
the command with an R1 response. Debug: 99 followed by the 4 address bytes.""",
    0x1A3: """
sd_cmd12: STOP_TRANSMISSION, R1b.""",
    0x1A7: """
------------------------------------------------------------------------------
rom_load (event 20, Game Boy $7F36 = 03): load a file from the SD card into the
cartridge memory, following the 512-byte load table.
Gate: scratch 3E/3F must be F1/F2 (set by the bank-1 licence check).
Table words (via table_read): 7E = sectors per cluster, 7D must be 1,
7C = file size in bytes, 00.. = {file sector offset, LBA} pairs.
Port EF = 1 while loading. Each step: tell the destination logic which file
sector comes next (E0-E3), map the file sector to an LBA (map_sector), read
one cluster with CMD18 into the cartridge memory, CMD12, then wait (delay_l).
------------------------------------------------------------------------------""",
    0x1EE: """
------------------------------------------------------------------------------
UNREACHABLE (1EE-289): older code driving a 24-bit address (E4-E6) and
control port (E7) in loops of 400h/800h steps: probably a copy/clear of the
save RAM or PSRAM from an earlier design. Nothing calls it; removed in FW5.
------------------------------------------------------------------------------""",
    0x28A: """
------------------------------------------------------------------------------
table_page / table_read: read 32-bit word s5 (+ page offset from scratch 3B)
of the load table into s3:s2:s1:s0 (s0 = LSB) via port BF and C0-C3.
------------------------------------------------------------------------------""",
    0x29D: """
------------------------------------------------------------------------------
map_sector: translate a file sector offset (s7-sA) into an LBA using the
{offset, LBA} pairs: find the last pair whose offset <= file sector, then
LBA = pair.LBA + (file sector - pair.offset). Converts to a byte address for
standard-capacity cards (lba_to_addr).
------------------------------------------------------------------------------""",
    0x2BF: """
lba_to_addr: for SDSC cards (scratch 06 != 1) multiply s7-sA by 512.""",
    0x2CA: """
get_gb_sector: s7-sA = sector number from $7FB0-$7FB3 (converted for SDSC),
scratch 20 = ($7FB4 count) - 1. (Bit 7 of $7FB4, the write flag, is presumably
removed by the hardware, which reports it as event 40 instead.)""",
    0x2D3: """
Unreachable: pulse port E9.""",
    0x2DC: """
------------------------------------------------------------------------------
BIT-BANGED I2C on port EC (b0 SCL, b1 SDA, sF = shadow) / EB (inputs).
SCL high waits for the line to actually rise (clock stretching).
i2c_write_byte: s5 MSB first.  i2c_read_byte: 8 bits into s5.
i2c_get_ack: clock in the ACK bit; returns carry = 1 on NACK.
------------------------------------------------------------------------------""",
    0x32B: """
------------------------------------------------------------------------------
PCF8563 RTC ACCESS (I2C address 51: A2 write, A3 read)
rtc_write0: register sB = 00.  rtc_write: register sB = sD.
rtc_select_read: START, A2, register sB, repeated START, A3.
rtc_read: sD = register sB.
------------------------------------------------------------------------------""",
    0x355: """
rtc_publish: burst-read PCF8563 registers 2-8 (seconds .. years) and write
each into the Game Boy RTC window: ED = register number, EE = value
(the window shows them at $Ax08-$Ax0E).""",
    0x35E: """
rtc_set_from_gb (event 10, $7FD0 = 01): for registers 2-8, select the byte
via F0, read what the Game Boy wrote (B6) and store it in the PCF8563.""",
    0x367: """
rtc_init: control 1 = 20 (stop), CLKOUT = 80 (enabled), control 1 = 00. If the
VL (clock integrity) flag in the seconds register is set, reset the clock to
year 00, month 01, weekday 03, day 01, 00:00:00 and restart it.""",
    0x38D: """
------------------------------------------------------------------------------
sd_wait_tran: CMD13 until the card status (bits 15:8) is 09 = state "tran"
and ready-for-data; otherwise send CMD12 and retry.
------------------------------------------------------------------------------""",
    0x395: """
------------------------------------------------------------------------------
ISR: one event per interrupt, read from port B5
  80  read sectors   ($7FB4 = n)        -> CMD18 + CMD12
  40  write sectors  ($7FB4 = n | $80)  -> CMD25 + CMD12
  20  ROM load       ($7F36 = 03)       -> rom_load
  10  set RTC        ($7FD0 = 01)       -> rtc_set_from_gb
  08  flash page write (firmware update) -> bank 1 with scratch 3F = 01
------------------------------------------------------------------------------""",
    0x3F0: """
------------------------------------------------------------------------------
bank_call: switch to program bank 1 and back. Bank 1 has the same eight
instructions here, except that its 3F3 is "CALL 1B5" (bank-1 dispatcher).
Writing 1 to C8 switches banks; the NOPs (LOAD s0, s0) cover the fetch
pipeline, so execution continues at 3F3 in bank 1, calls the bank-1 code, and
returns to 3F4, where C8 = 0 switches back. In this bank 3F3 is only a NOP.
------------------------------------------------------------------------------""",
    0x3FF: """
Interrupt vector.""",
}

C = {
    0x000: "", 0x001: "scratch 3F = 0: bank 1 runs its boot path",
    0x003: "-> bank 1 (licence check, sets 3E/3F)",
    0x004: "debug: licence flags (F1, F2 when ok)",
    0x009: "SD controller setup, slow clock",
    0x00B: "CMD0", 0x00C: "debug B0", 0x00F: "CMD8 (SEND_IF_COND 1AA)",
    0x011: "echoed check pattern", 0x013: "AA = card understood CMD8",
    0x015: "scratch 01 = 2: SD version 2 card", 0x018: "CMD55/ACMD41 until ready",
    0x019: "CMD2 (ALL_SEND_CID)", 0x01A: "keep CID word", 0x01C: "CMD3 (SEND_RELATIVE_ADDR)",
    0x01F: "RCA = response bits 31:16", 0x023: "clock divider 0: full speed",
    0x024: "", 0x025: "software reset register = 0", 0x026: "CMD7 (SELECT_CARD)",
    0x027: "", 0x029: "CMD16 SET_BLOCKLEN 512", 0x02A: "CMD55",
    0x02B: "ACMD6: 4-bit bus", 0x02C: "controller: 4-bit bus", 0x02D: "CMD13",
    0x02E: "PCF8563 init", 0x02F: "debug EE: init done",
    0x032: "RTC window mapped?", 0x035: "start at register 2 (seconds)",
    0x036: "no interrupts during the I2C burst", 0x039: "pause, then poll again",
    0x044: "",
    0x050: "argument 000001AA", 0x053: "up to 255 attempts",
    0x05D: "OCR bits 31:24", 0x05E: "bit 31: power-up done",
    0x060: "not ready: count down", 0x064: "gave up", 0x068: "",
    0x06A: "not v2: scratch 01 = 1", 0x06D: "bit 30: CCS (high capacity)",
    0x06F: "high capacity", 0x070: "debug 82", 0x073: "debug 88",
    0x075: "standard capacity", 0x076: "scratch 06 = capacity flag",
    0x078: "CMD55", 0x07A: "argument = RCA << 16", 0x07D: "CMD13",
    0x07F: "ACMD41 (index 29)", 0x080: "R3: response, no CRC check",
    0x082: "", 0x085: "(dead: overwritten below)", 0x086: "argument 4030_0000",
    0x08C: "CMD2", 0x08D: "R2 (136-bit, CRC)", 0x08F: "CMD3", 0x092: "CMD7",
    0x097: "ACMD6", 0x09A: "argument 2: 4-bit bus", 0x09C: "CMD16",
    0x0A7: "reg 20 = 0", 0x0A8: "reg 18 = 0", 0x0A9: "reg 38 = 0 (cmd events off)",
    0x0AA: "reg 40 = 0 (data events off)", 0x0AB: "reg 34 = 0 (clear cmd events)",
    0x0AC: "reg 3C = 0 (clear data events)", 0x0AE: "reg 24 = 0", 0x0AF: "reg 1C = 0: 1-bit bus",
    0x0B0: "reg 28 = 1: reset", 0x0B1: "clock divider 48: slow identification clock",
    0x0B3: "reg 28 = 0: release reset",
    0x0E7: "", 0x0E8: "b0: response expected", 0x0EA: "b1: long response",
    0x0EC: "-> 136-bit", 0x0EE: "-> 48-bit", 0x0EF: "sB b3 -> busy check",
    0x0F2: "sB b2 -> CRC check", 0x0F5: "sB b4 -> index check",
    0x0F8: "data phase?", 0x0FB: "read data", 0x0FF: "write data",
    0x100: "reg 60: DMA address from scratch 1A-1D", 0x10A: "reg 44: block size - 1",
    0x113: "reg 48: block count - 1", 0x118: "reg 04: command (index, flags)",
    0x11C: "reg 00: argument; this starts the command",
    0x122: "wait for command event", 0x125: "06: error bits", 0x127: "b0: command complete",
    0x129: "clear command events", 0x12D: "data phase?", 0x130: "debug 55",
    0x132: "wait for data event (b0 = transfer complete)", 0x137: "keep data status",
    0x138: "clear data events", 0x13C: "data phase done",
    0x13F: "register 08 = response", 0x155: "debug TX busy?", 0x158: "send byte",
    0x15A: "start write cycle to register sE", 0x15C: "read register sE",
    0x15D: "ack/done bits",
    0x181: "CMD18", 0x182: "data phase: read", 0x186: "CMD24", 0x187: "data phase: write",
    0x189: "CMD25", 0x18C: "DMA address = 0", 0x190: "block size - 1 = 01FF",
    0x194: "", 0x195: "reg 40 = 1: data events on", 0x196: "R1",
    0x197: "debug 99, then the address bytes", 0x1A3: "CMD12", 0x1A4: "R1b",
    0x1A7: "debug: licence flags", 0x1AB: "licensed?", 0x1B1: "table word 7E: sectors per cluster",
    0x1B5: "block count - 1 = one cluster", 0x1B7: "table word 7D must be 1",
    0x1BC: "busy flag for the GB-visible status", 0x1BF: "done",
    0x1C2: "start at file sector 0", 0x1C7: "load-table page 0",
    0x1C9: "tell the destination which file sector comes next",
    0x1D1: "file sector -> card address", 0x1D2: "read one cluster", 0x1D3: "stop",
    0x1D4: "wait (lets the cluster drain into cartridge memory?)",
    0x1D5: "file sector += sectors per cluster", 0x1E3: "table word 7C: file size",
    0x1E5: "file sector * 2 < size / 256  <=>  file sector * 512 < size",
    0x1EC: "more to load",
    0x28B: "page select", 0x290: "page C0", 0x292: "page 80",
    0x294: "word index", 0x298: "b31:24", 0x29B: "b7:0",
    0x29D: "pair index 2, 4, 6, ...", 0x2A0: "compare file sector with pair offset",
    0x2A8: "file sector < offset: use previous pair", 0x2A9: "end of table",
    0x2AF: "end of table reached: fall back to pair 0", 0x2B2: "file sector - offset",
    0x2B9: "+ LBA", 0x2BF: "", 0x2C0: "high capacity: block address as is",
    0x2C2: "SDSC: byte address = sector * 512",
    0x2CA: "$7FB3", 0x2CD: "$7FB0", 0x2CF: "$7FB4", 0x2D1: "block count - 1",
    0x2DC: "SCL and SDA released", 0x2E0: "", 0x2E3: "SDA low while SCL high = START",
    0x2E7: "", 0x2EB: "SDA high while SCL high = STOP",
    0x2ED: "bit mask", 0x2EE: "", 0x2F0: "bit = 0", 0x2F2: "bit = 1",
    0x2F4: "next bit; carry out after bit 0", 0x2F7: "8 bits",
    0x2FC: "ACK = SDA low", 0x302: "NACK = SDA high", 0x305: "carry = ACK bit (1 = NACK)",
    0x307: "SCL low", 0x30B: "release SCL", 0x30D: "wait until SCL is high (stretching)",
    0x311: "SDA low", 0x314: "release SDA", 0x31B: "sample SDA", 0x31D: "shift into s5",
    0x32B: "value 00", 0x32E: "device address 51 << 1 = A2 (write)",
    0x332: "abort on NACK", 0x333: "register number", 0x337: "value",
    0x33B: "STOP", 0x34A: "A3 (read)", 0x34F: "",
    0x355: "", 0x357: "window index", 0x358: "window data",
    0x359: "last register (years)?", 0x35C: "ACK, read next",
    0x35E: "first register: seconds", 0x35F: "select byte sB of the GB data",
    0x361: "byte the GB wrote", 0x362: "store in RTC",
    0x367: "control 1 = 20: STOP", 0x36A: "CLKOUT control = 80: enabled",
    0x36D: "control 1 = 00: run", 0x36F: "seconds register",
    0x371: "VL flag: clock integrity lost?", 0x374: "stop clock",
    0x377: "years = 00", 0x379: "months = 01", 0x37C: "weekdays = 03",
    0x37F: "days = 01", 0x382: "hours = 00", 0x384: "minutes = 00",
    0x386: "seconds = 00 (clears VL)", 0x388: "control 2 = 00", 0x38A: "control 1 = 00: run",
    0x38D: "CMD13 SEND_STATUS", 0x38F: "status bits 15:8", 0x390: "09 = tran, ready for data",
    0x393: "not ready: CMD12 and retry",
    0x395: "event flags", 0x396: "read sectors", 0x398: "card ready",
    0x399: "LBA and count from $7FB0-$7FB4", 0x39A: "CMD18 into the sector buffer",
    0x39B: "CMD12", 0x39D: "write sectors", 0x3A1: "CMD25 from the sector buffer",
    0x3A4: "ROM load", 0x3A8: "set RTC", 0x3AC: "flash page write",
    0x3AE: "scratch 3F = 1: bank 1 takes the update path", 0x3B0: "-> bank 1",
    0x3B2: "",
    0x3F0: "", 0x3F1: "select bank 1", 0x3F2: "NOP (pipeline)",
    0x3F3: "NOP here; CALL 1B5 in bank 1", 0x3F4: "", 0x3F5: "select bank 0",
    0x3F6: "NOP (pipeline)", 0x3F7: "",
    0x3FF: "",
}
