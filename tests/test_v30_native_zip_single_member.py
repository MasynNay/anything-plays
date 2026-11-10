"""Reject unverified extra entries inside candidate native core ZIPs."""
import io
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
