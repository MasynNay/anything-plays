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
    from anything_plays.portable_profiles import load_bundle, save_bundle
    from anything_plays.system_profiles import BUTTONS_BY_SYSTEM, default_for
    from anything_plays.settings_defaults import DEFAULT

    if app.cap is not None or app.armed or app._gamepad.api is not None:
        raise RuntimeError("Control backup smoke requires no active devices")

    selected = app.system_key.get()
    if selected not in BUTTONS_BY_SYSTEM:
        raise RuntimeError("Frozen control backup has no selected console")

    with TemporaryDirectory(prefix="ap32-private-archive-smoke-") as td:
        base = Path(td)
        archive = base / "all-console-controls.json"
        tampered = base / "invalid-archive.json"
        single_archive = base / "one-console-controls.json"
        standalone_export = base / "selected-console-export.json"

        # Export is a pure backup action. Verify the actual installed GUI
        # does not attempt a second write to the local profile store.
        with patch(
            "anything_plays.ui_profiles.filedialog.asksaveasfilename",
            return_value=str(standalone_export),
        ), patch.object(
            app.profile_store, "put",
            side_effect=RuntimeError("Export attempted local profile write"),
        ) as forbidden_write:
            _click_button(root, "Export controls")
        forbidden_write.assert_not_called()
        if not standalone_export.is_file():
            raise RuntimeError("Frozen Export controls created no portable file")
        exported_one, _theme, legacy_one = load_bundle(
            standalone_export, selected_system=selected,
            allowed_themes=app.THEMES,
        )
        if legacy_one or not exported_one["zones"]:
            raise RuntimeError("Frozen one-console export was not usable")
        file_text = standalone_export.read_text("utf-8")
        if any(key in file_text for key in (
                "zone_image", "rom_directory", "controller_id",
                "camera_frame", "saved_games")):
            raise RuntimeError("Frozen one-console export leaked private fields")

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
        untouched = next(name for name in others if name != independent)
        # These fields are local-only, absent from the portable archive.
        # Both affected and unaffected consoles must retain them.
        for name in (independent, untouched):
            local = app.profile_store.get(name)
            local["zone_image"] = f"local-only-{name}.png"
            app.profile_store.put(name, local)
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
        if any(
            app.profile_store.get(name).get("zone_image")
            != f"local-only-{name}.png"
            for name in (independent, untouched)
        ):
            raise RuntimeError("Full restore erased local-only console data")
        if (app.cfg["tolerance"] != modified[selected]["tolerance"]
                or not app._undo_all_profile_restore_button.instate(["!disabled"])
                or app.armed):
            raise RuntimeError("Frozen restore left incorrect live/undo state")

        # Post-restore user edits must not be silently discarded. A newer
        # local-only background, however, must survive an approved undo.
        newer = app.profile_store.get(independent)
        newer["zone_image"] = "newer-local-only-art.png"
        newer["tolerance"] = 48 if modified[independent]["tolerance"] != 48 else 49
        app.profile_store.put(independent, newer)
        with patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=False,
        ) as declined:
            _click_button(root, "Undo all restore")
        if declined.call_count != 1 or not app._undo_all_profile_restore_button.instate(["!disabled"]):
            raise RuntimeError("Undo conflict did not require approval")
        if (app.profile_store.get(independent)["tolerance"] != newer["tolerance"]
                or app.profile_store.get(independent)["zone_image"] != "newer-local-only-art.png"):
            raise RuntimeError("Declined undo discarded newer control edits")
        with patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=True,
        ) as accepted:
            _click_button(root, "Undo all restore")
        if (accepted.call_count != 1
                or "newer control edits" not in accepted.call_args.args[1]
                or "\n\n" not in accepted.call_args.args[1]):
            raise RuntimeError("Approved undo did not explain destructive changes")
        if (app.profile_store.get(independent).get("zone_image")
                != "newer-local-only-art.png"):
            raise RuntimeError("Undo erased a newer local-only background")
        if (app.profile_store.get(untouched).get("zone_image")
                != f"local-only-{untouched}.png"):
            raise RuntimeError("Undo changed an untouched console background")
        for name in BUTTONS_BY_SYSTEM:
            if app.profile_store.get(name)["tolerance"] != original[name]["tolerance"]:
                raise RuntimeError("Undo all did not restore previous profiles")
        if (app.cfg["tolerance"] != original[selected]["tolerance"]
                or not app._undo_all_profile_restore_button.instate(["disabled"])
                or app.armed or app.cap is not None
                or app._gamepad.api is not None):
            raise RuntimeError("Frozen restore undo changed devices or controls")

        # Repeat the important privacy and Undo checks with the one-console
        # UI. Portable files omit zone_image but must never erase its path.
        active = app.profile_store.get(selected)
        original_tolerance = active["tolerance"]
        active["zone_image"] = "my-local-background.png"
        app.profile_store.put(selected, active)
        app.cfg = app.profile_store.get(selected)
        app.refresh_settings()
        imported = copy.deepcopy(app.cfg)
        imported["tolerance"] = (
            original_tolerance + 2 if original_tolerance <= 88
            else original_tolerance - 2
        )
        save_bundle(single_archive, selected, imported)
        with patch(
            "anything_plays.ui_profiles.filedialog.askopenfilename",
            return_value=str(single_archive),
        ), patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=True,
        ) as confirmed_import:
            _click_button(root, "Import controls")
        if confirmed_import.call_count != 1:
            raise RuntimeError("Single-console import lacked confirmation")
        if (app.profile_store.get(selected)["zone_image"]
                != "my-local-background.png"):
            raise RuntimeError("Single-console import erased local artwork")
        if (app.profile_store.get(selected)["tolerance"]
                != imported["tolerance"]):
            raise RuntimeError("Single-console import did not apply controls")
        if not app._undo_import_button.instate(["!disabled"]):
            raise RuntimeError("Single-console import did not offer Undo")

        # A later control edit must cause Undo to ask rather than silently
        # losing the new value. A local-only background must never be undone.
        newer_tolerance = 47 if imported["tolerance"] != 47 else 48
        app.tolerance.set(newer_tolerance)
        app.zone_image_path.set("my-newer-local-background.png")
        with patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=False,
        ) as declined_single:
            _click_button(root, "Undo import")
        if declined_single.call_count != 1:
            raise RuntimeError("Single-console Undo did not warn about new edits")
        if app.tolerance.get() != newer_tolerance:
            raise RuntimeError("Declined single-console Undo discarded new edits")
        with patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=True,
        ) as accepted_single:
            _click_button(root, "Undo import")
        if accepted_single.call_count != 1:
            raise RuntimeError("Single-console Undo did not require approval")
        if (app.profile_store.get(selected)["tolerance"] != original_tolerance
                or app.profile_store.get(selected)["zone_image"]
                != "my-newer-local-background.png"
                or not app._undo_import_button.instate(["disabled"])):
            raise RuntimeError("Single-console Undo lost local data or old controls")
        if app.armed or app.cap is not None or app._gamepad.api is not None:
            raise RuntimeError("Single-console import activated gameplay devices")

        # An atomic preference write can fail AFTER the control profile was
        # stored. A strict import transaction must restore the old profile.
        before_failed_import = app.profile_store.get(selected)
        with patch(
            "anything_plays.ui_profiles.filedialog.askopenfilename",
            return_value=str(single_archive),
        ), patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=True,
        ), patch(
            "anything_plays.ui_profiles.write_json_atomically",
            side_effect=OSError("private simulated disk failure"),
        ), patch(
            "anything_plays.ui_profiles.messagebox.showerror",
        ) as save_failed:
            _click_button(root, "Import controls")
        if save_failed.call_count != 1:
            raise RuntimeError("A failed preferences write was not reported")
        if app.profile_store.get(selected) != before_failed_import:
            raise RuntimeError("A failed preference write retained imported controls")
        if app.armed or app.cap is not None or app._gamepad.api is not None:
            raise RuntimeError("Failed preference write activated gameplay")

        # Reset only portable controls. The same actual installed Tk button
        # must ask before discarding layout edits and retain local artwork.
        reset_source = app.profile_store.get(selected)
        reset_source["tolerance"] = (
            69 if default_for(selected, DEFAULT)["tolerance"] != 69 else 68
        )
        reset_source["zone_image"] = "local-before-reset.png"
        app.profile_store.put(selected, reset_source)
        app.cfg = app.profile_store.get(selected)
        app.refresh_settings()
        app.zone_image_path.set("new-unsaved-local-artwork.png")
        with patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=False,
        ) as declined_reset:
            _click_button(root, "Reset controls")
        if declined_reset.call_count != 1:
            raise RuntimeError("Frozen reset did not request confirmation")
        if app.profile_store.get(selected)["tolerance"] != reset_source["tolerance"]:
            raise RuntimeError("Declined reset changed stored controls")
        with patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=True,
        ) as accepted_reset:
            _click_button(root, "Reset controls")
        if accepted_reset.call_count != 1:
            raise RuntimeError("Frozen reset did not require approval")
        after_reset = app.profile_store.get(selected)
        if (after_reset["tolerance"] != default_for(selected, DEFAULT)["tolerance"]
                or after_reset.get("zone_image") != "new-unsaved-local-artwork.png"
                or app.armed or app.cap is not None
                or app._gamepad.api is not None):
            raise RuntimeError("Frozen reset erased local artwork or activated input")
        # Undo reset must recover the original controls without undoing
        # subsequent artwork changes or silently discarding newer controls.
        if not app._undo_profile_reset_button.instate(["!disabled"]):
            raise RuntimeError("Frozen reset failed to offer Undo")
        app.zone_image_path.set("artwork-after-reset.png")
        app.tolerance.set(
            49 if default_for(selected, DEFAULT)["tolerance"] != 49 else 48
        )
        with patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=False,
        ) as decline_undo_reset:
            _click_button(root, "Undo reset")
        if decline_undo_reset.call_count != 1:
            raise RuntimeError("Frozen Undo reset discarded newer control edits")
        with patch(
            "anything_plays.ui_profiles.messagebox.askyesno",
            return_value=True,
        ) as approve_undo_reset:
            _click_button(root, "Undo reset")
        if approve_undo_reset.call_count != 1:
            raise RuntimeError("Frozen Undo reset lacked conflict confirmation")
        after_undo_reset = app.profile_store.get(selected)
        if (after_undo_reset["tolerance"] != reset_source["tolerance"]
                or after_undo_reset["zone_image"] != "artwork-after-reset.png"
                or not app._undo_profile_reset_button.instate(["disabled"])
                or app.armed or app.cap is not None
                or app._gamepad.api is not None):
            raise RuntimeError("Frozen Undo reset failed to restore controls safely")
    return True


