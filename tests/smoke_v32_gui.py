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
