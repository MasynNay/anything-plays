"""Validate, migrate, and persist independent camera-control profiles.

Coordinates are normalized to the range [0, 1], so saved layouts remain
independent of camera resolution. The public API is intentionally small:
``default_for``, ``normalize``, ``fit_to_grid``, and ``ProfileStore``.
"""

import copy
import json
import math
from pathlib import Path

from anything_plays.atomic_storage import write_json_atomically


BUTTONS_BY_SYSTEM = {
    "gb": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select"),
    "gbc": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select"),
    "gba": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select", "L", "R"),
    "snes": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select", "X", "Y", "L", "R"),
    "nes": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select"),
    "genesis": ("Left", "Up", "Right", "A", "Start", "B", "Down", "X", "Y", "Z", "Mode", "C"),
    "mastersystem": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select"),
    "gamegear": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select"),
    "sg1000": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select"),
    "atari2600": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select"),
    "atari7800": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select"),
    "pce": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select"),
    "ngp": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select"),
    "ngpc": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select"),
    "ws": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select", "X", "Y"),
    "wsc": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Select", "X", "Y"),
    # N64 and GameCube use camera-to-controller bridges while their 3D
    # video is still rendered in an external GPU window.
    "n64": ("Left", "Up", "Right", "A", "Start", "B", "Down", "Z", "L", "R", "C Up", "C Down", "C Left", "C Right"),
    "gamecube": ("Left", "Up", "Right", "A", "Start", "B", "Down", "X", "Y", "Z", "L", "R",
                 "C Up", "C Down", "C Left", "C Right"),
}

DISABLED_MAPPING = "(None)"


def enabled_zones(profile, system):
    """Return the console buttons that are currently mapped to an input."""
    mapping = profile.get("mapping", {})
    return [
        button for button in BUTTONS_BY_SYSTEM[system]
        if mapping.get(button, button) != DISABLED_MAPPING
    ]


def _grid_cells(count):
    """Return evenly sized, symmetric grid slots for enabled control zones.

    Incomplete final rows occupy whole columns so Shuffle can never hang
    outside the same grid or partially overlap a neighboring control.
    """
    columns = 3 if count <= 11 else 5
    rows = math.ceil(count / columns)
    full_rows, remainder = divmod(count, columns)
    positions = [
        (column, row)
        for row in range(full_rows)
        for column in range(columns)
    ]
    if remainder:
        if columns == 3 and remainder == 2:
            final_columns = (0, 2)
        elif columns == 5 and remainder == 2:
            final_columns = (1, 3)
        elif columns == 5 and remainder == 4:
            final_columns = (0, 1, 3, 4)
        else:
            first = (columns - remainder) // 2
            final_columns = range(first, first + remainder)
        positions.extend((column, full_rows) for column in final_columns)
    return columns, rows, positions


def fit_to_grid(profile, system):
    """Snap all visible controls, including Shuffle, into equal grid cells.

    Disabled button zones and the hidden Shuffle zone retain their stored
    rectangles so they can be enabled again without losing their positions.
    """
    names = enabled_zones(profile, system)
    if profile.get("shuffle_enabled", True):
        names.append("Shuffle")
    if not names:
        return profile

    columns, rows, positions = _grid_cells(len(names))
    zones = profile.setdefault("zones", {})
    for name, (column, row) in zip(names, positions):
        zones[name] = [
            column / columns,
            row / rows,
            (column + 1) / columns,
            (row + 1) / rows,
        ]
    return profile


def default_for(system, base):
    """Build an independent, horizontally balanced layout for one console."""
    profile = copy.deepcopy(base)
    buttons = BUTTONS_BY_SYSTEM[system]
    count = len(buttons) + 1  # Shuffle has an equal-sized, separate grid cell.
    columns, rows, positions = _grid_cells(count)
    profile["zones"] = {
        button: [column / columns, row / rows,
                 (column + 1) / columns, (row + 1) / rows]
        for button, (column, row) in zip((*buttons, "Shuffle"), positions)
    }
    profile["mapping"] = {button: button for button in buttons}
    return profile


def _valid_rectangle(rectangle):
    """Reject malformed or out-of-bounds rectangles from saved JSON."""
    return (
        isinstance(rectangle, (list, tuple))
        and len(rectangle) == 4
        and all(
            isinstance(value, (float, int)) and not isinstance(value, bool)
            for value in rectangle
        )
        and 0 <= rectangle[0] < rectangle[2] <= 1
        and 0 <= rectangle[1] < rectangle[3] <= 1
    )


def normalize(system, profile, base):
    """Merge valid legacy settings into defaults without changing the input."""
    result = default_for(system, base)
    if not isinstance(profile, dict):
        return result

    # Unknown top-level settings may belong to an older or newer UI version.
    for key, value in profile.items():
        if key not in ("zones", "mapping"):
            result[key] = copy.deepcopy(value)

    zones = profile.get("zones", {})
    if isinstance(zones, dict):
        for button in result["zones"]:
            rectangle = zones.get(button)
            if _valid_rectangle(rectangle):
                result["zones"][button] = list(rectangle)

    mapping = profile.get("mapping", {})
    if isinstance(mapping, dict):
        allowed = (*BUTTONS_BY_SYSTEM[system], DISABLED_MAPPING)
        for button in result["mapping"]:
            if mapping.get(button) in allowed:
                result["mapping"][button] = mapping[button]
    return result


class ProfileStore:
    """Store per-console profiles as JSON using an atomic file replacement."""

    def __init__(self, path, base):
        self.path = Path(path)
        self.base = base
        self.profiles = {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.profiles = {
                    key: normalize(key, value, base)
                    for key, value in data.items()
                    if key in BUTTONS_BY_SYSTEM
                }
        except (OSError, ValueError, TypeError):
            # A missing or corrupt file must not prevent the UI from starting.
            pass

    def get(self, system):
        """Return a copy so callers cannot mutate the stored profile."""
        return copy.deepcopy(
            self.profiles.get(system, default_for(system, self.base))
        )

    def put(self, system, profile):
        """Validate and persist a console profile without partial JSON writes."""
        self.profiles[system] = normalize(system, profile, self.base)
        write_json_atomically(self.path, self.profiles)
