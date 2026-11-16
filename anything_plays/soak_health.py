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
