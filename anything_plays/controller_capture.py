"""Edge-based physical button selection for the 3.2 controller remapper.

This intentionally does no SDL or Tk work. Existing held inputs are ignored
until released and pressed again; simultaneous presses are rejected instead of
choosing an arbitrary controller action.
"""

from anything_plays.gamepad import SOURCES


def newly_pressed_source(previous, current):
    """Return (source or None, new_baseline, ambiguous).

    Only recognized SDL control sources may assign a mapping. A transition
    involving multiple new inputs is ambiguous and must not commit a mapping.
    """
    current_set = frozenset(value for value in current if value in SOURCES)
    previous_set = frozenset(value for value in previous if value in SOURCES)
    fresh = current_set - previous_set
    if len(fresh) == 1:
        return next(iter(fresh)), current_set, False
    return None, current_set, len(fresh) > 1
