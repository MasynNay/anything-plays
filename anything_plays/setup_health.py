"""Local, strictly redacted setup checks for Anything Plays 3.2.

The report contains only an allowlisted console ID and small state labels.
It never records filesystem paths, ROM names, camera names, frames, Bluetooth
identifiers, or other user data. The UI copies it only after a user action.
"""

from anything_plays.system_profiles import BUTTONS_BY_SYSTEM


# The 3.2 QA installers have 18 setup profiles but only one native core,
# mGBA. Keep every preview-specific help message consistent with this
# intentionally narrow shipping inventory, not the full 3.1.1 release.
PREVIEW_BUNDLED_SYSTEMS = frozenset(("gb", "gbc", "gba"))


def preview_missing_core_guidance(system):
    """Return (status, next step) only; never inspect private ROM paths."""
    if system not in BUTTONS_BY_SYSTEM:
        raise ValueError("Choose a supported console before checking a core.")
    if system in PREVIEW_BUNDLED_SYSTEMS:
        return (
            "Preview mGBA emulator file missing",
            "GB, GBC and GBA are intended to use bundled mGBA in this 3.2 "
            "test installer. If it is missing, check this preview installation "
            "or its emulator components; a source checkout must supply a "
            "compatible mGBA core. Stable 3.1.1 is installed separately.",
        )
    return (
        "Not bundled in this 3.2 preview",
        "This test installer bundles mGBA for GB, GBC and GBA only. "
        "Other console profiles are visible, but their native emulator "
        "cores are not bundled. This is not a damaged installation. "
        "Choose GB, GBC or GBA for bundled gameplay, or wait for a "
        "reviewed full-core preview. Stable 3.1.1 is unaffected.",
    )


def build_setup_report(
    *, system, camera_count, camera_selected, camera_active,
    core_found, controller_enabled, controller_detected, embedded_mode,
    preview_minimal=False,
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

    if not embedded_mode:
        core = (
            "External emulator mode",
            "An embedded core check is not a valid readiness test here. "
            "Verify your external emulator configuration and input settings."
        )
    elif core_found:
        core = (
            "Core file located",
            "An emulator core file is present. This does not verify game compatibility."
        )
    elif preview_minimal:
        core = preview_missing_core_guidance(system)
    else:
        core = (
            "Core file not located",
            "Check installed emulator components or reinstall the official "
            "complete package. No game files are required to run this check."
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
