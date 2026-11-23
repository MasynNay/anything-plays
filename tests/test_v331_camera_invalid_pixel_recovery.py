"""3.3.1: malformed webcam pixels must enter the safe disconnect/retry path.

No physical camera, permission dialog, game ROM, emulator or device is opened.
Mock OpenCV devices are used to exercise real discovery and Tk tick methods.
"""
import unittest
from unittest.mock import Mock, patch

import numpy as np

from anything_plays import cameras
from anything_plays.ui_gameplay import GameplayMixin


class CameraFrameContractTests(unittest.TestCase):
    def test_normal_bgr_bgra_frames_and_noncontiguous_view_are_usable(self):
        frame = np.zeros((12, 16, 3), dtype=np.uint8)
        bgra = np.zeros((12, 16, 4), dtype=np.uint8)
        self.assertTrue(cameras.usable_bgr_frame(frame))
        self.assertTrue(cameras.usable_bgr_frame(bgra))
        self.assertTrue(cameras.usable_bgr_frame(frame[:, ::2, :]))

    def test_only_nonempty_uint8_bgr_or_bgra_arrays_are_accepted(self):
        invalid = (
            None, object(), Mock(), b"not-pixels", [],
            np.array(7, dtype=np.uint8),
            np.zeros((4, 6), dtype=np.uint8),             # grayscale
            np.zeros((4, 6, 1), dtype=np.uint8),          # one channel
            np.zeros((4, 6, 2), dtype=np.uint8),          # incomplete BGR
            np.zeros((0, 6, 3), dtype=np.uint8),
            np.zeros((4, 0, 3), dtype=np.uint8),
            np.zeros((4, 6, 3), dtype=np.uint16),
            np.zeros((4, 6, 3), dtype=np.float32),
        )
        for frame in invalid:
            with self.subTest(kind=type(frame).__name__,
                              shape=getattr(frame, "shape", None)):
                self.assertFalse(cameras.usable_bgr_frame(frame))

    def test_discovery_does_not_advertise_malformed_first_camera(self):
        malformed = (
            object(),
            np.zeros((4, 6), dtype=np.uint8),
            np.zeros((4, 6, 3), dtype=np.float32),
        )
        for broken_pixels in malformed:
            with self.subTest(kind=type(broken_pixels).__name__,
                              shape=getattr(broken_pixels, "shape", None)):
                bad = Mock()
                bad.isOpened.return_value = True
                bad.read.return_value = True, broken_pixels
                good = Mock()
                good.isOpened.return_value = True
                good.read.return_value = (
                    True, np.zeros((6, 10, 3), dtype=np.uint8),
                )
                opened = []

                def fake_capture(index, backend):
                    opened.append(index)
                    return bad if index == 0 else good

                with (
                    patch.object(cameras.cv2, "VideoCapture",
                                 side_effect=fake_capture),
                    patch.object(cameras, "name_for",
                                 side_effect=lambda index: f"Camera {index}"),
                    patch.object(cameras.platform, "system",
                                 return_value="Linux"),
                    patch.object(cameras.time, "sleep"),
                ):
                    found = cameras.discover(max_index=2)
                self.assertEqual(found, [(1, "Camera 1")])
                self.assertEqual(opened, [0, 0, 0, 1])
                self.assertEqual(bad.release.call_count, 3)
                good.release.assert_called_once()

    def test_discovery_no_valid_pixels_returns_no_camera(self):
        cam = Mock()
        cam.isOpened.return_value = True
        cam.read.return_value = (True, np.zeros((7, 8), dtype=np.uint8))
        with (
            patch.object(cameras.cv2, "VideoCapture", return_value=cam),
            patch.object(cameras.platform, "system", return_value="Linux"),
            patch.object(cameras.time, "sleep"),
        ):
            self.assertEqual(cameras.discover(max_index=1), [])
        self.assertEqual(cam.release.call_count, 3)


class LiveCameraFrameRecoveryTests(unittest.TestCase):
    @staticmethod
    def app_with_frame(pixels, *, mirror=False):
        app = Mock()
        app._closing = False
        app._active_camera_name = "Chosen camera (device 0)"
        app.camera_name.get.return_value = "Chosen camera (device 0)"
        app.cap = Mock()
        app.cap.isOpened.return_value = True
        app.cap.read.return_value = True, pixels
        app.frame = None
        app.reference_image = False
        app.mirror.get.return_value = mirror
        app._pending_object_controls = False
        app.emu.error = None
        app.emu.save_warning = None
        app.emu.audio_warning = None
        app.emu.resume_info = None
        app.emu.running = False
        app.root.after.return_value = "next-camera-tick"

        def simulate_releasing_camera():
            app.stop_controls()
            app.cap = None
            app.frame = None

        app.stop_camera.side_effect = simulate_releasing_camera
        return app

    def test_malformed_live_frame_releases_controls_and_requests_reconnect(self):
        broken = (
            object(),
            np.zeros((9, 10), dtype=np.uint8),
            np.zeros((9, 10, 1), dtype=np.uint8),
            np.zeros((9, 10, 3), dtype=np.uint16),
            np.zeros((9, 10, 3), dtype=np.float32),
            np.zeros((0, 10, 3), dtype=np.uint8),
        )
        for frame in broken:
            with self.subTest(kind=type(frame).__name__,
                              shape=getattr(frame, "shape", None)):
                app = self.app_with_frame(frame)
                GameplayMixin.tick(app)
                app.stop_camera.assert_called_once()
                app.stop_controls.assert_called_once()
                app._queue_camera_retry.assert_called_once_with(
                    "Chosen camera (device 0)"
                )
                app.draw_camera.assert_not_called()
                self.assertIsNone(app.cap)
                self.assertIsNone(app.frame)
                self.assertEqual(app._camera_tick_job, "next-camera-tick")
                # The general outer exception handler used to disarm, stop,
                # and NOT retry after a tracking-format crash.
                self.assertFalse(any(
                    "Tracking error" in str(call)
                    for call in app.status.set.call_args_list
                ))

    def test_invalid_pixels_are_rejected_before_mirror_flip(self):
        app = self.app_with_frame(
            np.zeros((8, 10), dtype=np.uint8), mirror=True,
        )
        with patch("anything_plays.ui_gameplay.cv2.flip") as flip:
            GameplayMixin.tick(app)
        flip.assert_not_called()
        app._queue_camera_retry.assert_called_once()

    def test_valid_live_color_frame_reaches_existing_tracking_pipeline(self):
        frame = np.zeros((8, 10, 3), dtype=np.uint8)
        app = self.app_with_frame(frame)
        GameplayMixin.tick(app)
        self.assertIs(app.frame, frame)
        app.draw_camera.assert_called_once()
        app.stop_camera.assert_not_called()
        app._queue_camera_retry.assert_not_called()
        self.assertEqual(app._camera_tick_job, "next-camera-tick")

    def test_valid_bgra_frame_remains_supported(self):
        frame = np.zeros((8, 10, 4), dtype=np.uint8)
        app = self.app_with_frame(frame)
        GameplayMixin.tick(app)
        self.assertIs(app.frame, frame)
        app.draw_camera.assert_called_once()
        app.stop_camera.assert_not_called()
        app._queue_camera_retry.assert_not_called()


if __name__ == "__main__":
    unittest.main()
