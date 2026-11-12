"""3.1.1 camera driver failures cannot freeze discovery or strand live UI state.

No real webcam, camera permission request, ROM, or Tk window is required.
Failures are injected at the native capture constructor, read, and release.
"""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import Mock, patch

from anything_plays import cameras
from anything_plays.ui_camera import CameraMixin


class CameraDiscoveryRecoveryTests(unittest.TestCase):
    def test_constructor_read_and_release_failures_do_not_hide_later_camera(self):
        attempts = {0: 0, 1: 0, 2: 0}
        read_failure = Mock()
        read_failure.isOpened.return_value = True
        read_failure.read.side_effect = RuntimeError("USB camera removed")
        close_failure = Mock()
        close_failure.isOpened.return_value = False
        close_failure.release.side_effect = OSError("driver already closed")
        closed = Mock()
        closed.isOpened.return_value = False
        healthy = Mock()
        healthy.isOpened.return_value = True
        healthy.read.return_value = (True, object())

        def construct(index, backend):
            attempts[index] += 1
            if index == 0 and attempts[index] == 1:
                raise OSError("device disappeared during native construction")
            if index == 0 and attempts[index] == 2:
                return read_failure
            if index == 0:
                return close_failure
            if index == 1:
                return closed
            if index == 2:
                return healthy
            self.fail("Discovery scanned beyond max_index")

        with patch.object(cameras.cv2, "VideoCapture", side_effect=construct), \
             patch.object(cameras, "name_for", side_effect=lambda i: f"Camera {i}"), \
             patch.object(cameras.time, "sleep") as sleep:
            detected = cameras.discover(max_index=3)

        self.assertEqual(detected, [(2, "Camera 2")])
        self.assertEqual(attempts, {0: 3, 1: 2, 2: 1})
        read_failure.release.assert_called_once()
        close_failure.release.assert_called_once()
        closed.release.assert_called()
        healthy.release.assert_called_once()
        self.assertEqual(sleep.call_count, 3)

    def test_empty_avfoundation_device_list_never_opens_phantom_camera(self):
        device_api = types.SimpleNamespace(
            devicesWithMediaType_=lambda media: [],
        )
        fake_avfoundation = types.SimpleNamespace(
            AVCaptureDevice=device_api,
            AVMediaTypeVideo="video",
        )
        with patch.dict(sys.modules, {"AVFoundation": fake_avfoundation}), \
             patch.object(cameras.platform, "system", return_value="Darwin"), \
             patch.object(cameras.cv2, "VideoCapture") as capture:
            found = cameras.discover(max_index=8)

        self.assertEqual(found, [])
        capture.assert_not_called()

    def test_healthy_first_camera_does_not_sleep_after_success(self):
        healthy = Mock()
        healthy.isOpened.return_value = True
        healthy.read.return_value = (True, object())
        with patch.object(cameras.cv2, "VideoCapture", return_value=healthy), \
             patch.object(cameras, "name_for", return_value="Webcam"), \
             patch.object(cameras.time, "sleep") as sleep:
            self.assertEqual(cameras.discover(max_index=1), [(0, "Webcam")])
        healthy.release.assert_called_once()
        sleep.assert_not_called()


class CameraShutdownTests(unittest.TestCase):
    @staticmethod
    def app():
        app = CameraMixin()
        app.root = Mock()
        app.stop_controls = Mock()
        app.reference_image = False
        app.frame = object()
        app.camera_photo = object()
        app.canvas = Mock()
        app.camera_bezel = Mock()
        app.status = Mock()
        app.stream_clear_camera = Mock()
        app._camera_reconnect_job = None
        app._camera_reconnect_name = None
        app._camera_reconnect_attempts = 0
        app.cap = Mock()
        return app

    def test_release_error_clears_every_ui_state_and_pauses_controls(self):
        app = self.app()
        old_capture = app.cap
        old_capture.release.side_effect = OSError("camera unplugged mid-close")
        app.stop_camera()

        app.stop_controls.assert_called_once()
        old_capture.release.assert_called_once()
        self.assertIsNone(app.cap)
        self.assertIsNone(app.frame)
        self.assertIsNone(app.camera_photo)
        self.assertIsNone(app._camera_canvas_item)
        app.canvas.delete.assert_called_once_with("all")
        app.stream_clear_camera.assert_called_once()
        app.camera_bezel.set_active.assert_called_once_with(False)
        app.status.set.assert_called_with("Camera stopped")
        # The old broken driver must not be retried or released twice.
        app.stop_camera()
        old_capture.release.assert_called_once()

    def test_failed_native_open_never_leaves_active_bezel_or_modal_crash(self):
        app = self.app()
        app.camera_name = Mock()
        app.camera_name.get.return_value = "Webcam (device 0)"
        app.camera_options = {"Webcam (device 0)": 0}
        with patch("anything_plays.ui_camera.cv2.VideoCapture",
                   side_effect=RuntimeError("driver unexpectedly failed")), \
             patch("anything_plays.ui_camera.messagebox.showerror") as popup:
            app.start_camera()
        self.assertIsNone(app.cap)
        self.assertIsNone(app.frame)
        self.assertIsNone(app.camera_photo)
        self.assertGreaterEqual(app.stop_controls.call_count, 1)
        self.assertEqual(popup.call_count, 1)
        app.camera_bezel.set_active.assert_called_with(False)


if __name__ == "__main__":
    unittest.main()
