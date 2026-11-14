"""Local, strictly redacted setup checks for Anything Plays 3.2.

The report contains only an allowlisted console ID and small state labels.
It never records filesystem paths, ROM names, camera names, frames, Bluetooth
identifiers, or other user data. The UI copies it only after a user action.
"""

from anything_plays.system_profiles import BUTTONS_BY_SYSTEM


def build_setup_report(
    *, system, camera_count, camera_selected, camera_active,
    core_found, controller_enabled, controller_detected, embedded_mode,
):
    """Describe observed setup state, without claiming hardware acceptance."""
    if system not in BUTTONS_BY_SYSTEM:
        raise ValueError("Choose a supported console before checking setup.")

    count = max(0, min(20, int(camera_count)))
    if camera_active:
        camera = (
            "Camera preview running",
            "The camera is open. Choose a target color before enabling object controls.",
        )
    elif camera_selected:
        camera = (
            "Camera selected but not running",
            "Click Use camera. If opening fails, check OS privacy permissions "
            "and close any other app using the camera.",
        )
    elif count:
        camera = (
            "Camera available",
            "Select a camera and click Use camera. Keyboard play is also available.",
        )
    else:
        camera = (
            "No camera found",
            "Refresh cameras, check OS camera permissions and USB connections. "
            "You can still play using a keyboard without a webcam.",
        )

    core = (
        ("Core file located", "An emulator core file is present. This does not verify game compatibility.")
        if core_found
        else ("Core file not located",
              "Check installed emulator components or reinstall the official complete package. "
              "No game files are required to run this check.")
    )

    if not controller_enabled:
        gamepad = (
            "Controller input disabled",
            "Optional: enable it in the Controller panel or use keyboard controls.",
        )
    elif controller_detected:
        gamepad = (
            "Controller detected",
            "Open controller setup to test live buttons and choose a console mapping.",
        )
    else:
        gamepad = (
            "Waiting for controller",
            "Pair a compatible USB or Bluetooth controller, then choose Rescan.",
        )

    backend = (
        ("Embedded input path selected",
         "The selected game can use in-app keyboard and supported gamepad controls.")
        if embedded_mode
        else ("External game backend selected",
              "In-app controller inputs may not reach the external emulator. "
              "Check that emulator's own input configuration.")
    )

    return {
        "format": "anything-plays-setup-check",
        "version": 1,
        "console": system,
        "checks": {
            "camera": {"status": camera[0], "next": camera[1]},
            "emulator": {"status": core[0], "next": core[1]},
            "controller": {"status": gamepad[0], "next": gamepad[1]},
            "input_backend": {"status": backend[0], "next": backend[1]},
        },
    }
