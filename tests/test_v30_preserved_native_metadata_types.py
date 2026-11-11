"""Fail-closed preserved-native archive metadata regressions (synthetic bytes only)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.stage_v30_approved_source_inputs import (
    ORIGINAL_11, UNAPPROVED_ORIGINAL, _original_inputs,
)


class PreservedNativeMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = []
        for name in sorted(ORIGINAL_11):
            filename = f"{name}_libretro.so.zip"
            data = ("synthetic-" + name).encode("ascii")
            (self.root / filename).write_bytes(data)
            self.rows.append({
                "name": filename,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            })
        data = b"synthetic-sys"
        (self.root / "Dolphin.zip").write_bytes(data)
        self.rows.append({
            "name": "Dolphin.zip",
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
        })
        self.record = {
            "target": "linux-x64",
            "status": "UNAPPROVED-TEST-INPUTS",
            "public_distribution_approved": False,
            "original_archive_count": 12,
            "files": self.rows,
        }

    def check(self):
        (self.root / UNAPPROVED_ORIGINAL).write_text(
            json.dumps(self.record), encoding="utf-8"
        )
        return _original_inputs(self.root, "linux-x64", ".so")

    def test_valid_synthetic_metadata(self):
        self.assertEqual(len(self.check()), 12)

    def test_boolean_size_is_not_an_integer(self):
        self.rows[0]["size_bytes"] = True
        with self.assertRaisesRegex(ValueError, "changed"):
            self.check()

    def test_float_size_is_not_an_integer(self):
        self.rows[0]["size_bytes"] = float(self.rows[0]["size_bytes"])
        with self.assertRaisesRegex(ValueError, "changed"):
            self.check()

    def test_malformed_digest_rejected(self):
        for value in (None, 123, "A" * 64, "g" * 64, "0" * 63):
            with self.subTest(value=value):
                self.rows[0]["sha256"] = value
                with self.assertRaisesRegex(ValueError, "changed"):
                    self.check()

    def test_rejected_metadata_does_not_modify_archives(self):
        original = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.rows[0]["size_bytes"] = True
        with self.assertRaises(ValueError):
            self.check()
        for name, data in original.items():
            self.assertEqual((self.root / name).read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
