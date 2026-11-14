"""Small, deterministic rolling camera-calibration metrics.

Consumes only centers and active zone names from already processed frames.
Never retains images, frame buffers, object contours or camera identifiers.
"""

from collections import Counter
from math import hypot


def calibration_summary(samples):
    """Summarize a recent bounded sequence of (center, zone) observations.

    center is (x, y) or None; zone is a button-zone name or None.
    Movement between adjacent detected frames is motion, NOT an accuracy
    score: a deliberately moving toy or fish will have high movement.
    """
    frames = 0
    seen = 0
    zone_hits = Counter()
    movements = []
    previous = None
    for center, zone in samples:
        frames += 1
        if center is None:
            previous = None
            continue
        seen += 1
        if zone:
            zone_hits[zone] += 1
        if previous is not None:
            movements.append(hypot(center[0] - previous[0],
                                   center[1] - previous[1]))
        previous = center
    return {
        "frames": frames,
        "seen": seen,
        "lost": frames - seen,
        "detection_percent": round(100 * seen / frames) if frames else 0,
        "zone_hits": dict(sorted(zone_hits.items())),
        "average_motion_px": round(sum(movements) / len(movements), 1)
        if movements else None,
    }
