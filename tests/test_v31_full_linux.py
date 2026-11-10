"""3.1 Linux full-library repackage: source-byte and fail-closed checks."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.assemble_v31_full_linux import (
    STABLE, PREVIEW, FULL, SOURCE_REVISION, sha, validate_inputs, build,
)


class ReleaseCandidateLinuxTests(unittest.TestCase):
    def test_candidate_keeps_distinct_nonrelease_install_identity(self):
        self.assertEqual(STABLE, "anything-plays_3.0.0_amd64.deb")
        self.assertTrue(FULL.startswith("anything-plays-31-preview_"))
        self.assertNotEqual(PREVIEW, FULL)

    def test_release_checksum_and_source_receipt_are_mandatory(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            old, new = root/STABLE, root/PREVIEW
            old.write_bytes(b"original" * 40)
            new.write_bytes(b"preview" * 40)
            sums, receipt = root/"SHA256SUMS.txt", root/"PREVIEW1_RECEIPT.json"
            sums.write_text(sha(old)+"  "+STABLE+"\n", "utf-8")
            receipt.write_text(json.dumps({"target":"linux-x64",
                "installer":PREVIEW, "sha256":sha(new),
                "source_revision":SOURCE_REVISION}),"utf-8")
            self.assertEqual(validate_inputs(old,new,sums,receipt), sha(old))
            new.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                validate_inputs(old,new,sums,receipt)
            sums.write_text("0"*64+"  "+STABLE+"\n", "utf-8")
            with self.assertRaises(ValueError):
                validate_inputs(old,new,sums,receipt)

    def test_repackaging_rejects_release_flags_before_reading_any_input(self):
        with patch.dict(os.environ, {
            "AP_V31_PREVIEW":"1", "AP_V31_FULL_TEST_CORES":"1",
            "AP_RELEASE_BUILD":"1"}):
            with self.assertRaises(ValueError):
                build(*[Path("missing") for _ in range(5)])

    def test_no_release_publishing_in_job(self):
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/v31-full-linux-qa.yml").read_text("utf-8")
        self.assertIn("gh release download v3.0.0", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("contents: write", workflow)


if __name__ == "__main__":
    unittest.main()