def _exercise_installed_artwork_downloads(app):
    """Prove the actual frozen URL action keeps separate images per console.

    Synthetic PNG responses are injected, so no network traffic, webcam,
    ROM or controller hardware is involved in this acceptance check.
    """
    import io
    from pathlib import Path
    from PIL import Image

    initial = app.system_key.get()
    other = "snes" if initial != "snes" else "gba"

    def download_color(system, rgb):
        source = io.BytesIO()
        Image.new("RGB", (3, 4), rgb).save(source, format="PNG")
        source.seek(0)
        with patch(
            "anything_plays.ui_zones.simpledialog.askstring",
            return_value=f"https://example.invalid/{system}.png",
        ), patch(
            "anything_plays.ui_zones.urllib.request.urlopen",
            return_value=source,
        ) as network, patch(
            "anything_plays.ui_zones.messagebox.showerror",
        ) as errors:
            app.ask_zone_url()
        network.assert_called_once()
        errors.assert_not_called()
        cache = Path(app.zone_image_path.get())
        if cache.name != f"zone-art-{system}.png":
            raise RuntimeError("Frozen preview used a shared artwork filename")
        if cache.parent != app.preferences_path.parent or not cache.is_file():
            raise RuntimeError("Frozen artwork escaped private preview settings")
        with Image.open(cache) as saved:
            if saved.getpixel((0, 0)) != rgb:
                raise RuntimeError("Frozen artwork colors changed after caching")
        return cache

    try:
        first = download_color(initial, (14, 44, 190))
        original_bytes = first.read_bytes()
        app.system_key.set(other)
        if app.switch_system() is not True:
            raise RuntimeError("Frozen preview could not select second console")
        second = download_color(other, (205, 112, 18))
        if first == second or first.read_bytes() != original_bytes:
            raise RuntimeError("Second console overwrote first console artwork")
        app.system_key.set(initial)
        if app.switch_system() is not True:
            raise RuntimeError("Frozen preview could not restore first console")
        if app.zone_image_path.get() != str(first):
            raise RuntimeError("Frozen console switch lost prior artwork path")
    finally:
        if app.system_key.get() != initial:
            app.system_key.set(initial)
            app.switch_system()
    if app.cap is not None or app.armed or app._gamepad.api is not None:
        raise RuntimeError("Artwork download unexpectedly activated hardware")
    return True


