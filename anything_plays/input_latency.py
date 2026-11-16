"""Opt-in, constant-memory camera-to-native-input software timing.

No camera pixels, button names, ROMs, device IDs, per-frame history, or
wall-clock timestamps are collected. Results describe software stages only:
start of processing an already-read camera frame -> input buffer handoff ->
the next Libretro input snapshot. They are NOT physical sensor/display latency.
"""

from __future__ import annotations

import math
import time

# Explicit boundaries make percentiles *buckets*, not fabricated precision.
_BUCKET_UPPER_MS = (2, 5, 10, 20, 33, 50, 75, 100, 150, 250, 500)
_STAGES = ("tracking_to_dispatch", "dispatch_to_native", "tracking_to_native")


def _percentile_bucket(histogram, count, percentile):
    """Nearest-rank percentile from fixed bins; return an honest range."""
    if not count:
        return None
    target = math.ceil(count * percentile / 100)
    subtotal = 0
    for index, size in enumerate(histogram):
        subtotal += size
        if subtotal >= target:
            low = 0 if index == 0 else _BUCKET_UPPER_MS[index - 1]
            if index == len(_BUCKET_UPPER_MS):
                return ">500"
            return f"{low}-{_BUCKET_UPPER_MS[index]}"
    return None


class InputLatencyProbe:
    """Fixed-size histograms and at most one pending camera observation.

    Owned by InputBuffer and accessed while its state_lock is held. Repeated
    camera frames replace stale pending observations instead of growing a
    queue or attributing an old image's timestamp to the newest game input.
    """

    def __init__(self, clock=None):
        self._clock = clock if clock is not None else time.perf_counter
        self._pending = None
        self.samples = 0
        self.superseded = 0
        self.discarded_pending = 0
        self._histograms = {
            stage: [0] * (len(_BUCKET_UPPER_MS) + 1)
            for stage in _STAGES
        }

    @staticmethod
    def _valid(value):
        return type(value) in (int, float) and math.isfinite(value)

    def published(self, started_at):
        """A new held-button snapshot reached the native input buffer."""
        if not self._valid(started_at):
            return
        published_at = self._clock()
        if not self._valid(published_at) or published_at < started_at:
            return
        if self._pending is not None:
            self.superseded += 1
        self._pending = (started_at, published_at)

    def consumed(self):
        """The next armed native frame receives this latest button snapshot."""
        if self._pending is None:
            return
        started_at, published_at = self._pending
        self._pending = None
        consumed_at = self._clock()
        if not self._valid(consumed_at) or consumed_at < published_at:
            return
        self.samples += 1
        elapsed = {
            "tracking_to_dispatch": (published_at - started_at) * 1000,
            "dispatch_to_native": (consumed_at - published_at) * 1000,
            "tracking_to_native": (consumed_at - started_at) * 1000,
        }
        for stage, ms in elapsed.items():
            index = next(
                (i for i, upper in enumerate(_BUCKET_UPPER_MS) if ms <= upper),
                len(_BUCKET_UPPER_MS)
            )
            self._histograms[stage][index] += 1

    def discard(self):
        """Stop/ROM transitions must not create a stale late sample."""
        if self._pending is not None:
            self.discarded_pending += 1
            self._pending = None

    def snapshot(self):
        """Safe, aggregate-only values for an explicit local diagnostic."""
        return {
            "scope": "software_input_snapshot_not_physical_latency",
            "samples": self.samples,
            "superseded": self.superseded,
            "discarded_pending": self.discarded_pending,
            "stages": {
                stage: {
                    "p50_bucket_ms": _percentile_bucket(
                        self._histograms[stage], self.samples, 50
                    ),
                    "p95_bucket_ms": _percentile_bucket(
                        self._histograms[stage], self.samples, 95
                    ),
                }
                for stage in _STAGES
            },
        }
