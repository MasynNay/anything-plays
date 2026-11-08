"""Generate an *original*, strictly monochrome NG Pocket PSG audio probe.

No third-party ROM, BIOS, SDK, SNK compiler or downloaded toolchain is used.
Small hand-assembled TLCS-900/H instructions are encoded from public hardware
documentation. The 64-byte cartridge header, CPU entry address and mono
compatibility flag are genuine (not a renamed color .ngc image).

This is ONLY an experimental research cartridge, never a game for the product.
Its validity is determined by real Mednafen NeoPop native audio/video/input
callbacks in isolated CI. Do not treat a successful build as audio evidence.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys

ROM_START = 0x200000
HEADER_BYTES = 64
ENTRY = ROM_START + HEADER_BYTES
ROM_BYTES = 64 * 1024
# Neo Geo Pocket cartridge recognition convention, NOT a claim of SNK license.
CARTRIDGE_COPYRIGHT_FIELD = b"COPYRIGHT BY SNK CORPORATION"
TITLE = b"MONO PSG CI"  # twelve-byte cartridge title field
VARIANTS = (
    "direct-tone",
    "stop-z80-tone",
    "restart-z80-tone",
    "stop-z80-tone-noise",
)

# TLCS-900 native IO opcodes as documented in the source-audited Tixul
# NgpCraft t900as toolchain. LDB (short IO address), immediate = 08 addr imm.
# LDW (short IO address), immediate = 0A addr little-endian-imm16.
# JR always = 68 signed-8-bit-relative-displacement.
def io8(address: int, value: int) -> bytes:
    if not 0 <= address <= 0xFF or not 0 <= value <= 0xFF:
        raise ValueError("TLCS-900 byte I/O operand out of range")
    return bytes((0x08, address, value))


def io16(address: int, value: int) -> bytes:
    if not 0 <= address <= 0xFF or not 0 <= value <= 0xFFFF:
        raise ValueError("TLCS-900 word I/O operand out of range")
    return bytes((0x0A, address, value & 0xFF, value >> 8))


def original_mono_psg_code(variant: str) -> bytes:
    if variant not in VARIANTS:
        raise ValueError("Unknown original monochrome native PSG research mode")
    code = bytearray()
    # IMPORTANT: the ACTUAL shipped Beetle/Mednafen NeoPop source in
    # mednafen/ngp/mem.c shows:
    #     0xB8 = 0x55: PSG enabled; 0xB8 = 0xAA: PSG disabled
    #     0xB9 = 0x55: Z80 enabled; 0xB9 = 0xAA: Z80 stopped.
    # For TLCS-900 direct sound writes to 0xA0/0xA1, the Z80 MUST be OFF.
    # NeoPop's storeB() ignores those writes while Z80_IsEnabled() is true.
    # Prior diagnostic variants accidentally enabled Z80 and disabled PSG,
    # guaranteeing all four emitted silence; those results are superseded.
    # See upstream: https://github.com/libretro/beetle-ngp-libretro/blob/master/mednafen/ngp/mem.c
    if variant == "direct-tone":
        # Ordered bytes: stop Z80 before turning on sound and writing PSG.
        code += io8(0xB9, 0xAA)
        code += io8(0xB8, 0x55)
    elif variant == "restart-z80-tone":
        # Start both in word mode, then STOP Z80 before direct PSG writes.
        code += io16(0xB8, 0x5555)
        code += io8(0xB9, 0xAA)
    else:
        # One 16-bit store: little-endian low B8=55 -> PSG ON,
        # high B9=AA -> Z80 OFF, exactly as NeoPop storeW() requires.
        code += io16(0xB8, 0xAA55)

    # Direct TLCS-900 write to 0xA1 reaches T6W28 tone registers (not the
    # Z80's 0x4000/0x4001 bus). Tone1 divider 218 -> ~440 Hz at 3.072 MHz:
    # latch 0x80 | (218 & 0x0f) = 0x8A; data 218 >> 4 = 0x0D.
    # Register 1 attenuation = 0x90 (maximum level, not silent 0x9F).
    code += io8(0xA1, 0x8A)
    code += io8(0xA1, 0x0D)
    code += io8(0xA1, 0x90)
    if variant == "stop-z80-tone-noise":
        # Independent direct noise path, useful if tone-only routing is mute.
        # Noise latch 0xE4 = white noise, attenuator register 7 = 0xF0.
        code += io8(0xA0, 0xE4)
        code += io8(0xA0, 0xF0)

    # Keep clearing watchdog at 0x6F without CPU sleep/BIOS calls.
    # JR -5 returns to the beginning of the three-byte watchdog IO write.
    heartbeat = len(code)
    code += io8(0x6F, 0x4E)
    code += bytes((0x68, 0xFB))
    if heartbeat != len(code) - 5:
        raise AssertionError("Original NGP heartbeat loop is malformed")
    return bytes(code)


def create_original_mono_rom(variant: str) -> bytes:
    code = original_mono_psg_code(variant)
    assert len(CARTRIDGE_COPYRIGHT_FIELD) == 28
    assert len(TITLE) <= 12
    header = bytearray(HEADER_BYTES)
    header[:28] = CARTRIDGE_COPYRIGHT_FIELD
    struct.pack_into("<I", header, 0x1C, ENTRY)
    struct.pack_into("<H", header, 0x20, 0)  # Homebrew software ID
    header[0x22] = 0   # Dev subcode
    header[0x23] = 0   # Genuine monochrome system mode, not 0x10/NGPC color
    header[0x24:0x30] = TITLE.ljust(12, b" ")
    rom = bytes(header) + code
    if len(rom) > ROM_BYTES:
        raise ValueError("Unreasonable original NGP sound probe size")
    rom += b"\xFF" * (ROM_BYTES - len(rom))
    assert rom[0x23] == 0
    assert struct.unpack_from("<I", rom, 0x1C)[0] == ENTRY
    assert len(rom) == ROM_BYTES
    return rom


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, choices=VARIANTS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    path = args.output
    if path.suffix != ".ngp" or path.is_symlink() or path.exists():
        parser.error("Research ROM must be a new .ngp path, not a symlink")
    try:
        rom = create_original_mono_rom(args.variant)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(rom)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Original monochrome source build failed: {error}\n")
    print(f"ORIGINAL MONO RESEARCH ONLY: variant={args.variant} "
          f"bytes={len(rom)} sha256={hashlib.sha256(rom).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
