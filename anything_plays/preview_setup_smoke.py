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


def _exercise_installed_control_archive(app, root):
    """Use actual frozen Tk buttons to test 18-profile backup/restore/undo.

    All file pickers, confirmation dialogs and profiles are disposable. No
    physical camera, controller, real ROM or stable settings are accessed.
    """
    import copy
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from anything_plays.portable_profile_library import (
        load_library_archive, save_library_archive,
    )
    from anything_plays.system_profiles import BUTTONS_BY_SYSTEM

    if app.cap is not None or app.armed or app._gamepad.api is not None:
        raise RuntimeError("Control backup smoke requires no active devices")

    selected = app.system_key.get()
    if selected not in BUTTONS_BY_SYSTEM:
        raise RuntimeError("Frozen control backup has no selected console")

    with TemporaryDirectory(prefix="ap32-private-archive-smoke-") as td:
        base = Path(td)
        archive = base / "all-console-controls.json"
        tampered = base / "invalid-archive.json"

        # These are real Tk buttons owned by the installed application, not
        # direct calls to a mocked profile-controller implementation.
        with patch(
            "anything_plays.ui_profiles.filedialog.asksaveasfilename",
            return_value=str(archive),
        ):
            _click_button(root, "Back up all 18")
        if not archive.is_file():
            raise RuntimeError("Frozen profile backup did not create a file")

        exported = load_library_archive(archive)
        if set(exported) != set(BUTTONS_BY_SYSTEM):
            raise RuntimeError("Frozen backup omitted supported consoles")
        raw = archive.read_text("utf-8")
        # Restoring an identical backup is a no-op, not an extra disk write
        # or a prompt asking to replace controls that are already identical.
        with patch(
            "anything_plays.ui_profiles.filedialog.askopenfilename",
            return_value=str(archive),
        ), patch(
            "anything_plays.ui_profiles.messagebox.askyesno"
        ) as confirm_identical:
            _click_button(root, "Restore all 18")
        confirm_identical.assert_not_called()
        if "No changes were made" not in app.status.get():
            raise RuntimeError("Identical control backup did not skip restore")
        for forbidden in ("rom_directory", "zone_image", "controller_id",
                          "camera_frame", "saved_games"):
            if forbidden in raw:
                raise RuntimeError("Frozen backup contained nonportable state")

        # Deliberately change the active profile and a second console.
        # A batch restore must apply both, not only the visible console.
        others = [name for name in BUTTONS_BY_SYSTEM if name != selected]
        independent = others[-1]
        modified = copy.deepcopy(exported)
        for system in (selected, independent):
            old = modified[system].get("tolerance", 20)
            modified[system]["tolerance"] = old + 1 if old < 90 else old - 1
        save_library_archive(archive, modified)

        original = {
            name: app.profile_store.get(name)
            for name in BUTTONS_BY_SYSTEM
        }
        # The active console can have edited but not yet saved Tk controls.
        app.read_settings()
        original[selected] = copy.deepcopy(app.cfg)

        tampered.write_text(raw[:-1] + ",", "utf-8")
        with patch(
            "anything_plays.ui_profiles.filedialog.askopenfilename",
            return_value=str(tampered),
        ), patch(
            "anything_plays.ui_profiles.messagebox.showerror"
        ) as rejected:
            _click_button(root, "Restore all 18")
        if rejected.call_count != 1:
            raise RuntimeError("Corrupt full-profile backup was not rejected")
        for name in BUTTONS_BY_SYSTEM:
            if app.profile_store.get(name)["tolerance"] != original[name]["tolerance"]:
                raise RuntimeError("Invalid backup changed saved control data")

        with patch(
            "anything_plays.ui_profiles.filedialog.askopenfilename",
            return_value=str(archive),
        ), patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=False,
        ):
            _click_button(root, "Restore all 18")
        # ttk.Button.cget("state") may return a Tcl index object that
        # looks like "disabled" but does not compare equal to that string.
        # Ask Tk's state engine directly; this tests the actual button.
        if not app._undo_all_profile_restore_button.instate(["disabled"]):
            raise RuntimeError("Declined control restore enabled undo")
        for name in BUTTONS_BY_SYSTEM:
            if app.profile_store.get(name)["tolerance"] != original[name]["tolerance"]:
                raise RuntimeError("Declined backup changed saved profiles")

        with patch(
            "anything_plays.ui_profiles.filedialog.askopenfilename",
            return_value=str(archive),
        ), patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=True,
        ) as confirmed:
            _click_button(root, "Restore all 18")
        if confirmed.call_count != 1 or (
            "2 of 18" not in confirmed.call_args.args[1]
        ):
            raise RuntimeError("Restore preview did not name the two changes")

        for name in BUTTONS_BY_SYSTEM:
            expected = modified[name]["tolerance"]
            if app.profile_store.get(name)["tolerance"] != expected:
                raise RuntimeError("Full-profile restore did not apply atomically")
        if (app.cfg["tolerance"] != modified[selected]["tolerance"]
                or not app._undo_all_profile_restore_button.instate(["!disabled"])
                or app.armed):
            raise RuntimeError("Frozen restore left incorrect live/undo state")

        _click_button(root, "Undo all restore")
        for name in BUTTONS_BY_SYSTEM:
            if app.profile_store.get(name)["tolerance"] != original[name]["tolerance"]:
                raise RuntimeError("Undo all did not restore previous profiles")
        if (app.cfg["tolerance"] != original[selected]["tolerance"]
                or not app._undo_all_profile_restore_button.instate(["disabled"])
                or app.armed or app.cap is not None
                or app._gamepad.api is not None):
            raise RuntimeError("Frozen restore undo changed devices or controls")
    return True


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
    if set(quick._setup_readiness_vars) != {
            "emulator", "camera", "controller", "input_backend"}:
        raise RuntimeError("Frozen Get started lacks live readiness summary")
    _click_button(quick, "Refresh status")
    if (not quick._setup_readiness_vars["emulator"].get().startswith("Emulator:")
            or not quick._setup_readiness_vars["camera"].get().startswith("Camera:")):
        raise RuntimeError("Frozen readiness summary did not refresh")

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

    original_windows = _live_toplevels(root)
    original_traces = len(app.theme_name.trace_info())
    control_archive_verified = _exercise_installed_control_archive(app, root)
    if _live_toplevels(root) != original_windows:
        raise RuntimeError("Frozen control backup left a native Tk dialog")
    if len(app.theme_name.trace_info()) != original_traces:
        raise RuntimeError("Frozen control backup changed theme callbacks")
    initial_windows = _live_toplevels(root)
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
        # Source and frozen UI must agree: changing console releases even
        # an old valid cached game frame, Game-only output, and Stream Mode
        # pixel snapshots. Only synthetic pixels are used.
        import numpy as np
        from unittest.mock import Mock
        with app.emu.lock:
            app.emu.frame = np.zeros((8, 8, 3), dtype=np.uint8)
            old_serial = app.emu.frame_serial
        app.game_photo = object()
        app._last_game_render = ("previous game",)
        app._stream_game_frame = object()
        app._stream_game_serial = old_serial
        app._stream_last_render = ("previous stream",)
        app.game_bezel.set_active(True)
        with patch.object(app, "_game_only_canvas", Mock()) as other_canvas:
            app.system_key.set("snes")
            app.switch_system()
            other_canvas.delete.assert_called_with("all")
        with app.emu.lock:
            if app.emu.frame is not None or app.emu.frame_serial <= old_serial:
                raise RuntimeError("Frozen console switch retained old game frame")
        if (app.game_photo is not None
                or app._last_game_render is not None
                or app._stream_game_frame is not None
                or app._stream_game_serial is not None
                or app._stream_last_render is not None):
            raise RuntimeError("Frozen console switch retained cached game video")
        if app.game_bezel.active:
            raise RuntimeError("Frozen console switch retained active game bezel")
        # The same stale-frame guarantees must also hold on an ordinary
        # unload while the preview game window remains mounted.
        with app.emu.lock:
            app.emu.frame = np.zeros((8, 8, 3), dtype=np.uint8)
            old_serial = app.emu.frame_serial
        app.game_photo = object()
        app._stream_game_frame = object()
        app._stream_game_serial = old_serial
        app._stream_canvas_item = 9
        app._stream_photo = object()
        camera_reference = object()
        app._stream_camera_frame = camera_reference
        with patch.object(app, "_game_only_canvas", Mock()) as game_canvas, \
             patch.object(app, "_stream_canvas", Mock()) as stream_canvas:
            app.unload_rom()
            game_canvas.delete.assert_called_with("all")
            stream_canvas.delete.assert_called_with("all")
        if (app.emu.frame is not None or app.emu.frame_serial <= old_serial
                or app._stream_game_frame is not None
                or app._stream_photo is not None
                or app._stream_canvas_item is not None
                or app._stream_camera_frame is not camera_reference):
            raise RuntimeError("Frozen game unload left stale game video")
        if app.emu.find_system_core() is not None:
            raise RuntimeError("Limited 3.2 preview unexpectedly has an SNES core")
        # Refresh the real installed first-run window while a limited
        # console is selected, without starting any native game device.
        app.open_getting_started()
        quick = _active_window(app, "_quick_start_window")
        _click_button(quick, "Refresh status")
        if quick._setup_readiness_vars["emulator"].get() != (
                "Emulator: Not bundled in this 3.2 preview"):
            raise RuntimeError("Frozen Get started misreported preview core status")
        _click_button(quick, "Done")
        # Even a cached real executable must never count as the SNES
        # emulator. The diagnostic must resolve this console afresh.
        from anything_plays.ui_setup_diagnostics import _snapshot
        import sys
        with patch.object(app.emu, "core_path", sys.executable):
            observed = _snapshot(app)
        if observed["checks"]["emulator"]["status"] != "Not bundled in this 3.2 preview":
            raise RuntimeError("Frozen setup diagnostics trusted a stale core path")
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
        "v32_control_archive_roundtrip_verified": control_archive_verified,
    }
