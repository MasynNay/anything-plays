"""Pure acceptance checks for 3.1.1 synthetic GUI soak reporting.

A Tk window that exits before the requested wall-clock duration, or whose
callback raises, must NEVER be reported as a successful long-session test.
This module does not open a GUI, camera, controller or game ROM.
"""
from __future__ import annotations


def completion_failures(requested_seconds, elapsed_seconds, samples, callback_errors):
    """Return terminal QA failures; a synthetic run is not hardware acceptance.

    Accept at most one second of timer scheduling/clock noise on shutdown.
    A report with no samples cannot prove any bounded resource behavior.
    """
    errors = list(callback_errors)
    if not samples:
        errors.append("UI soak produced no resource samples")
    if elapsed_seconds + 1.0 < requested_seconds:
        errors.append(
            f"GUI exited early: {elapsed_seconds:.2f}s of "
            f"{requested_seconds}s requested"
        )
    return errors


def stream_target_is_valid(fps, *, stress_stream=False):
    """Separate a fixed-rate 180-second soak from a rotating-rate stress run.

    The stress test deliberately ends at an arbitrary 15/24/30 FPS target,
    so requiring precisely 24 FPS at shutdown would falsely fail healthy
    long-running Tk sessions. Do not accept strings/bools as numeric FPS.
    """
    return type(fps) is int and fps in (
        (15, 24, 30) if stress_stream else (24,)
    )


def stream_canvas_sample_failures(samples, warmup, *, stress_stream=False):
    """Keep long-Tk canvas QA strict except for proven privacy revocations.

    Clearing a live camera preview intentionally removes the entire
    OBS-facing composite so no stale private pixels can survive. A 5-second
    resource sample can coincide with that temporary *empty* canvas.
    Accept this only when a verified forced camera-clear event happened
    within the last two seconds, and the next resource sample confirms
    one canvas image again. A persistent blank, unexplained missing image,
    or multiple canvas items is still a failed endurance test.

    No pixels, camera IDs, native handles or individual event timestamps
    enter a report: only the existing sample time and a boolean indicator.
    """
    for index, sample in enumerate(samples):
        try:
            timestamp = sample["seconds"]
            items = sample["stream_items"]
            if (type(timestamp) not in (int, float) or type(items) is not int):
                return ["Stream canvas sample contains invalid measurements"]
        except (TypeError, KeyError):
            return ["Stream canvas sample contains invalid measurements"]
        if timestamp < warmup:
            continue
        if items == 1:
            continue
        if not (stress_stream and items == 0
                and sample.get("stream_recent_privacy_clear") is True):
            return ["Stream output canvas did not stay bounded and visible"]
        # Privacy clearing is deliberate. Demand that a later, independent
        # 5-second observation proves output reappeared well before the next
        # 8-second layout/rate transition; a missing final observation is
        # NOT proof of recovery.
        if index + 1 >= len(samples):
            return ["Stream did not prove recovery after privacy blank"]
        later = samples[index + 1]
        later_at = later.get("seconds")
        later_items = later.get("stream_items")
        if (type(later_at) not in (int, float)
                or later_at <= timestamp or later_at - timestamp > 7.5
                or type(later_items) is not int or later_items != 1):
            return ["Stream did not prove recovery after privacy blank"]
    return []
