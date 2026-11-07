"""Original NES diagnostic ROM assembled as data, not a third-party game.

No copyrighted ROM/BIOS/firmware is downloaded, installed or redistributed.
This source-only diagnostic uses an iNES NROM-128 image in CI to exercise the
NES video frame callback and real 2A03/APU pulse-wave PCM through FCEUmm.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

PRG_SIZE = 16 * 1024
CHR_SIZE = 8 * 1024


def build_nes_probe_rom():
    code = bytearray()
    def emit(*values):
        code.extend(values)
    def sta(address):
        emit(0x8D, address & 255, address >> 8)
    def lda(value):
        emit(0xA9, value)
    def wait_vblank():
        location = len(code)
        emit(0x2C, 0x02, 0x20)  # BIT $2002: check PPU vblank
        next_pc = len(code) + 2
        displacement = location - next_pc
        assert -128 <= displacement < 0
        emit(0x10, displacement & 255)  # BPL wait

    emit(0x78, 0xD8)     # SEI; CLD
    emit(0xA2, 0xFF, 0x9A)  # LDX #$FF; TXS
    lda(0)
    sta(0x2000)         # disable NMI
    sta(0x2001)         # disable rendering while configuring PPU

    # Enable APU pulse channel 1, duty 50%, constant maximum volume,
    # no sweep. Timer period 0x0FD yields approximately 440 Hz NTSC.
    lda(0x01); sta(0x4015)
    lda(0xBF); sta(0x4000)
    lda(0x08); sta(0x4001)
    lda(0xFD); sta(0x4002)
    lda(0x08); sta(0x4003)

    # Fill the background name table with cartridge-defined tile 0.
    lda(0x20); sta(0x2006)
    lda(0x00); sta(0x2006)
    emit(0xA2, 0x04)     # LDX #4 pages
    emit(0xA0, 0x00)     # LDY #0
    lda(0)
    outer = len(code)
    sta(0x2007)
    emit(0xC8)           # INY
    branch = len(code)
    emit(0xD0, (outer - (branch + 2)) & 255)  # BNE
    emit(0xCA)           # DEX
    branch = len(code)
    emit(0xD0, (outer - (branch + 2)) & 255)  # BNE

    # Palette entries: background purple and an alternating tile foreground.
    lda(0x3F); sta(0x2006)
    lda(0x00); sta(0x2006)
    lda(0x21); sta(0x2007)
    lda(0x16); sta(0x2007)
    lda(0x21); emit(0x85, 0x00)  # zero page scratch value
    lda(0); sta(0x2005); sta(0x2005)
    lda(0x0A); sta(0x2001)      # show background including left 8 pixels

    # Change the universal background color once per PPU vblank:
    # genuinely changing NES video, not fabricated framebuffer copies.
    loop = len(code)
    wait_vblank()
    lda(0x3F); sta(0x2006)
    lda(0); sta(0x2006)
    emit(0xA5, 0x00)      # LDA $00
    emit(0x49, 0x10)      # EOR #$10 => alternate palette entries
    emit(0x85, 0x00)      # STA $00
    sta(0x2007)
    lda(0); sta(0x2005); sta(0x2005)
    emit(0x4C, (0x8000 + loop) & 255, (0x8000 + loop) >> 8)
    assert len(code) < 1024, "Unexpected probe size"
    prg = bytearray([0xEA] * PRG_SIZE)
    prg[:len(code)] = code
    prg[0x3FFA:0x4000] = b"\x00\x80" * 3  # NMI/reset/IRQ vectors
    chr_rom = bytearray(CHR_SIZE)
    chr_rom[:8] = bytes((0xAA, 0x55) * 4)
    # The second plane stays zero, producing palette index 0 or 1.
    header = b"NES\x1a" + bytes((1, 1, 0, 0)) + bytes(8)
    assert len(header) == 16
    return header + bytes(prg) + bytes(chr_rom)


def write_nes_probe(destination):
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(build_nes_probe_rom())
    return {
        "source": "original Anything Plays NES video/audio diagnostic",
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "bytes": target.stat().st_size,
    }
