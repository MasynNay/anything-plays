"""3.3.1 native-core integrity checks must not follow local file redirects.

Synthetic byte files only: no native code, ROMs, cameras, controllers or network.
"""
import hashlib
import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from anything_plays.emulator_updates import _verified_record, check_emulator_updates


class NativeCoreNoFollowTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.core = self.root / "mgba_libretro.so"
        self.data = b"tiny synthetic core bytes, not executable"
        self.record = {
            "name": "mgba", "file": self.core.name,
            "sha256": hashlib.sha256(self.data).hexdigest(),
        }

    def test_regular_core_still_verifies_and_bad_checksum_is_modified(self):
        self.core.write_bytes(self.data)
        self.assertEqual(_verified_record(self.record, self.root), "verified")
        record = {**self.record, "sha256": "0" * 64}
        self.assertEqual(_verified_record(record, self.root), "modified")
        self.assertEqual(self.core.read_bytes(), self.data)

    def test_symlinked_core_is_not_hashed_even_if_content_matches(self):
        private = self.root / "outside-bytes"
        private.write_bytes(self.data)
        try:
            self.core.symlink_to(private)
        except (OSError, NotImplementedError):
            self.skipTest("This host does not permit test symlinks")
        with patch("anything_plays.emulator_updates.os.open") as opening:
            self.assertEqual(_verified_record(self.record, self.root), "invalid")
        opening.assert_not_called()
        self.assertEqual(private.read_bytes(), self.data)

    def test_broken_symlink_is_not_reported_as_a_missing_bundled_file(self):
        try:
            self.core.symlink_to(self.root / "removed-core-file")
        except (OSError, NotImplementedError):
            self.skipTest("This host does not permit test symlinks")
        self.assertEqual(_verified_record(self.record, self.root), "invalid")
        self.assertTrue(self.core.is_symlink())

    def test_unhashable_manifest_name_fails_closed(self):
        self.core.write_bytes(self.data)
        self.assertEqual(
            _verified_record({**self.record, "name": ["mgba"]}, self.root),
            "invalid",
        )
        self.assertEqual(
            _verified_record({**self.record, "name": {"core": "mgba"}}, self.root),
            "invalid",
        )

    def test_fd_that_is_no_longer_a_regular_file_is_rejected(self):
        self.core.write_bytes(self.data)
        with patch(
            "anything_plays.emulator_updates.os.fstat",
            return_value=Mock(st_mode=stat.S_IFIFO),
        ):
            self.assertEqual(_verified_record(self.record, self.root), "invalid")
        self.assertEqual(self.core.read_bytes(), self.data)

    @unittest.skipUnless(
        getattr(os, "O_NOFOLLOW", None) is not None,
        "Native O_NOFOLLOW is unavailable on this platform",
    )
    def test_race_replacing_core_with_symlink_is_not_followed(self):
        self.core.write_bytes(self.data)
        private = self.root / "outside-bytes"
        private.write_bytes(self.data)
        original_is_file = Path.is_file
        moved = False

        def race_after_file_check(path):
            nonlocal moved
            result = original_is_file(path)
            if path == self.core and result and not moved:
                moved = True
                path.unlink()
                path.symlink_to(private)
            return result

        with patch.object(Path, "is_file", race_after_file_check):
            # A no-follow open fails with OSError rather than reading the
            # symlink destination. The outer health report reports unreadable.
            with self.assertRaises(OSError):
                _verified_record(self.record, self.root)
        self.assertTrue(moved)
        self.assertTrue(self.core.is_symlink())
        self.assertEqual(private.read_bytes(), self.data)

    def test_missing_core_and_unreadable_core_have_distinct_results(self):
        self.assertEqual(_verified_record(self.record, self.root), "missing")
        self.core.write_bytes(self.data)
        with patch("anything_plays.emulator_updates.os.open",
                   side_effect=OSError("mocked filesystem failure")):
            with self.assertRaises(OSError):
                _verified_record(self.record, self.root)


if __name__ == "__main__":
    unittest.main()
