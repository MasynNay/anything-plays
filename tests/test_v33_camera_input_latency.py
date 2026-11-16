"""3.3 software-only camera input timing: no camera, native core or data logs."""

import time
import unittest
from unittest.mock import patch

from anything_plays.input_latency import InputLatencyProbe
from anything_plays.libretro_input import IDS, InputBuffer


class SteppedClock:
    def __init__(self, *values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


class BoundedProbeTests(unittest.TestCase):
    def test_percentile_ranges_for_tracking_dispatch_and_native_snapshot(self):
        probe = InputLatencyProbe(clock=SteppedClock(10.013, 10.040))
        probe.published(10.0)
        probe.consumed()
        result = probe.snapshot()
        self.assertEqual(result["samples"], 1)
        self.assertEqual(result["stages"]["tracking_to_dispatch"], {
            "p50_bucket_ms": "10-20", "p95_bucket_ms": "10-20",
        })
        self.assertEqual(result["stages"]["dispatch_to_native"], {
            "p50_bucket_ms": "20-33", "p95_bucket_ms": "20-33",
        })
        self.assertEqual(result["stages"]["tracking_to_native"], {
            "p50_bucket_ms": "33-50", "p95_bucket_ms": "33-50",
        })
        self.assertEqual(
            result["scope"], "software_input_snapshot_not_physical_latency"
        )
        self.assertEqual(len(probe._histograms), 3)
        self.assertEqual(max(map(len, probe._histograms.values())), 12)

    def test_older_camera_snapshots_are_superseded_not_miscounted(self):
        probe = InputLatencyProbe(clock=SteppedClock(2.00, 2.06, 2.08))
        probe.published(1.99)
        probe.published(2.05)
        probe.consumed()
        report = probe.snapshot()
        self.assertEqual(report["superseded"], 1)
        self.assertEqual(report["samples"], 1)
        self.assertEqual(report["stages"]["tracking_to_native"]["p95_bucket_ms"],
                         "20-33")
        self.assertIsNone(probe._pending)

    def test_percentile_buckets_do_not_store_or_expose_raw_samples(self):
        # P95 is the 19th observation for a sample of 20, not the worst.
        # The 20th outlier must not inflate the reported P95 bucket.
        tick = [0.0]
        probe = InputLatencyProbe(clock=lambda: tick[0])
        for i in range(20):
            start = 100 + i
            tick[0] = start + 0.003
            probe.published(start)
            tick[0] = start + (0.650 if i == 19 else 0.004)
            probe.consumed()
        report = probe.snapshot()
        self.assertEqual(report["samples"], 20)
        self.assertEqual(
            report["stages"]["tracking_to_native"]["p95_bucket_ms"],
            "2-5",
        )
        self.assertNotIn("100.", str(report))
        self.assertEqual(
            sum(probe._histograms["tracking_to_native"]), 20
        )

    def test_stop_discards_pending_and_never_counts_stale_input(self):
        inputs = InputBuffer()
        inputs.enable_latency_probe(clock=SteppedClock(10.02))
        inputs.set_camera_buttons(["A"], ["B"], sample_started_at=10.0)
        inputs.disarm()
        inputs.before_frame(armed=False)
        stats = inputs.latency_snapshot()
        self.assertEqual(stats["discarded_pending"], 1)
        self.assertEqual(stats["samples"], 0)
        self.assertIsNone(stats["stages"]["tracking_to_native"]["p95_bucket_ms"])
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 0)

    def test_missing_newer_camera_timestamp_discards_old_pending_not_controls(self):
        inputs = InputBuffer()
        inputs.enable_latency_probe(clock=SteppedClock(
            10.01, 10.21, 10.25,
        ))
        inputs.set_camera_buttons(["A"], ["B"], sample_started_at=10.0)
        self.assertIsNotNone(inputs.latency_probe._pending)
        # A later frame had an optional camera-timer exception; its real
        # P1/P2 input update must replace the earlier held-button state.
        inputs.set_camera_buttons([], [], sample_started_at=None)
        self.assertIsNone(inputs.latency_probe._pending)
        inputs.before_frame(armed=True)
        report = inputs.latency_snapshot()
        self.assertEqual(report["samples"], 0)
        self.assertEqual(report["discarded_pending"], 1)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 0)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 0)

        inputs.set_camera_buttons(["A"], [], sample_started_at=10.2)
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 0)
        self.assertEqual(inputs.latency_snapshot()["samples"], 1)
        self.assertEqual(inputs.latency_snapshot()["discarded_pending"], 1)

    def test_held_ports_consumed_together_under_native_frame_lock(self):
        # Native frame may consume exactly the most recent camera state.
        inputs = InputBuffer()
        inputs.enable_latency_probe(clock=SteppedClock(100.020, 100.045))
        inputs.set_camera_buttons(["A"], ["B"], sample_started_at=100.0)
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 1)
        self.assertEqual(inputs.latency_snapshot()["samples"], 1)
        inputs.after_frame()
        # Do not count an unchanged held input once per emulation frame.
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.latency_snapshot()["samples"], 1)
        inputs.disable_latency_probe()
        self.assertFalse(inputs.latency_snapshot()["enabled"])
        self.assertEqual(inputs.latency_snapshot()["samples"], 1)

    def test_invalid_clocks_never_make_fake_or_negative_samples(self):
        for observed in (
            None, float("nan"), float("inf"), -1e20, 10**1000,
            True, "not clock"
        ):
            with self.subTest(observed=observed):
                probe = InputLatencyProbe(clock=lambda: 10.0)
                probe.published(observed)
                probe.consumed()
                self.assertEqual(probe.snapshot()["samples"], 0)
        probe = InputLatencyProbe(clock=SteppedClock(1.0, 0.0))
        probe.published(2.0)  # clock moved backward, rejected
        self.assertEqual(probe.snapshot()["samples"], 0)

    def test_failed_optional_clock_cannot_break_native_buttons(self):
        # A diagnostics-only timing callback must never escape through the
        # native Libretro input snapshot, even if a clock implementation
        # raises private device/path details.
        times = iter((100.010, OSError("/home/private/camera-id"),
                      100.110, 100.150))

        def sometimes_fails():
            result = next(times)
            if isinstance(result, Exception):
                raise result
            return result

        inputs = InputBuffer()
        inputs.enable_latency_probe(clock=sometimes_fails)
        inputs.set_camera_buttons(["A"], ["B"], sample_started_at=100.0)
        inputs.before_frame(armed=True)  # clock raises; game remains armed
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 1)
        self.assertEqual(inputs.latency_snapshot()["samples"], 0)
        inputs.after_frame()
        inputs.set_camera_buttons(["A"], sample_started_at=100.1)
        inputs.before_frame(armed=True)  # later valid timing recovers
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 0)
        report = inputs.latency_snapshot()
        self.assertEqual(report["samples"], 1)
        self.assertNotIn("/home/private", str(report))

    def test_bad_newer_publication_revokes_old_pending_latency(self):
        ticks = iter((2.01, RuntimeError("private device"),
                      2.21, 2.25))

        def tick():
            value = next(ticks)
            if isinstance(value, Exception):
                raise value
            return value

        probe = InputLatencyProbe(clock=tick)
        probe.published(2.0)
        self.assertIsNotNone(probe._pending)
        probe.published(2.1)  # newer frame; invalid clock
        self.assertIsNone(probe._pending)
        self.assertEqual(probe.snapshot()["discarded_pending"], 1)
        probe.consumed()  # old timestamp cannot be attributed to new input
        self.assertEqual(probe.snapshot()["samples"], 0)
        probe.published(2.2)
        probe.consumed()
        self.assertEqual(probe.snapshot()["samples"], 1)
        self.assertIsNone(probe._pending)
        self.assertEqual(
            probe.snapshot()["stages"]["tracking_to_native"]["p95_bucket_ms"],
            "33-50"
        )

    def test_exhausted_clock_is_optional_and_recovers_when_reenabled(self):
        inputs = InputBuffer()
        inputs.enable_latency_probe(clock=iter(()).__next__)
        inputs.set_camera_buttons(["A"], sample_started_at=1.0)
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(inputs.latency_snapshot()["samples"], 0)
        inputs.enable_latency_probe(clock=SteppedClock(2.03, 2.06))
        inputs.set_camera_buttons(["A"], sample_started_at=2.0)
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.latency_snapshot()["samples"], 1)

    def test_sleep_resume_clock_jumps_are_not_reported_as_active_input_lag(self):
        # Large idle gaps used to land in the >500 ms latency bucket and
        # corrupt an active-session percentile. Actual button updates must
        # not depend on whether this optional timer can be sampled.
        probe = InputLatencyProbe(clock=SteppedClock(
            4005.0, 4005.020, 7606.020, 7606.040, 7606.070,
        ))
        probe.published(1.0)  # suspended during camera processing
        self.assertIsNone(probe._pending)
        probe.published(4005.0)  # fresh frame after resume
        probe.consumed()  # suspended again before native snapshot
        self.assertEqual(probe.snapshot()["samples"], 0)
        probe.published(7606.030)  # healthy observation after resume
        probe.consumed()
        report = probe.snapshot()
        self.assertEqual(report["samples"], 1)
        self.assertEqual(report["clock_discontinuities"], 2)
        self.assertEqual(
            report["stages"]["tracking_to_native"]["p95_bucket_ms"],
            "33-50",
        )
        self.assertEqual(sum(probe._histograms["tracking_to_native"]), 1)
        self.assertIsNone(probe._pending)

    def test_expired_timing_still_delivers_and_releases_both_native_ports(self):
        inputs = InputBuffer()
        inputs.enable_latency_probe(clock=SteppedClock(
            4005.0, 4006.010, 4006.025,
        ))
        inputs.set_camera_buttons(["A"], ["B"], sample_started_at=1.0)
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 1)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 1)
        self.assertEqual(inputs.latency_snapshot()["samples"], 0)
        self.assertEqual(inputs.latency_snapshot()["clock_discontinuities"], 1)
        inputs.after_frame()
        inputs.set_camera_buttons([], [], sample_started_at=4006.0)
        inputs.before_frame(armed=True)
        self.assertEqual(inputs.state(0, 1, 0, IDS["A"]), 0)
        self.assertEqual(inputs.state(1, 1, 0, IDS["B"]), 0)
        self.assertEqual(inputs.latency_snapshot()["samples"], 1)

    def test_constant_memory_after_thousands_of_samples(self):
        clock = [1.0]
        def current():
            clock[0] += 0.008
            return clock[0]
        probe = InputLatencyProbe(clock=current)
        for _ in range(12000):
            probe.published(clock[0] - 0.003)
            probe.consumed()
        self.assertEqual(probe.snapshot()["samples"], 12000)
        self.assertIsNone(probe._pending)
        self.assertEqual(sum(len(x) for x in probe._histograms.values()), 36)
        self.assertEqual(sum(probe._histograms["tracking_to_native"]), 12000)
        self.assertEqual(probe.snapshot()["superseded"], 0)

    def test_no_time_probes_are_sampled_without_explicit_opt_in(self):
        inputs = InputBuffer()
        self.assertIsNone(inputs.latency_snapshot())
        with patch("anything_plays.input_latency.time.perf_counter",
                   side_effect=AssertionError("no implicit sampling")):
            inputs.set_camera_buttons(["A"], sample_started_at=22.0)
            inputs.before_frame(armed=True)
            self.assertIsNone(inputs.latency_snapshot())


if __name__ == "__main__":
    unittest.main()
