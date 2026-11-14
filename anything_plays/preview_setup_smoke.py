"""Exercise the real 3.2 frozen setup windows, without touching hardware.

This module is called only from the explicit opt-in installed-GUI smoke
harness.  It does not open a camera, connect a controller, load a game or
approve a public build. The desktop source GUI smoke separately covers
interactive controller remapping and color sampling flows.
"""

import tkinter as tk
from tkinter import ttk
from unittest.mock import patch

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


SETUP_LIFECYCLE_ROUNDS = 8
SETUP_DIALOGS_PER_ROUND = 5


def _live_toplevels(parent):
    """Collect all remaining native Tk dialogs, including nested children."""
    found = set()
    for child in parent.winfo_children():
        if isinstance(child, tk.Toplevel) and child.winfo_exists():
            found.add(str(child))
        found.update(_live_toplevels(child))
    return found


def _one_installed_setup_roundtrip(app, root):
    """Open/close five real dialogs, including the no-device safety checks."""
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


def exercise_installed_preview_setup(app, root):
    """Prove repeated setup use has no orphan Tk windows or theme callbacks."""
    if current_identity()["channel"] != "v32_preview":
        raise RuntimeError("Never run 3.2 GUI setup checks on stable identity")
    if (getattr(app, "cap", None) is not None
            or getattr(app, "armed", None) is not False
            or getattr(getattr(app, "_gamepad", None), "api", None) is not None):
        raise RuntimeError("Installed 3.2 setup must begin with devices disarmed")

    # Frozen installation, not just source mocks: changing the discovery
    # order cannot replace a user's selected USB webcam. Do not open devices.
    app.finish_scan([(0, "Built-in camera"), (2, "USB camera")])
    app.camera_name.set("USB camera (device 2)")
    app.finish_scan([(2, "USB camera"), (0, "Built-in camera")])
    if app.camera_name.get() != "USB camera (device 2)":
        raise RuntimeError("Camera refresh changed an existing chosen webcam")
    app.finish_scan([(0, "Built-in camera")])
    if (app.camera_name.get() != "Built-in camera (device 0)"
            or "no longer listed" not in app.status.get()):
        raise RuntimeError("Missing webcam was not clearly marked")
    app.finish_scan([])
    if app.camera_name.get() or app.cap is not None or app.armed:
        raise RuntimeError("Camera refresh opened or armed a substitute device")

    initial_windows = _live_toplevels(root)
    original_traces = len(app.theme_name.trace_info())
    for round_number in range(SETUP_LIFECYCLE_ROUNDS):
        _one_installed_setup_roundtrip(app, root)
        root.update_idletasks()
        if _live_toplevels(root) != initial_windows:
            raise RuntimeError(
                f"Frozen setup left a native Tk window after round {round_number + 1}"
            )
        if len(app.theme_name.trace_info()) != original_traces:
            raise RuntimeError(
                f"Frozen setup leaked a theme callback after round {round_number + 1}"
            )
        if (app.cap is not None or app.armed is not False
                or app._gamepad.api is not None):
            raise RuntimeError(
                "Repeated preview setup unexpectedly activated gameplay devices"
            )

    # A full application (3.1.1) includes more native cores, but this
    # preview intentionally has mGBA only. Verify that a real frozen App
    # refuses an unsupported console without trying to read even a dummy
    # ROM, launching a core or telling users the install is corrupted.
    old_system = app.system_key.get()
    try:
        app.system_key.set("snes")
        app.switch_system()
        if app.emu.find_system_core() is not None:
            raise RuntimeError("Limited 3.2 preview unexpectedly has an SNES core")
        with patch(
            "anything_plays.ui_library.messagebox.showinfo"
        ) as popup, patch.object(
            app.emu, "start", side_effect=RuntimeError(
                "Unbundled preview attempted to start a native emulator"
            )
        ) as native_start, patch.object(
            app.emu, "stop", wraps=app.emu.stop,
        ) as native_stop:
            app.start_rom("synthetic-unbundled-preview-game.sfc")
        native_start.assert_not_called()
        native_stop.assert_called_once()
        if app.emu.frame is not None:
            raise RuntimeError("Blocked preview launch retained stale native video")
        popup.assert_called_once()
        if app.current_rom is not None:
            raise RuntimeError("Unbundled preview kept a fake game as playable")
        if "Not bundled in this 3.2 preview" not in app.game_status.get():
            raise RuntimeError("Unbundled console showed an inaccurate error")
        if "not a damaged installation" not in popup.call_args.args[1]:
            raise RuntimeError("Missing preview core was reported as corruption")
        # Native stop() can preserve its previous ROM path. Do not let the
        # Restart button revive a game we already rejected and unloaded.
        app.emu.rom = "stale-frozen-preview-game.gba"
        app.retry_current_rom()
        native_start.assert_not_called()
        if app.current_rom is not None or "Choose a game ROM" not in app.game_status.get():
            raise RuntimeError("Blocked preview launch left a stale restart option")
    finally:
        app.system_key.set(old_system)
        app.switch_system()
    if app.cap is not None or app.armed is not False:
        raise RuntimeError("Core guidance changed camera input safety")

    return {
        "v32_unbundled_core_launch_safe": True,
        "v32_setup_windows_verified": True,
        "v32_setup_dialog_count": (
            SETUP_DIALOGS_PER_ROUND * SETUP_LIFECYCLE_ROUNDS
        ),
        "v32_setup_repeat_cycles": SETUP_LIFECYCLE_ROUNDS,
        "v32_setup_no_orphan_windows": True,
        "v32_setup_theme_traces_stable": True,
        "v32_setup_camera_untouched": True,
        "v32_setup_gamepad_untouched": True,
        "v32_setup_still_disarmed": True,
    }
