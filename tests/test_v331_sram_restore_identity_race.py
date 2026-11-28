"""SRAM restore must not certify a different or changing disk snapshot."""
import ctypes as C
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.libretro_save import SaveRAM


class SRAMRestoreIdentityRaceTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.memory = C.create_string_buffer(b"INIT", 4)
        scope = patch("anything_plays.libretro_save._user_save_directory",
                      return_value=self.root / "fallback")
        scope.start()
        self.addCleanup(scope.stop)
        self.save = SaveRAM(self.root / "game.gba",
                            lambda _: C.addressof(self.memory), lambda _: 4)
        self.save.path.write_bytes(b"GOOD")

    def test_stable_restore_certifies_identity_and_skips_rewrite(self):
        self.save.restore()
        self.assertEqual(self.memory.raw, b"GOOD")
        self.assertIsNotNone(self.save._last_saved_file_signature)
        self.assertFalse(self.save.persist())

    def test_replacement_during_open_is_not_certified(self):
        replacement = self.root / "replacement.sav"
        replacement.write_bytes(b"SYNC")
        before = replacement.stat()
        os.utime(replacement, ns=(before.st_atime_ns,
                                  before.st_mtime_ns + 5_000_000_000))
        original = os.open
        swapped = False

        def replace_before_open(path, flags, *args, **kwargs):
            nonlocal swapped
            if Path(path) == self.save.path and not swapped:
                os.replace(replacement, self.save.path)
                swapped = True
            return original(path, flags, *args, **kwargs)

        with patch("anything_plays.libretro_save.os.open",
                   side_effect=replace_before_open):
            self.save.restore()
        self.assertTrue(swapped)
        self.assertEqual(self.memory.raw, b"SYNC")
        self.assertIsNone(self.save._last_saved_file_signature)
        self.assertTrue(self.save.persist())
        self.assertFalse(self.save.persist())

    def test_descriptor_metadata_change_during_read_is_not_certified(self):
        real_fstat = os.fstat
        probes = 0

        def changed_fd(fd):
            nonlocal probes
            info = real_fstat(fd)
            probes += 1
            if probes == 2:
                from types import SimpleNamespace
                return SimpleNamespace(
                    st_dev=info.st_dev, st_ino=info.st_ino,
                    st_size=info.st_size,
                    st_mtime_ns=info.st_mtime_ns + 1,
                    st_ctime_ns=info.st_ctime_ns,
                )
            return info

        with patch("anything_plays.libretro_save.os.fstat",
                   side_effect=changed_fd):
            self.save.restore()
        self.assertEqual(probes, 2)
        self.assertEqual(self.memory.raw, b"GOOD")
        self.assertIsNone(self.save._last_saved_file_signature)
        self.assertTrue(self.save.persist())

    def test_path_metadata_changes_after_read_do_not_certify(self):
        original = os.fstat
        probes = 0

        def touch_after_read(fd):
            nonlocal probes
            probes += 1
            if probes == 2:
                info = self.save.path.stat()
                os.utime(self.save.path, ns=(info.st_atime_ns,
                                            info.st_mtime_ns + 5_000_000_000))
            return original(fd)

        with patch("anything_plays.libretro_save.os.fstat",
                   side_effect=touch_after_read):
            self.save.restore()
        self.assertEqual(self.memory.raw, b"GOOD")
        self.assertIsNone(self.save._last_saved_file_signature)

    def test_optional_post_read_metadata_failure_keeps_readable_progress(self):
        real_fstat = os.fstat
        probes = 0

        def failed_verification(fd):
            nonlocal probes
            probes += 1
            if probes == 2:
                raise OSError("metadata temporarily unavailable")
            return real_fstat(fd)

        with patch("anything_plays.libretro_save.os.fstat",
                   side_effect=failed_verification):
            self.save.restore()
        self.assertEqual(self.memory.raw, b"GOOD")
        self.assertIsNotNone(self.save._last_saved_digest)
        self.assertIsNone(self.save._last_saved_file_signature)
        self.assertTrue(self.save.persist())
        self.assertFalse(self.save.persist())

    def test_truncated_restore_remains_unverified(self):
        self.save.path.write_bytes(b"OK")
        self.save.restore()
        self.assertEqual(self.memory.raw, b"OKIT")
        self.assertIsNone(self.save._last_saved_digest)
        self.assertIsNone(self.save._last_saved_file_signature)
        self.assertTrue(self.save.persist())
        self.assertEqual(self.save.path.read_bytes(), b"OKIT")


if __name__ == "__main__":
    unittest.main()
