"""Run an extended GUI memory soak with synthetic camera and game frames.

This exercises the actual Tk/PIL/OpenCV render loops without ROMs or camera
hardware. It is NOT proof that native N64/GameCube cores are leak-free. Run
locally on macOS, or under xvfb-run on Linux:

  PYTHONPATH=. python tests/soak_gui.py --seconds 3600 --report soak.json

The process reports resident memory growth after a brief warm-up, bounded
canvas item counts, and native Tk image reuse. Longer runs expose gradual
growth that a one-minute smoke test may not show.
"""
import argparse
import gc
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
import tracemalloc
from unittest.mock import patch

import numpy as np

from app import App


def rss_megabytes():
    """Report process RSS without requiring an extra installed dependency."""
    if sys.platform.startswith("linux"):
        try:
            pages = int(Path("/proc/self/statm").read_text().split()[1])
            return pages * os.sysconf("SC_PAGE_SIZE") / (1024 * 1024)
        except (OSError, ValueError, IndexError):
            return None
    if sys.platform == "darwin":
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
        except (ImportError, OSError):
            return None
    return None


class SyntheticCamera:
    """Reusable webcam buffer; OpenCV still performs the real UI processing."""

    def __init__(self):
        self.frame = np.zeros((160, 240, 3), dtype=np.uint8)
        self.opened = True
        self.frame_number = 0

    def isOpened(self):
        return self.opened

    def read(self):
        if not self.opened:
            return False, None
        self.frame_number += 1
        x = self.frame_number % self.frame.shape[1]
        self.frame[:, :, :] = 20
        self.frame[45:100, x:x + 5, :] = (50, 130, 225)
        return True, self.frame

    def release(self):
        self.opened = False


def soak(seconds, max_growth_mb, report_path, *, enable_gamepad=False):
    if seconds < 8:
        raise ValueError("Soak must run at least 8 seconds")
    tracemalloc.start()
    report = {"seconds_requested": seconds,
              "test_type": "synthetic Tk + OpenCV UI, not native emulator",
              "samples": [], "passed": False,
              "real_controller_hardware_tested": False,
              "physical_camera_tested": False,
              "gamepad_sdl_polling_requested": bool(enable_gamepad)}
    started = time.monotonic()
    warmup = min(15, max(3, seconds // 5))
    failures = []

    with tempfile.TemporaryDirectory(prefix="anything-plays-soak-") as home:
        with (patch("pathlib.Path.home", return_value=Path(home)),
              patch.object(App, "scan_cameras", lambda self: None),
              patch.object(App, "check_emulator_updates",
                           lambda self, automatic=False: None)):
            root = tk.Tk()
            app = App(root)
            # Exercise the real 3.1 SDL poll timer with synthetic video.
            # No USB/Bluetooth hardware, controller window or ROM is needed.
            if enable_gamepad:
                app.gamepad_enabled.set(True)
            camera = SyntheticCamera()
            app.cap = camera
            app.reference_image = False
            app.emu.running = True
            app.current_rom = "synthetic-frame.gba"
            frame_number = 0

            def emit_frame():
                nonlocal frame_number
                if app._closing:
                    return
                frame_number += 1
                frame = np.zeros((120, 160, 3), dtype=np.uint8)
                frame[:, :, 0] = frame_number % 256
                with app.emu.lock:
                    app.emu.frame = frame
                    app.emu.frame_serial += 1
                root.after(17, emit_frame)

            def sample():
                if app._closing:
                    return
                gc.collect()
                current, peak = tracemalloc.get_traced_memory()
                items_camera = len(app.canvas.find_all())
                items_game = len(app.game_canvas.find_all())
                after_jobs = len(root.tk.call("after", "info"))
                cache = len(app._zone_thumbnail_cache)
                sample_data = {
                    "seconds": round(time.monotonic() - started, 2),
                    "rss_mb": rss_megabytes(),
                    "python_heap_mb": round(current / (1024 * 1024), 2),
                    "python_peak_mb": round(peak / (1024 * 1024), 2),
                    "camera_items": items_camera,
                    "game_items": items_game,
                    "pending_tk_jobs": after_jobs,
                    "cached_zone_art": cache,
                    "gamepad_enabled": bool(app.gamepad_enabled.get()),
                    "sdl_backend_initialized": app._gamepad.api is not None,
                    "gamepad_connected": app._gamepad.controller is not None,
                }
                report["samples"].append(sample_data)
                if (enable_gamepad and sample_data["seconds"] >= warmup
                        and (not sample_data["gamepad_enabled"]
                             or not sample_data["sdl_backend_initialized"])):
                    failures.append("SDL controller polling stopped unexpectedly")
                    app.close()
                    return
                if (items_camera > 1 or items_game > 1 or
                        after_jobs > 32 or cache > 12 or
                        len(app.library_images) > 300):
                    failures.append("UI resource counts exceeded fixed bounds")
                    app.close()
                    return
                root.after(5000, sample)

            def shutdown():
                if not app._closing:
                    app.close()

            root.after(20, emit_frame)
            root.after(1000, sample)
            root.after(int(seconds * 1000), shutdown)
            try:
                root.mainloop()
            finally:
                if not app._closing:
                    app.close()
            report["frames_emitted"] = frame_number
            report["camera_frames"] = camera.frame_number

    samples = report["samples"]
    report["sdl_initialized_samples"] = sum(
        1 for sample in samples if sample["sdl_backend_initialized"])
    if enable_gamepad and report["sdl_initialized_samples"] < 2:
        failures.append("SDL controller backend did not sustain polling")
    baseline = next((s for s in samples if s["seconds"] >= warmup), None)
    if baseline is None and samples:
        baseline = samples[0]
    readings = [
        s["rss_mb"] for s in samples
        if s["rss_mb"] is not None and s["seconds"] >= warmup
    ]
    if baseline is not None and readings and baseline["rss_mb"] is not None:
        growth = max(0, max(readings) - baseline["rss_mb"])
        report["resident_growth_mb"] = round(growth, 2)
        if growth > max_growth_mb:
            failures.append(
                f"Resident memory rose {growth:.1f} MB after warm-up"
            )
    report["warmup_seconds"] = warmup
    report["growth_limit_mb"] = max_growth_mb
    report["errors"] = failures
    report["passed"] = not failures and bool(samples)
    result_path = Path(report_path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        key: report[key] for key in (
            "passed", "frames_emitted", "resident_growth_mb", "errors"
        ) if key in report
    }, indent=2), flush=True)
    return report["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--max-growth-mb", type=float, default=96.0)
    parser.add_argument("--enable-gamepad", action="store_true",
                        help="Exercise SDL polling without physical HID hardware")
    parser.add_argument("--report", default="soak-report.json")
    args = parser.parse_args()
    sys.exit(0 if soak(args.seconds, args.max_growth_mb, args.report,
                       enable_gamepad=args.enable_gamepad) else 1)
