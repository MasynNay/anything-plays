"""GameCube scheduling-clock faults must not stall or spin native playback.

Exercises the actual CoreSession.run loop with a fake native core and
stop-event. No ROM emulator, Dolphin, GPU, speaker, real clock, or camera.
"""
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from anything_plays.gamecube_native_timing import GameCubeNativeTiming
from anything_plays.ui_setup_diagnostics import _gamecube_performance_summary_lines


class StopClock:
    def __init__(self):
        self.done = False
        self.waits = []

    def is_set(self):
        return self.done

    def set(self):
        self.done = True

    def wait(self, interval):
        self.waits.append(interval)
        return self.done


def simulated_worker(clock_values, *, system="gamecube", count=5):
    """Return counters from CoreSession.run without any native DLL."""
    from anything_plays.gba_emulator import CoreSession

    values = iter(clock_values)
    def clock():
        value = next(values)
        if isinstance(value, Exception):
            raise value
        return value

    with tempfile.TemporaryDirectory() as td:
        filename = Path(td) / "synthetic-core.so"
        filename.write_bytes(b"synthetic-only")
        sess = object.__new__(CoreSession)
        sess.system = system
        sess.rom = Path(td) / "sample-homebrew.dol"
        sess.rom.write_bytes(b"synthetic-only")
        sess.core_path = str(filename)
        sess._load_game = Mock()
        sess.persist_game_progress = Mock()
        sess.audio = Mock(output_error=None)
        sess.save_ram = None
        sess.enable_state_resume = False
        timing = GameCubeNativeTiming()
        if system == "gamecube":
            sess.native_run_timing = timing
        stop = StopClock()
        inputs = Mock()
        emu = SimpleNamespace(
            inputs=inputs, stop_event=stop, armed=True,
            running=False, launching=True, audio_sink=None,
            audio_warning=None, save_warning=None,
        )
        sess.emulator = emu
        fake = MagicMock()
        calls = []
        def native_step():
            calls.append(True)
            if len(calls) >= count:
                stop.set()
        fake.run.side_effect = native_step
        with (
            patch("anything_plays.gba_emulator.NativeCore",
                  return_value=fake),
            patch("anything_plays.gba_emulator.SaveRAM"),
            patch("anything_plays.gba_emulator.time.monotonic",
                  side_effect=clock),
        ):
            sess.run()
        return timing, stop, inputs, fake, sess, calls


