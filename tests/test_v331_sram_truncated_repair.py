"""3.3.1: an unchanged game must repair externally truncated SRAM on disk.

Only four-byte synthetic cartridge RAM and temporary files are used. No game,
ROM, native emulator, camera, controller, or physical removable drive.
"""
import ctypes as C
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.libretro_save import SaveRAM


class SRAMTruncatedCheckpointRepairTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.memory = C.create_string_buffer(b"GOOD", 4)
        with patch("anything_plays.libretro_save._user_save_directory",
                   return_value=self.root / "safe-saves"):
            self.save = SaveRAM(
                self.root / "game.gba",
                lambda _kind: C.addressof(self.memory),
                lambda _kind: 4,
            )

    def test_unchanged_healthy_snapshot_is_not_rewritten(self):
        self.assertTrue(self.save.persist())
        before = self.save.path.read_bytes()
        with patch.object(
            SaveRAM, "_write_atomic",
            side_effect=AssertionError("unchanged save must not touch disk")
        ) as write:
            self.assertFalse(self.save.persist())
        write.assert_not_called()
        self.assertEqual(before, b"GOOD")

    def test_truncated_legacy_snapshot_is_repaired_even_if_sram_unchanged(self):
        self.assertTrue(self.save.persist())
        self.save.path.write_bytes(b"GO")
        self.assertTrue(self.save.persist())
        self.assertEqual(self.save.path.read_bytes(), b"GOOD")
        self.assertFalse(self.save.persist())
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_zero_byte_legacy_save_is_repaired_from_active_game_ram(self):
        self.assertTrue(self.save.persist())
        self.save.path.write_bytes(b"")
        self.assertTrue(self.save.persist())
        self.assertEqual(self.save.path.read_bytes(), b"GOOD")

    def test_oversized_legacy_file_is_normalized_even_if_sram_unchanged(self):
        self.assertTrue(self.save.persist())
        self.save.path.write_bytes(b"GOOD" + b"extra")
        self.assertTrue(self.save.persist())
        self.assertEqual(self.save.path.read_bytes(), b"GOOD")

    def test_truncated_user_owned_fallback_is_repaired(self):
        self.save.path = self.save.fallback_path
        self.assertTrue(self.save.persist())
        self.assertEqual(self.save.path, self.save.fallback_path)
        self.save.path.write_bytes(b"G")
        self.assertTrue(self.save.persist())
        self.assertEqual(self.save.path.read_bytes(), b"GOOD")
        self.assertFalse(self.save.persist())

    def test_stat_error_after_positive_is_file_probe_retries_safe_snapshot(self):
        self.assertTrue(self.save.persist())
        original_stat = Path.stat
        attempts = [0]
        destination = self.save.path

        def racy_stat(path, *args, **kwargs):
            if path == destination:
                attempts[0] += 1
                if attempts[0] == 2:
                    raise OSError("PRIVATE media fault /Users/owner/save.sav")
            return original_stat(path, *args, **kwargs)

        # The old code checked is_file() only. Now a failed *second* metadata
        # query must not abort saving or mark a potentially incomplete file
        # as durable. The normal atomic writer can retry safely.
        with patch.object(Path, "stat", racy_stat):
            self.assertTrue(self.save.persist())
        self.assertGreaterEqual(attempts[0], 2)
        self.assertEqual(self.save.path.read_bytes(), b"GOOD")

    def test_failed_repair_never_advances_saved_digest_or_clobbers_file(self):
        self.assertTrue(self.save.persist())
        self.save.path.write_bytes(b"G")
        previous_digest = self.save._last_saved_digest
        with patch.object(
            SaveRAM, "_write_atomic",
            side_effect=OSError("PRIVATE both save directories unavailable")
        ) as write:
            with self.assertRaises(OSError):
                self.save.persist()
        self.assertEqual(write.call_count, 2)
        self.assertEqual(self.save._last_saved_digest, previous_digest)
        self.assertEqual(self.save.path.read_bytes(), b"G")
        self.assertTrue(self.save.persist())
        self.assertEqual(self.save.path.read_bytes(), b"GOOD")

    def test_changed_game_ram_still_persists_at_existing_file_size(self):
        self.assertTrue(self.save.persist())
        self.memory.raw = b"NEXT"
        self.assertTrue(self.save.persist())
        self.assertEqual(self.save.path.read_bytes(), b"NEXT")
        self.assertFalse(self.save.persist())


if __name__ == "__main__":
    unittest.main()
