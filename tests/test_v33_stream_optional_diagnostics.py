"""3.3: optional Stream timing must never destroy a healthy OBS picture.

Mocks exercise the actual StreamMixin Tk timer callback, without opening a
webcam, native core, OBS encoder or output window.
"""
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_stream import (
    DEFAULT_STREAM, StreamCadenceTracker, StreamMixin,
)


class StreamOptionalDiagnosticsTests(unittest.TestCase):
    def make_app(self, *, render=True):
        class Harness(StreamMixin):
            pass
        app = Harness()
        app._closing = False
        app._stream_output_window = object()
        app._stream_options = dict(DEFAULT_STREAM)
        app._stream_cadence = StreamCadenceTracker()
        app._stream_canvas = Mock()
        app._stream_photo = object()
        app._stream_canvas_item = 3
        app._stream_last_render = ("old photo",)
        app.root = Mock()
        app._render_stream_frame = Mock(return_value=render)
        return app

    def test_missing_finish_clock_keeps_valid_obs_image_and_normal_refresh(self):
        app = self.make_app()
        photo = app._stream_photo
        with patch("anything_plays.ui_stream.stream_optional_perf_clock",
                   side_effect=(10.0, None)):
            app._stream_render_tick()
        app._render_stream_frame.assert_called_once_with()
        self.assertIs(app._stream_photo, photo)
        app._stream_canvas.delete.assert_not_called()
        app.root.after.assert_called_once_with(42, app._stream_render_tick)
        m = app.stream_performance_snapshot()["metrics"]
        self.assertEqual(m["stream_failed_ticks"], 0)
        self.assertEqual(m["stream_render_samples"], 0)

    def test_reversed_optional_clock_keeps_preview_and_skips_invalid_cost(self):
        app = self.make_app()
        with patch("anything_plays.ui_stream.stream_optional_perf_clock",
                   side_effect=(10.0, 9.0)):
            app._stream_render_tick()
        app._stream_canvas.delete.assert_not_called()
        app.root.after.assert_called_once_with(42, app._stream_render_tick)
        m = app.stream_performance_snapshot()["metrics"]
        self.assertEqual(m["stream_failed_ticks"], 0)
        self.assertEqual(m["stream_render_samples"], 0)

    def test_corrupt_success_collector_does_not_blank_a_published_photo(self):
        app = self.make_app()
        photo = app._stream_photo
        app._stream_cadence.record_tick = Mock(side_effect=OSError(
            "PRIVATE USB serial /Users/owner/camera"
        ))
        with patch("anything_plays.ui_stream.stream_optional_perf_clock",
                   side_effect=(10.0, 10.01)):
            app._stream_render_tick()
        app._stream_canvas.delete.assert_not_called()
        self.assertIs(app._stream_photo, photo)
        self.assertIsNone(app._stream_cadence)
        self.assertEqual(getattr(app, "_stream_session_faults", 0), 0)
        app.root.after.assert_called_once_with(32, app._stream_render_tick)
        self.assertIsNone(app.stream_performance_snapshot())

    def test_failed_canvas_still_blanks_and_retries_if_counter_throws(self):
        app = self.make_app()
        app._render_stream_frame.side_effect = ValueError(
            "PRIVATE /home/user/device"
        )
        app._stream_cadence.record_tick = Mock(side_effect=RuntimeError(
            "PRIVATE instrumentation failure"
        ))
        with patch("anything_plays.ui_stream.stream_optional_perf_clock",
                   side_effect=(10.0, 10.01)):
            app._stream_render_tick()
        self.assertIsNone(app._stream_photo)
        self.assertIsNone(app._stream_canvas_item)
        self.assertIsNone(app._stream_cadence)
        app._stream_canvas.delete.assert_called_once_with("all")
        app.root.after.assert_called_once_with(1000, app._stream_render_tick)
        self.assertEqual(app._stream_session_faults, 1)
        self.assertTrue(app._stream_recovery_pending)

    def test_corrupt_snapshot_is_optional_and_preserves_active_capture(self):
        app = self.make_app()
        app._stream_cadence.snapshot = Mock(
            side_effect=OSError("PRIVATE /Users/owner/game.iso")
        )
        self.assertIsNone(app.stream_performance_snapshot())
        app._stream_cadence.snapshot = Mock(return_value=["PRIVATE"])
        self.assertIsNone(app.stream_performance_snapshot())
        self.assertIsNotNone(app._stream_photo)
        app._stream_canvas.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
