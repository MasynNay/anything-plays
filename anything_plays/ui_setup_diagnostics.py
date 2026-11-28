"""Read-only setup troubleshooting window for Anything Plays 3.2.

Each Refresh only reads current local state. It never opens cameras, starts
emulators, downloads assets, changes gamepad mappings or sends diagnostics.
"""

import json
import math
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



# Setup's JSON and Tk labels consume these optional snapshots directly.
# Validate at this boundary too; the collector's own safeguards alone
# cannot protect against a damaged in-memory probe or subclass override.
_INPUT_BUCKET_LABELS = frozenset((
    "0-2", "2-5", "5-10", "10-20", "20-33", "33-50",
    "50-75", "75-100", "100-150", "150-250", "250-500", ">500",
))
_INPUT_STAGE_NAMES = (
    "tracking_to_dispatch", "dispatch_to_native", "tracking_to_native",
)


def _safe_input_timing_report(value):
    """Copy only complete, bounded first-party aggregate input observations."""
    if (type(value) is not dict
            or value.get("scope") != "software_input_snapshot_not_physical_latency"
            or type(value.get("enabled")) is not bool
            or type(value.get("stages")) is not dict):
        return None
    counts = {}
    for key in ("samples", "superseded", "discarded_pending",
                "clock_discontinuities", "late_camera_updates_dropped"):
        number = value.get(key, 0 if key == "late_camera_updates_dropped" else None)
        if type(number) is not int or not 0 <= number <= (2**63 - 1):
            return None
        counts[key] = number
    stages = {}
    for stage in _INPUT_STAGE_NAMES:
        entry = value["stages"].get(stage)
        if type(entry) is not dict:
            return None
        ranges = {}
        for percentile in ("p50_bucket_ms", "p95_bucket_ms"):
            bucket = entry.get(percentile)
            if bucket is None:
                if counts["samples"] != 0:
                    return None
            elif type(bucket) is not str or bucket not in _INPUT_BUCKET_LABELS:
                # A malformed extension value (e.g. list/dict) must not
                # throw from the optional setup-report validator.
                return None
            ranges[percentile] = bucket
        stages[stage] = ranges
    return {
        "scope": "software_input_snapshot_not_physical_latency",
        **counts,
        "stages": stages,
        "enabled": value["enabled"],
    }


# These are names from the built-in native-timing, GPU preview, and
# PortAudio aggregate collectors. Unknown extension keys are never copied
# into a user-visible setup report or clipboard.
_GC_INTEGER_METRICS = frozenset((
    "native_completed_frames", "native_run_calls",
    "native_run_p95_bucket_code", "native_run_over_16ms",
    "native_run_over_50ms", "native_run_over_100ms",
    "scheduler_late_frames", "scheduler_resyncs", "scheduler_wait_calls",
    "scheduler_clock_recovery_events",
    "gpu_readback_calls", "gpu_readback_timing_samples",
    "gpu_readback_staging_allocations", "gpu_readback_staging_reuses",
    "gpu_readback_staging_peak_bytes",
    "gamecube_preview_clock_failures", "gamecube_hardware_frames",
    "gamecube_preview_readback_skips", "gpu_readback_p95_bucket_code",
    "gpu_readback_over_16ms", "gpu_readback_over_33ms",
    "audio_output_callback_calls", "audio_output_requested_frames",
    "audio_output_underrun_frames",
    "audio_output_device_underflow_callbacks", "audio_queue_dropped_frames",
    "audio_core_pcm_frames", "audio_core_nonzero_channel_values",
    "audio_native_rate_hz", "audio_output_rate_hz",
    "gamecube_preview_target_fps", "gamecube_preview_cadence_intervals",
))
_GC_REAL_METRICS = frozenset((
    "native_reported_core_fps", "native_run_mean_ms",
    "native_run_max_ms", "native_run_total_seconds",
    "native_run_non_readback_mean_ms", "gpu_readback_share_of_native_run",
    "scheduler_late_total_seconds", "scheduler_late_max_ms",
    "scheduler_wait_total_seconds", "gpu_readback_max_ms",
    "gamecube_preview_observed_capture_fps",
    "gamecube_preview_max_interval_ms",
))
_GC_BOOLEAN_METRICS = frozenset((
    "audio_delivery_measurements_available", "audio_stream_active",
    "audio_stream_started_during_session",
))
_GC_REQUIRED = frozenset((
    "native_run_calls", "native_run_mean_ms", "native_run_max_ms",
    "gpu_readback_calls", "gpu_readback_max_ms",
    "gpu_readback_share_of_native_run",
    "gamecube_preview_target_fps",
    "gamecube_preview_observed_capture_fps",
    "gamecube_preview_cadence_intervals",
    "gamecube_preview_max_interval_ms", "scheduler_late_frames",
    "scheduler_resyncs", "scheduler_late_max_ms",
    "audio_output_device_underflow_callbacks",
    "audio_output_underrun_frames", "audio_queue_dropped_frames",
))


