"""Reject unverified extra entries inside candidate native core ZIPs."""
import io
import stat
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from create_v30_candidate_lock import read_native_payload


class NativeZipSingleMemberTests(unittest.TestCase):
    def archive(self, entries):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as z:
            for name, payload in entries:
                z.writestr(name, payload)
        return output.getvalue()

    def read(self, entries):
        return read_native_payload(self.archive(entries), "mgba_libretro.so", "linux-x64", "mgba")

    def test_exact_single_native_file_is_accepted(self):
        self.assertEqual(self.read([("mgba_libretro.so", b"native")]), b"native")

    def test_unix_regular_mode_is_accepted(self):
        entry = zipfile.ZipInfo("mgba_libretro.so")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFREG | 0o644) << 16
        self.assertEqual(self.read([(entry, b"native")]), b"native")

    def test_unix_special_file_modes_are_rejected(self):
        for kind in (stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFLNK):
            with self.subTest(kind=kind):
                entry = zipfile.ZipInfo("mgba_libretro.so")
                entry.create_system = 3
                entry.external_attr = (kind | 0o644) << 16
                with self.assertRaisesRegex(ValueError, "non-regular core ZIP payload"):
                    self.read([(entry, b"not a regular native library")])

    def test_unexpected_extra_file_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid core ZIP payload"):
            self.read([("mgba_libretro.so", b"native"), ("hidden.txt", b"unverified")])

    def test_extra_directory_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid core ZIP payload"):
            self.read([("mgba_libretro.so", b"native"), ("extra/", b"")])

    def test_duplicate_native_entry_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid core ZIP payload"):
            self.read([("mgba_libretro.so", b"native"), ("mgba_libretro.so", b"replacement")])


if __name__ == "__main__":
    unittest.main()
