"""Regression tests: malformed preserved provenance must fail closed, not crash."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from create_v30_candidate_lock import build_candidate, CORES, PLATFORMS


class CandidateLockMalformedRecordTests(unittest.TestCase):
    def _reject(self, record, message):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "inputs.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("PRESERVED_NATIVE_INPUTS.json", json.dumps(record))
            with self.assertRaisesRegex(ValueError, message):
                build_candidate({platform: archive for platform in PLATFORMS})

    @staticmethod
    def _record():
        return {
            "source_revision": "a" * 40,
            "target": "windows-x64",
            "status": "UNAPPROVED-TEST-INPUTS",
            "public_distribution_approved": False,
            "original_archive_count": 12,
            "source_core_provenance": {
                "cores": [{"name": name} for name in sorted(CORES)],
            },
            "files": [{"name": f"archive-{i}"} for i in range(12)],
        }

    def test_non_object_top_level_provenance(self):
        for bad in (None, [], "not an object", 7):
            with self.subTest(bad=bad):
                self._reject(bad, "preserved provenance must be a JSON object")

    def test_unhashable_core_name(self):
        record = self._record()
        record["source_core_provenance"]["cores"][0]["name"] = ["bad"]
        self._reject(record, "native core name must be a string")

    def test_unhashable_archive_name(self):
        record = self._record()
        record["files"][0]["name"] = {"bad": True}
        self._reject(record, "archive name must be a string")


if __name__ == "__main__":
    unittest.main()
