"""Generate a completely original Atari 2600 4 KiB 6507 test cartridge.

This test ROM is authored as opcodes in this repository and created only on CI.
It alternates visible TIA background color every NTSC frame and enables TIA
audio channel zero. No third-party ROM, BIOS or emulator app is included.
"""
from pathlib import Path
import hashlib

ROM_BYTES = 4096


def build_atari_2600_probe_rom():
    code = bytearray()
    def emit(*values): code.extend(values)
    def lda(value): emit(0xA9, value)
    def ldx(value): emit(0xA2, value)
    def sta(address): emit(0x85, address)
    def lda_zeropage(address): emit(0xA5, address)
    def bne(target):
        distance = target - (len(code) + 2)
        if not -128 <= distance <= 127:
            raise ValueError("Branch exceeds 6502 relative range")
        emit(0xD0, distance & 255)
    def wsync_loop(count):
        ldx(count)
        start = len(code)
        sta(0x02)   # TIA WSYNC: hold CPU until new scanline
        emit(0xCA)  # DEX
        bne(start)

    emit(0x78, 0xD8)         # SEI, CLD
    emit(0xA2, 0xFF, 0x9A)  # LDX #$FF; TXS
    lda(0x40); sta(0x80)    # RIOT RAM: initial color
    lda(0x04); sta(0x15)    # TIA AUDC0 waveform
    lda(0x10); sta(0x17)    # TIA AUDF0 frequency divider
    lda(0x0F); sta(0x19)    # TIA AUDV0 volume, nonzero PCM
    begin_frame = len(code)
    lda(0x02); sta(0x00)    # VSYNC on
    sta(0x02); sta(0x02); sta(0x02)  # three VSYNC lines
    lda(0); sta(0x00)       # VSYNC off
    lda(0x02); sta(0x01)    # VBLANK on
    wsync_loop(37)          # conventional NTSC vertical blank lines
    lda(0); sta(0x01)       # video active
    lda_zeropage(0x80)
    emit(0x49, 0x20)        # alternate between two visible TIA colors
    sta(0x80)
    sta(0x09)              # COLUBK background
    wsync_loop(192)         # visible picture scanlines
    lda(0x02); sta(0x01)   # VBLANK on for overscan
    wsync_loop(30)
    emit(0x4C, (0xF000 + begin_frame) & 255,
         (0xF000 + begin_frame) >> 8)  # repeat 262-line frame
    assert len(code) < 512
    rom = bytearray([0xEA] * ROM_BYTES)
    rom[:len(code)] = code
    rom[-4:] = b"\x00\xf0\x00\xf0"  # RESET/IRQ vectors at $FFFC
    return bytes(rom)


def write_atari_probe(path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = build_atari_2600_probe_rom()
    target.write_bytes(data)
    return {"source": "original Anything Plays TIA video/audio test",
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data)}
