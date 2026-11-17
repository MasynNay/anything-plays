"""Conservative GameCube framebuffer readback rate policy.

Dolphin continues to execute every emulation frame and produce sound. This
only reduces expensive, synchronous OpenGL->CPU copies used to update Tk's
preview. A user can restore 60 FPS preview at any time. Clocks are monotonic.
"""
PREVIEW_FPS = {
    "Performance (20 FPS)": 20,
    "Balanced (30 FPS)": 30,
    "Quality (60 FPS)": 60,
}
DEFAULT_PREVIEW_MODE = "Balanced (30 FPS)"


def preview_fps(mode):
    """Normalize malformed/legacy preferences to an explicit safe default."""
    # User preference files may be damaged or supplied by extensions.
    # An unhashable list/dict must never raise across a ctypes video
    # callback while Dolphin is executing a native frame.
    if not isinstance(mode, str):
        return PREVIEW_FPS[DEFAULT_PREVIEW_MODE]
    return PREVIEW_FPS.get(mode, PREVIEW_FPS[DEFAULT_PREVIEW_MODE])


def should_capture(last_capture, now, mode):
    """Only skip a preview copy; never skip a native Dolphin frame.

    Optional GPU preview callbacks may receive corrupted clock metadata
    after a host suspend, driver reset or test extension. Never propagate
    a bad value into the native Dolphin callback.
    """
    import math

    if type(now) not in (int, float):
        return False
    try:
        if not math.isfinite(now) or now < 0:
            return False
    except (TypeError, ValueError, OverflowError):
        return False
    if last_capture is None or type(last_capture) not in (int, float):
        return True
    try:
        if not math.isfinite(last_capture) or last_capture < 0:
            return True
    except (TypeError, ValueError, OverflowError):
        return True
    elapsed = now - last_capture
    if elapsed < 0:
        return True  # clock discontinuity
    # Small tolerance compensates for timer jitter; avoids 29.9 FPS output.
    return elapsed >= (1 / preview_fps(mode)) - 0.001


_GPU_READBACK_BIN_MAX_MS = (2, 4, 8, 16, 33, 50, 100, 250)


class ReadbackTimingHistogram:
    """Fixed-memory GPU preview-copy costs, no frame traces or device data.

    Counters are per GameCube session, across all 20/30/60 FPS preview modes.
    Only copies with a valid perf_counter duration contribute to the P95.
    """

    def __init__(self):
        self.buckets = [0] * (len(_GPU_READBACK_BIN_MAX_MS) + 1)
        self.samples = 0
        self.over_16ms = 0
        self.over_33ms = 0

    def record(self, seconds):
        import math

        if type(seconds) not in (int, float):
            return False
        try:
            valid = math.isfinite(seconds) and 0 <= seconds <= 3600
        except (TypeError, ValueError, OverflowError):
            valid = False
        if not valid:
            return False
        elapsed_ms = seconds * 1000
        i = next(
            (n for n, upper in enumerate(_GPU_READBACK_BIN_MAX_MS)
             if elapsed_ms <= upper), len(_GPU_READBACK_BIN_MAX_MS),
        )
        self.buckets[i] += 1
        self.samples += 1
        self.over_16ms += int(elapsed_ms > 16)
        self.over_33ms += int(elapsed_ms > 33)
        return True

    def snapshot(self):
        p95 = -1
        if self.samples:
            rank = (self.samples * 95 + 99) // 100  # nearest-rank P95
            cumulative = 0
            for i, count in enumerate(self.buckets):
                cumulative += count
                if cumulative >= rank:
                    p95 = i
                    break
        return {
            "gpu_readback_p95_bucket_code": p95,
            "gpu_readback_over_16ms": self.over_16ms,
            "gpu_readback_over_33ms": self.over_33ms,
        }


class PreviewCadenceTracker:
    """Constant-memory capture *publication* cadence for one preview mode.

    Native Dolphin retro_run is not counted here. No frames, filenames, raw
    trace history or per-frame timings appear in the aggregate snapshot.
    Only one in-memory monotonic observation is retained until teardown.
    """

    def __init__(self):
        self.mode = None
        self.last_publication = None
        self.published = 0
        self.intervals = 0
        self.total_seconds = 0.0
        self.max_interval_seconds = 0.0

    def reset_for(self, mode):
        """Reflect a target change immediately, even if readback is skipped.

        A performance check made immediately after changing 20/30/60 must
        never display the previous target or previous interval measurements.
        """
        selected = (
            mode if isinstance(mode, str) and mode in PREVIEW_FPS
            else DEFAULT_PREVIEW_MODE
        )
        if selected != self.mode:
            self.mode = selected
            self.last_publication = None
            self.published = 0
            self.intervals = 0
            self.total_seconds = 0.0
            self.max_interval_seconds = 0.0

    def record_published(self, now, mode):
        import math

        self.reset_for(mode)
        if not isinstance(now, (int, float)):
            return
        try:
            valid = math.isfinite(now)
        except (TypeError, OverflowError, ValueError):
            return
        if not valid or now < 0:
            return
        if (self.last_publication is not None
                and (now < self.last_publication
                     or now - self.last_publication > 3600)):
            # A clock reversal or hours-long suspended window starts a new
            # observation segment. Do not turn a sleep/resume gap into a
            # fictitious low preview FPS. Match Stream Mode's suspend policy.
            self.last_publication = None
            self.published = 0
            self.intervals = 0
            self.total_seconds = 0.0
            self.max_interval_seconds = 0.0

        if self.last_publication is not None:
            elapsed = now - self.last_publication
            if elapsed > 0:
                self.intervals += 1
                self.total_seconds += elapsed
                self.max_interval_seconds = max(
                    self.max_interval_seconds, elapsed
                )
        self.last_publication = now
        self.published += 1

    def snapshot(self):
        """Allowlisted numeric facts, not rendered FPS or speaker metrics."""
        target = preview_fps(self.mode) if self.mode is not None else 0
        cadence = (
            self.intervals / self.total_seconds
            if self.intervals > 0 and self.total_seconds > 0 else 0.0
        )
        return {
            "gamecube_preview_target_fps": target,
            "gamecube_preview_observed_capture_fps": round(cadence, 2),
            "gamecube_preview_cadence_intervals": self.intervals,
            "gamecube_preview_max_interval_ms": round(
                self.max_interval_seconds * 1000, 2
            ),
        }
