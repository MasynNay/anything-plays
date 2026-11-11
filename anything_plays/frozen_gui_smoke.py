"""Actual frozen desktop Tk UI startup diagnostic, separate from the compact app entry point.

It never grants emulator binary distribution rights or tests physical cameras.
"""
import os
import sys
import tkinter as tk

def _exercise_installed_stream_mode(app):
    """Test the *frozen* DS output and settings without opening real devices.

    Invoked only for an explicit, disposable RC2 CI smoke. Never includes a
    real webcam frame, ROM, personal preference, or OBS capture process.
    """
    import numpy as np

    app.open_stream_mode()
    app.root.update_idletasks()
    output = getattr(app, "_stream_output_window", None)
    controls = getattr(app, "_stream_controls_window", None)
    canvas = getattr(app, "_stream_canvas", None)
    if (output is None or controls is None or canvas is None
            or not output.winfo_exists() or not controls.winfo_exists()
            or controls is output or canvas.master is not output):
        raise RuntimeError("Installed RC2 did not open separate stream windows")
    if len(canvas.find_all()) != 1:
        raise RuntimeError("Installed Stream Output has no composed display")

    variables = app._stream_vars
    variables["layout"].set("Side by side")
    variables["theme"].set("Ocean Dark")
    variables["frame_rate"].set("15 FPS")
    variables["game_size"].set(62.0)
    variables["border_width"].set(9.0)
    variables["swap_screens"].set(True)
    app.root.update_idletasks()
    app._render_stream_frame()
    options = app._stream_options
    if (options["layout"] != "Side by side"
            or options["theme"] != "Ocean Dark"
            or options["frame_rate"] != "15 FPS"
            or options["game_size"] != 62
            or options["border_width"] != 9
            or options["swap_screens"] is not True):
        raise RuntimeError("Installed stream customization did not take effect")

    frame = np.zeros((72, 96, 3), dtype=np.uint8)
    frame[:, :, 1] = 180
    app.reference_image = True
    app.frame = frame
    app.stream_camera_snapshot(frame)
    app._render_stream_frame()
    if (app._stream_photo is None
            or len(canvas.find_all()) != 1
            or app._stream_camera_frame is None):
        raise RuntimeError("Installed stream did not render synthetic camera frame")
    app.reference_image = False
    app.frame = None
    app.close_stream_mode()
    if (app._stream_output_window is not None
            or app._stream_controls_window is not None
            or app._stream_frame_job is not None
            or app._stream_photo is not None):
        raise RuntimeError("Installed stream left windows, timers or image buffers")

    return {
        "stream_output_window_opened": True,
        "stream_settings_separate": True,
        "stream_appearance_configured": True,
        "stream_camera_reference_rendered": True,
        "stream_closed_cleanly": True,
    }


def run_smoke_gui(app_type, systems):
    """Only CI's explicit opt-in: prove installed PyInstaller GUI opens.

    This executes the EXACT same Tk root and App initialization as normal
    gameplay. It then returns after one real GUI event-loop interval. Camera
    hardware is deliberately NOT tested in an unattended runner. The report
    describes only desktop window startup, not ROM compatibility or licensing.
    """
    import json
    from pathlib import Path
    import traceback

    report_name = os.environ.get("AP_V30_UI_SMOKE_REPORT", "")
    if os.environ.get("AP_V30_UI_SMOKE_CHECK") != "1" or not report_name:
        print("Installed window smoke mode requires explicit CI test opt-in",
              file=sys.stderr)
        return 2
    report = Path(report_name)
    if report.exists() or report.is_symlink():
        print("Startup report must not pre-exist", file=sys.stderr)
        return 2
    result = {
        "schema_version": 1,
        "status": "UNAPPROVED-3.0-INSTALLED-DESKTOP-STARTUP-CHECK",
        "passed": False,
        "actual_tk_window_started": False,
        "actual_app_initialized": False,
        "actual_tk_mainloop_ran": False,
        "frozen_binary": bool(getattr(sys, "frozen", False)),
        "camera_hardware_tested": False,
        "gameplay_hardware_tested": False,
        "physical_qa_approved": False,
        "public_distribution_approved": False,
        "error": None,
    }
    root = None
    app = None
    try:
        root = tk.Tk()
        result["actual_tk_window_started"] = True
        app = app_type(root)
        result["actual_app_initialized"] = True

        def callback_error(cls, value, tb):
            result["error"] = "".join(traceback.format_exception(cls, value, tb))[-9000:]
            try:
                root.quit()
            except tk.TclError:
                pass

        root.report_callback_exception = callback_error

        def finish():
            result["actual_tk_mainloop_ran"] = True
            if (root.winfo_exists()
                    and root.winfo_children()
                    and "Anything Plays" in root.title()
                    and app.system_key.get() in systems):
                result["passed"] = True
                result["initialized_system"] = app.system_key.get()
                result["top_level_widgets"] = len(root.winfo_children())
                result["console_profile_count"] = len(systems)
                if os.environ.get("AP_V31_STREAM_SMOKE_CHECK") == "1":
                    try:
                        result.update(_exercise_installed_stream_mode(app))
                    except Exception:
                        result["error"] = traceback.format_exc()[-9000:]
                        result["passed"] = False
            else:
                result["error"] = "Tk root/App did not render a live configured window"
            root.quit()

        root.after(1200, finish)
        root.mainloop()
    except BaseException:
        result["passed"] = False
        result["error"] = traceback.format_exc()[-9000:]
    finally:
        if root is not None:
            try:
                if app is not None:
                    app.close()
                else:
                    root.destroy()
            except Exception:
                if result["error"] is None:
                    result["error"] = traceback.format_exc()[-9000:]
                result["passed"] = False
        try:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")
        except OSError as exc:
            print(f"Cannot record installed desktop launch: {exc}", file=sys.stderr)
            return 1
    return 0 if result["passed"] else 1


