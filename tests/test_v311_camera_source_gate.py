"""No stock OpenCV wheel may be mistaken for the reviewed FFmpeg-off source."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.qa_v31_linux_camera_only_wheel import SOURCE_SHA256
from tools.v311_camera_source_gate import (
    SOURCE_RUN_BY_TARGET, require_pinned_native_camera_wheel,
)


class SourceBuiltCameraProvenanceTests(unittest.TestCase):
    def receipt(self, target="linux-x64"):
        return {
            "source_ci_run_id": SOURCE_RUN_BY_TARGET[target],
            "source_sha256": SOURCE_SHA256,
            "target": target,
            "native_wheel_sha256": "a" * 64,
            "native_camera_capture_backend_proven": True,
            "frozen_installer_tested": False,
            "redistribution_approved": False,
            "public_release_approved": False,
        }

    def inspect(self, report, target="linux-x64"):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"original-camera.json"
            path.write_text(json.dumps(report), "utf-8")
            return require_pinned_native_camera_wheel(path, target)

    def test_valid_original_source_receipt_on_each_host(self):
        for target in SOURCE_RUN_BY_TARGET:
            with self.subTest(target=target):
                expected=self.receipt(target)
                self.assertEqual(self.inspect(expected, target), expected)

    def test_mutating_any_hash_source_or_frozen_status_fails(self):
        for key,value in (
            ("source_ci_run_id", 1),
            ("source_sha256", "b"*64),
            ("native_wheel_sha256", "x"*64),
            ("native_camera_capture_backend_proven", False),
            ("frozen_installer_tested", True),
            ("redistribution_approved", True),
            ("public_release_approved", True),
            ("target", "windows-x64"),
        ):
            with self.subTest(key=key):
                edited=self.receipt()
                edited[key]=value
                with self.assertRaises(ValueError):
                    self.inspect(edited)

    def test_missing_receipt_does_not_allow_stock_native_wheel(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                require_pinned_native_camera_wheel(
                    Path(root)/"missing.json", "linux-x64")
        with self.assertRaises(ValueError):
            self.inspect(self.receipt(), "macos-x64")
        with self.assertRaises(ValueError):
            self.inspect(self.receipt(), "unreviewed-arm64")


if __name__ == "__main__":
    unittest.main()
