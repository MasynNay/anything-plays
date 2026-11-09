"""Source-generated SG-1000 TMS9918A Graphics-I and PSG test cartridge.

Original Z80 opcodes write directly to the SG-1000's legacy video and audio
ports. This tests the SG-1000 mode rather than incorrectly reusing SMS mode 4.
No commercial ROM, logo, firmware or copyrighted asset is included.
"""
from __future__ import annotations
import hashlib
from pathlib import Path

ROM_SIZE = 32768


def build_sg1000_probe_rom():
    code = bytearray()
    labels = {}
    relocations = []
    def emit(*bytes_):
        code.extend(bytes_)
    def write_port(port, value):
        emit(0x3E, value & 255, 0xD3, port)
    def control(lo, hi):
        write_port(0xBF, lo)
        write_port(0xBF, hi)
    def register(index, value):
        control(value, 0x80 | index)
    def address_vram(value):
        control(value & 255, 0x40 | ((value >> 8) & 0x3F))
    def label(name):
        labels[name] = len(code)
    def jr_nz(name):
        relocations.append((len(code), name))
        emit(0x20, 0)
    def delay(prefix):
        emit(0x01, 0xFF, 0xFF)  # LD BC,$FFFF
        label(prefix)
        emit(0x0B, 0x78, 0xB1)  # DEC BC; LD A,B; OR C
        jr_nz(prefix)

    emit(0xF3, 0x31, 0xF0, 0xDF)  # DI; LD SP,$DFF0
    # TMS9918 Graphics I configuration. Pattern Generator $0800,
    # Name Table $0400, Color Table $0200. Never enable SMS mode 4.
    for index, value in (
        (0, 0x00), (1, 0x80), (2, 0x01), (3, 0x08),
        (4, 0x01), (5, 0x02), (6, 0x00), (7, 0x01),
    ):
        register(index, value)

    # Tile #0 has alternating pixels; each Graphics-I tile row is 1 byte.
    address_vram(0x0800)
    for _ in range(8):
        write_port(0xBE, 0xAA)

    # Fill 32 x 24 name table entries with tile #0.
    address_vram(0x0400)
    emit(0x01, 0x00, 0x03)  # LD BC,768
    label("tiles")
    emit(0xAF, 0xD3, 0xBE)  # XOR A; OUT ($BE),A
    emit(0x0B, 0x78, 0xB1)
    jr_nz("tiles")

    # Graphics I uses one foreground/background byte per group of 8 tiles.
    # Tile #0 uses Color Table byte 0 at $0200.
    address_vram(0x0200)
    write_port(0xBE, 0x61)  # deep red foreground, black background
    register(1, 0xC0)  # 16KB VRAM and display enabled, interrupts disabled

    # Real SN76489 tone and volume commands.
    for value in (0x8F, 0x1C, 0x90):
        write_port(0x7F, value)

    label("animation")
    address_vram(0x0200)
    write_port(0xBE, 0x31)  # green
    delay("green_hold")
    address_vram(0x0200)
    write_port(0xBE, 0x61)  # red
    delay("red_hold")
    emit(0xC3, labels["animation"] & 255, labels["animation"] >> 8)

    for offset, name in relocations:
        delta = labels[name] - (offset + 2)
        if not -128 <= delta <= 127:
            raise ValueError("Original SG-1000 JR target out of range")
        code[offset + 1] = delta & 255
    assert len(code) < 1024
    rom = bytearray(ROM_SIZE)
    rom[:len(code)] = code
    return bytes(rom)


def write_sg1000_probe(destination):
    path = Path(destination)
    if path.suffix.lower() != ".sg":
        raise ValueError("SG-1000 cartridge must use .sg")
    rom = build_sg1000_probe_rom()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(rom)
    return {
        "system": "sg1000",
        "source": "original SG-1000 TMS9918 Graphics I and PSG",
        "sha256": hashlib.sha256(rom).hexdigest(),
        "bytes": len(rom),
    }
