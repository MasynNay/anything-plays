"""Optional GameCube perf_counter errors must not break real native loops.

The tests exercise CoreSession.run against a fake native ABI and intentionally
bad instrumentation, not against a physical game or driver.
"""
import math
from pathlib import Path
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from anything_plays.gamecube_native_timing import GameCubeNativeTiming
from anything_plays.gba_emulator import CoreSession, _optional_gamecube_perf_clock
from anything_plays.ui_setup_diagnostics import _gamecube_performance_summary_lines


def make_session(tmp, stop, *, timing=None):
    core = Path(tmp) / "synthetic-dolphin-libretro.so"
    core.write_bytes(b"synthetic native ABI bytes")
    rom = Path(tmp) / "homebrew-test.dol"
    rom.write_bytes(b"synthetic noncommercial ROM placeholder")
    session = object.__new__(CoreSession)
    session.system = "gamecube"
    session.rom = rom
    session.core_path = str(core)
    session._load_game = Mock()
    session.persist_game_progress = Mock()
    session.audio = Mock(output_error=None)
    session.save_ram = None
    session.enable_state_resume = False
    session.native_run_timing = timing if timing is not None else GameCubeNativeTiming()
    session.emulator = SimpleNamespace(
        inputs=Mock(system="gamecube"), stop_event=stop,
        armed=True, running=False, launching=True, audio_sink=None,
        audio_warning=None, save_warning=None,
    )
    core = MagicMock()
    core.av_info = Mock()
    core.memory_data = Mock(return_value=None)
    core.memory_size = Mock(return_value=0)
    return session, core


class OptionalGameCubeClockTests(unittest.TestCase):
    def test_optional_perf_clock_rejects_native_errors_and_bad_values(self):
        for raw in (None, True, False, "private /home/user", {},
                    [], -1.0, float("nan"), float("inf"),
                    float("-inf"), 10**1000):
            with self.subTest(type=type(raw).__name__):
                with patch("anything_plays.gba_emulator.time.perf_counter",
                           return_value=raw):
                    self.assertIsNone(_optional_gamecube_perf_clock())
        with patch("anything_plays.gba_emulator.time.perf_counter",
                   side_effect=OSError("native driver /Users/owner/secret")):
            self.assertIsNone(_optional_gamecube_perf_clock())
        with patch("anything_plays.gba_emulator.time.perf_counter",
                   return_value=123.456):
            self.assertEqual(_optional_gamecube_perf_clock(), 123.456)

    def test_real_core_loop_keeps_running_when_optional_clock_always_throws(self):
        with tempfile.TemporaryDirectory() as tmp:
            stop = threading.Event()
            timing = GameCubeNativeTiming()
            session, fake = make_session(tmp, stop, timing=timing)
            frames = []
            def advance():
                frames.append(1)
                if len(frames) == 4:
                    stop.set()
            fake.run.side_effect = advance
            with (
                patch("anything_plays.gba_emulator.NativeCore", return_value=fake),
                patch("anything_plays.gba_emulator.SaveRAM"),
                patch("anything_plays.gba_emulator.time.perf_counter",
                      side_effect=OSError("GPU private /home/user/serial")),
            ):
                session.run()
            self.assertEqual(len(frames), 4)
            self.assertEqual(fake.run.call_count, 4)
            self.assertEqual(session.emulator.inputs.before_frame.call_count, 4)
            self.assertEqual(session.emulator.inputs.after_frame.call_count, 4)
            self.assertEqual(timing.native_run_calls, 0)
            self.assertEqual(timing.scheduler_wait_calls, 0)
            self.assertGreater(timing.reported_core_fps, 20)
            self.assertFalse(session.emulator.launching)
            self.assertIsNone(session.emulator.audio_sink)
            fake.close.assert_called_once()
            session.audio.close.assert_called_once()

    def test_real_loop_recovers_timing_after_missing_and_reversed_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            stop = threading.Event()
            timing = GameCubeNativeTiming()
            session, fake = make_session(tmp, stop, timing=timing)
            virtual = [0.0]
            frames = []
            def advance():
                frames.append(1)
                virtual[0] += 0.040
                if len(frames) == 5:
                    stop.set()
            fake.run.side_effect = advance
            # Frame 1: missing start. Frame 2: valid 4ms sample.
            # Frame 3: reversed clock. Frame 4: valid 6ms sample.
            # Frame 5: missing end. Every native frame still executes.
            timestamps = iter((None, 1.000, 1.004, 2.000, 1.999,
                               3.000, 3.006, 4.000, None))
            with (
                patch("anything_plays.gba_emulator.NativeCore", return_value=fake),
                patch("anything_plays.gba_emulator.SaveRAM"),
                patch("anything_plays.gba_emulator.time.monotonic",
                      side_effect=lambda: virtual[0]),
                patch("anything_plays.gba_emulator._optional_gamecube_perf_clock",
                      side_effect=lambda: next(timestamps)),
            ):
                session.run()
            self.assertEqual(fake.run.call_count, 5)
            self.assertEqual(session.emulator.inputs.after_frame.call_count, 5)
            self.assertEqual(timing.native_run_calls, 2)
            self.assertAlmostEqual(timing.native_run_total_seconds, 0.010)
            self.assertEqual(timing.scheduler_wait_calls, 0)
            fake.close.assert_called_once()

    def test_setup_panel_does_not_confuse_missing_clock_with_stopped_game(self):
        lines = _gamecube_performance_summary_lines(
            {"metrics": {"native_run_calls": 0}}
        )
        self.assertEqual(len(lines), 1)
        self.assertIn("No valid GameCube native timing samples", lines[0])
        self.assertIn("gameplay may still be running", lines[0])
        self.assertNotIn("has not completed", lines[0])


if __name__ == "__main__":
    unittest.main()
