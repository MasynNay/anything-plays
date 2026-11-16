"""Bounded, allocation-free native timing for GameCube's real Libretro loop.

Every retro_run() includes Dolphin CPU work, GPU commands, callbacks and any
synchronous GL readback. The readback counter is a SUBSET of this time:
never double-count it or infer the host GPU is fast from total FPS alone.
No individual timestamps, ROM paths, device data or trace logs are stored.
"""
from __future__ import annotations

import math


# Integer bin codes are exported instead of per-frame samples or falsely
# precise percentile values. Code 8 means >500ms; -1 means no samples.
_NATIVE_RUN_P95_BIN_UPPER_MS = (8, 16, 25, 33, 50, 100, 250, 500)
_MAX_TIMING_SAMPLE_SECONDS = 3600.0


def _safe_duration_seconds(value):
    """Validate optional native metrics without ever raising in retro_run().

    A native core callback or extension may return malformed/nonfinite
    values, including arbitrarily large Python integers. An hours-long
    timer discontinuity should not become a frame-time sample.
    """
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and 0 <= value <= _MAX_TIMING_SAMPLE_SECONDS
    except (OverflowError, TypeError, ValueError):
        return False


class GameCubeNativeTiming:
    def __init__(self):
        self.native_run_calls = 0
        self.native_run_total_seconds = 0.0
        self.native_run_max_seconds = 0.0
        self.native_run_histogram = [0] * (len(_NATIVE_RUN_P95_BIN_UPPER_MS) + 1)
        self.native_run_over_16ms = 0
        self.native_run_over_50ms = 0
        self.native_run_over_100ms = 0
        self.scheduler_wait_total_seconds = 0.0
        self.scheduler_wait_calls = 0
        # Aggregates only: how often Dolphin missed its frame deadline,
        # how far behind it was, and whether the scheduler reset its clock.
        # No timestamps or individual frame history are retained.
        self.scheduler_late_frames = 0
        self.scheduler_late_total_seconds = 0.0
        self.scheduler_late_max_seconds = 0.0
        self.scheduler_resyncs = 0
        self.reported_core_fps = None

    def record_native_run(self, duration):
        if not _safe_duration_seconds(duration):
            # Optional telemetry must never crash native emulation.
            return
        self.native_run_calls += 1
        self.native_run_total_seconds += duration
        self.native_run_max_seconds = max(self.native_run_max_seconds, duration)
        elapsed_ms = duration * 1000
        bucket = next(
            (i for i, upper in enumerate(_NATIVE_RUN_P95_BIN_UPPER_MS)
             if elapsed_ms <= upper),
            len(_NATIVE_RUN_P95_BIN_UPPER_MS),
        )
        self.native_run_histogram[bucket] += 1
        self.native_run_over_16ms += int(duration > 1 / 60)
        self.native_run_over_50ms += int(duration > 0.050)
        self.native_run_over_100ms += int(duration > 0.100)

    def record_wait(self, duration):
        if not _safe_duration_seconds(duration):
            return
        self.scheduler_wait_calls += 1
        self.scheduler_wait_total_seconds += duration

    def record_lateness(self, seconds, *, resynchronized=False):
        """Record missed native deadlines separately from GL readback cost.

        Ignore sub-5ms scheduling jitter and malformed clocks; the native
        run duration already includes the GPU readback and must not be added
        to this separate missed-deadline counter.
        """
        if not _safe_duration_seconds(seconds):
            return
        if seconds < 0.005:
            return
        self.scheduler_late_frames += 1
        self.scheduler_late_total_seconds += seconds
        self.scheduler_late_max_seconds = max(self.scheduler_late_max_seconds, seconds)
        if resynchronized:
            self.scheduler_resyncs += 1

    def _p95_bucket_code(self):
        if not self.native_run_calls:
            return -1
        target = math.ceil(self.native_run_calls * 0.95)
        subtotal = 0
        for index, samples in enumerate(self.native_run_histogram):
            subtotal += samples
            if subtotal >= target:
                return index
        return -1

    def snapshot(self, *, gpu_readback_seconds=0.0):
        reported = self.reported_core_fps
        if type(reported) not in (int, float):
            reported = 0.0
        else:
            try:
                if not math.isfinite(reported) or not 20 < reported < 240:
                    reported = 0.0
            except (OverflowError, TypeError, ValueError):
                reported = 0.0
        native = self.native_run_total_seconds
        count = self.native_run_calls
        try:
            readback = float(gpu_readback_seconds)
            if not math.isfinite(readback) or readback < 0:
                readback = 0.0
        except (ValueError, TypeError, OverflowError):
            # Local diagnostics must not crash even if a third-party timing
            # callback supplies invalid or unreasonably large numeric data.
            readback = 0.0
        # Clock readings can differ by a tiny amount at coarse resolution.
        readback = min(native, readback)
        return {
            "native_run_calls": count,
            "native_reported_core_fps": round(reported, 3),
            "native_run_mean_ms": round(1000 * native / count, 3) if count else 0.0,
            "native_run_max_ms": round(self.native_run_max_seconds * 1000, 3),
            "native_run_p95_bucket_code": self._p95_bucket_code(),
            "native_run_total_seconds": round(native, 4),
            "native_run_over_16ms": self.native_run_over_16ms,
            "native_run_over_50ms": self.native_run_over_50ms,
            "native_run_over_100ms": self.native_run_over_100ms,
            "native_run_non_readback_mean_ms": (
                round(1000 * (native - readback) / count, 3) if count else 0.0
            ),
            "gpu_readback_share_of_native_run": (
                round(readback / native, 4) if native else 0.0
            ),
            "scheduler_late_frames": self.scheduler_late_frames,
            "scheduler_late_total_seconds": round(
                self.scheduler_late_total_seconds, 4
            ),
            "scheduler_late_max_ms": round(
                self.scheduler_late_max_seconds * 1000, 3
            ),
            "scheduler_resyncs": self.scheduler_resyncs,
            "scheduler_wait_calls": self.scheduler_wait_calls,
            "scheduler_wait_total_seconds": round(
                self.scheduler_wait_total_seconds, 4
            ),
        }
