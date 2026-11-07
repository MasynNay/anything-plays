"""Original Super Nintendo LoROM exercising 65816 PPU video and SPC700 DSP.

The ROM is generated at test time from independent machine instructions:
Mode-0 BG tile checkerboard, shifting palette and an SPC-IPL-transferred
looping test-tone sample. No commercial ROM/firmware/BIOS/sample is distributed.
"""
from __future__ import annotations
import hashlib
from pathlib import Path

ROM_SIZE = 32 * 1024
CPU_BASE = 0x8000
HEADER = 0x7FC0
TEST_SPC_SAMPLE = (
    b"\x04\x02\x04\x02" + b"\xB0" + b"\x77" * 8
    + b"\xB3" + b"\x77" * 8
)


def build_snes_probe_rom():
    program = bytearray()
    labels = {}
    branches = []
    jumps = []

    def emit(*values):
        program.extend(values)
    def label(name):
        if name in labels:
            raise ValueError("Duplicate SNES label")
        labels[name] = len(program)
    def lda(value):
        emit(0xA9, value & 255)
    def lda_abs(addr):
        emit(0xAD, addr & 255, (addr >> 8) & 255)
    def sta(addr):
        emit(0x8D, addr & 255, (addr >> 8) & 255)
    def stz(addr):
        emit(0x9C, addr & 255, (addr >> 8) & 255)
    def cmp_abs(addr):
        emit(0xCD, addr & 255, (addr >> 8) & 255)
    def ldx16(value):
        emit(0xA2, value & 255, (value >> 8) & 255)
    def branch(opcode, destination):
        branches.append((len(program), destination))
        emit(opcode, 0)
    def jump(destination):
        jumps.append((len(program), destination))
        emit(0x4C, 0, 0)
    def wait_ack(name):
        label(name)
        cmp_abs(0x2140)
        branch(0xD0, name)  # BNE
    def begin_upload(addr, name):
        # Standard SPC700 IPL handshake. Increment the previous echo
        # by $22 for the next transfer kick token; never send token zero.
        lda(addr & 255)
        sta(0x2142)
        lda((addr >> 8) & 255)
        sta(0x2143)
        lda_abs(0x2140)
        emit(0x18, 0x69, 0x22)  # CLC; ADC #$22
        branch(0xD0, name + "_token_nonzero")
        emit(0x1A)  # INC A
        label(name + "_token_nonzero")
        sta(0x2141)
        sta(0x2140)
        wait_ack(name + "_ack")
    def send_bytes(data, name):
        for index, value in enumerate(data):
            if index > 255:
                raise ValueError("Original SNES SPC payload too long")
            lda(value)
            sta(0x2141)
            lda(index)
            sta(0x2140)
            wait_ack(name + "_" + str(index))
    def dsp(register, value, name):
        # Writing two bytes to SPC IPL $F2/$F3 programs a DSP register.
        begin_upload(0x00F2, name + "_begin")
        send_bytes((register, value), name + "_bytes")
    def palette(color):
        lda(1)
        sta(0x2121)  # CGADD palette entry 1
        lda(color & 255)
        sta(0x2122)
        lda((color >> 8) & 255)
        sta(0x2122)
    def delay(name):
        ldx16(0xFFFF)
        label(name)
        emit(0xCA)  # 16-bit DEX
        branch(0xD0, name)

    # Native mode, 8-bit accumulator and 16-bit X/Y, IRQ disabled.
    emit(0x78, 0x18, 0xFB, 0xC2, 0x10, 0xE2, 0x20)
    lda(0x80)
    sta(0x2100)  # Forced blank during PPU VRAM initialization.
    stz(0x2105)  # Mode 0, four 2bpp backgrounds.
    lda(0x04)
    sta(0x2107)  # BG1 name table VRAM word $0800.
    stz(0x210B)  # BG1 tile character data at VRAM word $0000.
    lda(0x01)
    sta(0x212C)  # BG1 visible on main screen.
    stz(0x212D)  # No sub-screen overlay.
    lda(0x80)
    sta(0x2115)  # Auto-increment VRAM word address after $2119.
    stz(0x2116)
    stz(0x2117)

    # Tile 0, 2bpp, 8 rows: alternating black / palette color 1.
    for _ in range(8):
        lda(0xAA)
        sta(0x2118)
        stz(0x2119)

    stz(0x2116)
    lda(0x08)
    sta(0x2117)
    ldx16(0x0400)  # Fill all 1024 BG1 name-table words with tile #0.
    label("tilemap")
    stz(0x2118)
    stz(0x2119)
    emit(0xCA)
    branch(0xD0, "tilemap")

    stz(0x2121)
    stz(0x2122)
    stz(0x2122)  # Palette 0 = black.
    lda(0x1F)
    sta(0x2122)
    stz(0x2122)  # Palette 1 = red.
    lda(0x0F)
    sta(0x2100)  # Full screen brightness.

    # APU IPL advertises AA/BB in the two shared data registers.
    lda(0xAA)
    label("spc_aa")
    cmp_abs(0x2140)
    branch(0xD0, "spc_aa")
    lda(0xBB)
    label("spc_bb")
    cmp_abs(0x2141)
    branch(0xD0, "spc_bb")

    begin_upload(0x0200, "sample_start")
    send_bytes(TEST_SPC_SAMPLE, "sample")

    writes = (
        (0x6C, 0x20), (0x4C, 0x00), (0x5C, 0xFF),
        (0x5D, 0x02), (0x00, 0x7F), (0x01, 0x7F),
        (0x02, 0x00), (0x03, 0x02), (0x04, 0x00),
        (0x05, 0xC3), (0x06, 0x2F), (0x5C, 0x00),
        (0x0C, 0x7F), (0x1C, 0x7F), (0x4C, 0x01),
    )
    for index, (register, value) in enumerate(writes):
        dsp(register, value, f"dsp_{index}")

    label("animate")
    palette(0x03E0)  # Green
    delay("green_delay")
    palette(0x001F)  # Red
    delay("red_delay")
    jump("animate")

    for offset, name in branches:
        delta = labels[name] - (offset + 2)
        if not -128 <= delta <= 127:
            raise ValueError(f"SNES branch out of range: {name}")
        program[offset + 1] = delta & 255
    for offset, name in jumps:
        target = CPU_BASE + labels[name]
        program[offset + 1:offset + 3] = target.to_bytes(2, "little")
    if len(program) > 0x6000:
        raise ValueError("Original SNES program exceeds LoROM budget")

    rom = bytearray(ROM_SIZE)
    rom[:len(program)] = program
    rom[HEADER:HEADER + 21] = b"ANYTHING PLAYS SNES".ljust(21, b" ")
    rom[0x7FD5] = 0x20  # LoROM, slow ROM.
    rom[0x7FD6] = 0x00  # ROM-only game.
    rom[0x7FD7] = 0x05  # 32KiB cartridge.
    rom[0x7FD8] = 0x00  # No SRAM.
    rom[0x7FD9] = 0x01  # NTSC.
    rom[0x7FDB] = 0x00  # Version zero.
    for offset in (0x7FFA, 0x7FFC, 0x7FFE):
        rom[offset:offset + 2] = CPU_BASE.to_bytes(2, "little")
    # Cartridge header checksum and complement: prevents false invalid-ROM
    # warnings in cores that validate the LoROM map.
    rom[0x7FDC:0x7FE0] = b"\xFF\xFF\x00\x00"
    checksum = sum(rom) & 0xFFFF
    rom[0x7FDC:0x7FDE] = ((~checksum) & 0xFFFF).to_bytes(2, "little")
    rom[0x7FDE:0x7FE0] = checksum.to_bytes(2, "little")
    return bytes(rom)


def write_snes_probe(destination):
    path = Path(destination)
    if path.suffix.lower() not in (".sfc", ".smc"):
        raise ValueError("Original SNES test file must end with .sfc or .smc")
    data = build_snes_probe_rom()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "source": "original 65c816 Mode-0 tilemap and SPC700 IPL tone test",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "contains_commercial_game": False,
    }
