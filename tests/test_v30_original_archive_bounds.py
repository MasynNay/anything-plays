"""Regression tests for bounded extraction of preserved native input archives."""
import io
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from create_v30_candidate_lock import read_original_archive, MAX_ORIGINAL_ARCHIVE_BYTES


class OriginalArchiveBoundsTests(unittest.TestCase):
    def make_outer(self, name, payload):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(name, payload)
        return zipfile.ZipFile(io.BytesIO(stream.getvalue()))

    def test_regular_original_archive(self):
        with self.make_outer("core.zip", b"native-archive") as outer:
            self.assertEqual(read_original_archive(outer, "core.zip", "linux-x64"), b"native-archive")

    def test_declared_oversize_rejected_before_decompression(self):
        with self.make_outer("core.zip", b"native") as outer:
            with patch.object(outer.getinfo("core.zip"), "file_size", MAX_ORIGINAL_ARCHIVE_BYTES + 1):
                with self.assertRaisesRegex(ValueError, "oversized"):
                    read_original_archive(outer, "core.zip", "linux-x64")

    def test_bounded_read_rejects_excess_actual_bytes(self):
        with self.make_outer("core.zip", b"native") as outer:
            class ExcessReader:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def read(self, limit):
                    self.limit = limit
                    return type("SyntheticOversize", (), {"__len__": lambda self: limit})()
            reader = ExcessReader()
            with patch.object(outer, "open", return_value=reader):
                with self.assertRaisesRegex(ValueError, "exceeds limit"):
                    read_original_archive(outer, "core.zip", "linux-x64")
            self.assertEqual(reader.limit, MAX_ORIGINAL_ARCHIVE_BYTES + 1)


if __name__ == "__main__":
    unittest.main()
