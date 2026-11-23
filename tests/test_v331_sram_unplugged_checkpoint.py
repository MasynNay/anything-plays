"""3.3.1: cartridge SRAM remains durable if the original ROM drive disappears.

All bytes are synthetic memory buffers in temporary directories. No game
ROM, native core, webcam, controller or real removable device is accessed.
"""
import ctypes as C
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.libretro_save import SaveRAM


class SaveRamRemovableDriveRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.games = self.root / "removable-games"
        self.games.mkdir()
        self.rom = self.games / "game.gba"
        self.buffer = C.create_string_buffer(b"GOOD", 4)
        with patch("anything_plays.libretro_save._user_save_directory",
                   return_value=self.root / "user-saves"):
            self.save = SaveRAM(
                self.rom, lambda _kind: C.addressof(self.buffer),
                lambda _kind: 4,
            )
        self.legacy = self.save.legacy_path
        self.fallback = self.save.fallback_path

    def test_unreadable_legacy_file_probe_uses_writable_fallback(self):
        self.assertTrue(self.save.persist())
        self.assertEqual(self.legacy.read_bytes(), b"GOOD")
        self.assertFalse(self.fallback.exists())

        actual_file_probe = Path.is_file
        original_writer = SaveRAM._write_atomic

        def unplugged_probe(path):
            if path == self.legacy:
                raise OSError("PRIVATE unplugged USB /media/owner/roms")
            return actual_file_probe(path)

        def unplugged_writer(destination, snapshot, *, create_directory):
            if destination == self.legacy:
                raise OSError("PRIVATE no longer mounted")
            return original_writer(
                destination, snapshot, create_directory=create_directory
            )

        # Bytes have NOT changed since the successful ROM-adjacent save.
        # The old digest shortcut raised during is_file() and never tried
        # the established user-owned fallback writer.
        with (
            patch.object(Path, "is_file", unplugged_probe),
            patch.object(SaveRAM, "_write_atomic",
                         side_effect=unplugged_writer) as writing,
        ):
            self.assertTrue(self.save.persist())
        self.assertEqual(writing.call_count, 2)
        self.assertEqual(self.save.path, self.fallback)
        self.assertEqual(self.fallback.read_bytes(), b"GOOD")
        self.assertEqual(self.legacy.read_bytes(), b"GOOD")
        self.assertFalse(self.save.persist())
        self.assertEqual(list(self.fallback.parent.glob("*.tmp")), [])

    def test_transient_probe_failure_can_rewrite_original_complete_snapshot(self):
        self.assertTrue(self.save.persist())
        original_probe = Path.is_file
        failures = [0]

        def temporary_stat_fault(path):
            if path == self.legacy and failures[0] == 0:
                failures[0] += 1
                raise PermissionError("PRIVATE transient filesystem probe")
            return original_probe(path)

        with patch.object(Path, "is_file", temporary_stat_fault):
            # Retry the intact snapshot instead of reporting an unsafe
            # no-change success on a destination we could not inspect.
            self.assertTrue(self.save.persist())
        self.assertEqual(self.save.path, self.legacy)
        self.assertEqual(self.legacy.read_bytes(), b"GOOD")
        self.assertFalse(self.save.persist())
        self.assertEqual(failures, [1])

    def test_unmounted_rom_directory_falls_back_even_for_unchanged_ram(self):
        self.assertTrue(self.save.persist())
        self.games.rename(self.root / "unmounted")
        self.assertTrue(self.save.persist())
        self.assertEqual(self.save.path, self.fallback)
        self.assertEqual(self.fallback.read_bytes(), b"GOOD")
        self.assertFalse(self.save.persist())

    def test_unreadable_fallback_probe_retries_complete_snapshot(self):
        self.save.path = self.fallback
        self.assertTrue(self.save.persist())
        original_probe = Path.is_file

        def transient_failure(path):
            if path == self.fallback:
                raise OSError("PRIVATE temporary user-data metadata error")
            return original_probe(path)

        with patch.object(Path, "is_file", transient_failure):
            self.assertTrue(self.save.persist())
        self.assertEqual(self.save.path, self.fallback)
        self.assertEqual(self.fallback.read_bytes(), b"GOOD")
        self.assertFalse(self.save.persist())

    def test_unwritable_fallback_does_not_claim_success_or_update_digest(self):
        self.save.path = self.fallback
        self.assertTrue(self.save.persist())
        prior_digest = self.save._last_saved_digest
        self.buffer.raw = b"NEXT"
        with patch.object(
            SaveRAM, "_write_atomic",
            side_effect=OSError("PRIVATE user save disk full")
        ):
            with self.assertRaises(OSError):
                self.save.persist()
        self.assertEqual(self.save._last_saved_digest, prior_digest)
        self.assertEqual(self.fallback.read_bytes(), b"GOOD")
        self.assertTrue(self.save.persist())
        self.assertEqual(self.fallback.read_bytes(), b"NEXT")


if __name__ == "__main__":
    unittest.main()
