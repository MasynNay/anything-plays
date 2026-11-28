"""Curated, local camera-control layout starters for every supported console.

These are deterministic layouts, not tested accessibility prescriptions.
They never change a user's tracking calibration or device configuration.
"""
from anything_plays.portable_profiles import make_bundle
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import (
    BUTTONS_BY_SYSTEM, DISABLED_MAPPING, default_for, normalize,
)

LAYOUTS = {
    "movement": ("Large movement zones", "Four direction zones only. A/B and all other camera buttons are disabled."),
    "actions": ("Two large action zones", "A and B fill the camera area. Movement and other camera buttons are disabled."),
    "adventure": ("Large adventure controls", "Four directions, A, B and Start. Other camera buttons are disabled."),
    "contrast": ("High-contrast full layout", "All console buttons in the standard grid, with high-contrast labels and no Shuffle zone."),
    "mirrored": ("Mirrored full layout", "All console buttons in a horizontally mirrored grid, with no Shuffle zone."),
}


def build_layout(system, key, current):
    """Return a fresh portable bundle, preserving all tracking parameters.

    Each layout replaces camera-zone geometry and mappings only, with
    explicit visual changes for high contrast. No theme or local path is
    exported. The existing confirmed apply flow controls activation.
    """
    if system not in BUTTONS_BY_SYSTEM or key not in LAYOUTS:
        raise ValueError("Unknown console or built-in layout.")
    if not isinstance(current, dict):
        raise ValueError("Current controls are unavailable.")
    buttons = BUTTONS_BY_SYSTEM[system]
    profile = normalize(system, current, DEFAULT)
    defaults = default_for(system, DEFAULT)
    profile["zones"] = defaults["zones"]
    profile["mapping"] = {name: name for name in buttons}
    profile["shuffle_enabled"] = False
    if key in ("movement", "actions", "adventure"):
        # Deliberately non-overlapping large targets. Inactive zones keep
        # their default geometry for later remapping but cannot trigger.
        positions = {
            "movement": {
                "Up": (0, 0, 1, .25), "Left": (0, .25, .5, .75),
                "Right": (.5, .25, 1, .75), "Down": (0, .75, 1, 1),
            },
            "actions": {"A": (0, 0, .5, 1), "B": (.5, 0, 1, 1)},
            "adventure": {
                "Up": (0, 0, .5, .25), "Left": (0, .25, .25, .75),
                "Right": (.25, .25, .5, .75), "Down": (0, .75, .5, 1),
                "A": (.5, 0, 1, .4), "B": (.5, .4, 1, .8),
                "Start": (.5, .8, 1, 1),
            },
        }[key]
        for name in buttons:
            if name in positions:
                profile["zones"][name] = list(positions[name])
            else:
                profile["mapping"][name] = DISABLED_MAPPING
    elif key == "contrast":
        profile.update(zone_style="High contrast", zone_opacity=100,
                       zone_border_width=8, zone_font_size=max(50, profile["zone_font_size"]))
    elif key == "mirrored":
        for name, (x0, y0, x1, y1) in profile["zones"].items():
            profile["zones"][name] = [1-x1, y0, 1-x0, y1]
    return make_bundle(system, profile)


def layout_changes(system, current, proposed):
    """Compare normalized effective controls, never raw private fields."""
    before = normalize(system, current, DEFAULT)
    after = normalize(system, proposed, DEFAULT)
    names = BUTTONS_BY_SYSTEM[system]
    disabled = tuple(name for name in names
                     if before["mapping"][name] != DISABLED_MAPPING
                     and after["mapping"][name] == DISABLED_MAPPING)
    enabled = tuple(name for name in names
                    if before["mapping"][name] == DISABLED_MAPPING
                    and after["mapping"][name] != DISABLED_MAPPING)
    remapped = tuple(name for name in names
                     if before["mapping"][name] != after["mapping"][name]
                     and name not in disabled and name not in enabled)
    moved = tuple(name for name in names
                  if after["mapping"][name] != DISABLED_MAPPING
                  and before["zones"][name] != after["zones"][name])
    active = tuple(name for name in names
                   if after["mapping"][name] != DISABLED_MAPPING)
    return {
        "disabled": disabled, "enabled": enabled, "remapped": remapped,
        "moved": moved, "active": active,
        "shuffle_changed": before["shuffle_enabled"] != after["shuffle_enabled"],
    }