def _safe_gamecube_performance_report(value):
    """Only valid scalar GameCube A/V metrics, never device/driver strings."""
    if (type(value) is not dict
            or value.get("format") != "anything-plays-gamecube-performance"
            or type(value.get("version")) is not int
            or value["version"] != 1
            or value.get("scope") !=
            "aggregate_native_av_not_physical_hardware_certification"
            or type(value.get("metrics")) is not dict):
        return None
    observed = value["metrics"]
    safe = {}
    for key in _GC_INTEGER_METRICS:
        if key not in observed:
            continue
        number = observed[key]
        if type(number) is not int:
            return None
        if key in ("native_run_p95_bucket_code", "gpu_readback_p95_bucket_code"):
            valid = -1 <= number <= 8
        elif key == "gamecube_preview_target_fps":
            valid = number in (0, 20, 30, 60)
        elif key in ("audio_native_rate_hz", "audio_output_rate_hz"):
            valid = 8000 <= number <= 192000
        elif key == "gpu_readback_staging_peak_bytes":
            # bounded_dimensions() caps native GL buffers at 4096x4096
            # RGBA bytes. A fabricated, impossible capacity is unsafe data.
            valid = 0 <= number <= 4096 * 4096 * 4
        else:
            valid = 0 <= number <= (2**63 - 1)
        if not valid:
            return None
        safe[key] = number
    for key in _GC_REAL_METRICS:
        if key not in observed:
            continue
        number = observed[key]
        if type(number) not in (int, float):
            return None
        try:
            valid = math.isfinite(number) and 0 <= number <= 1e12
        except (OverflowError, TypeError, ValueError):
            valid = False
        if key == "gpu_readback_share_of_native_run":
            valid = valid and number <= 1
        if not valid:
            return None
        safe[key] = number
    for key in _GC_BOOLEAN_METRICS:
        if key in observed:
            if type(observed[key]) is not bool:
                return None
            safe[key] = observed[key]
    if not _GC_REQUIRED.issubset(safe):
        # Never format an incomplete legacy/custom report as healthy A/V.
        return None
    frames = safe.get("audio_core_pcm_frames")
    nonzero = safe.get("audio_core_nonzero_channel_values")
    if (frames is not None and nonzero is not None
            and nonzero > 2 * frames):
        return None
    return {
        "format": "anything-plays-gamecube-performance",
        "version": 1,
        "scope": "aggregate_native_av_not_physical_hardware_certification",
        "metrics": safe,
    }


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
        try:
            timing = _safe_input_timing_report(inputs.latency_snapshot())
        except Exception:
            timing = None
        if timing is not None:
            report["input_latency"] = timing
    # Every optional probe fails independently of the camera/controller/
    # core checks, and only known numeric values reach the local clipboard.
    if (isinstance(app.emu, Emulator)
            and app.system_key.get() == "gamecube"
            and bool(app.uses_embedded_emulator())):
        try:
            performance = _safe_gamecube_performance_report(
                app.emu.gamecube_performance_snapshot()
            )
        except Exception:
            performance = None
        if performance is not None:
            report["gamecube_performance"] = performance
    if isinstance(app, StreamMixin):
        try:
            # Do not dispatch to an extension/subclass override: even a
            # well-formed-looking custom report might contain camera paths
            # or values the setup window would mistake for real cadence.
            stream = StreamMixin.stream_performance_snapshot(app)
        except Exception:
            stream = None
        if stream is not None:
            report["stream_cadence"] = stream
    return report


def _input_timing_summary_lines(timing):
    """Render known aggregate-only stages, never arbitrary diagnostic text."""
    # Counters are owned by first-party bounded probes. Never print supplied
    # error text, paths, serials, per-frame samples or private camera labels.
    notices = []
    discontinuities = timing.get("clock_discontinuities", 0)
    if type(discontinuities) is int and discontinuities > 0:
        notices.append(
            f"Discarded {discontinuities} suspended/invalid clock intervals "
            "(software timing only)."
        )
    late_updates = timing.get("late_camera_updates_dropped", 0)
    if type(late_updates) is int and late_updates > 0:
        notices.append(
            f"Rejected {late_updates} late camera updates after disarm "
            "(P1/P2 safety)."
        )
    if not timing["samples"]:
        return (
            "No software input samples yet (enable held camera controls).",
            *notices,
        )
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
    return tuple(lines + notices)


