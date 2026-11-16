"""Read-only setup troubleshooting window for Anything Plays 3.2.

Each Refresh only reads current local state. It never opens cameras, starts
emulators, downloads assets, changes gamepad mappings or sends diagnostics.
"""

import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from anything_plays.build_identity import current_identity
from anything_plays.libretro_input import InputBuffer
from anything_plays.gba_emulator import Emulator
from anything_plays.ui_stream import StreamMixin
from anything_plays.setup_health import build_setup_report
from anything_plays.ui_setup_theme import bind_theme_canvas


def _safe_refresh_failure_message(_error):
    """Never display or copy raw driver, Tcl or local filesystem errors."""
    return (
        "Unable to check current setup. Check device connection "
        "and choose Refresh again."
    )


def _snapshot(app):
    selected = app.camera_name.get() in app.camera_options
    active = False
    cap = getattr(app, "cap", None)
    if cap is not None:
        try:
            active = bool(cap.isOpened())
        except Exception:
            active = False
    # Refresh must reflect the core actually discoverable for the current
    # console, not an old core_path cached before a core-pack install,
    # rollback, deletion or console change. No library is loaded or started.
    # Older test façades and optional integrations without a resolver retain
    # the prior read-only cached-path behavior.
    finder = getattr(app.emu, "find_system_core", None)
    if callable(finder):
        try:
            path = finder()
        except (OSError, TypeError, ValueError, KeyError, RuntimeError):
            path = None
    else:
        path = getattr(app.emu, "core_path", None)
    try:
        core_found = bool(path and Path(path).is_file())
    except (OSError, TypeError, ValueError):
        core_found = False
    reader = getattr(app, "_gamepad", None)
    enabled = app.gamepad_enabled.get()
    connected = bool(enabled and reader is not None
                     and reader.controller is not None)
    report = build_setup_report(
        system=app.system_key.get(),
        camera_count=len(app.camera_options),
        camera_selected=selected,
        camera_active=active,
        core_found=core_found,
        controller_enabled=enabled,
        controller_detected=connected,
        embedded_mode=bool(app.uses_embedded_emulator()),
        preview_minimal=current_identity()["channel"] == "v32_preview",
    )
    # Only include measurements from the first-party, opt-in and bounded
    # histogram implementation. Never copy arbitrary device or plugin data.
    inputs = getattr(app.emu, "inputs", None)
    if isinstance(inputs, InputBuffer):
        timing = inputs.latency_snapshot()
        if timing is not None:
            report["input_latency"] = timing
    # Accept only our built-in emulator class; a third-party integration
    # cannot inject arbitrary paths, devices, or private driver strings.
    if (isinstance(app.emu, Emulator)
            and app.system_key.get() == "gamecube"
            and bool(app.uses_embedded_emulator())):
        performance = app.emu.gamecube_performance_snapshot()
        if performance is not None:
            report["gamecube_performance"] = performance
    # Stream Mode owns a single Tk output; only its first-party mixin can
    # provide an allowlisted, in-memory count for the current window.
    if isinstance(app, StreamMixin):
        stream = app.stream_performance_snapshot()
        if stream is not None:
            report["stream_cadence"] = stream
    return report


def _input_timing_summary_lines(timing):
    """Render known aggregate-only stages, never arbitrary diagnostic text."""
    if not timing["samples"]:
        return ("No software input samples yet (enable held camera controls).",)
    lines = []
    for stage, label in (
        ("tracking_to_dispatch", "Tracking → input buffer"),
        ("dispatch_to_native", "Input buffer → native frame"),
        ("tracking_to_native", "Combined software input"),
    ):
        bucket = timing["stages"][stage]
        lines.append(
            f"{label}: P50 {bucket['p50_bucket_ms']} ms · "
            f"P95 {bucket['p95_bucket_ms']} ms"
        )
    return tuple(lines)


