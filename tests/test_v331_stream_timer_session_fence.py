"""3.3.1: late OBS refresh callbacks belong only to their original window.

All Tk timers/windows, images and native game devices are synthetic. No webcam,
ROM, emulator, OBS recorder, keyboard input or personal configuration is used.
"""
import unittest
from unittest.mock import Mock

from PIL import Image

from anything_plays.ui_stream import DEFAULT_STREAM, StreamMixin


class Host(StreamMixin):
    def __init__(self):
        self._closing = False
        self._stream_output_window = Mock()
        self._stream_canvas = Mock()
        self._stream_controls_window = None
        self._stream_options = dict(DEFAULT_STREAM)
        self._stream_last_render = object()
        self._stream_photo = object()
        self._stream_canvas_item = 7
        self._stream_camera_frame = Image.new("RGB", (6, 6), "red")
        self._stream_game_frame = Image.new("RGB", (6, 6), "blue")
        self._stream_frame_job = None
        self._stream_save_job = None
        self._stream_resize_cache = None
        self._stream_camera_last_snapshot = None
        self._stream_camera_force_next_snapshot = False
        self._stream_cadence = None
        self.root = Mock()
        self.callbacks = []
        self._render_stream_frame = Mock(return_value=False)
        self._stream_update_diagnostic = Mock()
        self.save_preferences = Mock()

        def schedule(_delay, callback):
            self.callbacks.append(callback)
            return f"stream-timer-{len(self.callbacks)}"

        self.root.after.side_effect = schedule

    def schedule_one(self):
        self._stream_render_tick()
        return self.callbacks[-1]


class StreamTimerSessionTests(unittest.TestCase):
    def test_old_queued_tick_after_reopen_cannot_read_or_mutate_new_output(self):
        app = Host()
        old_callback = app.schedule_one()
        old_window = app._stream_output_window
        app._render_stream_frame.reset_mock()
        app.root.after.reset_mock()
        app._stream_output_window = Mock()
        app._stream_frame_job = "live-new-session-timer"
        new_photo = object()
        app._stream_photo = new_photo
        old_callback()
        self.assertIs(app._stream_photo, new_photo)
        self.assertEqual(app._stream_frame_job, "live-new-session-timer")
        app._render_stream_frame.assert_not_called()
        app.root.after.assert_not_called()
        old_window.destroy.assert_not_called()

    def test_old_queued_tick_after_close_does_not_reschedule(self):
        app = Host()
        old_callback = app.schedule_one()
        app.close_stream_mode()
        app._render_stream_frame.reset_mock()
        app.root.after.reset_mock()
        old_callback()
        app._render_stream_frame.assert_not_called()
        app.root.after.assert_not_called()
        self.assertIsNone(app._stream_photo)
        self.assertIsNone(app._stream_output_window)

    def test_live_timer_still_polls_and_rearms_at_selected_rate(self):
        app = Host()
        callback = app.schedule_one()
        self.assertEqual(app._stream_frame_job, "stream-timer-1")
        app._render_stream_frame.reset_mock()
        callback()
        app._render_stream_frame.assert_called_once()
        self.assertEqual(len(app.callbacks), 2)
        self.assertEqual(app._stream_frame_job, "stream-timer-2")
        self.assertEqual(app.root.after.call_args.args[0], 42)

    def test_missing_cancelable_tk_timer_closes_output_and_releases_pixels(self):
        app = Host()
        output = app._stream_output_window
        canvas = app._stream_canvas
        app.root.after.side_effect = lambda ms, callback: None
        app._stream_render_tick()
        self.assertIsNone(app._stream_output_window)
        self.assertIsNone(app._stream_photo)
        self.assertIsNone(app._stream_camera_frame)
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_frame_job)
        canvas.delete.assert_called_with("all")
        output.destroy.assert_called_once()

    def test_no_timer_id_and_old_callback_cannot_touch_reopened_output(self):
        app = Host()
        captured = []

        def faulty_after(ms, callback):
            captured.append(callback)
            return None

        app.root.after.side_effect = faulty_after
        app._stream_render_tick()
        self.assertIsNone(app._stream_output_window)
        app._stream_output_window = Mock()
        app._stream_photo = object()
        app._stream_frame_job = "new-owned-job"
        app.root.after.reset_mock()
        app._render_stream_frame.reset_mock()
        captured[0]()
        self.assertEqual(app._stream_frame_job, "new-owned-job")
        self.assertIsNotNone(app._stream_photo)
        app._render_stream_frame.assert_not_called()
        app.root.after.assert_not_called()

    def test_reentrant_scheduler_does_not_overwrite_new_window_job(self):
        app = Host()
        old = app._stream_output_window
        new = Mock()

        def switch_inside_after(ms, callback):
            app._stream_output_window = new
            app._stream_frame_job = "already-owned-new-window-job"
            return "obsolete-old-window-job"

        app.root.after.side_effect = switch_inside_after
        app._stream_render_tick()
        self.assertEqual(app._stream_frame_job,
                         "already-owned-new-window-job")
        self.assertIs(app._stream_output_window, new)
        app.root.after_cancel.assert_called_once_with(
            "obsolete-old-window-job"
        )
        new.destroy.assert_not_called()
        old.destroy.assert_not_called()

    def test_reentrant_scheduler_exception_cannot_close_new_window(self):
        app = Host()
        new = Mock()

        def reopen_and_raise(ms, callback):
            app._stream_output_window = new
            app._stream_frame_job = "new-stream-job"
            raise RuntimeError("PRIVATE driver /Users/owner/camera")

        app.root.after.side_effect = reopen_and_raise
        app._stream_render_tick()
        self.assertIs(app._stream_output_window, new)
        self.assertEqual(app._stream_frame_job, "new-stream-job")
        new.destroy.assert_not_called()

    def test_old_callback_after_failed_after_cancel_is_still_fenced(self):
        app = Host()
        stale = app.schedule_one()
        app.root.after_cancel.side_effect = OSError(
            "PRIVATE stale Tcl handle /home/person"
        )
        app.close_stream_mode()
        new = Mock()
        app._stream_output_window = new
        app._stream_frame_job = "new-job"
        app._render_stream_frame.reset_mock()
        stale()
        self.assertEqual(app._stream_frame_job, "new-job")
        app._render_stream_frame.assert_not_called()
        new.destroy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
