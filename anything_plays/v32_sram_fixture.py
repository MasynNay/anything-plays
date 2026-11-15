"""Fixed, non-game cartridge-memory QA bytes; no commercial ROM, firmware or BIOS.

This module carries only disposable test constants. It does not execute
native code, read user files or authorize public 3.2 distribution.
"""
ROM_FOLDER = "synthetic-gba-roms"
ROM_NAME = "original-test-cartridge.gba"
ROM_CANARY = b"AP32-ONLY-SYNTHETIC-ROM-NOT-PLAYABLE-OR-A-REAL-GAME"
OLD_SRAM = bytes((i * 7 + 13) % 256 for i in range(128))
NEW_SRAM = bytes((i * 11 + 19) % 256 for i in range(128))
assert len(OLD_SRAM) == len(NEW_SRAM) == 128 and OLD_SRAM != NEW_SRAM
