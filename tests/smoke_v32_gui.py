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
                with patch.dict(os.environ, {"AP_V30_UI_SMOKE_CHECK": "1"}):
                    root = tk.Tk()
                    app = None
                    try:
                        app = App(root)
                        root.update_idletasks()
                        assert not app.armed
                        assert app.cap is None
                        assert app._gamepad.api is None

                        # A single visible entry opens the unified first-run path.
                        click_named_button(root, "Get started")
                        root.update_idletasks()
                        launchpad = app._quick_start_window
                        assert launchpad is not None
                        assert launchpad.winfo_exists()
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
                        app._controller_guide_close()
                        assert app._controller_guide_window is None

                        # Local setup check may copy an allowlisted JSON report.
                        click_named_button(launchpad, "Check my setup")
                        root.update_idletasks()
                        checker = app._setup_diagnostics_window
                        assert checker.winfo_exists()
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
