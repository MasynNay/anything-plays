"""Regression: Stream Mode Stop/Close always retires OBS pixels.

These tests inject platform-adapter errors. They never open an actual
camera, emulator, Tk screen, user game, or OBS capture session.
"""
import unittest
from unittest.mock import Mock, call, patch

from PIL import Image

from anything_plays.ui_stream import (
    DEFAULT_STREAM, StreamMixin, StreamPanelResizeCache,
)
from anything_plays.ui_theme import ThemeMixin


class StreamCloseFailureIsolationTests(unittest.TestCase):
    def make_app(self):
        class Harness(StreamMixin):
            THEMES = ThemeMixin.THEMES

        app = Harness()
        app.theme_name = Mock()
        app.theme_name.get.return_value = "Dark"
        app.initialize_stream_mode({})
        app.root = Mock()
        app.save_preferences = Mock()
        app._closing = False
        app._stream_output_window = Mock()
        app._stream_controls_window = Mock()
        app._stream_canvas = Mock()
        app._stream_frame_job = "frame-task"
        app._stream_save_job = "save-task"
        app._stream_photo = object()
        app._stream_camera_frame = Image.new("RGB", (8, 8), "red")
        app._stream_game_frame = Image.new("RGB", (8, 8), "blue")
        app._stream_game_serial = 3
        app._stream_last_render = ("cached view",)
        app._stream_resize_cache = StreamPanelResizeCache()
        app._stream_resize_cache.contained(
            "CAMERA", app._stream_camera_frame, (0, 0, 10, 10),
        )
        app._stream_resize_cache.contained(
            "GAME", app._stream_game_frame, (0, 0, 10, 10),
        )
        app._stream_recovery_pending = True
        return app

    def assert_capture_retired(self, app, *, output, canvas, cache):
        self.assertIsNone(app._stream_output_window)
        self.assertIsNone(app._stream_controls_window)
        self.assertIsNone(app._stream_canvas)
        self.assertIsNone(app._stream_photo)
        self.assertIsNone(app._stream_frame_job)
        self.assertIsNone(app._stream_save_job)
        self.assertIsNone(app._stream_game_frame)
        self.assertIsNone(app._stream_camera_frame)
        self.assertIsNone(app._stream_last_render)
        self.assertIsNone(app._stream_resize_cache)
        self.assertFalse(app._stream_recovery_pending)
        self.assertEqual(cache._entries, {})
        canvas.delete.assert_called_once_with("all")
        output.destroy.assert_called_once_with()

    def test_frame_and_save_timer_adapter_exceptions_do_not_abort_close(self):
        app = self.make_app()
        output, canvas, cache = (
            app._stream_output_window, app._stream_canvas, app._stream_resize_cache,
        )
        app.root.after_cancel.side_effect = [
            OSError("private camera path"), ValueError("private ROM path"),
        ]
        app.close_stream_mode()
        self.assertEqual(
            app.root.after_cancel.call_args_list,
            [call("frame-task"), call("save-task")],
        )
        app.save_preferences.assert_called_once()
        self.assert_capture_retired(app, output=output, canvas=canvas, cache=cache)

    def test_unexpected_preferences_and_controls_destroy_exceptions_are_isolated(self):
        app = self.make_app()
        output, canvas, cache = (
            app._stream_output_window, app._stream_canvas, app._stream_resize_cache,
        )
        app.save_preferences.side_effect = RuntimeError("secret config path")
        app._stream_controls_window.destroy.side_effect = AssertionError(
            "private active controller name"
        )
        app.close_stream_mode()
        self.assert_capture_retired(app, output=output, canvas=canvas, cache=cache)

    def test_output_destroy_failure_does_not_keep_cached_private_images(self):
        app = self.make_app()
        output, canvas, cache = (
            app._stream_output_window, app._stream_canvas, app._stream_resize_cache,
        )
        output.destroy.side_effect = OSError("private OBS capture source")
        app.close_stream_mode()
        self.assert_capture_retired(app, output=output, canvas=canvas, cache=cache)
        # Repeat Close is safe after a failed native Tk destruction.
        app.close_stream_mode()
        self.assertIsNone(app._stream_photo)

    def test_canvas_blank_failure_still_retires_all_image_references(self):
        app = self.make_app()
        output, canvas, cache = (
            app._stream_output_window, app._stream_canvas, app._stream_resize_cache,
        )
        canvas.delete.side_effect = RuntimeError("destroyed Tk canvas")
        app.close_stream_mode()
        self.assert_capture_retired(app, output=output, canvas=canvas, cache=cache)

    def test_frame_schedule_exception_closes_capture_without_leaving_photo(self):
        app = self.make_app()
        app._stream_frame_job = None
        output, canvas, cache = (
            app._stream_output_window, app._stream_canvas, app._stream_resize_cache,
        )
        app._render_stream_frame = Mock(return_value=True)
        app.root.after.side_effect = OSError("private USB camera location")
        with patch("anything_plays.ui_stream.stream_optional_perf_clock",
                   side_effect=[10.0, 10.002]):
            app._stream_render_tick()
        self.assert_capture_retired(app, output=output, canvas=canvas, cache=cache)
        app.root.after.assert_called_once()
        self.assertIsNone(app._stream_cadence)

    def test_unrelated_app_input_is_untouched_by_stream_close(self):
        app = self.make_app()
        app.emu = Mock()
        app.cap = Mock()
        camera, emu = app.cap, app.emu
        app.close_stream_mode()
        self.assertIs(app.cap, camera)
        self.assertIs(app.emu, emu)
        camera.release.assert_not_called()
        emu.stop.assert_not_called()
        emu.stop_event.set.assert_not_called()


if __name__ == "__main__":
    unittest.main()
