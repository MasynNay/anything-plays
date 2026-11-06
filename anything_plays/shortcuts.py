"""Editable, per-console keyboard shortcuts.

Only Tk keysyms are accepted. The mapping is application-local and does not
inject keys into the operating system or external emulators.
"""
import re

from anything_plays.system_profiles import BUTTONS_BY_SYSTEM

DEFAULT_KEYS = {
    "Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right",
    "A": "z", "B": "x", "X": "s", "Y": "a", "L": "q", "R": "w",
    "Start": "Return", "Select": "BackSpace", "C": "d",
    "Z": "e", "Mode": "t",
    "C Up": "i", "C Down": "k", "C Left": "j", "C Right": "l",
}
RESERVED_KEYS = frozenset({"Escape", "F10", "F11"})
_ALLOWED = re.compile(r"^[a-zA-Z0-9_]{1,32}$")


def _key_identity(keysym):
    """Treat single-letter Tk keysyms case-insensitively."""
    return keysym.lower() if len(keysym) == 1 else keysym


def normalize_bindings(system, saved=None):
    """Provide the active console's complete, conflict-free key bindings."""
    names = BUTTONS_BY_SYSTEM[system]
    result = {name: DEFAULT_KEYS[name] for name in names}
    if not isinstance(saved, dict):
        return result
    for name, key in saved.items():
        if name not in result or not valid_keysym(key):
            continue
        if key == result[name]:
            continue
        if _key_identity(key) in (_key_identity(value) for button, value in result.items() if button != name):
            continue
        result[name] = key
    return result


def valid_keysym(keysym):
    return (isinstance(keysym, str)
            and _ALLOWED.fullmatch(keysym) is not None
            and keysym not in RESERVED_KEYS)


def rebind(system, bindings, button, keysym):
    """Return new bindings or raise ValueError for reserved/conflicting keys."""
    if button not in BUTTONS_BY_SYSTEM[system]:
        raise ValueError("Button is not available for this console")
    if not valid_keysym(keysym):
        raise ValueError("Use a regular keyboard key; Esc/F10/F11 are reserved for view and safety")
    updated = normalize_bindings(system, bindings)
    if _key_identity(keysym) in (_key_identity(key) for other, key in updated.items() if other != button):
        raise ValueError(f"{keysym} is already assigned to another button")
    updated[button] = keysym
    return updated


def button_for_key(system, bindings, keysym):
    """Resolve a Tk keysym to a game input, ignoring case for letter keys."""
    if not isinstance(keysym, str):
        return None
    normalized = _key_identity(keysym)
    for button, mapped in normalize_bindings(system, bindings).items():
        if _key_identity(mapped) == normalized:
            return button
    return None
