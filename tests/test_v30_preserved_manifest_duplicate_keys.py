"""Fail-closed regression for ambiguous preserved native manifest JSON keys."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.stage_v30_approved_source_inputs import (
    ORIGINAL_11, UNAPPROVED_ORIGINAL, _original_inputs,
)


class PreservedManifestDuplicateKeysTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.extension = ".so"
        self.target = "linux-x64"
        names = sorted([f"{name}_libretro{self.extension}.zip" for name in ORIGINAL_11] + ["Dolphin.zip"])
        self.rows = []
        for name in names:
            data = ("synthetic:" + name).encode("ascii")
            (self.root / name).write_bytes(data)
            self.rows.append({"name": name, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
        self.record = {
            "target": self.target,
            "status": "UNAPPROVED-TEST-INPUTS",
            "public_distribution_approved": False,
            "original_archive_count": 12,
            "files": self.rows,
        }

    def write_raw(self, text):
        (self.root / UNAPPROVED_ORIGINAL).write_text(text, encoding="utf-8")

    def verify(self):
        return _original_inputs(self.root, self.target, self.extension)

    def test_valid_manifest_still_accepted(self):
        self.write_raw(json.dumps(self.record))
        self.assertEqual(len(self.verify()), 12)

    def test_duplicate_top_level_key_rejected_without_mutating_archives(self):
        original = (self.root / self.rows[0]["name"]).read_bytes()
        raw = json.dumps(self.record)
        self.write_raw(raw[:-1] + ', "target": "linux-x64"}')
        with self.assertRaisesRegex(ValueError, "Duplicate preserved native manifest JSON key"):
            self.verify()
        self.assertEqual((self.root / self.rows[0]["name"]).read_bytes(), original)

    def test_duplicate_nested_row_key_rejected(self):
        raw = json.dumps(self.record)
        first = json.dumps(self.rows[0])
        tampered = first[:-1] + ', "size_bytes": ' + str(self.rows[0]["size_bytes"]) + '}'
        self.assertIn(first, raw)
        self.write_raw(raw.replace(first, tampered, 1))
        with self.assertRaisesRegex(ValueError, "Duplicate preserved native manifest JSON key"):
            self.verify()

    def test_duplicate_nested_key_rejected_even_if_values_identical(self):
        raw = json.dumps(self.record)
        self.write_raw(raw[:-1] + ', "original_archive_count": 12}')
        with self.assertRaisesRegex(ValueError, "Duplicate preserved native manifest JSON key"):
            self.verify()


    def test_nonfinite_json_constants_rejected_at_every_depth(self):
        # Python's json.loads accepts these nonstandard constants by default.
        raw = json.dumps(self.record)
        first = json.dumps(self.rows[0])
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant, location="top"):
                self.write_raw(raw[:-1] + ', "extra": ' + constant + '}')
                with self.assertRaisesRegex(ValueError, "Non-finite preserved native"):
                    self.verify()
            with self.subTest(constant=constant, location="row"):
                tampered = first[:-1] + ', "extra": ' + constant + '}'
                self.write_raw(raw.replace(first, tampered, 1))
                with self.assertRaisesRegex(ValueError, "Non-finite preserved native"):
                    self.verify()

    def test_nonfinite_rejection_preserves_original_archive_bytes(self):
        name = self.rows[0]["name"]
        original = (self.root / name).read_bytes()
        self.write_raw(json.dumps(self.record)[:-1] + ', "extra": NaN}')
        with self.assertRaisesRegex(ValueError, "Non-finite preserved native"):
            self.verify()
        self.assertEqual((self.root / name).read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