class GameCubeSchedulerClockRecoveryTests(unittest.TestCase):
    def test_validation_fails_closed_without_exposing_driver_messages(self):
        from anything_plays.gba_emulator import _optional_gamecube_frame_clock
        for broken in (
            None, False, -0.01, 10**1000,
            float("nan"), float("inf"), {}, [],
            "PRIVATE /home/owner/rom.iso",
            OSError("PRIVATE native timer /Users/owner/device"),
        ):
            with self.subTest(value=type(broken).__name__):
                def read(broken=broken):
                    if isinstance(broken, Exception):
                        raise broken
                    return broken
                with patch("anything_plays.gba_emulator.time.monotonic",
                           side_effect=read):
                    self.assertIsNone(_optional_gamecube_frame_clock())
        with patch("anything_plays.gba_emulator.time.monotonic",
                   return_value=15.125):
            self.assertEqual(_optional_gamecube_frame_clock(), 15.125)

    def test_real_native_loop_recovers_from_invalid_initial_and_mid_clock(self):
        # Initial missing time, then a mid-session exception and a 7-second
        # backwards jump. A normal core frame still runs at each step.
        timeline = [
            float("nan"), 8.0,
            RuntimeError("PRIVATE driver /Users/owner/a.iso"),
            8.016, 1.0, 1.016,
        ]
        timing, stop, inputs, native, session, calls = simulated_worker(timeline)
        self.assertEqual(len(calls), 5)
        self.assertEqual(timing.native_completed_frames, 5)
        self.assertEqual(timing.scheduler_clock_recovery_events, 3)
        self.assertEqual(timing.scheduler_late_frames, 0)
        self.assertEqual(timing.scheduler_resyncs, 0)
        self.assertEqual(inputs.before_frame.call_count, 5)
        self.assertEqual(inputs.after_frame.call_count, 5)
        self.assertEqual(native.close.call_count, 1)
        self.assertEqual(session.persist_game_progress.call_count, 1)
        self.assertTrue(stop.waits)
        self.assertTrue(all(0 <= x <= 0.05 for x in stop.waits))
        self.assertTrue(all(math.isfinite(x) for x in stop.waits))

    def test_valid_monotonic_frames_are_unchanged(self):
        timeline = [10.0, 10.0, 10.016, 10.032]
        timing, stop, inputs, native, session, calls = simulated_worker(
            timeline, count=3
        )
        self.assertEqual(len(calls), 3)
        self.assertEqual(timing.scheduler_clock_recovery_events, 0)
        self.assertEqual(timing.scheduler_late_frames, 0)
        self.assertEqual(timing.native_completed_frames, 3)
        self.assertTrue(all(0 <= x <= 0.05 for x in stop.waits))

    def test_forward_slow_native_frames_keep_existing_missed_deadline_metrics(self):
        timing, _, _, _, _, calls = simulated_worker(
            [0.0, 0.35, 0.70, 1.05], count=3
        )
        self.assertEqual(len(calls), 3)
        self.assertEqual(timing.scheduler_late_frames, 3)
        self.assertEqual(timing.scheduler_resyncs, 3)
        self.assertEqual(timing.scheduler_clock_recovery_events, 0)

    def test_non_gamecube_uses_the_original_scheduler_without_new_clock(self):
        from anything_plays.gba_emulator import _optional_gamecube_frame_clock
        with patch("anything_plays.gba_emulator._optional_gamecube_frame_clock",
                   side_effect=RuntimeError("Must not enter GameCube clock")) as gated:
            timing, stop, inputs, native, session, calls = simulated_worker(
                [10.0, 10.0, 10.016], system="gba", count=2
            )
        gated.assert_not_called()
        self.assertEqual(len(calls), 2)
        self.assertEqual(native.close.call_count, 1)
        self.assertTrue(all(math.isfinite(x) for x in stop.waits))

    def test_aggregate_is_one_counter_no_trace_data(self):
        timing = GameCubeNativeTiming()
        timing.record_native_run(0.016)
        timing.record_clock_recovery()
        timing.record_clock_recovery()
        report = timing.snapshot()
        self.assertEqual(report["scheduler_clock_recovery_events"], 2)
        self.assertEqual(report["scheduler_late_frames"], 0)
        self.assertNotIn("clock_timestamp", str(report))
        self.assertLessEqual(len(vars(timing)), 16)
        self.assertTrue(all(type(v) in (int, float) and math.isfinite(v)
                            for v in report.values()))

    def test_local_setup_summary_only_reports_bounded_clock_recovery_count(self):
        timing = GameCubeNativeTiming()
        timing.record_clock_recovery()
        timing.record_native_run(0.016)
        m = timing.snapshot()
        m.update({
            "gpu_readback_calls": 0,
            "gpu_readback_max_ms": 0,
            "gpu_readback_share_of_native_run": 0,
            "gamecube_preview_target_fps": 30,
            "gamecube_preview_cadence_intervals": 0,
            "gamecube_preview_max_interval_ms": 0,
            "audio_output_device_underflow_callbacks": 0,
            "audio_output_underrun_frames": 0,
            "audio_queue_dropped_frames": 0,
        })
        lines = _gamecube_performance_summary_lines({"metrics": m})
        self.assertTrue(any("scheduling clock recoveries: 1" in x for x in lines))
        self.assertNotIn("PRIVATE", " ".join(lines))


if __name__ == "__main__":
    unittest.main()
