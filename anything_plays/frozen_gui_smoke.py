"""Actual frozen desktop Tk UI startup diagnostic, separate from the compact app entry point.

It never grants emulator binary distribution rights or tests physical cameras.
"""
import os
import sys
import tkinter as tk

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


