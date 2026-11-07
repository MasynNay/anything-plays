"""Original Atari 7800 MARIA and TIA sound diagnostic cartridge.

Generate a 32KiB A78-format ROM containing original 6502 instructions.
MARIA scans a real RAM display-list list and reads an original graphics bitmap
from cartridge ROM. BACKGRND colors and the MARIA sprite palette change between
frames, rather than fabricating video in the frontend. TIA audio channel zero
is configured independently. No BIOS, signature, retail game, or commercial
assets are included; generated test ROMs remain CI-only.
"""
from __future__ import annotations
import hashlib
from pathlib import Path

ROM_SIZE = 32768
HEADER_SIZE = 128
CPU_BASE = 0x8000
MARIA_BACKGROUND = 0x20
MARIA_WSYNC = 0x24


def build_atari7800_probe_rom():
    code = bytearray()
    branches = []
    labels = {}

    def emit(*data):
        code.extend(data)
    def label(name):
        labels[name] = len(code)
    def lda(value):
        emit(0xA9, value & 255)
    def sta_zp(addr):
        emit(0x85, addr & 255)
    def sta_abs(addr):
        emit(0x8D, addr & 255, (addr >> 8) & 255)
    def lda_zp(addr):
        emit(0xA5, addr & 255)
    def ldx(value):
        emit(0xA2, value & 255)
    def bne(target):
        branches.append((len(code), target))
        emit(0xD0, 0)
    def absolute_bytes(address, raw):
        """Write a short original MARIA DLL or display list into console RAM."""
        for i, value in enumerate(raw):
            lda(value)
            sta_abs(address + i)

    def scanlines(name, count):
        if not 1 <= count <= 255:
            raise ValueError("Atari 7800 scanline delay count invalid")
        ldx(count)
        label(name)
        sta_zp(MARIA_WSYNC)
        emit(0xCA)  # DEX
        bne(name)

    emit(0x78, 0xD8, 0xA2, 0xFF, 0x9A)  # SEI, CLD, SP=$FF
    # The 7800's input-control register selects MARIA rather than TIA
    # video. $07: cartridge enabled, MARIA enabled, mode locked.
    lda(0x07); sta_zp(0x01)
    lda(0x00)
    sta_zp(0x3C)  # Disable DMA until the DLL and display lists exist.

    # MARIA DMA needs both a real RAM-resident DLL and at least one valid
    # DL graphics object. A background-only / DMA-disabled program can
    # produce 60 Hz silent black video in ProSystem despite active CPU/PSG.
    # Each of the 16 zones spans 16 rasters and points at the same DL.
    # Four bytes of original bitmap per line, drawn at X=64 in palette 1.
    dll = bytes((0x0F, 0x19, 0x00)) * 16
    display_list = bytes((0x00, 0x3C, 0x90, 64, 0, 0))
    absolute_bytes(0x1800, dll)
    absolute_bytes(0x1900, display_list)
    lda(0x18); sta_zp(0x2C)  # DPPH: $18xx
    lda(0x00); sta_zp(0x30)  # DPPL: $xx00
    lda(0x4E); sta_zp(0x25)  # Palette 1, color 1.
    lda(0x82); sta_zp(0x26)  # Palette 1, color 2.
    lda(0xD4); sta_zp(0x27)  # Palette 1, color 3.
    lda(0x40); sta_zp(0x3C)  # MARIA DMA ON in 160AB graphics mode.
    lda(0x04); sta_zp(0x15)  # TIA AUDC0 square/noise waveform.
    lda(0x10); sta_zp(0x17)  # TIA AUDF0 divider.
    lda(0x0F); sta_zp(0x19)  # TIA AUDV0 volume.
    lda(0x24)
    sta_zp(0x80)  # Working color in 7800 RAM, not cartridge memory.

    label("frame")
    # A full scanline-aligned NTSC raster: the bands produce real spatial
    # color variation without a MARIA display-list/DMA dependency.
    lda(0x00); sta_zp(MARIA_BACKGROUND)
    scanlines("top", 38)
    lda_zp(0x80)
    sta_zp(MARIA_BACKGROUND)
    scanlines("first_band", 85)
    lda(0x82)
    sta_zp(MARIA_BACKGROUND)
    scanlines("second_band", 85)
    lda(0x00)
    sta_zp(MARIA_BACKGROUND)
    scanlines("bottom", 54)
    lda_zp(0x80)
    emit(0x49, 0x40)  # EOR #$40; shift palette hue between frames.
    sta_zp(0x80)
    sta_zp(0x25)  # Change actual MARIA sprite color as well as BACKGRND.
    emit(0x4C, 0, 0)  # JMP frame
    code[-2:] = (CPU_BASE + labels["frame"]).to_bytes(2, "little")
    for offset, destination in branches:
        delta = labels[destination] - (offset + 2)
        if not -128 <= delta <= 127:
            raise ValueError("Atari 7800 scanline branch out of range")
        code[offset + 1] = delta & 255
    assert len(code) < 768

    body = bytearray([0xEA] * ROM_SIZE)
    body[:len(code)] = code
    # Bitmap data at 6502 $9000. MARIA adds the raster offset to the high
    # address, so each of 16 line pages carries its own original 4-byte
    # alternating pixel pattern.
    for line in range(16):
        address = 0x1000 + line * 0x100
        body[address:address + 4] = bytes(
            (0x55 if line % 2 else 0xAA, 0xE4, 0x1B, 0xFF)
        )
    body[-8:-6] = b"\xFF\x87"  # Atari 7800 region / cart base metadata
    for off in (ROM_SIZE - 6, ROM_SIZE - 4, ROM_SIZE - 2):
        body[off:off+2] = CPU_BASE.to_bytes(2, "little")
    header = bytearray(HEADER_SIZE)
    header[0] = 1
    header[1:17] = b"ATARI7800".ljust(16, b" ")
    header[17:49] = b"ANYTHING PLAYS ORIGINAL 7800".ljust(32, b" ")
    header[49:53] = ROM_SIZE.to_bytes(4, "big")
    header[55] = header[56] = 1  # Two standard joysticks.
    header[57] = 0  # NTSC.
    header[100:128] = b"ACTUAL CART DATA STARTS HERE"
    return bytes(header) + bytes(body)


def write_atari7800_probe(destination):
    path = Path(destination)
    if path.suffix.lower() != ".a78":
        raise ValueError("Atari 7800 test ROM needs .a78 format")
    data = build_atari7800_probe_rom()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "system": "atari7800",
        "source": "original 6502 MARIA background and TIA sound test",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }
