"""Exercise the real 3.2 frozen setup windows, without touching hardware.

This module is called only from the explicit opt-in installed-GUI smoke
harness.  It does not open a camera, connect a controller, load a game or
approve a public build. The desktop source GUI smoke separately covers
interactive controller remapping and color sampling flows.
"""

import tkinter as tk
from tkinter import ttk

from anything_plays.build_identity import current_identity


def _active_window(app, attribute):
    window = getattr(app, attribute, None)
    if window is None or not window.winfo_exists():
        raise RuntimeError("Missing 3.2 setup window: " + attribute)
    return window


def _click_button(window, caption):
    """Invoke a native button, not internal close state or raw widget destroy."""
    found = []

    def walk(parent):
        for child in parent.winfo_children():
            if isinstance(child, ttk.Button) and child.cget("text") == caption:
                found.append(child)
            walk(child)

    walk(window)
    if len(found) != 1:
        raise RuntimeError(
            f"Expected one {caption!r} action in installed 3.2 setup, found {len(found)}"
        )
    found[0].invoke()


def exercise_installed_preview_setup(app, root):
    """Return explicit check results only if all four real dialogs round-trip."""
    if current_identity()["channel"] != "v32_preview":
        raise RuntimeError("Never run 3.2 GUI setup checks on stable identity")
    if (getattr(app, "cap", None) is not None
            or getattr(app, "armed", None) is not False
            or getattr(getattr(app, "_gamepad", None), "api", None) is not None):
        raise RuntimeError("Installed 3.2 setup must begin with devices disarmed")

    # Get started is the single onboarding entry. Verify the real native
    # window (not a mock) and close it through its own Done button.
    app.open_getting_started()
    root.update_idletasks()
    quick = _active_window(app, "_quick_start_window")
    app.open_getting_started()
    if _active_window(app, "_quick_start_window") is not quick:
        raise RuntimeError("Opening Get started twice created duplicate windows")

    # Calibration uses the already available main camera preview and can be
    # cancelled without opening a device or granting gameplay input.
    app.open_calibration_wizard()
    root.update_idletasks()
    calibration = _active_window(app, "_calibration_window")
    _click_button(calibration, "Check stationary jitter")
    if getattr(app, "_calibration_stability_running", False):
        raise RuntimeError("Disconnected preview started a jitter measurement")
    if "Start the webcam" not in app._calibration_stability_status.get():
        raise RuntimeError("Frozen calibration did not explain missing camera")
    app.close_camera_calibration(restore=True)
    if getattr(app, "_calibration_window", None) is not None:
        raise RuntimeError("Frozen calibration failed to close/rollback")

    app.open_controller_setup_guide()
    root.update_idletasks()
    _active_window(app, "_controller_guide_window")
    app._controller_guide_close()
    if getattr(app, "_controller_guide_window", None) is not None:
        raise RuntimeError("Frozen controller guide failed to close")

    app.open_controller_settings()
    root.update_idletasks()
    remap = _active_window(app, "_gamepad_setup_window")
    _click_button(remap, "Press to assign")
    if getattr(app, "_controller_capture", None) is not None:
        raise RuntimeError("Disconnected controller unexpectedly started capture")
    _click_button(remap, "Done")
    if getattr(app, "_gamepad_setup_window", None) is not None:
        raise RuntimeError("Frozen controller remapping failed to close")

    app.open_setup_diagnostics()
    root.update_idletasks()
    check = _active_window(app, "_setup_diagnostics_window")
    _click_button(check, "Done")
    if getattr(app, "_setup_diagnostics_window", None) is not None:
        raise RuntimeError("Frozen setup diagnostics failed to close")

    _click_button(quick, "Done")
    if getattr(app, "_quick_start_window", None) is not None:
        raise RuntimeError("Frozen Get started failed to close")
    if (app.cap is not None or app.armed is not False
            or app._gamepad.api is not None):
        raise RuntimeError("Preview setup unexpectedly activated gameplay devices")

    return {
        "v32_setup_windows_verified": True,
        "v32_setup_dialog_count": 5,
        "v32_setup_camera_untouched": True,
        "v32_setup_gamepad_untouched": True,
        "v32_setup_still_disarmed": True,
    }
