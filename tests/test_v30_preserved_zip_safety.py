"""Reject unsafe preserved ZIP metadata before trusting native inputs."""
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from create_v30_candidate_lock import build_candidate, PLATFORMS, MAX_PROVENANCE_BYTES


class PreservedZipSafetyTests(unittest.TestCase):
    def _check(self, *, symlink=False, oversized=False):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "preserved.zip"
            with zipfile.ZipFile(artifact, "w") as archive:
                data = b" " * (MAX_PROVENANCE_BYTES + 1) if oversized else json.dumps({}).encode()
                archive.writestr("PRESERVED_NATIVE_INPUTS.json", data)
                if symlink:
                    link = zipfile.ZipInfo("malicious_link")
                    link.create_system = 3
                    link.external_attr = (stat.S_IFLNK | 0o777) << 16
                    archive.writestr(link, "outside")
            return build_candidate({platform: artifact for platform in PLATFORMS})

    def test_rejects_unix_symlink_zip_member(self):
        with self.assertRaisesRegex(ValueError, "symlinked preserved ZIP member"):
            self._check(symlink=True)

    def test_rejects_oversized_provenance_before_reading_json(self):
        with self.assertRaisesRegex(ValueError, "oversized preserved provenance"):
            self._check(oversized=True)

    def test_normal_zip_reaches_existing_provenance_validation(self):
        with self.assertRaisesRegex(ValueError, "missing source revision"):
            self._check()


if __name__ == "__main__":
    unittest.main()
