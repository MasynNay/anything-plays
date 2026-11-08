"""Preserve exact developer-build native archives without approving public distribution."""
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.fetch_dolphin_sys import read_system_archive


class V30OriginalInputCaptureTests(unittest.TestCase):
    def test_dolphin_preserves_exact_archive_bytes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            upstream = root / "archive"
            capture = root / "preserved"
            upstream.mkdir()
            raw = b"real bytes would be a ZIP; this test checks only capture"
            (upstream / "Dolphin.zip").write_bytes(raw)
            with patch.dict(os.environ, {
                "AP_RELEASE_BUILD": "0",
                "AP_CORE_ARCHIVE_DIR": str(upstream),
                "AP_CORE_ARCHIVE_CAPTURE_DIR": str(capture),
            }):
                result = read_system_archive()
            self.assertEqual(result, raw)
            self.assertEqual((capture / "Dolphin.zip").read_bytes(), raw)
            self.assertEqual(
                hashlib.sha256(result).hexdigest(),
                hashlib.sha256((capture / "Dolphin.zip").read_bytes()).hexdigest(),
            )

    def test_symlink_capture_is_refused(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            upstream = root / "source"
            upstream.mkdir()
            (upstream / "Dolphin.zip").write_bytes(b"placeholder")
            capture = root / "alias"
            try:
                capture.symlink_to(upstream, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            with patch.dict(os.environ, {
                "AP_RELEASE_BUILD": "0",
                "AP_CORE_ARCHIVE_DIR": str(upstream),
                "AP_CORE_ARCHIVE_CAPTURE_DIR": str(capture),
            }):
                with self.assertRaisesRegex(ValueError, "symlinked"):
                    read_system_archive()

    def test_capture_workflow_requires_all_original_archives(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/v30-full-bundle.yml").read_text(encoding="utf-8")
        self.assertIn("AP_CORE_ARCHIVE_CAPTURE_DIR: preserved-native-inputs", workflow)
        self.assertIn("PRESERVED_NATIVE_INPUTS.json", workflow)
        self.assertIn("original_archive_count", workflow)
        self.assertIn("retention-days: 90", workflow)
        self.assertIn("UNAPPROVED", workflow)


if __name__ == "__main__":
    unittest.main()
