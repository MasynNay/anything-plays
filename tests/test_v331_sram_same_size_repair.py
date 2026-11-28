"""3.3.1: equal-size external changes must not trick unchanged SRAM checkpoints.

Only synthetic four-byte native memory and temporary files are used. No ROM,
native emulator, real save directory, cloud account, network or USB storage.
"""
import ctypes as C
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.libretro_save import SaveRAM


class SRAMSameSizeRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.rom = self.root / "example.gba"
        self.memory = C.create_string_buffer(b"GOOD", 4)
        self.scope = patch(
            "anything_plays.libretro_save._user_save_directory",
            return_value=self.root / "backup-saves",
        )
        self.scope.start()
        self.addCleanup(self.scope.stop)
        self.save = SaveRAM(
            self.rom, lambda _id: C.addressof(self.memory), lambda _id: 4,
        )

    def assert_save_bytes(self, expected=b"GOOD"):
        self.assertEqual(self.save.path.read_bytes(), expected)

    @staticmethod
    def alter_timestamp(path):
        before = path.stat()
        # Explicitly advance mtime beyond filesystem timestamp resolution
        # so the four-platform fixture represents a real external edit.
        os.utime(
            path, ns=(before.st_atime_ns, before.st_mtime_ns + 5_000_000_000)
        )

    def test_unchanged_complete_save_skips_thousands_of_writes(self):
        self.assertTrue(self.save.persist())
        first_identity = self.save._last_saved_file_signature
        self.assertIsNotNone(first_identity)
        with patch.object(
            SaveRAM, "_write_atomic",
            side_effect=AssertionError("unchanged bytes must not rewrite"),
        ) as writer:
            for _ in range(1000):
                self.assertFalse(self.save.persist())
        writer.assert_not_called()
        self.assertEqual(self.save._last_saved_file_signature, first_identity)
        self.assert_save_bytes()

    def test_equal_size_in_place_external_edit_is_repaired(self):
        self.assertTrue(self.save.persist())
        self.save.path.write_bytes(b"EVIL")
        self.alter_timestamp(self.save.path)
        self.assertTrue(self.save.persist())
        self.assert_save_bytes()
        self.assertFalse(self.save.persist())

    def test_equal_size_atomic_cloud_replacement_is_repaired(self):
        self.assertTrue(self.save.persist())
        previous = self.save._last_saved_file_signature
        external = self.root / "cloud-shadow.sav"
        external.write_bytes(b"SYNC")
        self.alter_timestamp(external)
        os.replace(external, self.save.path)
        self.assertNotEqual(
            self.save._last_saved_file_signature,
            self.save.path.stat().st_mtime_ns
        )
        self.assertTrue(self.save.persist())
        self.assert_save_bytes()
        self.assertNotEqual(self.save._last_saved_file_signature, previous)
        self.assertFalse(self.save.persist())

    def test_metadata_only_external_change_forces_safe_reverification(self):
        self.assertTrue(self.save.persist())
        self.alter_timestamp(self.save.path)
        self.assertTrue(self.save.persist())
        self.assertFalse(self.save.persist())
        self.assert_save_bytes()

    def test_same_size_replacement_after_restore_is_repaired(self):
        self.save.path.write_bytes(b"GOOD")
        self.save.restore()
        self.assertEqual(self.memory.raw, b"GOOD")
        self.assertIsNotNone(self.save._last_saved_file_signature)
        self.save.path.write_bytes(b"SYNC")
        self.alter_timestamp(self.save.path)
        self.assertTrue(self.save.persist())
        self.assert_save_bytes()

    def test_normal_unchanged_restore_does_not_rewrite(self):
        self.save.path.write_bytes(b"GOOD")
        self.save.restore()
        before = self.save._last_saved_file_signature
        with patch.object(
            SaveRAM, "_write_atomic",
            side_effect=AssertionError("healthy restore should remain untouched"),
        ) as writer:
            self.assertFalse(self.save.persist())
        writer.assert_not_called()
        self.assertEqual(self.save._last_saved_file_signature, before)

    def test_same_size_change_in_user_owned_fallback_is_repaired(self):
        self.save.path = self.save.fallback_path
        self.assertTrue(self.save.persist())
        self.save.path.write_bytes(b"SYNC")
        self.alter_timestamp(self.save.path)
        self.assertTrue(self.save.persist())
        self.assert_save_bytes()
        self.assertFalse(self.save.persist())

    def test_deleted_file_is_recreated_even_when_native_ram_is_unchanged(self):
        self.assertTrue(self.save.persist())
        self.save.path.unlink()
        self.assertTrue(self.save.persist())
        self.assert_save_bytes()
        self.assertFalse(self.save.persist())

    def test_unsuccessful_repair_does_not_advance_digest_or_identity(self):
        self.assertTrue(self.save.persist())
        identity = self.save._last_saved_file_signature
        digest = self.save._last_saved_digest
        self.save.path.write_bytes(b"EVIL")
        self.alter_timestamp(self.save.path)
        with patch.object(
            SaveRAM, "_write_atomic",
            side_effect=OSError("PRIVATE /Users/owner/drive missing"),
        ):
            with self.assertRaises(OSError):
                self.save.persist()
        self.assertEqual(self.save._last_saved_file_signature, identity)
        self.assertEqual(self.save._last_saved_digest, digest)
        self.assert_save_bytes(b"EVIL")
        self.assertTrue(self.save.persist())
        self.assert_save_bytes()

    def test_failed_post_commit_metadata_probe_retries_next_checkpoint(self):
        original_stat = Path.stat
        called = [0]
        dest = self.save.path

        def faulty_stat(path, *args, **kwargs):
            if path == dest and called[0] == 0:
                called[0] += 1
                raise OSError("PRIVATE disappeared after fsync")
            return original_stat(path, *args, **kwargs)

        with patch.object(Path, "stat", faulty_stat):
            self.assertTrue(self.save.persist())
        self.assertIsNone(self.save._last_saved_file_signature)
        self.assert_save_bytes()
        self.assertTrue(self.save.persist())  # conservatively verify again
        self.assertFalse(self.save.persist())
        self.assertEqual(called, [1])

    def test_legacy_symlink_keeps_existing_unchanged_restore_behavior(self):
        target = self.root / "external-sync.sav"
        target.write_bytes(b"GOOD")
        try:
            self.save.path.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlinks unavailable: {type(exc).__name__}")
        self.save.restore()
        with patch.object(
            SaveRAM, "_write_atomic",
            side_effect=AssertionError("stable linked saves remain compatible"),
        ) as writer:
            self.assertFalse(self.save.persist())
        writer.assert_not_called()
        self.assertEqual(target.read_bytes(), b"GOOD")
        self.assertTrue(self.save.path.is_symlink())

    def test_private_preview_never_touches_stable_same_size_save(self):
        stable = self.rom.with_suffix(".sav")
        stable.write_bytes(b"STBL")
        with (
            patch("anything_plays.libretro_save.is_v32_preview",
                  return_value=True),
            patch("anything_plays.libretro_save.is_v33_candidate",
                  return_value=False),
        ):
            preview = SaveRAM(
                self.rom, lambda _id: C.addressof(self.memory),
                lambda _id: 4,
            )
            self.assertNotEqual(preview.path, stable)
            self.assertTrue(preview.persist())
            preview.path.write_bytes(b"SYNC")
            self.alter_timestamp(preview.path)
            self.assertTrue(preview.persist())
            self.assertEqual(preview.path.read_bytes(), b"GOOD")
            self.assertEqual(stable.read_bytes(), b"STBL")


if __name__ == "__main__":
    unittest.main()
