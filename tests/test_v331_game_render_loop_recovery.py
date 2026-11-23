"""3.3.1 game-video Tk timer survives invalid clocks and widget faults.

No native ROM, webcam, gamepad or actual Tk window is used. Every display
callback is a lightweight mocked facade around the real GameplayMixin.
"""
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_gameplay import (
    GameplayMixin, optional_game_render_clock,
)


class RenderHarness(GameplayMixin):
    def __init__(self):
        self._closing = False
        self.root = Mock()
        self.root.after.return_value = "next-render-tick"
        self.emu = Mock()
        self.emu.running = True
        self.emu.gamecube_preview_mode = "Balanced (30 FPS)"
        self.system_key = Mock()
        self.system_key.get.return_value = "gba"
        self.game_status = Mock()
        self.draw_game = Mock()
        self._game_tick_job = None
        self._game_render_last_clock = None
        self._game_render_retry_at = 0
        self._game_render_warning_at = 0


class GameRenderLoopRecoveryTests(unittest.TestCase):
    def test_normal_active_emulator_repaints_at_existing_fast_rate(self):
        app = RenderHarness()
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   return_value=123.0) as clock:
            app.game_render_tick()
        clock.assert_called_once()
        app.draw_game.assert_called_once()
        app.root.after.assert_called_once_with(16, app.game_render_tick)
        self.assertEqual(app._game_tick_job, "next-render-tick")

    def test_idle_emulator_keeps_slow_poll(self):
        app = RenderHarness()
        app.emu.running = False
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   return_value=123.0):
            app.game_render_tick()
        app.root.after.assert_called_once_with(250, app.game_render_tick)

    def test_gamecube_preview_frame_rates_are_preserved(self):
        for mode, interval in (
            ("Performance (20 FPS)", 50),
            ("Balanced (30 FPS)", 33),
            ("Quality (60 FPS)", 17),
        ):
            with self.subTest(mode=mode):
                app = RenderHarness()
                app.system_key.get.return_value = "gamecube"
                app.emu.gamecube_preview_mode = mode
                with patch("anything_plays.ui_gameplay.time.monotonic",
                           return_value=123.0):
                    app.game_render_tick()
                app.draw_game.assert_called_once()
                app.root.after.assert_called_once_with(
                    interval, app.game_render_tick,
                )

    def test_invalid_timestamps_skip_unsafe_draw_but_reschedule(self):
        for value in (None, True, "123", -1, float("nan"),
                      float("inf"), float("-inf"), 10**13):
            with self.subTest(value=str(value)):
                app = RenderHarness()
                with patch("anything_plays.ui_gameplay.time.monotonic",
                           return_value=value):
                    app.game_render_tick()
                app.draw_game.assert_not_called()
                app.root.after.assert_called_once_with(
                    250, app.game_render_tick,
                )
                self.assertEqual(app._game_tick_job, "next-render-tick")
                self.assertIsNone(app._game_render_last_clock)

    def test_platform_clock_exception_does_not_destroy_render_timer(self):
        app = RenderHarness()
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   side_effect=OSError("PRIVATE native clock fault")):
            app.game_render_tick()
        app.draw_game.assert_not_called()
        app.root.after.assert_called_once_with(250, app.game_render_tick)

    def test_render_recovers_on_next_valid_timestamp(self):
        app = RenderHarness()
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   side_effect=[float("nan"), 42.0]):
            app.game_render_tick()
            app.game_render_tick()
        app.draw_game.assert_called_once()
        self.assertEqual(
            [call.args[0] for call in app.root.after.call_args_list],
            [250, 16],
        )
        self.assertEqual(app._game_render_last_clock, 42.0)

    def test_clock_rollback_invalidates_old_render_retry_deadlines(self):
        app = RenderHarness()
        app._game_render_last_clock = 990.0
        app._game_render_retry_at = 1000.0
        app._game_render_warning_at = 1200.0
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   return_value=12.0):
            app.game_render_tick()
        app.draw_game.assert_called_once()
        self.assertEqual(app._game_render_retry_at, 0)
        self.assertEqual(app._game_render_warning_at, 0)
        self.assertEqual(app._game_render_last_clock, 12.0)

    def test_normal_error_backoff_prevents_repeated_render_crashes(self):
        app = RenderHarness()
        app.draw_game.side_effect = RuntimeError("PRIVATE GPU path /Users/home")
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   side_effect=[20.0, 20.1, 22.1]):
            app.game_render_tick()
            app.game_render_tick()
            app.game_render_tick()
        self.assertEqual(app.draw_game.call_count, 2)
        self.assertEqual(app._game_render_retry_at, 24.1)
        self.assertEqual(app.game_status.set.call_count, 1)
        status = app.game_status.set.call_args.args[0]
        self.assertIn("Display error", status)
        self.assertIn("RuntimeError", status)
        self.assertNotIn("PRIVATE", status)
        self.assertNotIn("/Users/", status)
        self.assertEqual(app.root.after.call_count, 3)

    def test_destroyed_status_variable_cannot_end_repaint_timer(self):
        app = RenderHarness()
        app.draw_game.side_effect = ValueError("PRIVATE video metadata")
        app.game_status.set.side_effect = RuntimeError("Tk label gone")
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   return_value=30.0):
            app.game_render_tick()
        app.game_status.set.assert_called_once()
        app.root.after.assert_called_once_with(16, app.game_render_tick)

    def test_tk_error_only_pauses_render_for_half_second(self):
        app = RenderHarness()
        app.draw_game.side_effect = tk.TclError("lost game canvas")
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   return_value=50.0):
            app.game_render_tick()
        self.assertEqual(app._game_render_retry_at, 50.5)
        app.game_status.set.assert_not_called()
        app.root.after.assert_called_once_with(16, app.game_render_tick)

    def test_transient_console_status_error_uses_low_cost_retry(self):
        app = RenderHarness()
        app.system_key.get.side_effect = OSError("Tk combobox missing")
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   return_value=42.0):
            app.game_render_tick()
        app.draw_game.assert_called_once()
        app.root.after.assert_called_once_with(250, app.game_render_tick)

    def test_tk_scheduler_failure_does_not_escape_render_callback(self):
        app = RenderHarness()
        app.root.after.side_effect = tk.TclError("destroyed root")
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   return_value=42.0):
            app.game_render_tick()
        app.draw_game.assert_called_once()
        app.root.after.assert_called_once()
        self.assertIsNone(app._game_tick_job)

    def test_stop_during_draw_does_not_schedule_another_frame(self):
        app = RenderHarness()
        app.draw_game.side_effect = lambda: setattr(app, "_closing", True)
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   return_value=42.0):
            app.game_render_tick()
        app.draw_game.assert_called_once()
        app.root.after.assert_not_called()

    def test_closed_window_does_not_sample_clock_or_draw(self):
        app = RenderHarness()
        app._closing = True
        with patch("anything_plays.ui_gameplay.time.monotonic") as clock:
            app.game_render_tick()
        clock.assert_not_called()
        app.draw_game.assert_not_called()
        app.root.after.assert_not_called()

    def test_invalid_clock_helper_returns_none_for_faulty_extension(self):
        with patch("anything_plays.ui_gameplay.time.monotonic",
                   side_effect=Exception("vendor GPU clock")):
            self.assertIsNone(optional_game_render_clock())


if __name__ == "__main__":
    unittest.main()
