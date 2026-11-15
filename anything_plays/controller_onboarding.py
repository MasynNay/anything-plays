"""Readable, privacy-safe controller onboarding status for Anything Plays 3.2.

This helper does not initialize SDL, read game files, or send game input.
It only describes the observable state already supplied by the UI.
"""


def setup_guidance(*, enabled, connected, focused, pressed_count, embedded):
    """Return a heading and next action for the manual controller setup guide.

    Connected means the existing SDL reader has a handle, *not* an
    independently verified physical USB/Bluetooth pairing.
    """
    if not enabled:
        return (
            "1 · Enable controller input",
            "Connect your USB or Bluetooth controller, then choose Enable & scan. "
            "This does not enable camera controls or start a game.",
        )
    if not connected:
        return (
            "2 · Waiting for a controller",
            "Connect a compatible controller. Choose Rescan after pairing. "
            "If it still is not found, try USB or use keyboard controls instead.",
        )
    if not focused:
        return (
            "3 · Focus Anything Plays",
            "Click the application or this guide, then press a button or move "
            "a stick. Unfocused gamepad input is intentionally released.",
        )
    if not embedded:
        return (
            "4 · Check this console backend",
            "The controller is detected, but the selected game's current "
            "backend does not accept this embedded-controller input. "
            "Try an embedded console or configure keyboard controls.",
        )
    if pressed_count > 0:
        return (
            "4 · Input detected",
            "The controller is reporting button or stick activity. "
            "Open Button mapping to choose which game actions those inputs send.",
        )
    return (
        "3 · Test a button",
        "Controller connected. Press a face button, D-pad direction, trigger "
        "or move a stick to see live input. Then open Button mapping.",
    )
