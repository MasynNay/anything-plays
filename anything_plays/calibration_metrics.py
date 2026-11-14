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

def calibration_advice(report, *, sampled):
    """Human-readable next step based only on observed frame/zone counts.

    Never call detection a measured accuracy or assert lighting problems.
    Do not prevent saving on a percentage threshold: moving targets are
    naturally absent from some frames, and brief occlusion is normal.
    """
    if not sampled:
        return "Sample your target color in the main camera preview first."
    if report["frames"] < 8:
        return "Collect at least 8 live frames after sampling the color."
    if report["seen"] == 0:
        return (
            "No matching target was observed. Keep it in frame, try a new "
            "color sample, then review tolerance or minimum object area."
        )
    if report["detection_percent"] < 40:
        return (
            "The target was found in fewer than 40% of recent frames. "
            "Check lighting and contrast, or adjust tracking tolerance."
        )
    if not report["zone_hits"]:
        return (
            "Target detected, but it has not entered a control zone. "
            "Move it across one of the labeled regions to check triggering."
        )
    if len(report["zone_hits"]) == 1:
        return (
            "A zone was observed. Try moving into another labeled zone "
            "before saving your setup."
        )
    return (
        "Target detections and multiple zones were observed. Review the "
        "preview and save when the behavior matches what you expect."
    )
