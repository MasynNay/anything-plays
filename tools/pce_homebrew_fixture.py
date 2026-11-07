"""Original PC Engine HuCard: HuC6280 VDC tiles, VCE palette and PSG tone.

Generated at CI runtime. No commercial HuCard game, CD firmware, BIOS or
third-party art is shipped. The reset vector is at physical ROM bank 0's
$1FFE, corresponding to CPU $FFFE after HuC6280 initializes MPR7 to bank 0.
"""
from __future__ import annotations
import hashlib
from pathlib import Path

ROM_SIZE = 32768
RESET_CPU = 0xE000
RESET_VECTOR_ROM_OFFSET = 0x1FFE


def build_pce_probe_rom():
    code = bytearray()
    labels, branches, jumps = {}, [], []

    def emit(*args):
        code.extend(args)
    def lda(value):
        emit(0xA9, value & 255)
    def sta(addr):
        emit(0x8D, addr & 255, (addr >> 8) & 255)
    def vdc(index, value):
        emit(0x03, index, 0x13, value & 255, 0x23, (value >> 8) & 255)
    def label(name):
        if name in labels:
            raise ValueError("Duplicate HuC6280 label")
        labels[name] = len(code)
    def branch(op, name):
        branches.append((len(code), name))
        emit(op, 0)
    def jump(name):
        jumps.append((len(code), name))
        emit(0x4C, 0, 0)
    def vce_entry(index, value):
        lda(index & 255)
        sta(0x0402)
        lda(index >> 8)
        sta(0x0403)
        lda(value & 255)
        sta(0x0404)
        lda((value >> 8) & 255)
        sta(0x0405)
    def psg_register(address, value):
        lda(value)
        sta(address)

    emit(0x78, 0xD8, 0xD4)   # SEI, CLD, CSH high CPU speed
    lda(0xFF)
    emit(0x53, 0x01)        # TAM MPR0 -> physical I/O bank FF
    lda(0xF8)
    emit(0x53, 0x02)        # TAM MPR1 -> physical RAM bank F8
    lda(0x00)
    emit(0x53, 0x80)        # Keep MPR7 mapped to original ROM bank 0
    emit(0xA2, 0xFF, 0x9A)  # LDX #FF; TXS (stack in bank F8)
    lda(0)
    sta(0x2000)            # RAM state controlling displayed palette
    sta(0x0400)            # VCE 5MHz clock
    vce_entry(0, 0x0000)   # Transparent/background black
    vce_entry(1, 0x0038)   # Fully bright red
    vce_entry(2, 0x0007)   # Fully bright blue
    vce_entry(3, 0x01C0)   # Fully bright green

    # 32x32 BAT (background tilemap), 256 visible pixels, tile index 128.
    # VDC auto-increments MAWR when high VRAM data byte is written via ST2.
    vdc(0x05, 0)  # BG disabled until VRAM is fully initialized.
    vdc(0x09, 0)  # MWR: 32x32 BAT
    vdc(0x00, 0)  # MAWR: VRAM word 0
    emit(0x03, 0x02)  # ST0 VWR
    emit(0xA2, 0x04)  # 4 * 256 = 1024 BAT entries
    label("bat_outer")
    emit(0xA0, 0x00)  # LDY #0; 256 iterations
    label("bat_inner")
    emit(0x13, 0x80, 0x23, 0x00)  # tile index 128, palette 0
    emit(0x88)  # DEY
    branch(0xD0, "bat_inner")
    emit(0xCA)  # DEX
    branch(0xD0, "bat_outer")

    # Tile 128 pattern starts at VRAM word $0800. Each row encodes two
    # 8-bit bitplanes in a 16-bit word; the remaining planes are zero.
    vdc(0x00, 0x0800)
    emit(0x03, 0x02)  # VWR again after writing MAWR
    for row in range(8):
        emit(0x13, 0xAA if row % 2 else 0x55, 0x23, 0x00)
    for _ in range(8):
        emit(0x13, 0x00, 0x23, 0x00)
    for index, value in (
        (0x0A, 0x0202), # HSR
        (0x0B, 0x001F), # HDR, 32 tile width
        (0x0C, 0x0E02), # VPR
        (0x0D, 0x00DF), # VDR, 224 scanlines
        (0x0E, 0x000C), # VCR
        (0x07, 0),      # BXR
        (0x08, 0),      # BYR
        (0x05, 0x0080), # CR: BG enable
    ):
        vdc(index, value)

    # Real HuC6280 PSG channel zero. Program original square-ish 32-sample
    # waveform, enable stereo volume and select nonzero channel frequency.
    for address, value in (
        (0x0800, 0), (0x0801, 0xFF),
        (0x0804, 0), (0x0802, 0x80),
        (0x0803, 0x01), (0x0805, 0xFF),
    ):
        psg_register(address, value)
    for sample in ((0x1F,) * 16 + (0,) * 16):
        psg_register(0x0806, sample)
    psg_register(0x0804, 0x9F)  # Enable tone with nonzero volume.

    # Alternate VCE palette color 1. The actual original BG tile continuously
    # reads that palette color, producing changing video from native VDC/VCE.
    label("animation")
    lda(1)
    sta(0x0402)
    lda(0)
    sta(0x0403)
    emit(0xAD, 0x00, 0x20)    # LDA RAM $2000
    emit(0x49, 0x3F)          # EOR #$3F red / blue
    sta(0x2000)
    sta(0x0404)
    lda(0)
    sta(0x0405)

    # Approximately 65,536 iterations at 7MHz for visibly distinct frames.
    emit(0xA2, 0)            # LDX #0
    label("delay_outer")
    emit(0xA0, 0)            # LDY #0
    label("delay_inner")
    emit(0x88)               # DEY
    branch(0xD0, "delay_inner")
    emit(0xCA)               # DEX
    branch(0xD0, "delay_outer")
    jump("animation")

    for offset, name in branches:
        relative = labels[name] - (offset + 2)
        if not -128 <= relative <= 127:
            raise ValueError("HuC6280 relative jump out of range: " + name)
        code[offset + 1] = relative & 255
    for offset, name in jumps:
        target = RESET_CPU + labels[name]
        code[offset + 1:offset + 3] = target.to_bytes(2, "little")
    if len(code) >= RESET_VECTOR_ROM_OFFSET:
        raise ValueError("Original HuCard exceeds first physical ROM bank")
    rom = bytearray([0xEA] * ROM_SIZE)
    rom[:len(code)] = code
    rom[RESET_VECTOR_ROM_OFFSET:RESET_VECTOR_ROM_OFFSET + 2] = (
        RESET_CPU.to_bytes(2, "little")
    )
    return bytes(rom)


def write_pce_probe(destination):
    path = Path(destination)
    if path.suffix.lower() != ".pce":
        raise ValueError("Original PC Engine HuCard must end in .pce")
    image = build_pce_probe_rom()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(image)
    return {
        "system": "pce", "source": "original HuC6280 VDC/VCE/PSG test",
        "sha256": hashlib.sha256(image).hexdigest(),
        "bytes": len(image),
    }
