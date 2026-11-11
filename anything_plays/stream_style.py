"""Validated, bounded customization for the separate OBS-capture stream view.

Stream settings never contain paths, recording destinations, or camera
permissions. They only affect native Tk display chrome in one popup window.
"""
from __future__ import annotations

import re

STREAM_LAYOUTS = ("Stacked", "Side by side")
STREAM_ORDER = ("Game first", "Camera first")
DEFAULT_STREAM_STYLE = {
    "layout": "Stacked",
    "order": "Game first",
    "theme": "Follow app theme",
    "border_color": "Theme accent",
    "border_width": 10,
    "gap": 18,
    "game_share": 50,
    "show_labels": True,
}
_RGB_HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")


def normalize_stream_style(value, *, themes):
    """Ignore untrusted or legacy preference values without raising in Tk.

    Numeric ranges bound geometry, and literal Tk color strings are accepted
    only in six-digit RGB form (never arbitrary Tcl color names).
    """
    candidate = value if isinstance(value, dict) else {}
    result = dict(DEFAULT_STREAM_STYLE)
    for key, choices in (
        ("layout", STREAM_LAYOUTS),
        ("order", STREAM_ORDER),
        ("theme", ("Follow app theme", *themes)),
    ):
        if candidate.get(key) in choices:
            result[key] = candidate[key]
    color = candidate.get("border_color")
    if color == "Theme accent" or (
        isinstance(color, str) and _RGB_HEX.fullmatch(color)
    ):
        result["border_color"] = color
    for key, low, high in (
        ("border_width", 2, 28),
        ("gap", 0, 48),
        ("game_share", 25, 75),
    ):
        value = candidate.get(key)
        if type(value) is int:
            result[key] = max(low, min(high, value))
    if type(candidate.get("show_labels")) is bool:
        result["show_labels"] = candidate["show_labels"]
    return result


def stream_palette(style, *, themes, app_theme):
    name = style["theme"]
    if name == "Follow app theme":
        name = app_theme
    palette = themes.get(name, themes["Dark"])
    outer, surface, foreground, accent, _button, field = palette
    border = (accent if style["border_color"] == "Theme accent"
              else style["border_color"])
    return {
        "background": outer,
        "surface": surface,
        "label": foreground,
        "accent": border,
        "inset": field,
        "screen": "#04090f",
    }
