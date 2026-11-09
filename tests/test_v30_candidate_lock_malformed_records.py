"""Malformed preserved input metadata must fail with a controlled rejection.

All archives in this test are synthetic and are never release candidates.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from tools.create_v30_candidate_lock import CORES, PLATFORMS, build_candidate


class MalformedPreservedProvenanceTests(unittest.TestCase):
    def _check_rejection(self, broken_field, bad_value, message):
        with TemporaryDirectory() as directory:
            inputs = {}
            for platform in PLATFORMS:
                path = Path(directory) / (platform + ".zip")
                record = {
                    "source_revision": "a" * 40,
                    "target": platform,
                    "status": "UNAPPROVED-TEST-INPUTS",
                    "public_distribution_approved": False,
                    "original_archive_count": 12,
                    "source_core_provenance": {
                        "cores": [{"name": name} for name in sorted(CORES)],
                    },
                    "files": [{"name": f"synthetic-{index}"} for index in range(12)],
                }
                if platform == "linux-x64":
                    if broken_field == "cores":
                        record["source_core_provenance"]["cores"][0] = bad_value
                    else:
                        record["files"][0] = bad_value
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr("PRESERVED_NATIVE_INPUTS.json", json.dumps(record))
                inputs[platform] = path
            with self.assertRaisesRegex(ValueError, message):
                build_candidate(inputs)

    def test_non_mapping_core_record_is_rejected(self):
        self._check_rejection("cores", "not-a-record", "malformed native core provenance row")

    def test_null_archive_record_is_rejected(self):
        self._check_rejection("files", None, "malformed original archive record")


if __name__ == "__main__":
    unittest.main()
