"""Bounded, allocation-free native timing for GameCube's real Libretro loop.

Every retro_run() includes Dolphin CPU work, GPU commands, callbacks and any
synchronous GL readback. The readback counter is a SUBSET of this time:
never double-count it or infer the host GPU is fast from total FPS alone.
No individual timestamps, ROM paths, device data or trace logs are stored.
"""
from __future__ import annotations

import math


class GameCubeNativeTiming:
    def __init__(self):
        self.native_run_calls = 0
        self.native_run_total_seconds = 0.0
        self.native_run_max_seconds = 0.0
        self.native_run_over_16ms = 0
        self.native_run_over_50ms = 0
        self.native_run_over_100ms = 0
        self.scheduler_wait_total_seconds = 0.0
        self.scheduler_wait_calls = 0
        self.reported_core_fps = None

    def record_native_run(self, duration):
        if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0:
            return
        self.native_run_calls += 1
        self.native_run_total_seconds += duration
        self.native_run_max_seconds = max(self.native_run_max_seconds, duration)
        self.native_run_over_16ms += int(duration > 1 / 60)
        self.native_run_over_50ms += int(duration > 0.050)
        self.native_run_over_100ms += int(duration > 0.100)

    def record_wait(self, duration):
        if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0:
            return
        self.scheduler_wait_calls += 1
        self.scheduler_wait_total_seconds += duration

    def snapshot(self, *, gpu_readback_seconds=0.0):
        reported = self.reported_core_fps
        if (type(reported) not in (int, float)
                or not math.isfinite(reported) or not 20 < reported < 240):
            reported = 0.0
        native = self.native_run_total_seconds
        count = self.native_run_calls
        readback = float(gpu_readback_seconds)
        if not math.isfinite(readback) or readback < 0:
            readback = 0.0
        # Clock readings can differ by a tiny amount at coarse resolution.
        readback = min(native, readback)
        return {
            "native_run_calls": count,
            "native_reported_core_fps": round(reported, 3),
            "native_run_mean_ms": round(1000 * native / count, 3) if count else 0.0,
            "native_run_max_ms": round(self.native_run_max_seconds * 1000, 3),
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
            "scheduler_wait_calls": self.scheduler_wait_calls,
            "scheduler_wait_total_seconds": round(
                self.scheduler_wait_total_seconds, 4
            ),
        }
