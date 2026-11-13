"""3.1.1: native webcam faults must not escape the arm button or kill Tk ticks.

No webcam, GUI window or real game is needed. Captures simulate USB errors.
"""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_camera import CameraMixin
from anything_plays.ui_gameplay import GameplayMixin


class CameraUIHarness(CameraMixin, GameplayMixin):
    def __init__(self):
        self._closing = False
        self.root = Mock()
        self.root.after.side_effect = lambda ms, fn: f"timer-{ms}"
        self.emu = Mock()
        self.emu.error = None
        self.emu.save_warning = None
        self.emu.audio_warning = None
        self.emu.resume_info = None
        self.emu.running = False
        self.armed = False
        self.external_input = None
        self.system_key = Mock()
        self.system_key.get.return_value = "gba"
        self.uses_embedded_emulator = lambda: True
        self.cap = Mock()
        self.frame = None
        self.camera_photo = object()
        self.reference_image = False
        self.camera_name = Mock()
        self.camera_name.get.return_value = "Webcam (device 0)"
        self.camera_options = {"Webcam (device 0)": 0}
        self.camera_bezel = Mock()
        self.canvas = Mock()
        self.status = Mock()
        self.game_status = Mock()
        self._camera_reconnect_job = None
        self._camera_reconnect_attempts = 0
        self._camera_reconnect_name = None
        self.stream_clear_camera = Mock()
        self.stop_controls = Mock()


class NativeCameraStatusTests(unittest.TestCase):
    def test_arm_button_reports_missing_camera_when_native_status_throws(self):
        for failure in (OSError("USB unplugged"), RuntimeError("driver error")):
            with self.subTest(failure=str(failure)):
                app = CameraUIHarness()
                app.cap.isOpened.side_effect = failure
                with patch("anything_plays.ui_gameplay.messagebox.showinfo") as popup:
                    app.toggle()
                popup.assert_called_once()
                self.assertEqual(popup.call_args.args[0], "Camera required")
                self.assertFalse(app.armed)
                app.emu.set_camera_buttons.assert_not_called()

    def test_camera_poll_recovers_and_reschedules_after_isopened_driver_error(self):
        app = CameraUIHarness()
        old = app.cap
        old.isOpened.side_effect = RuntimeError("webcam unplugged")
        old.release.side_effect = OSError("driver removed before close")
        app.tick()

        self.assertIsNone(app.cap)
        self.assertIsNone(app.frame)
        self.assertIsNone(app.camera_photo)
        self.assertEqual(old.release.call_count, 1)
        self.assertEqual(app.stop_controls.call_count, 1)
        app.camera_bezel.set_active.assert_called_once_with(False)
        app.stream_clear_camera.assert_called_once()
        scheduled_delays = [call.args[0] for call in app.root.after.call_args_list]
        self.assertIn(2000, scheduled_delays, "camera retry is bounded")
        self.assertIn(200, scheduled_delays, "main Tk tick remains alive")
        self.assertEqual(len(scheduled_delays), 2)

    def test_safe_camera_status_does_not_mask_a_healthy_camera(self):
        app = CameraUIHarness()
        app.cap.isOpened.return_value = True
        self.assertTrue(app._camera_is_open())
        app.cap.isOpened.return_value = False
        self.assertFalse(app._camera_is_open())
        app.cap = None
        self.assertFalse(app._camera_is_open())


if __name__ == "__main__":
    unittest.main()
