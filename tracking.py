"""Pure camera-frame analysis for color tracking and input-zone hit testing.

This module never opens cameras or presses buttons. Keeping recognition separate
from side effects makes a dropped frame or a tracking regression testable.
"""

import cv2
import numpy as np

from system_profiles import DISABLED_MAPPING


def locate_target(frame, rgb, tolerance, min_area):
    """Return ``(center, contour)`` for the largest matching color region.

    RGB preferences are converted to OpenCV HSV. Hue distance wraps around
    red's 0/179 boundary; saturation and value use wider tolerances to account
    for changing lighting. A 3x3 opening removes isolated sensor noise.
    """
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
    eligible = (contour for contour in contours if cv2.contourArea(contour) >= min_area)
    contour = max(eligible, key=cv2.contourArea, default=None)
    if contour is None:
        return None, None

    moments = cv2.moments(contour)
    if not moments["m00"]:
        return None, contour
    center = (
        int(moments["m10"] / moments["m00"]),
        int(moments["m01"] / moments["m00"]),
    )
    return center, contour


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
