"""Regression coverage for native library ZIP member type validation."""
import io
import stat
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from create_v30_candidate_lock import read_native_payload


class NativeZipMemberSafetyTests(unittest.TestCase):
    @staticmethod
    def archive(mode):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            info = zipfile.ZipInfo("mgba_libretro.so")
            info.create_system = 3
            info.external_attr = (mode | 0o777) << 16
            archive.writestr(info, b"payload")
        return buffer.getvalue()

    def test_regular_native_file_accepted(self):
        self.assertEqual(read_native_payload(self.archive(stat.S_IFREG), "mgba_libretro.so", "linux-x64", "mgba"), b"payload")

    def test_symlink_named_like_native_file_rejected(self):
        with self.assertRaisesRegex(ValueError, "symlinked core ZIP payload"):
            read_native_payload(self.archive(stat.S_IFLNK), "mgba_libretro.so", "linux-x64", "mgba")

    def test_missing_expected_native_file_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid core ZIP payload"):
            read_native_payload(self.archive(stat.S_IFREG), "other_libretro.so", "linux-x64", "mgba")


if __name__ == "__main__":
    unittest.main()
