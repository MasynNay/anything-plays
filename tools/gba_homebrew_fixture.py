"""Original standalone GBA ARM7TDMI Mode-3 and sound-chip test cartridge.

The program is constructed from original ARM instructions without an assembler,
Nintendo program, game assets or proprietary BIOS. This diagnostic only exists
in source form; the generated .gba image is never shipped to players.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import struct

SIZE = 256 * 1024
ENTRY_OFFSET = 0xC0
ROM_BASE = 0x08000000
DISPCNT = 0x04000000
VRAM_BASE = 0x06000000


def arm_immediate(value):
    """Encode an ARM immediate's 8-bit payload and 2x right rotation."""
    value &= 0xFFFFFFFF
    for rotation in range(16):
        bits = 2 * rotation
        candidate = ((value << bits) | (value >> (32 - bits))) & 0xFFFFFFFF
        if candidate <= 0xFF:
            return (rotation << 8) | candidate
    raise ValueError(f"ARM instruction cannot encode {value:#x} directly")


def make_program():
    words, labels, branches = [], {}, []
    def emit(word):
        words.append(word & 0xFFFFFFFF)
    def mov(rd, value):
        emit(0xE3A00000 | (rd << 12) | arm_immediate(value))
    def orr(rd, rn, value):
        emit(0xE3800000 | (rn << 16) | (rd << 12) | arm_immediate(value))
    def add(rd, rn, value):
        emit(0xE2800000 | (rn << 16) | (rd << 12) | arm_immediate(value))
    def strh(rd, rn, offset=0):
        if not 0 <= offset <= 255:
            raise ValueError("ARM STRH immediate overflow")
        emit(0xE1C000B0 | (rn << 16) | (rd << 12)
             | ((offset & 0xF0) << 4) | (offset & 0x0F))
    def label(name):
        if name in labels:
            raise ValueError("Duplicate ARM label")
        labels[name] = len(words)
    def b(name, condition=14):
        branches.append((len(words), name, condition))
        emit(0)
    def mov_reg(rd, rm):
        emit(0xE1A00000 | (rd << 12) | rm)
    def cmp_reg(rn, rm):
        emit(0xE1500000 | (rn << 16) | rm)

    # No stack, interrupts or BIOS calls: every instruction is ARM-state
    # ROM code. The Libretro HLE boot path starts at this header entry.
    mov(0, DISPCNT)
    mov(1, 0x400)
    orr(1, 1, 3)  # Mode 3 (240x160 RGB555) and BG2 enabled.
    strh(1, 0)
    mov(2, VRAM_BASE)
    mov(3, 0x001F)  # Red
    mov(4, 0x7C00)  # Blue

    # GBA DMG-channel audio: master on, both stereo routes for channel 2,
    # full volume and fixed 50%-duty square wave. No downloaded sound file.
    mov(8, 0x80)
    strh(8, 0, 0x84)  # SOUNDCNT_X
    mov(8, 0x2200)
    orr(8, 8, 0x77)
    strh(8, 0, 0x80)  # SOUNDCNT_L
    mov(8, 2)
    strh(8, 0, 0x82)  # SOUNDCNT_H: DMG sound volume ratio
    mov(8, 0xF000)
    orr(8, 8, 0x80)
    strh(8, 0, 0x68)  # SOUND2CNT_L duty and volume
    mov(8, 0xC300)
    orr(8, 8, 0xAA)
    strh(8, 0, 0x6C)  # SOUND2CNT_H frequency and trigger

    # Fill all video pixels, swap two visible colors, and repeat. This tests
    # the physical GBA PPU/video callback instead of faking RGB in Python.
    mov(6, 0x10000)
    add(6, 6, 0x2C00)  # 240 x 160 x 2 bytes (76800)
    label("frame")
    mov(5, 0)
    label("pixels")
    emit(0xE18230B5)  # STRH r3,[r2,r5] (register offset)
    add(5, 5, 2)
    cmp_reg(5, 6)
    b("pixels", 3)  # BLO, unsigned less than
    mov_reg(7, 3)
    mov_reg(3, 4)
    mov_reg(4, 7)
    mov(5, 0x100000)
    label("delay")
    emit(0xE2555001)  # SUBS r5,r5,#1
    b("delay", 1)  # BNE
    b("frame")
    for index, name, condition in branches:
        displacement = labels[name] - index - 2
        if not -(1 << 23) <= displacement < (1 << 23):
            raise ValueError("ARM branch target too far away")
        words[index] = (condition << 28) | 0x0A000000 | (displacement & 0xFFFFFF)
    return b"".join(struct.pack("<I", word) for word in words)


def build_gba_probe_rom():
    code = make_program()
    if len(code) >= 2048:
        raise ValueError("Unexpected GBA test program size")
    rom = bytearray(SIZE)
    # Branch past the 192-byte standard GBA metadata area to original code.
    # ARM PC for a branch is instruction address + 8.
    distance = (ENTRY_OFFSET - 8) // 4
    struct.pack_into("<I", rom, 0, 0xEA000000 | distance)
    rom[0xA0:0xAC] = b"ANYTHINGPLAY"
    rom[0xAC:0xB0] = b"AP30"
    rom[0xB0:0xB2] = b"00"
    rom[0xB2] = 0x96
    rom[0xBD] = (0x19 - sum(rom[0xA0:0xBD])) & 0xFF
    rom[ENTRY_OFFSET:ENTRY_OFFSET+len(code)] = code
    return bytes(rom)


def write_gba_probe(destination):
    path=Path(destination)
    if path.suffix.lower() != ".gba":
        raise ValueError("Original GBA test must end with .gba")
    image=build_gba_probe_rom()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(image)
    return {
        "source":"original ARM7TDMI Mode 3 graphics / channel-2 PCM cartridge",
        "sha256":hashlib.sha256(image).hexdigest(),
        "bytes":len(image),
        "contains_commercial_game":False,
    }