def _gamecube_performance_summary_lines(performance):
    """Explain native costs without inventing rendered or audible FPS."""
    m = performance["metrics"]
    if not m["native_run_calls"]:
        return ("GameCube has not completed a native gameplay frame yet.",)
    observed_preview = (
        f"{m['gamecube_preview_observed_capture_fps']} FPS"
        if m['gamecube_preview_cadence_intervals'] > 0
        else "waiting for two published preview images"
    )
    # This is a bounded percentile *range*, not a precise per-frame P95.
    # Older session reports may predate this 3.3 field.
    p95_labels = (
        "0–8", "8–16", "16–25", "25–33", "33–50",
        "50–100", "100–250", "250–500", ">500",
    )
    p95_code = m.get("native_run_p95_bucket_code", -1)
    p95_label = (
        p95_labels[p95_code] + " ms"
        if type(p95_code) is int and 0 <= p95_code < len(p95_labels)
        else "not sampled"
    )
    readback_timing = (
        f" · timed {m['gpu_readback_timing_samples']} of "
        f"{m['gpu_readback_calls']} captures · "
        f"{m['gamecube_preview_clock_failures']} invalid clock reads"
        if ("gpu_readback_timing_samples" in m
            and "gamecube_preview_clock_failures" in m)
        else ""
    )
    return (
        f"Native frames: {m['native_run_calls']} · average "
        f"{m['native_run_mean_ms']} ms · maximum "
        f"{m['native_run_max_ms']} ms per retro_run · P95 " 
        f"{p95_label}",
        f"GPU readback: {m['gpu_readback_calls']} captures · maximum "
        f"{m['gpu_readback_max_ms']} ms · "
        f"{m['gpu_readback_share_of_native_run'] * 100:.1f}% of "
        "native execution time (included, not additive)"
        f"{readback_timing}",
        f"Preview captures: target {m['gamecube_preview_target_fps']} FPS · "
        f"observed {observed_preview} over "
        f"{m['gamecube_preview_cadence_intervals']} intervals · "
        f"maximum gap {m['gamecube_preview_max_interval_ms']} ms",
        f"Late deadlines (>5 ms): {m['scheduler_late_frames']} · "
        f"resynchronizations: {m['scheduler_resyncs']} · "
        f"maximum lateness {m['scheduler_late_max_ms']} ms",
        f"Audio: {m['audio_output_device_underflow_callbacks']} device "
        f"underflow callbacks · {m['audio_output_underrun_frames']} "
        f"application underrun frames · "
        f"{m['audio_queue_dropped_frames']} queue-dropped frames",
    )


def _stream_cadence_summary_lines(stream):
    """Distinguish healthy timer refresh from changed-image publication."""
    m = stream["metrics"]
    ticks = (
        f"{m['stream_observed_refresh_fps']} FPS"
        if m["stream_refresh_intervals"] > 0
        else "waiting for two timer ticks"
    )
    published = (
        f"{m['stream_observed_publication_fps']} FPS"
        if m["stream_publication_intervals"] > 0
        else "waiting for two changed images"
    )
    # Aggregate composition time is not Tk callback frequency or OBS FPS.
    # Older reports may predate this field; do not invent a 0ms P95.
    cost_bins = (
        "0–5", "5–10", "10–16", "16–25", "25–33",
        "33–50", "50–67", "67–100", "100–200", "200–500", ">500",
    )
    code = m.get("stream_render_p95_bucket_code", -1)
    cost_p95 = (
        cost_bins[code] + " ms"
        if type(code) is int and 0 <= code < len(cost_bins)
        else "not sampled"
    )
    cache_counts_known = (
        "stream_resize_cache_hits" in m
        and "stream_resize_cache_misses" in m
    )
    fit_summary = (
        f"Source resize cache: {m['stream_resize_cache_hits']} reused · "
        f"{m['stream_resize_cache_misses']} resized"
        if cache_counts_known else "Source resize cache: not measured"
    )
    return (
        f"Requested Stream Mode refresh: {m['stream_target_refresh_fps']} FPS · "
        f"observed Tk tick {ticks}",
        f"Changed-image publication: {published} · "
        f"{m['stream_published_images']} compositions · "
        f"{m['stream_unchanged_ticks']} unchanged ticks",
        f"Longest refresh gap: {m['stream_max_refresh_gap_ms']} ms · "
        f"{m['stream_failed_ticks']} failed ticks",
        f"Stream composition: P95 {cost_p95} · "
        f"mean {m.get('stream_render_mean_ms', 0)} ms · "
        f"max {m.get('stream_render_max_ms', 0)} ms · "
        f"{m.get('stream_render_over_budget_ticks', 0)} over-budget "
        f"of {m.get('stream_render_samples', 0)} measured ticks",
        fit_summary,
    )


