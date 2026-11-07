"""Original Sega Master System / Game Gear Z80 VDP+PSG test cartridges.

Only original Z80 code, palette values and test patterns are generated here.
No Sega firmware, games or commercial assets are copied into the application.
ROMs are generated during CI; they are not part of the installed application.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROM_SIZE = 32768
SYSTEMS = ("mastersystem", "gamegear")
PORT_VDP_CONTROL = 0xBF
PORT_VDP_DATA = 0xBE
PORT_PSG = 0x7F


def build_sega8_probe_rom(system="mastersystem"):
    if system not in SYSTEMS:
        raise ValueError("Expected Sega Master System or Game Gear")

    code = bytearray()
    labels = {}
    branches = []
    def emit(*values):
        code.extend(values)
    def lda(value):
        emit(0x3E, value & 255)
    def out(port, value):
        lda(value)
        emit(0xD3, port)
    def control(low, high):
        out(PORT_VDP_CONTROL, low)
        out(PORT_VDP_CONTROL, high)
    def register(index, value):
        control(value, 0x80 | index)
    def vram(addr):
        control(addr & 255, 0x40 | ((addr >> 8) & 0x3F))
    def cram(addr):
        control(addr, 0xC0)
    def label(name):
        labels[name] = len(code)
    def jr_nz(name):
        branches.append((len(code), name))
        emit(0x20, 0)
    def wait():
        # 16-bit count, no interrupts; leave VDP free to scan between writes.
        emit(0x01, 0xFF, 0xFF)  # LD BC,0xFFFF
        loop_name = "wait_" + str(len(branches))
        label(loop_name)
        emit(0x0B, 0x78, 0xB1)  # DEC BC; LD A,B; OR C
        jr_nz(loop_name)
    def palette(index, value):
        if system == "gamegear":
            # 12-bit RGB; 2 bytes per entry, red/green then blue.
            cram(index * 2)
            out(PORT_VDP_DATA, value & 255)
            out(PORT_VDP_DATA, (value >> 8) & 15)
        else:
            # 6-bit SMS CRAM: --BBGGRR.
            cram(index)
            out(PORT_VDP_DATA, value & 63)

    emit(0xF3)  # DI
    emit(0x31, 0xF0, 0xDF)  # LD SP,$DFF0
    for reg, val in (
        (0, 0x04), (1, 0x00), (2, 0x0E), (3, 0xFF),
        (4, 0xFF), (5, 0x7E), (6, 0xFF), (7, 0x00),
        (8, 0x00), (9, 0x00), (10, 0xFF),
    ):
        register(reg, val)

    # One original 8x8 two-colour tile in mode 4: alternating black and
    # colour one. The other three bitplanes are zero.
    vram(0x0000)
    for _ in range(8):
        for value in (0xAA, 0, 0, 0):
            out(PORT_VDP_DATA, value)

    # VRAM tilemap $3800, 32x28 entries, each 2 bytes. Initialize all
    # entries to tile zero rather than relying on emulator power-on VRAM.
    vram(0x3800)
    emit(0x01, 0x00, 0x07)  # LD BC,1792
    label("tilemap")
    emit(0xAF, 0xD3, PORT_VDP_DATA)  # XOR A; OUT ($BE),A
    emit(0x0B, 0x78, 0xB1)  # DEC BC; LD A,B; OR C
    jr_nz("tilemap")

    palette(0, 0x000)
    if system == "gamegear":
        palette(1, 0x00F)  # red
    else:
        palette(1, 0x03)
    register(1, 0x40)  # Display on, V-blank IRQ disabled.

    # Program PSG tone channel zero and open its volume latch.
    for value in (0x8F, 0x1C, 0x90):
        out(PORT_PSG, value)

    label("animation")
    palette(1, 0x0F0 if system == "gamegear" else 0x0C)
    wait()
    palette(1, 0x00F if system == "gamegear" else 0x03)
    wait()
    emit(0xC3, 0, 0)  # JP animation (fixed up below)
    target = labels["animation"]
    code[-2:] = bytes((target & 255, target >> 8))
    for pos, name in branches:
        relative = labels[name] - (pos + 2)
        if not -128 <= relative <= 127:
            raise ValueError("Z80 branch overflow")
        code[pos + 1] = relative & 255
    assert len(code) < 0x600

    rom = bytearray(ROM_SIZE)
    rom[:len(code)] = code
    rom[0x7FF0:0x7FF8] = b"TMR SEGA"
    # Header region bits: 4=SMS export; 6=Game Gear export, 0xC=32K.
    rom[0x7FFF] = 0x6C if system == "gamegear" else 0x4C
    return bytes(rom)


def write_sega8_probe(destination, system="mastersystem"):
    path = Path(destination)
    suffix = ".gg" if system == "gamegear" else ".sms"
    if system not in SYSTEMS or path.suffix.lower() != suffix:
        raise ValueError("Original Sega 8-bit ROM extension does not match system")
    raw = build_sega8_probe_rom(system)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {
        "source": "original Sega 8-bit Z80 VDP/PSG diagnostic cartridge",
        "system": system, "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
