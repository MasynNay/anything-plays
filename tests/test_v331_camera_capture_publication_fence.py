"""3.3.1: stale native camera results cannot cross a Stop/reconnect boundary.

All pixels and camera handles are synthetic. No webcam, ROM, game controller,
GUI display, native recording or private camera image is opened.
"""
import unittest
from unittest.mock import Mock, patch

import numpy as np

from anything_plays.ui_gameplay import GameplayMixin


class CameraPublicationFenceTests(unittest.TestCase):
    @staticmethod
    def app(*, mirror=False):
        app = Mock()
        app._closing = False
        app._active_camera_name = "USB webcam (device 0)"
        app.camera_name.get.return_value = app._active_camera_name
        app.cap = Mock()
        app.cap.isOpened.return_value = True
        app.frame = None
        app.reference_image = False
        app.mirror.get.return_value = mirror
        app._pending_object_controls = False
        app.emu.running = False
        app.emu.error = None
        app.emu.save_warning = None
        app.emu.audio_warning = None
        app.emu.resume_info = None
        app.root.after.return_value = "next-tick"

        def stop():
            app.stop_controls()
            app.cap = None
            app.frame = None

        app.stop_camera.side_effect = stop
        return app

    @staticmethod
    def pixels(*, channels=3):
        return np.full((8, 12, channels), 137, dtype=np.uint8)

    def test_old_success_cannot_replace_new_camera_pixels(self):
        app = self.app()
        old = app.cap
        replacement = Mock()
        replacement.isOpened.return_value = True
        latest = self.pixels()
        latest[0, 0, 0] = 210

        def replace_during_read():
            app.cap = replacement
            app.frame = latest
            return True, self.pixels()

        old.read.side_effect = replace_during_read
        GameplayMixin.tick(app)
        self.assertIs(app.cap, replacement)
        self.assertIs(app.frame, latest)
        app.stop_camera.assert_not_called()
        app._queue_camera_retry.assert_not_called()
        app.draw_camera.assert_called_once()
        old.release.assert_not_called()
        replacement.release.assert_not_called()

    def test_old_failed_read_cannot_stop_new_active_camera(self):
        app = self.app()
        old = app.cap
        replacement = Mock()
        replacement.isOpened.return_value = True
        latest = self.pixels()

        def replace_and_fail():
            app.cap = replacement
            app.frame = latest
            raise OSError("PRIVATE retired USB device /dev/video0")

        old.read.side_effect = replace_and_fail
        GameplayMixin.tick(app)
        self.assertIs(app.cap, replacement)
        self.assertIs(app.frame, latest)
        app.stop_camera.assert_not_called()
        app.stop_controls.assert_not_called()
        app._queue_camera_retry.assert_not_called()
        app.draw_camera.assert_called_once()

    def test_old_failed_mirror_cannot_stop_new_active_camera(self):
        app = self.app(mirror=True)
        old = app.cap
        old.read.return_value = (True, self.pixels())
        replacement = Mock()
        replacement.isOpened.return_value = True
        latest = self.pixels(channels=4)

        def replace_and_fail(_frame, _flip_code):
            app.cap = replacement
            app.frame = latest
            raise RuntimeError("PRIVATE old camera mirror fault")

        with patch("anything_plays.ui_gameplay.cv2.flip",
                   side_effect=replace_and_fail):
            GameplayMixin.tick(app)
        self.assertIs(app.cap, replacement)
        self.assertIs(app.frame, latest)
        app.stop_camera.assert_not_called()
        app._queue_camera_retry.assert_not_called()
        app.draw_camera.assert_called_once()

    def test_explicit_stop_during_old_read_does_not_schedule_reconnect(self):
        app = self.app()
        old = app.cap

        def stop_during_read():
            app.stop_camera()
            return True, self.pixels()

        old.read.side_effect = stop_during_read
        GameplayMixin.tick(app)
        self.assertIsNone(app.cap)
        self.assertIsNone(app.frame)
        app.stop_camera.assert_called_once()
        app.stop_controls.assert_called_once()
        app._queue_camera_retry.assert_not_called()
        app.draw_camera.assert_not_called()
        self.assertEqual(app._camera_tick_job, "next-tick")

    def test_shutdown_during_old_read_drops_pixels_and_does_not_reschedule(self):
        app = self.app()
        old = app.cap

        def close_during_read():
            app._closing = True
            return True, self.pixels()

        old.read.side_effect = close_during_read
        GameplayMixin.tick(app)
        self.assertIsNone(app.frame)
        app.draw_camera.assert_not_called()
        app.stop_camera.assert_not_called()
        app._queue_camera_retry.assert_not_called()
        app.root.after.assert_not_called()

    def test_successful_native_mirror_returning_none_uses_safe_reconnect(self):
        app = self.app(mirror=True)
        old = app.cap
        old.read.return_value = (True, self.pixels())
        with patch("anything_plays.ui_gameplay.cv2.flip", return_value=None):
            GameplayMixin.tick(app)
        app.stop_camera.assert_called_once()
        app.stop_controls.assert_called_once()
        app._queue_camera_retry.assert_called_once_with(
            "USB webcam (device 0)"
        )
        self.assertIsNone(app.frame)
        app.draw_camera.assert_not_called()
        self.assertEqual(app._camera_tick_job, "next-tick")

    def test_native_mirror_returning_wrong_channels_or_dtype_retries(self):
        invalid = (
            np.zeros((8, 12), dtype=np.uint8),
            np.zeros((8, 12, 2), dtype=np.uint8),
            np.zeros((8, 12, 3), dtype=np.float32),
            np.zeros((0, 12, 3), dtype=np.uint8),
            object(),
        )
        for result in invalid:
            with self.subTest(kind=type(result).__name__,
                              shape=getattr(result, "shape", None)):
                app = self.app(mirror=True)
                app.cap.read.return_value = (True, self.pixels())
                with patch("anything_plays.ui_gameplay.cv2.flip",
                           return_value=result):
                    GameplayMixin.tick(app)
                app.stop_camera.assert_called_once()
                app._queue_camera_retry.assert_called_once()
                app.draw_camera.assert_not_called()

    def test_normal_mirrored_bgr_bgra_frames_still_track(self):
        for channels in (3, 4):
            with self.subTest(channels=channels):
                app = self.app(mirror=True)
                original = self.pixels(channels=channels)
                mirrored = original[:, ::-1, :].copy()
                app.cap.read.return_value = (True, original)
                with patch("anything_plays.ui_gameplay.cv2.flip",
                           return_value=mirrored) as flip:
                    GameplayMixin.tick(app)
                flip.assert_called_once_with(original, 1)
                self.assertIs(app.frame, mirrored)
                app.draw_camera.assert_called_once()
                app.stop_camera.assert_not_called()
                app._queue_camera_retry.assert_not_called()
                self.assertEqual(app._camera_tick_job, "next-tick")

    def test_normal_unmirrored_frame_keeps_existing_tracking_path(self):
        app = self.app()
        frame = self.pixels()
        app.cap.read.return_value = (True, frame)
        with patch("anything_plays.ui_gameplay.cv2.flip") as flip:
            GameplayMixin.tick(app)
        flip.assert_not_called()
        self.assertIs(app.frame, frame)
        app.draw_camera.assert_called_once()
        app.stop_camera.assert_not_called()
        app._queue_camera_retry.assert_not_called()


if __name__ == "__main__":
    unittest.main()
