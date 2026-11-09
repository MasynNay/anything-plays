"""Source-only original GB/GBC video-and-audio test cartridge.

Generates native LR35902 instructions, background scrolling and square-channel
APU sound without redistributing any commercial game or firmware.
The 48-byte hardware-required GB cartridge header logo marker is format data
needed for mGBA recognition; no logo artwork is rendered by this test game.
"""
from __future__ import annotations
import hashlib
from pathlib import Path

SIZE = 32768
ENTRY = 0x150
SYSTEMS = ("gb", "gbc")

def build_gb_probe_rom(system="gb"):
    if system not in SYSTEMS:
        raise ValueError("Expected GB or GBC")
    code = bytearray()
    def emit(*values):
        code.extend(values)
    def ldh(reg, value):
        emit(0x3e, value, 0xe0, reg)
    def nz(target):
        offset = target - (ENTRY + len(code) + 2)
        if not -128 <= offset <= 127:
            raise ValueError("Relative Z80 branch overflow")
        emit(0x20, offset & 255)

    emit(0xf3)  # DI
    ldh(0x40, 0x00)  # LCD off for VRAM write
    emit(0x21, 0x00, 0x80)  # HL=$8000
    emit(0x06, 16, 0x3e, 0xaa)  # 16 tile bytes of stripe bits
    tile = ENTRY + len(code)
    emit(0x22, 0x05)  # (HL+)=A; DEC B
    nz(tile)
    ldh(0x47, 0xe4)  # DMG mode: 4 grayscale palette values
    if system == "gbc":
        # CGB boot ROM / HLE can initialize every BG palette entry to
        # WHITE, so without BCPS/BCPD our moving hardware background is
        # invisible in native color mode. Program BG palette zero explicitly:
        # black, green, blue, white (little-endian RGB555).
        # BGPI $80: write index 0 and auto-increment after every BCPD byte.
        ldh(0x68, 0x80)
        for component in (0x00, 0x00, 0xE0, 0x03,
                          0x00, 0x7C, 0xFF, 0x7F):
            ldh(0x69, component)
    for reg, value in (
        (0x26,0x80), (0x24,0x77), (0x25,0x11),
        (0x10,0x00), (0x11,0x80), (0x12,0xf3),
        (0x13,0xaa), (0x14,0xc3),
    ):
        ldh(reg, value)
    ldh(0x40, 0x91)  # LCD on, BG layer active
    emit(0x16, 0x00)  # D = scroll position
    animation = ENTRY + len(code)
    emit(0x14, 0x7a, 0xe0, 0x43)  # INC D; A=D; SCX=A
    emit(0x01, 0xff, 0xff)  # BC=$FFFF delay
    delay = ENTRY + len(code)
    emit(0x0b, 0x78, 0xb1)  # DEC BC, A=B, OR C
    nz(delay)
    emit(0xc3, animation & 255, animation >> 8)  # JP animation
    assert len(code) < 256

    rom = bytearray(SIZE)
    rom[0x100:0x104] = bytes((0xc3, 0x50, 0x01, 0x00))
    # mGBA GBIsROM checks the cartridge logo signature (Pan Docs $0104-
    # $0133). Unlike the original program below, these are mandatory
    # interoperable cartridge-format bytes, not game code or a boot ROM.
    # The diagnostic ROM is generated only inside CI and never shipped.
    rom[0x104:0x134] = bytes.fromhex(
        "CE ED 66 66 CC 0D 00 0B 03 73 00 83 00 0C 00 0D "
        "00 08 11 1F 88 89 00 0E DC CC 6E E6 DD DD D9 99 "
        "BB BB 67 63 6E 0E EC CC DD DC 99 9F BB B9 33 3E"
    )
    rom[0x134:0x143] = b"ANYTHINGPLAYSGB"
    rom[0x143] = 0x80 if system == "gbc" else 0
    rom[0x147:0x14a] = b"\x00\x00\x00"
    rom[0x14b] = 0x33
    rom[ENTRY:ENTRY+len(code)] = code
    rom[0x14d] = (-sum(rom[0x134:0x14d]) - 25) & 255
    checksum = sum(rom) & 0xffff
    rom[0x14e:0x150] = checksum.to_bytes(2, "big")
    return bytes(rom)

def write_gb_probe(destination, system="gb"):
    path = Path(destination)
    if path.suffix.casefold() != "." + system:
        raise ValueError("GB/GBC test extension does not match the console")
    data = build_gb_probe_rom(system)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "system":system, "source":"original Anything Plays GB/GBC LR35902 code",
        "sha256": hashlib.sha256(data).hexdigest(), "bytes":len(data),
    }
