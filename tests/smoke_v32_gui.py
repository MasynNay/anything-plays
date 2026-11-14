"""End-to-end 3.2 Tk setup smoke under a virtual display.

Run with:
    PYTHONPATH=. xvfb-run -a python tests/smoke_v32_gui.py

All configuration writes are redirected to a temporary home. No real webcam,
ROM file, joystick, network service, or third-party emulator is started.
The assertions establish real Tk widget behavior, NOT physical hardware QA.
"""

import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch

from app import App


def all_widgets(parent):
    for child in parent.winfo_children():
        yield child
        yield from all_widgets(child)


def click_named_button(window, name):
    found = [
        item for item in all_widgets(window)
        if isinstance(item, ttk.Button) and item.cget("text") == name
    ]
    if len(found) != 1:
        raise AssertionError(
            f"Expected exactly one {name!r} button, found {len(found)}"
        )
    found[0].invoke()


def smoke():
    with tempfile.TemporaryDirectory(prefix="anything-plays-v32-gui-") as home:
        with patch("pathlib.Path.home", return_value=Path(home)):
            with patch("anything_plays.ui_camera.discover", return_value=[]):
                with patch.dict(os.environ, {
                    "AP_V30_UI_SMOKE_CHECK": "1",
                    "AP_V32_PREVIEW": "1",
                }):
                    root = tk.Tk()
                    app = None
                    try:
                        app = App(root)
                        root.update_idletasks()
                        assert app.preferences_path.parent.name == (
                            "anything-plays-32-preview"
                        )
                        assert "3.2" in root.title()
                        assert not app.armed
                        assert app.cap is None
                        assert app._gamepad.api is None

                        # Camera refresh keeps a chosen device even if
                        # enumeration order changes. These names are mock
                        # data; no actual VideoCapture is ever created.
                        app.finish_scan([
                            (0, "Built-in camera"), (2, "USB camera"),
                        ])
                        app.camera_name.set("USB camera (device 2)")
                        app.finish_scan([
                            (2, "USB camera"), (0, "Built-in camera"),
                        ])
                        assert app.camera_name.get() == "USB camera (device 2)"
                        assert app.cap is None and not app.armed
                        app.finish_scan([(0, "Built-in camera")])
                        assert app.camera_name.get() == "Built-in camera (device 0)"
                        assert "no longer listed" in app.status.get()
                        app.finish_scan([])
                        assert not app.camera_name.get()
                        assert app.cap is None and not app.armed

                        # A single visible entry opens the unified first-run path.
                        click_named_button(root, "Get started")
                        root.update_idletasks()
                        launchpad = app._quick_start_window
                        assert launchpad is not None
                        assert launchpad.winfo_exists()
                        first_run_canvas = next(
                            item for item in all_widgets(launchpad)
                            if isinstance(item, tk.Canvas)
                        )
                        app.theme_name.set("Plum Dark")
                        root.update_idletasks()
                        assert first_run_canvas.cget("bg") == (
                            app.THEMES["Plum Dark"][1]
                        )
                        app.open_getting_started()
                        assert app._quick_start_window is launchpad

                        # Entering the color wizard does not open a webcam.
                        click_named_button(launchpad, "Calibrate camera (optional)")
                        root.update_idletasks()
                        assert app._calibration_window.winfo_exists()
                        assert app.cap is None
                        click_named_button(
                            app._calibration_window, "Check stationary jitter",
                        )
                        assert not app._calibration_stability_running
                        assert "Start the webcam" in (
                            app._calibration_stability_status.get()
                        )
                        app.toggle()
                        assert not app.armed
                        assert "Finish or cancel calibration" in app.action.get()
                        app.close_camera_calibration(restore=True)
                        assert app._calibration_window is None
                        assert not app.armed

                        # Controller guidance is display-only until activated.
                        click_named_button(launchpad, "Set up controller or keyboard")
                        root.update_idletasks()
                        assert app._controller_guide_window.winfo_exists()
                        assert app._gamepad.api is None
                        guide_canvas = next(
                            item for item in all_widgets(app._controller_guide_window)
                            if isinstance(item, tk.Canvas)
                        )
                        app.theme_name.set("Ocean Dark")
                        root.update_idletasks()
                        assert guide_canvas.cget("bg") == (
                            app.THEMES["Ocean Dark"][1]
                        )
                        app._controller_guide_close()
                        assert app._controller_guide_window is None

                        # Real Tk controller remapping window must work even
                        # with SDL disabled and NO controller attached.
                        app.open_controller_settings()
                        root.update_idletasks()
                        remap = app._gamepad_setup_window
                        assert remap is not None and remap.winfo_exists()
                        remap_canvases = [
                            item for item in all_widgets(remap)
                            if isinstance(item, tk.Canvas)
                        ]
                        assert len(remap_canvases) >= 2
                        app.theme_name.set("Light")
                        root.update_idletasks()
                        assert remap_canvases[-1].cget("bg") == (
                            app.THEMES["Light"][1]
                        )
                        assert any(
                            isinstance(item, ttk.LabelFrame)
                            and "QUICK REMAP" in item.cget("text")
                            for item in all_widgets(remap)
                        )
                        click_named_button(remap, "Press to assign")
                        assert app._controller_capture is None
                        click_named_button(remap, "Done")
                        assert app._gamepad_setup_window is None
                        assert app.gamepad_setup_canvas is None

                        # Local setup check may copy an allowlisted JSON report.
                        click_named_button(launchpad, "Check my setup")
                        root.update_idletasks()
                        checker = app._setup_diagnostics_window
                        assert checker.winfo_exists()
                        diag_canvas = next(
                            item for item in all_widgets(checker)
                            if isinstance(item, tk.Canvas)
                        )
                        app.theme_name.set("Ocean Dark")
                        root.update_idletasks()
                        assert diag_canvas.cget("bg") == (
                            app.THEMES["Ocean Dark"][1]
                        )
                        click_named_button(checker, "Copy safe report")
                        report = json.loads(root.clipboard_get())
                        assert report["console"] == app.system_key.get()
                        assert set(report["checks"]) == {
                            "camera", "emulator", "controller", "input_backend"
                        }
                        encoded = json.dumps(report)
                        assert home not in encoded
                        assert "No camera found" in encoded
                        click_named_button(checker, "Done")
                        assert app._setup_diagnostics_window is None

                        # Even with the full real Tk interface open, an
                        # unavailable 3.2 console must not call any native
                        # emulator or mistake a limited preview for damage.
                        previous_console = app.system_key.get()
                        app.system_key.set("snes")
                        app.switch_system()
                        try:
                            # Source Tk setup reports the selected console,
                            # not an unrelated cached native binary path.
                            from anything_plays.ui_setup_diagnostics import _snapshot
                            import sys
                            with patch.object(
                                app.emu, "find_system_core", return_value=None,
                            ), patch.object(
                                app.emu, "core_path", sys.executable,
                            ):
                                checked = _snapshot(app)
                                assert checked["checks"]["emulator"]["status"] == (
                                    "Not bundled in this 3.2 preview"
                                )
                                assert sys.executable not in json.dumps(checked)
                            with patch.object(
                                app.emu, "find_system_core", return_value=None,
                            ), patch.object(
                                app.emu, "start",
                                side_effect=AssertionError(
                                    "Unbundled core was started"
                                ),
                            ) as native_start, patch.object(
                                app.emu, "stop", wraps=app.emu.stop,
                            ) as native_stop, patch(
                                "anything_plays.ui_library.messagebox.showinfo",
                            ) as notice:
                                app.start_rom("fake-source-preview-game.sfc")
                            native_start.assert_not_called()
                            native_stop.assert_called_once()
                            assert app.emu.frame is None
                            notice.assert_called_once()
                            assert app.current_rom is None
                            assert "Not bundled in this 3.2 preview" in (
                                app.game_status.get()
                            )
                            assert "not a damaged installation" in (
                                notice.call_args.args[1]
                            )
                            # The worker retains its old ROM string after
                            # stop(); 3.2 must not relaunch it via Restart.
                            app.emu.rom = "stale-source-preview-game.gba"
                            app.retry_current_rom()
                            native_start.assert_not_called()
                            assert app.current_rom is None
                            assert "Choose a game ROM" in app.game_status.get()
                        finally:
                            app.system_key.set(previous_console)
                            app.switch_system()
                        assert not app.armed
                        assert app.cap is None

                        click_named_button(launchpad, "Done")
                        assert app._quick_start_window is None
                        assert not app.armed
                        assert app._gamepad.api is None
                    finally:
                        if app is not None:
                            app.close()
                        else:
                            root.destroy()


if __name__ == "__main__":
    smoke()
    print("Anything Plays 3.2: combined Tk setup smoke passed (no hardware)")
