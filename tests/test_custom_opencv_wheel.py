"""Validate hash-locked, macOS arm64 FFmpeg-free OpenCV wheel selection."""

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from tools.verify_custom_opencv_wheel import verify_custom_wheel

FILENAME = "opencv_python_headless-4.14.0.94-cp313-cp313-macosx_15_0_arm64.whl"


class CustomWheelTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.wheel = Path(self.temp.name) / FILENAME
        self.pack()

    def pack(self, extra=None):
        with zipfile.ZipFile(self.wheel, "w") as archive:
            archive.writestr(
                "opencv_python_headless-4.14.0.94.dist-info/METADATA",
                "Metadata-Version: 2.3\nName: opencv-python-headless\nVersion: 4.14.0.94\n"
            )
            archive.writestr("cv2/cv2.abi3.so", b"test Mach-O")
            if extra:
                archive.writestr(extra, b"unapproved native content")
        self.sha = hashlib.sha256(self.wheel.read_bytes()).hexdigest()

    def test_accepts_matching_hash_and_metadata(self):
        report = verify_custom_wheel(self.wheel, self.sha)
        self.assertEqual(report["sha256"], self.sha)
        self.assertEqual(report["distribution"], "opencv-python-headless")
        self.assertFalse(report["redistribution_approved"])

    def test_rejects_changed_hash(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify_custom_wheel(self.wheel, "0" * 64)

    def test_rejects_bundled_ffmpeg_or_codecs(self):
        for extra in ("cv2/.dylibs/libavformat.61.dylib",
                      "cv2/.dylibs/libx264.164.dylib",
                      "cv2/.dylibs/libx265.215.dylib"):
            with self.subTest(extra=extra):
                self.pack(extra)
                with self.assertRaisesRegex(ValueError, "FFmpeg or GPL codec"):
                    verify_custom_wheel(self.wheel, self.sha)

    def test_rejects_invalid_architecture(self):
        other = self.wheel.with_name(FILENAME.replace("arm64", "x86_64"))
        self.wheel.rename(other)
        with self.assertRaisesRegex(ValueError, "does not target macos-arm64"):
            verify_custom_wheel(other, self.sha)

    def test_accepts_exact_other_platform_wheel_tags(self):
        targets = (
            ("windows-x86_64", "win_amd64"),
            ("linux-x86_64", "linux_x86_64"),
            ("macos-x86_64", "macosx_15_0_x86_64"),
        )
        for target, tag in targets:
            with self.subTest(target=target):
                original = self.wheel
                renamed = self.wheel.with_name(
                    "opencv_python_headless-4.14.0.94-cp313-cp313-" + tag + ".whl"
                )
                original.rename(renamed)
                try:
                    report = verify_custom_wheel(renamed, self.sha, target)
                    self.assertEqual(report["target"], target)
                finally:
                    renamed.rename(original)

    def test_rejects_symlink(self):
        link = self.wheel.with_name("linked-" + FILENAME)
        link.symlink_to(self.wheel)
        with self.assertRaisesRegex(ValueError, "regular file"):
            verify_custom_wheel(link, self.sha)


if __name__ == "__main__":
    unittest.main()
