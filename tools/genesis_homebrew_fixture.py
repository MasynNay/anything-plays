"""Original Genesis/Mega Drive M68000 test cartridge generated from opcodes.

This is a clean-room CI-only fixture: no third-party ROMs, assets or BIOS.
It renders an alternating two-colour tile map using the Genesis VDP and
generates an audible pulse using the console's SN76489-compatible PSG.
"""
from __future__ import annotations
from pathlib import Path
import hashlib

ROM_SIZE = 64 * 1024
ENTRY = 0x200
VDP_CTRL = 0x00C00004
VDP_DATA = 0x00C00000
PSG = 0x00C00011

# Each checkpoint replaces the NEXT instruction with BRA.S -2. This allows
# isolated native testing of the exact cartridge initialization instruction
# that first breaks Genesis Plus GX, without swapping in a third-party ROM.
PHASES = ("idle", "tmss", "vdp", "patterns", "tiles", "palette", "tone", "full")


def build_genesis_probe_rom(phase="full"):
    if phase not in PHASES:
        raise ValueError(f"Unknown original Genesis test phase: {phase}")
    code = bytearray()
    checkpoints = {"idle": 0}
    def w(n):
        code.extend((int(n) & 0xFFFF).to_bytes(2, "big"))
    def l(n):
        code.extend((int(n) & 0xFFFFFFFF).to_bytes(4, "big"))
    def imm_word(value, address):
        w(0x33FC); w(value); l(address)
    def imm_long(value, address):
        w(0x23FC); l(value); l(address)
    def imm_byte(value, address):
        w(0x13FC); w(value); l(address)
    def vdp_register(index, value):
        imm_word(0x8000 | (index << 8) | value, VDP_CTRL)
    def dbra(dreg, start):
        w(0x51C8 | dreg)
        # Motorola DBcc uses the PC at the displacement EXTENSION word,
        # i.e. opcode address + 2, not the end of the instruction.  We have
        # already appended the 2-byte opcode, so len(code) is that PC.
        # The previous +2 branched into immediate data and eventually
        # corrupted native Genesis Plus GX execution during retro_run().
        distance = start - (ENTRY + len(code))
        assert -32768 <= distance <= 32767
        w(distance)

    w(0x46FC); w(0x2700)  # MOVE.W #$2700,SR (mask interrupts)
    imm_long(0x53454741, 0x00A14000)  # TMSS license hardware unlock, "SEGA"
    checkpoints["tmss"] = len(code)

    # Configure VDP mode 5 with no V-blank interrupts (all vectors private).
    for index, value in (
        (0, 0x04), (1, 0x04), (2, 0x30), (3, 0x00), (4, 0x07),
        (5, 0x78), (6, 0x00), (7, 0x00), (10, 0x00),
        (11, 0x00), (12, 0x81), (13, 0x3F), (15, 0x02),
        (16, 0x01), (17, 0x00), (18, 0x00),
    ):
        vdp_register(index, value)
    checkpoints["vdp"] = len(code)

    # Paint two 8x8 tile patterns in native 4bpp at VRAM 0.
    imm_long(0x40000000, VDP_CTRL)
    for colour in (0x11111111, 0x22222222):
        for _ in range(8):
            imm_long(colour, VDP_DATA)
    checkpoints["patterns"] = len(code)

    # Plane A tile name table begins at VRAM 0xC000 (register #2 = 0x30).
    # Fill a visible 32x28 checkerboard. Each word is tile index 0 or 1.
    imm_long(0x40000003, VDP_CTRL)
    w(0x41F9); l(VDP_DATA)  # LEA $C00000,A0
    w(0x7000)              # MOVEQ #0,D0
    w(0x323C); w(895)       # MOVE.W #895,D1
    write_tile = ENTRY + len(code)
    w(0x3080)              # MOVE.W D0,(A0)
    w(0x0A40); w(0x0001)   # EORI.W #1,D0
    dbra(1, write_tile)
    checkpoints["tiles"] = len(code)

    # CRAM palette #0 black, #1 green, #2 purple.
    imm_long(0xC0000000, VDP_CTRL)
    for colour in (0x0000, 0x00E0, 0x0E0E):
        imm_word(colour, VDP_DATA)
    vdp_register(1, 0x44)  # mode 5 + display, interrupts disabled
    checkpoints["palette"] = len(code)

    # PSG tone channel zero: latch tone, set divider, max volume.
    for value in (0x8F, 0x1C, 0x90):
        imm_byte(value, PSG)
    checkpoints["tone"] = len(code)

    # Animate palette entry #1 periodically; keep tile #2 unchanged.
    # 65536 DBRA loops are about 0.1 s on a Genesis 68000.
    animation = ENTRY + len(code)
    imm_long(0xC0020000, VDP_CTRL)  # CRAM colour index 1
    imm_word(0x00E0, VDP_DATA)
    w(0x323C); w(0xFFFF)  # D1 0xFFFF
    start = ENTRY + len(code)
    w(0x4E71)  # NOP
    dbra(1, start)
    imm_long(0xC0020000, VDP_CTRL)
    imm_word(0x000E, VDP_DATA)
    w(0x323C); w(0xFFFF)
    start = ENTRY + len(code)
    w(0x4E71)
    dbra(1, start)
    w(0x4EF9); l(animation)  # JMP animation loop
    assert len(code) < 0x1000
    if phase != "full":
        # Preserve opcode offsets of all phases; truncate execution, not ROM.
        boundary = checkpoints[phase]
        assert boundary % 2 == 0 and boundary + 2 <= len(code)
        code[boundary:boundary + 2] = b"\x60\xfe"  # BRA.S * (infinite idle)

    rom = bytearray(ROM_SIZE)
    # Reserve space for supervisor/interrupt stack pushes near the high end of
    # $FF0000-$FFFFFF Genesis work RAM. $FF0000 is the *bottom* of RAM and
    # would underflow on the first 68000 stack push.
    rom[:4] = (0x00FFFF00).to_bytes(4, "big")  # initial supervisor SP
    rom[4:8] = ENTRY.to_bytes(4, "big")        # reset entry
    rom[0x100:0x110] = b"SEGA MEGA DRIVE "
    rom[0x120:0x120 + 31] = b"Anything Plays Genesis Audio Test"[:31]
    rom[0x150:0x150 + 31] = b"Anything Plays Genesis Audio Test"[:31]
    rom[0x1A0:0x1A4] = (0).to_bytes(4, "big")
    rom[0x1A4:0x1A8] = (ROM_SIZE - 1).to_bytes(4, "big")
    rom[0x1F0:0x1F3] = b"U  "
    rom[ENTRY:ENTRY+len(code)] = code
    return bytes(rom)


def write_genesis_probe(destination, *, phase="full"):
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_genesis_probe_rom(phase=phase)
    target.write_bytes(payload)
    return {
        "source": "original Anything Plays Genesis VDP/PSG test cartridge",
        "phase": phase,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }
