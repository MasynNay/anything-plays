"""Original PC Engine / TurboGrafx-16 HuCard graphics + PSG diagnostic ROM.

This source-only generator writes original HuC6280 instructions, VDC VRAM
tiles, VCE palette changes and a 32-sample PSG waveform. It does not download
or distribute a commercial game or CD BIOS. The HuCard ROM is temporary CI
content and never belongs in an Anything Plays installer.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROM_SIZE = 128 * 1024
CPU_ENTRY = 0xE000
BANK_BYTES = 8192


def build_pce_probe_rom():
    code = bytearray()
    labels = {}
    branches = []
    jumps = []

    def emit(*values):
        code.extend(values)
    def label(name):
        labels[name] = len(code)
    def lda(value):
        emit(0xA9, value & 255)
    def sta(addr):
        emit(0x8D, addr & 255, (addr >> 8) & 255)
    def psg(reg, value):
        lda(value)
        sta(0x0800 + reg)
    def vce_palette(index, rgb9):
        lda(index & 255); sta(0x0402)
        lda((index >> 8) & 1); sta(0x0403)
        lda(rgb9 & 255); sta(0x0404)
        lda((rgb9 >> 8) & 1); sta(0x0405)
    def vdc_reg(reg, value):
        lda(reg); sta(0x0000)
        lda(value & 255); sta(0x0002)
        lda(value >> 8); sta(0x0003)
    def branch(op, target):
        branches.append((len(code), target))
        emit(op, 0)
    def jump(target):
        jumps.append((len(code), target))
        emit(0x4C, 0, 0)
    def delay(tag):
        emit(0xA2, 0x00)  # LDX #0, 256 nested loops
        label(tag + "_outer")
        emit(0xA0, 0x00)  # LDY #0
        label(tag + "_inner")
        emit(0x88)  # DEY
        branch(0xD0, tag + "_inner")
        emit(0xCA)  # DEX
        branch(0xD0, tag + "_outer")

    emit(0x78, 0xD8)  # SEI, CLD
    # HuC6280 TAM #MPR mask. MPR0 -> hardware I/O ($FF), MPR1 -> RAM
    # ($F8), MPR7 -> first HuCard bank ($00), executing at $E000.
    lda(0xFF); emit(0x53, 0x01)
    lda(0xF8); emit(0x53, 0x02)
    lda(0x00); emit(0x53, 0x80)
    emit(0xA2, 0xFF, 0x9A)  # LDX #255; TXS

    # Original tone waveform: 16 high and 16 low DAC samples. PSG channel 0.
    psg(0, 0)
    psg(1, 0xFF)    # Master volume left/right.
    psg(4, 0x00)    # Waveform loading mode.
    for value in ([31] * 16 + [0] * 16):
        psg(6, value)
    psg(2, 0x58)    # Frequency low.
    psg(3, 0x04)    # Frequency high.
    psg(5, 0xFF)    # Stereo channel volume.
    psg(4, 0x9F)    # Enable tone and set amplitude.

    lda(0); sta(0x0400)  # VCE normal pixel clock.
    vce_palette(0, 0)    # BG backdrop = black.
    vce_palette(1, 0x038)  # Color 1 = red (9-bit G/R/B).

    # Actual VDC timing and background tilemap initialization.
    vdc_reg(0x05, 0x0000)  # Hide BG during VRAM writes.
    vdc_reg(0x09, 0x0000)  # 32x32 background map.
    vdc_reg(0x0A, 0x0202)  # HSR.
    vdc_reg(0x0B, 0x001F)  # HDR: 256 pixels.
    vdc_reg(0x0C, 0x0202)  # VPR.
    vdc_reg(0x0D, 0x00DF)  # 224 visible scanlines.
    vdc_reg(0x0E, 0x000C)  # VCR.
    vdc_reg(0x00, 0)       # VRAM write pointer = BAT word 0.
    lda(2); sta(0x0000)    # VWR selected.
    emit(0xA2, 0x04)       # Four blocks of 256 BAT words.
    label("fill_bat_outer")
    emit(0xA0, 0x00)       # LDY #0
    label("fill_bat_inner")
    lda(0x80); sta(0x0002)  # Tile index 128 (VRAM word $0800).
    lda(0x00); sta(0x0003)  # Palette zero; high write advances MAWR.
    emit(0xC8)             # INY
    branch(0xD0, "fill_bat_inner")
    emit(0xCA)             # DEX
    branch(0xD0, "fill_bat_outer")

    vdc_reg(0x00, 0x0800)  # Tile index 128: word 128*16.
    lda(2); sta(0x0000)   # VRAM data register.
    # 8 rows with 2 planes followed by 2 high bitplanes = 16 words.
    # Original alternating stripes choose palette indexes zero and one.
    for row in range(16):
        lda(0xAA if row < 8 else 0)
        sta(0x0002)
        lda(0)
        sta(0x0003)
    vdc_reg(0x05, 0x0080)  # Enable actual VDC background pixels.

    label("animation")
    vce_palette(1, 0x1C0)  # Green pixel palette.
    delay("green")
    vce_palette(1, 0x038)  # Red pixel palette.
    delay("red")
    jump("animation")

    for at, destination in branches:
        relative = labels[destination] - (at + 2)
        if not -128 <= relative <= 127:
            raise ValueError("HuC6280 short branch outside -128..127")
        code[at + 1] = relative & 255
    for at, destination in jumps:
        address = CPU_ENTRY + labels[destination]
        code[at + 1:at + 3] = address.to_bytes(2, "little")
    assert len(code) < 0x1800

    rom = bytearray(ROM_SIZE)
    # HuCard's first physical 8KB bank is mapped to CPU $E000-$FFFF
    # on reset. The reset vector is in the last 10 bytes of THAT bank.
    rom[:len(code)] = code
    for offset in range(0, ROM_SIZE, BANK_BYTES):
        for vector in range(0x1FF6, 0x2000, 2):
            rom[offset + vector:offset + vector + 2] = (
                CPU_ENTRY.to_bytes(2, "little")
            )
    return bytes(rom)


def write_pce_probe(destination):
    path = Path(destination)
    if path.suffix.lower() != ".pce":
        raise ValueError("Original HuCard ROM must have .pce extension")
    rom = build_pce_probe_rom()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(rom)
    return {
        "system": "pce",
        "source": "original HuC6280 VDC/VCE and PSG HuCard test",
        "bytes": len(rom), "sha256": hashlib.sha256(rom).hexdigest(),
        "requires_cd_bios": False,
    }
