"""Portable, deliberately minimal camera-control profiles for Anything Plays 3.2.

Only recognized control settings, normalized zone coordinates, and an optional
theme leave the user's machine. ROMs, paths, image URLs, saves, credentials,
gamepad device details, and camera frames are never serialized.

Import is a *validation step*, not an apply operation. The UI separately
previews and confirms changes before persisting anything.
"""

import json
import math
from pathlib import Path

from anything_plays.atomic_storage import write_json_atomically
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM, DISABLED_MAPPING


FORMAT = "anything-plays-control-profile"
VERSION = 1
MAX_FILE_BYTES = 64 * 1024

_INTEGERS = {
    "tolerance": (1, 90),
    "min_area": (5, 50000),
    "hold_frames": (1, 60),
    "cooldown_ms": (50, 10000),
    "zone_font_size": (8, 160),
    "zone_opacity": (75, 100),
    "zone_border_width": (2, 16),
}
_BOOLEANS = ("color2_enabled", "multi_fish_enabled", "mirror", "shuffle_enabled")
_ENUMS = {
    "color2_player": ("Player 1", "Player 2"),
    "camera_input_mode": ("Held while visible", "Pulse (classic)"),
    "zone_style": ("Bold", "High contrast", "Outline", "Minimal"),
    "zone_label_position": ("Center", "Top-left"),
}
_COLORS = ("rgb", "rgb2")
_ALLOWED = frozenset((*_INTEGERS, *_BOOLEANS, *_ENUMS, *_COLORS, "zones", "mapping"))


def _rectangle(value):
    return (
        isinstance(value, (list, tuple)) and len(value) == 4
        and all(type(x) in (int, float) and math.isfinite(x) for x in value)
        and 0 <= value[0] < value[2] <= 1
        and 0 <= value[1] < value[3] <= 1
    )


def sanitize_profile(system, profile, *, legacy=False):
    """Return only portable, validated settings; never mutate the source.

    Old unversioned saved profiles may include a private zone_image path,
    so unknown keys are *discarded* for legacy imports. Unknown keys in
    versioned documents are rejected to keep the format auditable.
    """
    if system not in BUTTONS_BY_SYSTEM:
        raise ValueError("Unknown console in control profile.")
    if not isinstance(profile, dict):
        raise ValueError("Control profile must contain a settings object.")
    if not legacy and set(profile) - _ALLOWED:
        raise ValueError("Unexpected settings in control profile.")

    clean = {}
    for key, (low, high) in _INTEGERS.items():
        if key in profile:
            value = profile[key]
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"Invalid {key} in control profile.")
            clean[key] = value
    for key in _BOOLEANS:
        if key in profile:
            if type(profile[key]) is not bool:
                raise ValueError(f"Invalid {key} in control profile.")
            clean[key] = profile[key]
    for key, options in _ENUMS.items():
        if key in profile:
            if type(profile[key]) is not str or profile[key] not in options:
                raise ValueError(f"Invalid {key} in control profile.")
            clean[key] = profile[key]
    for key in _COLORS:
        if key in profile:
            color = profile[key]
            if (not isinstance(color, (list, tuple)) or len(color) != 3
                    or any(type(channel) is not int or not 0 <= channel <= 255
                           for channel in color)):
                raise ValueError(f"Invalid {key} in control profile.")
            clean[key] = list(color)

    allowed = set(BUTTONS_BY_SYSTEM[system])
    if "zones" not in profile or not isinstance(profile["zones"], dict):
        raise ValueError("Control profile is missing button zones.")
    zones = {}
    for name, rect in profile["zones"].items():
        if name not in allowed and name != "Shuffle":
            raise ValueError(f"Unknown zone in control profile: {name!r}")
        if not _rectangle(rect):
            raise ValueError(f"Invalid rectangle for zone {name!r}.")
        zones[name] = list(rect)
    if not zones:
        raise ValueError("Control profile has no button zones.")
    clean["zones"] = zones

    mapping = profile.get("mapping", {})
    if not isinstance(mapping, dict):
        raise ValueError("Control profile button mapping must be an object.")
    clean_mapping = {}
    for name, action in mapping.items():
        if name not in allowed or type(action) is not str or action not in (
                *BUTTONS_BY_SYSTEM[system], DISABLED_MAPPING):
            raise ValueError(f"Invalid button mapping for {name!r}.")
        clean_mapping[name] = action
    clean["mapping"] = clean_mapping
    return clean


def make_bundle(system, profile, *, theme=None, allowed_themes=()):
    """Build a versioned profile containing no device or private file data."""
    clean = sanitize_profile(system, {k: v for k, v in profile.items()
                                      if k in _ALLOWED})
    bundle = {"format": FORMAT, "version": VERSION, "system": system,
              "profile": clean}
    if theme is not None:
        if theme not in allowed_themes:
            raise ValueError("Unknown application theme.")
        bundle["theme"] = theme
    return bundle


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key {key!r} in control profile.")
        result[key] = value
    return result


def parse_bundle(data, *, selected_system, allowed_themes=()):
    """Validate bytes/JSON and return (safe_profile, theme, is_legacy).

    For old plain JSON profiles, the selected console is assumed because the
    original format did not record it. New files must match exactly.
    """
    if selected_system not in BUTTONS_BY_SYSTEM:
        raise ValueError("Choose a supported console first.")
    if isinstance(data, bytes):
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("Control profile is larger than 64 KiB.")
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Control profile is not UTF-8.") from exc
    if not isinstance(data, str):
        raise ValueError("Control profile must be JSON text.")
    if len(data.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("Control profile is larger than 64 KiB.")
    try:
        document = json.loads(
            data, object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("Non-finite JSON number in control profile.")
            ),
        )
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError(f"Invalid control-profile JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("Control profile must be a JSON object.")

    legacy = "format" not in document and "version" not in document
    if legacy:
        profile, theme = document, None
    else:
        if set(document) - {"format", "version", "system", "profile", "theme"}:
            raise ValueError("Unexpected fields in profile document.")
        if document.get("format") != FORMAT or type(document.get("version")) is not int:
            raise ValueError("Unrecognized control-profile format.")
        if document["version"] != VERSION:
            raise ValueError("Unsupported control-profile version.")
        if document.get("system") != selected_system:
            raise ValueError(
                "This profile belongs to another console. Select "
                f"{document.get('system')!r} to import it."
            )
        profile = document.get("profile")
        theme = document.get("theme")
        if theme is not None and (
                type(theme) is not str or theme not in allowed_themes):
            raise ValueError("This profile uses an unsupported theme.")
    return sanitize_profile(selected_system, profile, legacy=legacy), theme, legacy


def load_bundle(path, *, selected_system, allowed_themes=()):
    """Bound reads, including a single extra byte to detect oversized files."""
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    return parse_bundle(
        data, selected_system=selected_system, allowed_themes=allowed_themes
    )


def save_bundle(path, system, profile, *, theme=None, allowed_themes=()):
    """Write only approved fields, with a crash-safe atomic replacement."""
    bundle = make_bundle(
        system, profile, theme=theme, allowed_themes=allowed_themes
    )
    write_json_atomically(path, bundle)