def _gamecube_performance_summary_lines(performance):
    """Explain native costs without inventing rendered or audible FPS."""
    m = performance["metrics"]
    valid_samples = m["native_run_calls"]
    completed = m.get("native_completed_frames", valid_samples)
    if type(completed) is not int or completed < valid_samples:
        # Legacy reports predate a separate completed-frame count.
        completed = valid_samples
    if not valid_samples:
        # Clock failure does not erase independently completed retro_run
        # calls. Old reports with no completion counter remain conservative.
        if completed:
            native_line = (
                f"Native frames completed: {completed} · "
                "no valid GameCube native timing samples "
                "(performance measurements unavailable)."
            )
        else:
            native_line = (
                "No valid GameCube native timing samples yet "
                "(gameplay may still be running)."
            )
        # Legacy minimal reports may only include a native timing counter.
        # Complete first-party snapshots can still show independent GPU
        # publication, audio and scheduler data despite the bad clock.
        independent_fields = (
            "gpu_readback_calls", "gpu_readback_max_ms",
            "gamecube_preview_observed_capture_fps",
            "gamecube_preview_cadence_intervals",
            "gamecube_preview_target_fps",
            "gamecube_preview_max_interval_ms",
            "scheduler_late_frames", "scheduler_resyncs",
            "scheduler_late_max_ms",
            "audio_output_device_underflow_callbacks",
            "audio_output_underrun_frames", "audio_queue_dropped_frames",
        )
        if not all(field in m for field in independent_fields):
            return (native_line,)
    else:
        native_line = None
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
    timed = m.get("gpu_readback_timing_samples")
    captures = m["gpu_readback_calls"]
    # Fixed P95 buckets from successful, validly timed GL captures only.
    # Older report schemas do not contain these fields: remain compatible.
    labels = (
        "0–2", "2–4", "4–8", "8–16", "16–33",
        "33–50", "50–100", "100–250", ">250",
    )
    code = m.get("gpu_readback_p95_bucket_code", -1)
    slow16 = m.get("gpu_readback_over_16ms")
    slow33 = m.get("gpu_readback_over_33ms")
    readback_p95 = ()
    if (type(timed) is int and timed > 0 and type(code) is int
            and 0 <= code < len(labels)
            and type(slow16) is int and type(slow33) is int
            and 0 <= slow33 <= slow16 <= timed):
        readback_p95 = (
            f"GPU readback P95 (timed captures): {labels[code]} ms · "
            f">16 ms: {slow16} · >33 ms: {slow33} "
            f"(of {timed} valid samples)",
        )
    if not valid_samples:
        # Readback may have its own valid clock, but there is no measured
        # native-run denominator for a readback-share percentage.
        readback_cost = (
            f"maximum {m['gpu_readback_max_ms']} ms · "
            "share unavailable (native timing missing)"
            if type(timed) is int and timed > 0
            else "maximum unmeasured · share unavailable"
        )
    elif type(timed) is int and captures > 0 and timed == 0:
        # A perf_counter() failure is not evidence that glReadPixels is free.
        readback_cost = "maximum unmeasured · share unavailable"
    elif type(timed) is int and 0 < timed < captures:
        readback_cost = (
            f"maximum {m['gpu_readback_max_ms']} ms · "
            f"at least {m['gpu_readback_share_of_native_run'] * 100:.1f}% "
            "of native execution time (partial timing)"
        )
    else:
        readback_cost = (
            f"maximum {m['gpu_readback_max_ms']} ms · "
            f"{m['gpu_readback_share_of_native_run'] * 100:.1f}% "
            "of native execution time (included, not additive)"
        )
    # Output status is explicitly different from underrun counters: a
    # silent/no-device session can have perfectly zero device underflows.
    # Older stored reports omit these fields; keep their original summary.
    audio_status = ""
    active = m.get("audio_stream_active")
    started = m.get("audio_stream_started_during_session")
    if type(active) is bool and type(started) is bool:
        callbacks = m.get("audio_output_callback_calls", 0)
        if active and started:
            audio_status = (
                " · output stream open, callbacks observed (speaker unverified)"
                if type(callbacks) is int and callbacks > 0
                else " · output stream open, awaiting audio callback"
            )
        elif started:
            audio_status = " · output stream closed (opened during session)"
        else:
            audio_status = " · no output stream opened (silent playback)"
        native_rate, output_rate = (
            m.get("audio_native_rate_hz"), m.get("audio_output_rate_hz")
        )
        if (started and type(native_rate) is int
                and type(output_rate) is int
                and 8_000 <= native_rate <= 192_000
                and 8_000 <= output_rate <= 192_000):
            audio_status += (
                f" · native {native_rate} Hz → output {output_rate} Hz"
            )
    # Source PCM is distinct from PortAudio callbacks: a core can emit
    # silence into a functioning stream, or produce nonzero PCM while the
    # output device is missing. Neither case proves audible speakers.
    source_frames = m.get("audio_core_pcm_frames")
    nonzero_values = m.get("audio_core_nonzero_channel_values")
    if (type(source_frames) is int and type(nonzero_values) is int
            and source_frames >= 0
            and 0 <= nonzero_values <= 2 * source_frames):
        if not source_frames:
            audio_status += " · core PCM not observed"
        elif not nonzero_values:
            audio_status += (
                f" · core generated {source_frames} silent PCM frames"
            )
        else:
            audio_status += (
                f" · core generated {source_frames} PCM frames, "
                f"{nonzero_values} nonzero channel values "
                "(speaker unverified)"
            )
    if m.get("audio_delivery_measurements_available", True) is False:
        audio_line = (
            "Audio: output callback/queue measurements unavailable "
            "(speaker unverified)"
        )
    else:
        audio_line = (
            f"Audio: {m['audio_output_device_underflow_callbacks']} device "
            f"underflow callbacks · {m['audio_output_underrun_frames']} "
            f"application underrun frames · "
            f"{m['audio_queue_dropped_frames']} queue-dropped frames"
        )
    clock_recoveries = m.get("scheduler_clock_recovery_events")
    clock_notice = (
        f" · scheduling clock recoveries: {clock_recoveries}"
        if type(clock_recoveries) is int and clock_recoveries > 0
        else ""
    )
    staging_lines = ()
    staging_keys = (
        "gpu_readback_staging_allocations",
        "gpu_readback_staging_reuses",
        "gpu_readback_staging_peak_bytes",
    )
    if all(key in m for key in staging_keys):
        staging_lines = (
            f"GPU transfer memory: {m['gpu_readback_staging_allocations']} "
            f"allocations · {m['gpu_readback_staging_reuses']} reuses · "
            f"peak {m['gpu_readback_staging_peak_bytes']} bytes "
            "(CPU staging only, not native GPU FPS).",
        )
    return (
        (native_line if native_line is not None else
         f"Native frames: {completed} · timed {valid_samples} of {completed} · "
         f"average {m['native_run_mean_ms']} ms · maximum "
         f"{m['native_run_max_ms']} ms per retro_run · P95 {p95_label}"),
        f"GPU readback: {captures} captures · {readback_cost}"
        f"{readback_timing}",
        *readback_p95,
        *staging_lines,
        f"Preview captures: target {m['gamecube_preview_target_fps']} FPS · "
        f"observed {observed_preview} over "
        f"{m['gamecube_preview_cadence_intervals']} intervals · "
        f"maximum gap {m['gamecube_preview_max_interval_ms']} ms",
        f"Late deadlines (>5 ms): {m['scheduler_late_frames']} · "
        f"resynchronizations: {m['scheduler_resyncs']} · "
        f"maximum lateness {m['scheduler_late_max_ms']} ms"
        f"{clock_notice}",
        f"{audio_line}{audio_status}",
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
    chassis_info = (
        (
            f"Static chassis cache: {m['stream_chassis_cache_hits']} reused · "
            f"{m['stream_chassis_cache_builds']} built (decoration only)",
        ) if ("stream_chassis_cache_hits" in m
               and "stream_chassis_cache_builds" in m) else ()
    )
    recovery_info = (
        (
            f"Session compositor recovery: {m['stream_session_faults']} "
            f"faults · {m['stream_session_recoveries']} recoveries · "
            f"{'retry pending' if m.get('stream_recovery_pending') else 'ready'}",
        ) if ("stream_session_faults" in m
               and "stream_session_recoveries" in m) else ()
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
    ) + chassis_info + recovery_info


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
        except Exception as exc:
            # Native extensions, platform drivers and destroyed Tk wrappers
            # may raise errors beyond ValueError/TclError. Always show the
            # same private-data-free message instead of crashing the dialog.
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
        except Exception:
            status.set("Cannot copy setup checks until they can be refreshed.")
            return
        try:
            app.root.clipboard_clear()
            app.root.clipboard_append(json.dumps(report, indent=2) + "\n")
            app.root.update_idletasks()
        except Exception:
            # A native clipboard adapter can raise an arbitrary exception.
            # Never include that text in the user-facing error dialog.
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
