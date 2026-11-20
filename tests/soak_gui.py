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
from anything_plays.soak_health import (
    completion_failures, stream_target_is_valid,
    stream_canvas_sample_failures,
)


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


def soak(seconds, max_growth_mb, report_path, *, enable_gamepad=False,
         enable_stream=False, stress_stream=False):
    if seconds < 8:
        raise ValueError("Soak must run at least 8 seconds")
    if stress_stream and not enable_stream:
        raise ValueError("Stream transition stress requires --enable-stream")
    if stress_stream and seconds < 40:
        raise ValueError("Stream fault recovery stress requires at least 40 seconds")
    tracemalloc.start()
    report = {"seconds_requested": seconds,
              "test_type": "synthetic Tk + OpenCV UI, not native emulator",
              "samples": [], "passed": False,
              "real_controller_hardware_tested": False,
              "physical_camera_tested": False,
              "stream_mode_requested": bool(enable_stream),
              "stream_transition_stress_requested": bool(stress_stream),
              "real_stream_hardware_tested": False,
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
            # Tk logs callback errors by default and continues mainloop;
            # without this hook a broken timer can look like a green soak.
            callback_errors = []

            def capture_tk_callback_error(error_type, error, traceback):
                # Native driver exceptions may contain user paths, camera
                # names or serials. Reports must retain only fixed classes.
                name = getattr(error_type, "__name__", "UnexpectedError")
                if name not in (
                    "OSError", "RuntimeError", "ValueError", "TypeError",
                    "TclError", "MemoryError", "IndexError", "AttributeError",
                    "Exception", "KeyError",
                ):
                    name = "UnexpectedError"
                callback_errors.append("Tk callback raised " + name)
                if not app._closing:
                    app.close()

            root.report_callback_exception = capture_tk_callback_error
            # Exercise the real 3.1 SDL poll timer with synthetic video.
            # No USB/Bluetooth hardware, controller window or ROM is needed.
            if enable_gamepad:
                app.gamepad_enabled.set(True)
            camera = SyntheticCamera()
            app.cap = camera
            app.reference_image = False
            app.emu.running = True
            app.current_rom = "synthetic-frame.gba"
            # Optional 3.3 QA runs the REAL Tk Stream Mode output window
            # alongside game/camera/SDL, without any native ROM or webcam.
            if enable_stream:
                app.open_stream_mode()
            frame_number = 0
            stream_stress_cycles = 0
            stream_controls_updates = 0
            stream_camera_clears = 0
            last_stream_privacy_clear_at = None
            stream_privacy_clear_checks = 0
            stream_privacy_clear_failures = 0
            stream_fault_injected = False
            stream_fault_blanked = False
            stream_fault_counted = False
            stream_fault_recovered = False
            stream_prior_publications = 0
            visited_rates = set()
            visited_layouts = set()

            def stress_stream_transitions():
                """Exercise actual Tk resize, mode switches and camera resets.

                This never restarts the capture backend or native game input.
                Only the optional output configuration and preview are
                manipulated, as users do during long OBS sessions.
                """
                nonlocal stream_stress_cycles, stream_camera_clears
                nonlocal stream_controls_updates, last_stream_privacy_clear_at
                nonlocal stream_privacy_clear_checks, stream_privacy_clear_failures
                if app._closing or not enable_stream:
                    return
                index = stream_stress_cycles
                rate = ("15 FPS", "24 FPS", "30 FPS")[index % 3]
                layout = ("DS stacked", "Side by side")[index % 2]
                visited_rates.add(rate)
                visited_layouts.add(layout)
                # Drive the *actual* traced Tk StringVar/DoubleVar/BooleanVar
                # controls, not internal _stream_options dict mutations.
                # This exercises scheduling, validation, layout geometry,
                # visual-only camera-pixel reuse and deferred preference save
                # while the real Tk webcam/game timers remain active.
                options = (
                    ("frame_rate", rate),
                    ("layout", layout),
                    ("swap_screens", bool(index % 2)),
                    ("theme", "Ocean Dark" if index % 2 else "Dark"),
                    ("border_width", 2 + (index * 3) % 15),
                    ("game_size", 35 + (index * 7) % 31),
                )
                for key, value in options:
                    control = app._stream_vars[key]
                    control.set(value)
                    stream_controls_updates += 1
                    if app._stream_options[key] != value:
                        failures.append(
                            "Stream control trace failed to apply " + key
                        )
                        app.close()
                        return
                window = app._stream_output_window
                if window is not None:
                    window.geometry(
                        "760x840" if layout == "DS stacked"
                        else "1120x660"
                    )
                if index % 4 == 0:
                    # Simulate a preview reset, not an actual webcam unplug.
                    # The very next source frame should publish a fresh image.
                    # Privacy revocation deliberately removes OBS-facing
                    # camera pixels. A resource sample during the short
                    # blank is not a leak; an output that does not recover
                    # within 2.5 seconds IS a regression.
                    last_stream_privacy_clear_at = time.monotonic()
                    app.stream_clear_camera()
                    stream_camera_clears += 1

                    def verify_privacy_clear_recovered():
                        nonlocal stream_privacy_clear_checks
                        nonlocal stream_privacy_clear_failures
                        if app._closing:
                            return
                        stream_privacy_clear_checks += 1
                        canvas = getattr(app, "_stream_canvas", None)
                        if (canvas is None
                                or len(canvas.find_all()) != 1
                                or getattr(app, "_stream_photo", None) is None):
                            stream_privacy_clear_failures += 1
                            failures.append(
                                "Stream output failed to recompose after privacy clear"
                            )
                            app.close()
                    root.after(2500, verify_privacy_clear_recovered)
                stream_stress_cycles += 1
                root.after(8000, stress_stream_transitions)

            def inject_stream_fault():
                """Inject exactly one compositor failure into the real Tk job.

                A synthetic exception never touches the camera read loop,
                emulator's native input buffers or the Stream Settings UI.
                The next scheduled capture should blank the OBS-facing canvas
                and its 1-second retry should then publish a new frame.
                """
                nonlocal stream_fault_injected, stream_prior_publications
                if app._closing or app._stream_output_window is None:
                    return
                report_before = app.stream_performance_snapshot()
                stream_prior_publications = report_before["metrics"][
                    "stream_published_images"
                ]
                def fail_once():
                    # Reinstall the original class method immediately. The
                    # error itself must be handled by StreamMixin's Tk timer.
                    del app._render_stream_frame
                    raise RuntimeError("Synthetic Stream Mode compositor fault")

                app._render_stream_frame = fail_once
                stream_fault_injected = True

                def inspect_blanked():
                    nonlocal stream_fault_blanked, stream_fault_counted
                    if app._closing or app._stream_canvas is None:
                        return
                    items = len(app._stream_canvas.find_all())
                    stream_fault_blanked = (
                        items == 0 and app._stream_photo is None
                    )
                    report_now = app.stream_performance_snapshot()
                    stream_fault_counted = (
                        report_now["metrics"]["stream_session_faults"] >= 1
                        and report_now["metrics"]["stream_recovery_pending"]
                    )

                def inspect_recovery():
                    nonlocal stream_fault_recovered
                    if app._closing or app._stream_canvas is None:
                        return
                    publication = app.stream_performance_snapshot()["metrics"][
                        "stream_published_images"
                    ]
                    metrics = app.stream_performance_snapshot()["metrics"]
                    stream_fault_recovered = (
                        len(app._stream_canvas.find_all()) == 1
                        and app._stream_photo is not None
                        and publication > stream_prior_publications
                        and metrics["stream_session_recoveries"] >= 1
                        and not metrics["stream_recovery_pending"]
                    )

                root.after(700, inspect_blanked)
                root.after(2500, inspect_recovery)

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
                stream_canvas = getattr(app, "_stream_canvas", None)
                stream_items = (
                    len(stream_canvas.find_all())
                    if stream_canvas is not None else 0
                )
                stream_report = (
                    app.stream_performance_snapshot()
                    if enable_stream else None
                )
                stream_metrics = (
                    stream_report["metrics"] if stream_report else {}
                )
                panel_cache = getattr(app, "_stream_resize_cache", None)
                resized_panels = (
                    len(panel_cache._entries) if panel_cache is not None else 0
                )
                observed = time.monotonic()
                recent_privacy_clear = (
                    stress_stream and stream_items == 0
                    and getattr(app, "_stream_photo", None) is None
                    and not getattr(app, "_stream_recovery_pending", False)
                    and last_stream_privacy_clear_at is not None
                    and 0 <= observed - last_stream_privacy_clear_at <= 2.0
                )
                sample_data = {
                    "seconds": round(observed - started, 2),
                    "rss_mb": rss_megabytes(),
                    "python_heap_mb": round(current / (1024 * 1024), 2),
                    "python_peak_mb": round(peak / (1024 * 1024), 2),
                    "camera_items": items_camera,
                    "game_items": items_game,
                    "stream_items": stream_items,
                    # A boolean QA-only reason; no webcam images or
                    # camera-reset timestamps are stored in the receipt.
                    "stream_recent_privacy_clear": bool(recent_privacy_clear),
                    "stream_resize_cache_items": resized_panels,
                    "stream_refresh_intervals": stream_metrics.get(
                        "stream_refresh_intervals", 0
                    ),
                    "stream_published_images": stream_metrics.get(
                        "stream_published_images", 0
                    ),
                    "stream_failed_ticks": stream_metrics.get(
                        "stream_failed_ticks", 0
                    ),
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
                if (items_camera > 1 or items_game > 1
                        or stream_items > 1 or resized_panels > 2 or
                        after_jobs > 32 or cache > 12 or
                        len(app.library_images) > 300):
                    failures.append("UI resource counts exceeded fixed bounds")
                    app.close()
                    return
                root.after(5000, sample)

            def shutdown():
                if not app._closing:
                    if enable_stream:
                        # Stream close intentionally clears all live
                        # counters. Preserve only numeric aggregate evidence
                        # before shutdown, never images or Tk objects.
                        report["stream_final"] = (
                            app.stream_performance_snapshot()
                        )
                    app.close()

            root.after(20, emit_frame)
            if stress_stream:
                root.after(2000, stress_stream_transitions)
                # Transitions occur at 2, 10, 18, 26 ... seconds. Inject
                # at precisely 22 seconds for both 45s and 1800s stress:
                # the 1-second retry and recovered frame precede the next
                # 15/24/30 FPS counter reset at 26 seconds.
                root.after(22000, inject_stream_fault)
            root.after(1000, sample)
            root.after(int(seconds * 1000), shutdown)
            try:
                root.mainloop()
            finally:
                if not app._closing:
                    app.close()
            report["frames_emitted"] = frame_number
            report["camera_frames"] = camera.frame_number
            report["stream_stress_cycles"] = stream_stress_cycles
            report["stream_controls_updates"] = stream_controls_updates
            report["stream_forced_preview_clears"] = stream_camera_clears
            report["stream_privacy_clear_checks"] = stream_privacy_clear_checks
            report["stream_privacy_clear_failures"] = stream_privacy_clear_failures
            report["stream_fault_injected"] = stream_fault_injected
            report["stream_fault_blanked"] = stream_fault_blanked
            report["stream_fault_counted"] = stream_fault_counted
            report["stream_fault_recovered"] = stream_fault_recovered
            report["stream_rates_visited"] = sorted(visited_rates)
            report["stream_layouts_visited"] = sorted(visited_layouts)

    elapsed_real_seconds = time.monotonic() - started
    report["elapsed_real_seconds"] = round(elapsed_real_seconds, 2)
    report["tk_callback_exception_count"] = len(callback_errors)
    failures.extend(completion_failures(
        seconds, elapsed_real_seconds, report["samples"], callback_errors,
    ))
    samples = report["samples"]
    report["sdl_initialized_samples"] = sum(
        1 for sample in samples if sample["sdl_backend_initialized"])
    if enable_gamepad and report["sdl_initialized_samples"] < 2:
        failures.append("SDL controller backend did not sustain polling")
    if enable_stream:
        final = report.get("stream_final")
        summary = final["metrics"] if isinstance(final, dict) else {}
        if (not summary
                or not stream_target_is_valid(
                    summary.get("stream_target_refresh_fps"),
                    stress_stream=stress_stream,
                )
                or summary.get("stream_refresh_intervals", 0) < 2
                or summary.get("stream_published_images", 0) < 2):
            failures.append(
                "Stream Mode did not sustain Tk refresh and output images"
            )
        if summary.get("stream_failed_ticks", 0):
            failures.append("Stream Mode output encountered failed Tk ticks")
        failures.extend(stream_canvas_sample_failures(
            samples, warmup, stress_stream=stress_stream
        ))
        report["stream_transient_privacy_blanks"] = sum(
            s["stream_items"] == 0
            and s["stream_recent_privacy_clear"] is True
            and s["seconds"] >= warmup
            for s in samples
        )
        if stress_stream:
            if (report.get("stream_privacy_clear_failures", 0)
                    or report.get("stream_privacy_clear_checks", 0)
                    < report.get("stream_forced_preview_clears", 0) - 1):
                failures.append(
                    "Stream privacy-clear output recovery was not verified"
                )
            # Stress must actually exercise transitions; a green idle soak
            # with a broken timer is not representative of long streaming.
            expected = max(1, (seconds - 10) // 8)
            if report.get("stream_stress_cycles", 0) < expected:
                failures.append("Stream transition stress timer did not progress")
            if report.get("stream_controls_updates", 0) < 6 * expected:
                failures.append("Traced Tk Stream Settings were not exercised")
            if set(report.get("stream_rates_visited", [])) != {
                "15 FPS", "24 FPS", "30 FPS"
            }:
                failures.append("Stream stress did not exercise all rates")
            if set(report.get("stream_layouts_visited", [])) != {
                "DS stacked", "Side by side"
            }:
                failures.append("Stream stress did not exercise both layouts")
            if report.get("stream_forced_preview_clears", 0) < 2:
                failures.append("Stream camera preview reset was not exercised")
            for field in (
                "stream_fault_injected", "stream_fault_blanked",
                "stream_fault_counted", "stream_fault_recovered",
            ):
                if report.get(field) is not True:
                    failures.append(
                        "Stream compositor fault recovery failed: " + field
                    )
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
    parser.add_argument("--enable-stream", action="store_true",
                        help="Exercise actual Stream Mode Tk output without OBS or hardware")
    parser.add_argument("--stress-stream", action="store_true",
                        help="For a long stream soak, rotate output size, 15/24/30 FPS, layout and preview resets")
    parser.add_argument("--report", default="soak-report.json")
    args = parser.parse_args()
    sys.exit(0 if soak(args.seconds, args.max_growth_mb, args.report,
                       enable_gamepad=args.enable_gamepad,
                       enable_stream=args.enable_stream,
                       stress_stream=args.stress_stream) else 1)
