"""Pure camera-frame analysis for color tracking and input-zone hit testing.

This module never opens cameras or presses buttons. Keeping recognition separate
from side effects makes a dropped frame or a tracking regression testable.
"""

import cv2
import numpy as np

from anything_plays.system_profiles import DISABLED_MAPPING


MAX_TRACKED_OBJECTS = 16


def locate_targets(frame, rgb, tolerance, min_area, *, max_targets=MAX_TRACKED_OBJECTS):
    """Find multiple *independent* matching fish, not only the largest one.

    Each connected color component is a separate fish. Sort by area so noise
    cannot flood the input buffer; cap tracking to 16 objects per color.
    Coordinates and contour data belong to the supplied, unmodified frame.
    Hue distance wraps safely around red's HSV boundary.
    """
    limit = max(1, min(MAX_TRACKED_OBJECTS, int(max_targets)))
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    target = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2HSV)[0, 0]
    hue, saturation, value = (int(channel) for channel in target)
    hue_image = hsv[:, :, 0].astype(np.int16)
    hue_distance = np.abs(hue_image - hue)
    hue_distance = np.minimum(hue_distance, 180 - hue_distance)
    saturation_distance = np.abs(hsv[:, :, 1].astype(np.int16) - saturation)
    value_distance = np.abs(hsv[:, :, 2].astype(np.int16) - value)
    mask = (
        (hue_distance <= tolerance // 2 + 1)
        & (saturation_distance <= max(35, tolerance * 3))
        & (value_distance <= max(45, tolerance * 4))
    ).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    eligible = (contour for contour in contours
                if cv2.contourArea(contour) >= min_area)
    matches = []
    for contour in sorted(eligible, key=cv2.contourArea, reverse=True)[:limit]:
        moments = cv2.moments(contour)
        if not moments["m00"]:
            continue
        center = (
            int(moments["m10"] / moments["m00"]),
            int(moments["m01"] / moments["m00"]),
        )
        matches.append((center, contour))
    return matches


def locate_target(frame, rgb, tolerance, min_area):
    """Backward-compatible largest-fish API for old saved profiles/tests."""
    matches = locate_targets(frame, rgb, tolerance, min_area, max_targets=1)
    return matches[0] if matches else (None, None)

def zone_at(center, frame_size, zones, mapping, shuffle_enabled):
    """Return the first enabled zone containing *center* (including edges).

    ``mapping`` contains effective button names or ``(None)``. The ordering
    of ``zones`` is preserved to match previously saved overlapping layouts.
    """
    if center is None:
        return None
    width, height = frame_size
    if width <= 0 or height <= 0:
        return None
    x, y = center[0] / width, center[1] / height
    for name, (left, top, right, bottom) in zones.items():
        if name == "Shuffle" and not shuffle_enabled:
            continue
        if name != "Shuffle" and mapping.get(name, name) == DISABLED_MAPPING:
            continue
        if left <= x <= right and top <= y <= bottom:
            return name
    return None
