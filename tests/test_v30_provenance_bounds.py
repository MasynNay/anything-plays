"""Fail-closed regression tests for preserved provenance ZIP decompression."""
import io
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from create_v30_candidate_lock import MAX_PROVENANCE_BYTES, read_preserved_provenance


class ProvenanceBoundsTests(unittest.TestCase):
    def archive(self, payload=b'{"status":"UNAPPROVED-TEST-INPUTS"}'):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as output:
            output.writestr("PRESERVED_NATIVE_INPUTS.json", payload)
        return zipfile.ZipFile(io.BytesIO(data.getvalue()))

    def test_normal_json_is_parsed(self):
        with self.archive() as outer:
            self.assertEqual(
                read_preserved_provenance(outer, outer.getinfo("PRESERVED_NATIVE_INPUTS.json"), "linux-x64")["status"],
                "UNAPPROVED-TEST-INPUTS",
            )

    def test_declared_oversize_rejected_before_read(self):
        with self.archive() as outer:
            entry = outer.getinfo("PRESERVED_NATIVE_INPUTS.json")
            with patch.object(entry, "file_size", MAX_PROVENANCE_BYTES + 1):
                with patch.object(outer, "open", side_effect=AssertionError("must not decompress")):
                    with self.assertRaisesRegex(ValueError, "oversized"):
                        read_preserved_provenance(outer, entry, "linux-x64")

    def test_actual_read_is_bounded_even_if_header_underreports(self):
        with self.archive() as outer:
            entry = outer.getinfo("PRESERVED_NATIVE_INPUTS.json")
            class OversizeReader:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def read(self, count):
                    self.count = count
                    return b"x" * count
            reader = OversizeReader()
            with patch.object(outer, "open", return_value=reader):
                with self.assertRaisesRegex(ValueError, "exceeds limit"):
                    read_preserved_provenance(outer, entry, "linux-x64")
            self.assertEqual(reader.count, MAX_PROVENANCE_BYTES + 1)

    def test_non_object_json_rejected(self):
        with self.archive(b"[]") as outer:
            with self.assertRaisesRegex(ValueError, "JSON object"):
                read_preserved_provenance(outer, outer.getinfo("PRESERVED_NATIVE_INPUTS.json"), "linux-x64")


if __name__ == "__main__":
    unittest.main()
