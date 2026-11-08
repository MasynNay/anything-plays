"""Original NGP mono cartridge with real PSG tone and changing K1GE background.

NO proprietary compiler, BIOS, commercial ROM, fake sound samples, or bundled
test cartridges. All instructions generated from auditable TLCS-900/H encodings.
A literal 0x00 monochrome cartridge compatibility byte is required; native
Libretro video/audio/input callbacks must independently prove the result.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

from tools.build_v30_ngp_original_mono_psg import (
    HEADER_BYTES, ROM_BYTES, original_mono_psg_code,
    create_original_mono_rom, io8,
)

STATUS = "ORIGINAL-MONO-K1GE-PSG-NATIVE-AV-UNAPPROVED"
# NeoPop's ngpgfx_write8() maps these addresses to the actual K1GE window
# and monochrome background registers. No K2GE color palette is used.
WINDOW_REGISTERS = ((0x8002, 10), (0x8003, 10),
                    (0x8004, 140), (0x8005, 132))
BACKGROUND_CONTROL = 0x8118
BACKGROUND_SHADES = (0x83, 0x87)  # Different actual monochrome grayscale levels.


def store8_absolute(address: int, value: int) -> bytes:
    """LD A,#imm8; LD (abs16),A. Exact TLCS-900 t900as encodings."""
    if not 0 <= address <= 0xFFFF or not 0 <= value <= 0xFF:
        raise ValueError("Bad original TLCS-900 memory byte write")
    # 21 imm = LD A,#imm, F1 lo hi 41 = LD (abs16),A.
    return bytes((0x21, value, 0xF1, address & 255, address >> 8, 0x41))


def frame_delay(outer: int = 96) -> bytes:
    """Delay visibly between frame shades without external clocks or threads.

    LD B,outer; outer: LD C,255; inner: DEC 1,C; JR NZ,inner;
    DEC 1,B; JR NZ,outer. The DEC byte-register instructions set Z;
    unlike word-register DEC on TLCS-900/H, whose flags do not update.
    """
    if not 10 <= outer <= 255:
        raise ValueError("Original delay loop bound out of range")
    return bytes((0x22, outer, 0x23, 255,
                  0xCB, 0x69, 0x6E, 0xFC,   # DEC C; JR NZ, -4
                  0xCA, 0x69, 0x6E, 0xF6)) # DEC B; JR NZ, -10


def original_monochrome_audio_video_code() -> bytes:
    # Reuse source-proven B8=55 PSG ON and B9=AA Z80 OFF tone initialization.
    base = original_mono_psg_code("stop-z80-tone")
    # Replace only the final 5-byte pure watchdog idle with a *real* K1GE
    # graphics loop. Never alter the sound writes which passed native CI.
    if not base.endswith(io8(0x6F, 0x4E) + bytes((0x68, 0xFB))):
        raise ValueError("Mono sound boot code no longer ends in safe watchdog loop")
    code = bytearray(base[:-5])
    for address, value in WINDOW_REGISTERS:
        code += store8_absolute(address, value)

    start = len(code)
    for shade in BACKGROUND_SHADES:
        code += io8(0x6F, 0x4E)
        code += store8_absolute(BACKGROUND_CONTROL, shade)
        code += frame_delay()
    distance = start - (len(code) + 2)
    if not -128 <= distance <= -1:
        raise ValueError("Original K1GE frame animation jumps outside short branch range")
    code += bytes((0x68, distance & 255)) # JR back to actual frame loop
    return bytes(code)


def create_original_mono_av_rom() -> bytes:
    template = create_original_mono_rom("stop-z80-tone")
    body = original_monochrome_audio_video_code()
    if len(body) > ROM_BYTES - HEADER_BYTES:
        raise ValueError("Original AV research exceeds ROM storage")
    rom = template[:HEADER_BYTES] + body
    rom += b"\xff" * (ROM_BYTES - len(rom))
    if rom[0x23] != 0 or len(rom) != ROM_BYTES:
        raise ValueError("Original AV fixture is not genuine monochrome")
    return rom


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    path = args.output
    if path.suffix != ".ngp" or path.exists() or path.is_symlink():
        parser.error("Only a NEW temporary original .ngp output path is permitted")
    rom = create_original_mono_av_rom()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(rom)
    print(f"{STATUS}: real MONO 0x00, {len(rom)} bytes, "
          f"sha256 {hashlib.sha256(rom).hexdigest()}; native A/V UNTESTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
