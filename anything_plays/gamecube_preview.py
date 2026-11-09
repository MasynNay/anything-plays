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
    return PREVIEW_FPS.get(mode, PREVIEW_FPS[DEFAULT_PREVIEW_MODE])


def should_capture(last_capture, now, mode):
    """Only skip a preview copy; never skip a native Dolphin frame."""
    if last_capture is None:
        return True
    elapsed = now - last_capture
    if elapsed < 0:
        return True  # clock discontinuity
    # Small tolerance compensates for timer jitter; avoids 29.9 FPS output.
    return elapsed >= (1 / preview_fps(mode)) - 0.001
