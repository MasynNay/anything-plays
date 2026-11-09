"""N64 evidence must survive independent CI job output directories."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.probe_n64_homebrew import copy_frame_evidence


class N64FrameEvidenceTests(unittest.TestCase):
    def test_creates_missing_evidence_directory_and_copies_image(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            preview = root / "n64-homebrew-frame.png"
            preview.write_bytes(b"test frame bytes")
            report = root / "missing" / "evidence" / "n64.json"
            self.assertTrue(copy_frame_evidence(preview, report))
            copied = report.with_name("n64-homebrew-frame.png")
            self.assertEqual(copied.read_bytes(), b"test frame bytes")

    def test_missing_image_does_not_invent_evidence(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertFalse(copy_frame_evidence(
                root / "missing.png", root / "report" / "n64.json"
            ))
            self.assertFalse((root / "report").exists())


if __name__ == "__main__":
    unittest.main()