def show_setup_diagnostics(app):
    existing = getattr(app, "_setup_diagnostics_window", None)
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.lift()
                existing.focus_set()
                return
        except tk.TclError:
            pass

    window = tk.Toplevel(app.root)
    app._setup_diagnostics_window = window
    window.title("Check my setup · Anything Plays 3.2")
    window.transient(app.root)
    window.geometry("625x615")
    window.minsize(480, 430)

    def close():
        app._setup_diagnostics_window = None
        app._input_timing_button = None
        try:
            window.destroy()
        except tk.TclError:
            pass

    window.protocol("WM_DELETE_WINDOW", close)
    shell = ttk.Frame(window, padding=(15, 14))
    shell.pack(fill="both", expand=True)
    ttk.Label(
        shell, text="What's stopping my setup?",
        font=("TkDefaultFont", 17, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        shell,
        text="Review camera, emulator and controller status without a game "
             "file or network connection. These checks cannot verify every "
             "webcam or game.",
        style="Helper.TLabel", wraplength=575, justify="left",
    ).pack(anchor="w", pady=(4, 10))

    holder = ttk.Frame(shell)
    holder.pack(fill="both", expand=True)
    canvas = tk.Canvas(holder, highlightthickness=0, borderwidth=0,
                       bg=app.THEMES.get(app.theme_name.get(),
                                         app.THEMES["Dark"])[1])
    bind_theme_canvas(app, window, canvas)
    scroll = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    cards = ttk.Frame(canvas)
    embedded = canvas.create_window((0, 0), window=cards, anchor="nw")
    cards.bind(
        "<Configure>",
        lambda _: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.bind(
        "<Configure>",
        lambda event: canvas.itemconfigure(embedded, width=event.width),
    )

    status = tk.StringVar(master=window)
    snapshot = {"value": None}

    def refresh():
        try:
            report = _snapshot(app)
        except (ValueError, tk.TclError) as exc:
            # Driver and Tcl exception text may contain local device/path
            # details; the displayed failure is intentionally fixed.
            status.set(_safe_refresh_failure_message(exc))
            return
        snapshot["value"] = report
        for child in cards.winfo_children():
            child.destroy()
        labels = (
            ("camera", "CAMERA"),
            ("emulator", "EMULATOR"),
            ("controller", "CONTROLLER"),
            ("input_backend", "INPUT PATH"),
        )
        for key, title in labels:
            item = report["checks"][key]
            frame = ttk.LabelFrame(cards, text=title, padding=10)
            frame.pack(fill="x", pady=(0, 9), padx=(0, 3))
            ttk.Label(
                frame, text=item["status"], style="Value.TLabel",
            ).pack(anchor="w")
            ttk.Label(
                frame, text=item["next"], wraplength=545, justify="left",
            ).pack(anchor="w", pady=(3, 0))
        stream = report.get("stream_cadence")
        if stream is not None:
            frame = ttk.LabelFrame(
                cards, text="STREAM MODE CAPTURE CADENCE", padding=10,
            )
            frame.pack(fill="x", pady=(0, 9), padx=(0, 3))
            for line in _stream_cadence_summary_lines(stream):
                ttk.Label(
                    frame, text=line, wraplength=545, justify="left",
                ).pack(anchor="w", pady=(3, 0))
            ttk.Label(
                frame,
                text="Tk timer refresh is not a changed image. A static scene "
                     "can have full timer cadence and very few compositions. "
                     "Neither number measures OBS recording FPS, camera "
                     "sensor FPS or native emulation speed.",
                wraplength=545, justify="left",
            ).pack(anchor="w", pady=(4, 0))
        timing = report.get("input_latency")
        if timing is not None:
            frame = ttk.LabelFrame(
                cards, text="OPTIONAL CAMERA INPUT TIMING", padding=10,
            )
            frame.pack(fill="x", pady=(0, 9), padx=(0, 3))
            state = "Measuring" if timing["enabled"] else "Stopped"
            ttk.Label(
                frame,
                text=f"{state} · {timing['samples']} native-input samples "
                     f"· {timing['superseded']} superseded "
                     f"· {timing['discarded_pending']} discarded",
                style="Value.TLabel",
            ).pack(anchor="w")
            for line in _input_timing_summary_lines(timing):
                ttk.Label(frame, text=line, wraplength=545,
                          justify="left").pack(anchor="w", pady=(3, 0))
            ttk.Label(
                frame,
                text="Already captured camera frame → next native input "
                     "snapshot only. These are bucket ranges, not physical "
                     "camera or screen response latency; no footage is recorded.",
                wraplength=545, justify="left",
            ).pack(anchor="w", pady=(5, 0))
        performance = report.get("gamecube_performance")
        if performance is not None:
            frame = ttk.LabelFrame(
                cards, text="GAMECUBE NATIVE A/V (DIAGNOSTIC)", padding=10,
            )
            frame.pack(fill="x", pady=(0, 9), padx=(0, 3))
            for line in _gamecube_performance_summary_lines(performance):
                ttk.Label(
                    frame, text=line, wraplength=545, justify="left",
                ).pack(anchor="w", pady=(3, 0))
            ttk.Label(
                frame,
                text="Preview capture FPS is how often RGB frames reached "
                     "this app, NOT native Dolphin emulation speed, visible "
                     "screen FPS or proof of physical audio. GPU readback "
                     "time is already included in native frame work.",
                wraplength=545, justify="left",
            ).pack(anchor="w", pady=(5, 0))
        timing_control = getattr(app, "_input_timing_button", None)
        if timing_control is not None:
            buffer = getattr(app.emu, "inputs", None)
            if isinstance(buffer, InputBuffer):
                timing_control.configure(
                    text="Stop input timing" if buffer._latency_enabled
                    else "Start input timing"
                )
        status.set(
            "Local checks refreshed. No device names or personal paths collected."
        )

    def copy():
        # Do not copy until explicitly clicked; always use our allowlisted,
        # locally reconstructed report, not arbitrary status/exception text.
        # A camera or controller may have changed since opening the dialog.
        # Copy a fresh, allowlisted snapshot rather than stale state.
        try:
            report = _snapshot(app)
        except (ValueError, tk.TclError):
            status.set("Cannot copy setup checks until they can be refreshed.")
            return
        try:
            app.root.clipboard_clear()
            app.root.clipboard_append(json.dumps(report, indent=2) + "\n")
            app.root.update_idletasks()
        except (OSError, RuntimeError, tk.TclError):
            messagebox.showerror(
                "Setup checks", "The safe report could not be copied.",
                parent=window,
            )
            return
        status.set(
            "Redacted setup report copied locally. Paste it into a GitHub issue "
            "only if you choose to share it."
        )

    footer = ttk.Frame(shell)
    footer.pack(fill="x", pady=(11, 0))
    inputs = getattr(app.emu, "inputs", None)
    if isinstance(inputs, InputBuffer):
        def toggle_timing():
            # Explicit local action only. Never start cameras or game cores.
            if inputs._latency_enabled:
                inputs.disable_latency_probe()
            else:
                inputs.enable_latency_probe()
            refresh()

        app._input_timing_button = ttk.Button(
            footer, text="Start input timing", command=toggle_timing,
        )
        app._input_timing_button.pack(side="left", padx=(0, 8))
    else:
        app._input_timing_button = None
    ttk.Button(
        footer, text="Refresh checks", command=refresh,
        style="Accent.TButton",
    ).pack(side="left")
    ttk.Button(
        footer, text="Copy safe report", command=copy,
    ).pack(side="left", padx=(8, 0))
    ttk.Button(
        footer, text="Done", command=close,
    ).pack(side="right")
    ttk.Label(
        shell, textvariable=status, style="Helper.TLabel",
        wraplength=575, justify="left",
    ).pack(anchor="w", pady=(8, 0))
    refresh()
