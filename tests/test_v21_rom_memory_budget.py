"""Prevent oversized disk images from exhausting the Python/native heap."""
import ctypes as C
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from anything_plays.gba_emulator import (
    CoreSession, Emulator, MAX_IN_MEMORY_ROM_BYTES,
)


class RomMemoryBudgetTests(unittest.TestCase):
    def test_small_in_memory_rom_is_still_supported(self):
        with TemporaryDirectory() as folder:
            rom = Path(folder) / "homebrew.gba"
            rom.write_bytes(b"HOME" * 16)
            emulator = Emulator()
            session = CoreSession(emulator, "gba", rom, None)
            info = session._game_info(False)
            self.assertEqual(info.size, len(rom.read_bytes()))
            self.assertEqual(
                C.string_at(info.data, info.size), rom.read_bytes()
            )

    def test_oversized_disc_is_rejected_before_reading_into_ram(self):
        with TemporaryDirectory() as folder:
            rom = Path(folder) / "wrong-image.gba"
            rom.write_bytes(b"small")
            session = CoreSession(Emulator(), "gba", rom, None)
            with patch.object(Path, "stat", return_value=SimpleNamespace(
                st_size=MAX_IN_MEMORY_ROM_BYTES + 1
            )), patch.object(Path, "read_bytes", side_effect=AssertionError(
                "Must not read the oversized ROM"
            )):
                with self.assertRaisesRegex(ValueError, "too large"):
                    session._game_info(False)

    def test_rom_growth_after_size_check_is_still_bounded(self):
        with TemporaryDirectory() as folder:
            rom = Path(folder) / "growing.gba"
            rom.write_bytes(b"small")
            session = CoreSession(Emulator(), "gba", rom, None)
            # Simulate a file changing from 5 bytes to a larger object
            # between stat() and open(). Do not allocate an actual 256MB file.
            with patch("anything_plays.gba_emulator.MAX_IN_MEMORY_ROM_BYTES", 16):
                with patch.object(Path, "stat", return_value=SimpleNamespace(
                    st_size=5
                )), patch.object(Path, "open", return_value=BytesIO(b"Z" * 32)):
                    with self.assertRaisesRegex(ValueError, "changed size"):
                        session._game_info(False)

    def test_full_path_core_does_not_read_entire_disc(self):
        with TemporaryDirectory() as folder:
            rom = Path(folder) / "game.rvz"
            rom.write_bytes(b"header")
            session = CoreSession(Emulator(), "gba", rom, None)
            with patch.object(Path, "read_bytes", side_effect=AssertionError(
                "Full-path game must not be read into process memory"
            )):
                info = session._game_info(True)
            self.assertFalse(info.data)
            self.assertEqual(info.size, 0)


if __name__ == "__main__":
    unittest.main()