def _exercise_installed_failed_console_switch(app):
    """An unreadable incoming console may not replace the running one.

    Uses the real frozen App and Tcl selector, with an injected profile-store
    read error. No ROM, native core, camera or controller is started.
    """
    import copy

    previous = app.system_key.get()
    incoming = "snes" if previous != "snes" else "gba"
    app.read_settings(previous)
    before = copy.deepcopy(app.cfg)
    before_system = app.emu.system
    before_description = app.system_description.cget("text")
    before_rom = app.current_rom
    with patch.object(
        app.profile_store, "get",
        side_effect=OSError("synthetic unavailable destination"),
    ), patch.object(
        app.emu, "stop",
        side_effect=AssertionError("Failed switch stopped the current game"),
    ) as no_native_stop, patch.object(
        app, "stop_external_emulator",
        side_effect=AssertionError("Failed switch stopped external game"),
    ) as no_external_stop:
        app.system_key.set(incoming)
        result = app.switch_system()
    no_native_stop.assert_not_called()
    no_external_stop.assert_not_called()
    if result is not False or app.system_key.get() != previous:
        raise RuntimeError("Failed frozen profile read changed selected console")
    if app._active_profile_system != previous or app.emu.system != before_system:
        raise RuntimeError("Failed frozen profile switch changed native system")
    if app.system_description.cget("text") != before_description:
        raise RuntimeError("Failed frozen switch changed the console label")
    if app.current_rom != before_rom or app.cfg != before:
        raise RuntimeError("Failed frozen switch discarded previous controls")
    if app.cap is not None or app.armed or app._gamepad.api is not None:
        raise RuntimeError("Failed console switch unexpectedly enabled input")
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
    private_artwork_verified = _exercise_installed_artwork_downloads(app)
    rejected_switch_verified = _exercise_installed_failed_console_switch(app)
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

    # A real packaged Tk app must remain alive when shutdown persistence
    # fails and the player declines to lose unsaved camera-control edits.
    # Use the actual App.close callback (with a synthetic disk failure);
    # the frozen runner must retain this root for reporting afterward.
    with patch.object(
        app, "persist_on_exit",
        side_effect=OSError("private fake disk failure"),
    ), patch(
        "anything_plays.ui_profiles.messagebox.askyesno", return_value=False,
    ) as decline:
        canceled = app.close()
    if (canceled is not False or decline.call_count != 1
            or "Exit without saving?" not in decline.call_args.args[1]
            or app._closing or not root.winfo_exists()):
        raise RuntimeError("Frozen app discarded an unsaved profile on exit")
    if (app.cap is not None or app.armed is not False
            or app._gamepad.api is not None):
        raise RuntimeError("Frozen shutdown guard unexpectedly activated devices")

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
        "v32_reset_undo_verified": control_archive_verified,
        "v32_console_artwork_isolation_verified": private_artwork_verified,
        "v32_failed_console_switch_recovery_verified": rejected_switch_verified,
        "v32_single_control_export_isolated": True,
        "v32_unsaved_shutdown_guard_verified": True,
    }
