"""Headless OpenCV's capture backend must survive on each build target."""
from types import SimpleNamespace
from unittest.mock import patch
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

    def test_ffmpeg_rejected_for_verified_camera_only_wheel(self):
        mock = self.stub(gui="COCOA")
        mock.CAP_FFMPEG = 1900
        mock.getBuildInformation = lambda: "  GUI: COCOA\n  FFMPEG: YES\n"
        mock.videoio_registry.hasBackend = lambda backend: backend == mock.CAP_AVFOUNDATION
        with patch.dict("os.environ", {"AP_REQUIRE_OPENCV_FFMPEG_OFF": "1"}):
            with self.assertRaisesRegex(RuntimeError, "requires FFMPEG: NO"):
                verify_opencv_build(mock, "darwin")

    def test_absent_ffmpeg_line_accepted_as_not_compiled(self):
        mock = self.stub(gui="COCOA")
        mock.CAP_FFMPEG = 1900
        mock.getBuildInformation = lambda: "  GUI: COCOA\n  AVFoundation: YES\n"
        mock.videoio_registry.hasBackend = lambda backend: backend == mock.CAP_AVFOUNDATION
        with patch.dict("os.environ", {"AP_REQUIRE_OPENCV_FFMPEG_OFF": "1"}):
            result = verify_opencv_build(mock, "darwin")
            self.assertEqual(result["ffmpeg_enabled"], "UNKNOWN")

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
