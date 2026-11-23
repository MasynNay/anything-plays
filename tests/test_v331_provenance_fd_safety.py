"""3.3.1: manifest readback is bounded, regular-file-only, and no-follow.

All fixtures are tiny local JSON and synthetic filesystem events. No emulator,
native core, ROM, controller, webcam, or online requests are involved.
"""
import json
import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from anything_plays.emulator_updates import find_provenance, MAX_MANIFEST_BYTES


class ProvenanceFdSafetyTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.first = self.root / "first"
        self.second = self.root / "second"
        self.first.mkdir()
        self.second.mkdir()
        self.one = self.first / "CORE_PROVENANCE.json"
        self.two = self.second / "CORE_PROVENANCE.json"
        self.two.write_text('{"cores": []}', encoding="utf-8")

    def _expect_second(self):
        found, data = find_provenance([self.first, self.second])
        self.assertEqual(found, self.two)
        self.assertEqual(data, {"cores": []})

    def test_regular_manifest_still_loads_without_modification(self):
        body = {"cores": [{"name": "mgba", "file": "mgba_libretro.so"}]}
        self.one.write_text(json.dumps(body), encoding="utf-8")
        before = self.one.read_bytes()
        found, data = find_provenance([self.first, self.second])
        self.assertEqual(found, self.one)
        self.assertEqual(data, body)
        self.assertEqual(self.one.read_bytes(), before)

    def test_open_requests_binary_no_follow_and_nonblocking_when_available(self):
        self.one.write_text('{"cores":[]}', encoding="utf-8")
        original = os.open
        flags_seen = []

        def open_checked(path, flags, *args, **kwargs):
            flags_seen.append(flags)
            return original(path, flags, *args, **kwargs)

        with patch("anything_plays.emulator_updates.os.open",
                   side_effect=open_checked):
            found, _ = find_provenance([self.first])
        self.assertEqual(found, self.one)
        self.assertEqual(len(flags_seen), 1)
        for optional_flag in ("O_BINARY", "O_NOFOLLOW", "O_NONBLOCK"):
            if getattr(os, optional_flag, 0):
                self.assertTrue(flags_seen[0] & getattr(os, optional_flag))

    def test_fstat_rejects_nonregular_fd_before_parsing(self):
        self.one.write_text('{"cores":[{"name":"mgba"}]}', encoding="utf-8")
        actual = os.fstat
        seen = []

        def fake_fstat(fd):
            seen.append(fd)
            if len(seen) == 1:
                return Mock(st_mode=stat.S_IFIFO)
            return actual(fd)

        with patch("anything_plays.emulator_updates.os.fstat",
                   side_effect=fake_fstat):
            self._expect_second()
        self.assertEqual(len(seen), 2)

    @unittest.skipUnless(
        getattr(os, "O_NOFOLLOW", None) is not None,
        "O_NOFOLLOW unavailable; symlink guard is best effort",
    )
    def test_symlink_swap_between_is_file_and_open_skips_private_data(self):
        self.one.write_text('{"cores":[]}', encoding="utf-8")
        private = self.root / "private.json"
        private.write_text('{"cores":[{"name":"private-data"}]}',
                           encoding="utf-8")
        original = Path.is_file
        swapped = []

        def race(path):
            result = original(path)
            if path == self.one and result and not swapped:
                path.unlink()
                path.symlink_to(private)
                swapped.append(True)
            return result

        try:
            with patch.object(Path, "is_file", race):
                self._expect_second()
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"OS does not permit test symlinks: {type(exc).__name__}")
        self.assertTrue(swapped)
        self.assertTrue(self.one.is_symlink())
        self.assertIn("private-data", private.read_text(encoding="utf-8"))

    @unittest.skipUnless(
        hasattr(os, "mkfifo") and hasattr(os, "O_NONBLOCK"),
        "A Unix nonblocking FIFO is required",
    )
    def test_swapped_fifo_is_not_read_and_healthy_manifest_wins(self):
        # A named pipe with no writer would block indefinitely on a normal
        # O_RDONLY open. O_NONBLOCK plus fstat must safely skip it.
        os.mkfifo(self.one)
        original = Path.is_file

        def race(path):
            if path == self.one:
                return True  # originally regular, replaced after the check
            return original(path)

        with patch.object(Path, "is_file", race):
            self._expect_second()

    def test_oversized_file_is_still_rejected_after_safe_open(self):
        self.one.write_bytes(b" " * (MAX_MANIFEST_BYTES + 1))
        self._expect_second()


if __name__ == "__main__":
    unittest.main()
