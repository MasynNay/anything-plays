"""Headless OpenCV's capture backend must survive on each build target."""
from types import SimpleNamespace
import unittest

from tools.check_opencv_build import verify_opencv_build

class _VideoIO:
    def __init__(self, supported=True):
        self.supported = supported
    def hasBackend(self, backend):
        return self.supported and backend in (200, 700, 1400)

class HeadlessCaptureTests(unittest.TestCase):
    def stub(self, gui="NONE", available=True):
        return SimpleNamespace(
            getBuildInformation=lambda: "  Video I/O:\n      GUI: " + gui + "\n",
            __version__="4.14.0",
            CAP_DSHOW=700, CAP_AVFOUNDATION=1200, CAP_V4L2=200,
            videoio_registry=SimpleNamespace(
                hasBackend=lambda backend: available
            ),
        )

    def test_headless_capture_backends_for_all_targets(self):
        for platform, backend in (
            ("win32", "DirectShow"), ("darwin", "AVFoundation"),
            ("linux", "V4L2"),
        ):
            with self.subTest(platform=platform):
                result = verify_opencv_build(self.stub(), platform)
                self.assertEqual(result["capture_backend"], backend)
                self.assertFalse(result["camera_hardware_tested"])

    def test_gui_enabled_cv2_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "without bundled Qt/GUI"):
            verify_opencv_build(self.stub(gui="QT5"), "linux")

    def test_macos_headless_wheel_may_report_native_cocoa(self):
        result = verify_opencv_build(self.stub(gui="COCOA"), "darwin")
        self.assertEqual(result["gui"], "COCOA")
        self.assertEqual(result["capture_backend"], "AVFoundation")
        with self.assertRaisesRegex(RuntimeError, "without bundled Qt/GUI"):
            verify_opencv_build(self.stub(gui="COCOA"), "win32")

    def test_missing_video_backend_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "V4L2"):
            verify_opencv_build(self.stub(available=False), "linux")


if __name__ == "__main__":
    unittest.main()
