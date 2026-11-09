"""Original WonderSwan V30MZ video and wavetable-audio test cartridges.

Produces legal source-generated x86-compatible machine code for the mono and
color WonderSwan. The program draws actual RAM tiles, changes hardware
palette registers, and programs the console's 4-bit wavetable channel.
No commercial ROM or boot firmware is included in installers or evidence.
"""
from __future__ import annotations
import hashlib
from pathlib import Path

ROM_SIZE = 128 * 1024
SYSTEMS = ("ws", "wsc")
CODE_SEGMENT = 0xE000  # This 128 KiB ROM is memory-mapped at $E0000.


def build_wonderswan_probe_rom(system="ws"):
    if system not in SYSTEMS:
        raise ValueError("Expected original monochrome or color WonderSwan")
    code = bytearray()
    labels = {}
    branches = []
    jumps = []

    def emit(*values):
        code.extend(values)
    def label(name):
        labels[name] = len(code)
    def mov_al(value):
        emit(0xB0, value & 255)
    def out(port, value):
        mov_al(value)
        emit(0xE6, port)
    def word_ram(address, value):
        # MOV WORD PTR DS:[absolute], immediate16.
        emit(0xC7, 0x06, address & 255, address >> 8,
             value & 255, (value >> 8) & 255)
    def jnz(name):
        branches.append((len(code), name))
        emit(0x75, 0)
    def jmp(name):
        jumps.append((len(code), name))
        emit(0xE9, 0, 0)
    def delay(name):
        emit(0xB9, 0xFF, 0xFF)  # MOV CX,$FFFF
        label(name)
        emit(0x49)  # DEC CX
        jnz(name)

    emit(0xFA, 0x31, 0xC0)       # CLI; XOR AX,AX
    emit(0x8E, 0xD8, 0x8E, 0xC0)  # DS=ES=0: internal console RAM.
    emit(0xBC, 0xFE, 0x1F)       # SP=$1FFE, in internal RAM.
    out(0x90, 0x00)  # Disable channel during waveform init.
    out(0x14, 0x01)  # LCD ON.
    out(0x07, 0x01)  # BG tilemap in RAM page $0800.
    if system == "wsc":
        out(0x60, 0x80)  # WSC 2bpp color (0x20 was monochrome mode).
    else:
        out(0x1C, 0xF0)  # Monochrome system grayscale luminance.
        out(0x20, 0x71)  # Palette0 color indexes for two-pixel test.
    # Fill the full 32x32 background tilemap with tile index 0.
    emit(0xBF, 0x00, 0x08)  # MOV DI,$0800.
    emit(0xB9, 0x00, 0x04)  # MOV CX,1024 words.
    emit(0x31, 0xC0)       # XOR AX,AX.
    emit(0xF3, 0xAB)       # REP STOSW.
    # First tile graphics: alternating bit 0 on every row, four greys.
    emit(0xBF, 0x00, 0x20)  # 2bpp tile data for both systems: $2000.
    emit(0xB9, 0x08, 0x00)
    emit(0xB8, 0xAA, 0x00)  # 2bpp tile row, plane 0 stripe.
    emit(0xF3, 0xAB)
    if system == "wsc":
        # 12-bit RGB RAM colors for palette 0 (entry 0 black, entry 1 red).
        word_ram(0xFE00, 0x000)
        word_ram(0xFE02, 0x00F)
    out(0x00, 0x01)  # Background screen enabled.
    out(0x10, 0x00)  # X scroll starts at zero.
    # Native DAC: channel 1 wave-table @ $0300, alternating 0/F nibble.
    emit(0xBF, 0x00, 0x03)  # DI = $0300
    emit(0xB9, 0x08, 0x00)  # 16 waveform bytes, 8 16-bit words
    emit(0xB8, 0xF0, 0xF0)  # Little endian waveform = F0 F0...
    emit(0xF3, 0xAB)
    out(0x8F, 0x0C)  # 0x0300 >> 6: wavetable base.
    out(0x80, 0x00)  # Channel 1 frequency low byte.
    out(0x81, 0x07)  # Frequency $700, audible ~375 Hz.
    out(0x88, 0xFF)  # Full stereo volume.
    out(0x91, 0x07)  # Sound output enabled to speaker/headphones.
    out(0x90, 0x01)  # Channel 1 waveform enabled.
    label("animation")
    if system == "wsc":
        word_ram(0xFE02, 0x0F0)  # Green palette entry 1.
    else:
        out(0x20, 0x72)  # Bright monochrome palette shade shift.
    delay("hold_one")
    if system == "wsc":
        word_ram(0xFE02, 0x00F)  # Red palette entry 1.
    else:
        out(0x20, 0x17)  # Different monochrome level.
    delay("hold_two")
    jmp("animation")

    for offset, name in branches:
        delta = labels[name] - (offset + 2)
        if not -128 <= delta <= 127:
            raise ValueError("NEC V30MZ branch beyond 8-bit displacement")
        code[offset + 1] = delta & 255
    for offset, name in jumps:
        delta = labels[name] - (offset + 3)
        code[offset + 1:offset + 3] = (
            delta & 0xFFFF
        ).to_bytes(2, "little")
    assert len(code) < 2048

    rom = bytearray(ROM_SIZE)
    rom[:len(code)] = code
    # WonderSwan footer: far jump reset opcode + 11 cart metadata bytes.
    # Bank image occupies the top 128K address window, hence CS=$E000.
    rom[-16:-11] = bytes((0xEA, 0, 0, 0, 0xE0))
    rom[-11] = 0x80  # Skip optional custom splash.
    rom[-10] = 0x00  # Unlicensed original homebrew publisher.
    rom[-9] = 0x01 if system == "wsc" else 0x00
    rom[-8] = 0x03  # Original test game identifier.
    rom[-7] = 0x00  # First revision.
    rom[-6] = 0x00  # 128KiB = 1Mbit ROM size.
    rom[-5] = 0x00  # No SRAM/EEPROM.
    rom[-4] = 0x00  # Bootloader flags.
    rom[-3] = 0x00  # Subsystem flags.
    rom[-2:] = (sum(rom[:-2]) & 0xFFFF).to_bytes(2, "little")
    return bytes(rom)


def write_wonderswan_probe(destination, system):
    target = Path(destination)
    if system not in SYSTEMS or target.suffix.lower() != "." + system:
        raise ValueError("Original WonderSwan test extension mismatch")
    data = build_wonderswan_probe_rom(system)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {
        "system": system,
        "source": "original NEC V30MZ WonderSwan video and wavetable DAC",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "requires_bios_file": False,
    }
