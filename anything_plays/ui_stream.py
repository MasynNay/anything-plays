"""OBS-friendly, themed dual-screen stream output for an active session.

The output is a normal resizable native Tk window that Window Capture can
select. Its separate settings window is never rendered into the stream.

No second camera or emulation process is ever opened. Camera snapshots arrive
only from the already annotated video pipeline; gameplay is read under the
existing emulator frame lock on Tk's main thread. The output has one Tcl image
item and a single cancellable, bounded-rate update job.
"""
from __future__ import annotations

import re
import json
import math
import threading
import time
from functools import lru_cache
import tkinter as tk
from tkinter import colorchooser, ttk

import cv2
from PIL import Image, ImageDraw, ImageFont, ImageTk

LAYOUTS = ("DS stacked", "Side by side")
FRAME_RATES = ("15 FPS", "24 FPS", "30 FPS")
STREAM_CAMERA_STALE_AFTER_SECONDS = 3.0
# Fixed-duration buckets for opt-in-style local aggregate diagnostics.
# Only an integer code is exported, never a sequence of frame timings.
_STREAM_RENDER_BIN_UPPER_MS = (5, 10, 16, 25, 33, 50, 67, 100, 200, 500)
_HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")
def stream_optional_perf_clock():
    """Best-effort monotonic perf clock for optional OBS composition.

    A broken platform clock must not unwind a Tk callback, generate false
    frame-cost samples, or interrupt the actual native emulator worker.
    """
    try:
        now = time.perf_counter()
        if type(now) in (float, int) and math.isfinite(now) and now >= 0:
            return now
    except Exception:
        pass
    return None


def stream_safe_failure_class(exc):
    """Return only fixed status categories, never driver or custom names."""
    category = type(exc).__name__
    return category if category in (
        "RuntimeError", "OSError", "ValueError", "TypeError", "IndexError",
        "AttributeError", "MemoryError", "OverflowError", "KeyError",
    ) else "UnexpectedError"


DEFAULT_STREAM = {
    "layout": "DS stacked",
    "frame_rate": "24 FPS",
    "theme": "Dark",
    "border_color": "",
    "border_width": 6,
    "game_size": 53,
    "swap_screens": False,
    "show_labels": True,
}


def validate_stream_settings(value, themes, default_theme="Dark"):
    """Tolerate malformed saved settings without constructing unsafe colors.

    Stream configuration is intentionally isolated from the user's normal
    app theme, controller bindings and existing console preferences.
    """
    raw = value if isinstance(value, dict) else {}
    theme = raw.get("theme", default_theme)
    if not isinstance(theme, str) or theme not in themes:
        theme = default_theme if default_theme in themes else next(iter(themes))
    layout = raw.get("layout", DEFAULT_STREAM["layout"])
    if layout not in LAYOUTS:
        layout = DEFAULT_STREAM["layout"]
    frame_rate = raw.get("frame_rate", DEFAULT_STREAM["frame_rate"])
    if not isinstance(frame_rate, str) or frame_rate not in FRAME_RATES:
        frame_rate = DEFAULT_STREAM["frame_rate"]
    color = raw.get("border_color", "")
    if not isinstance(color, str) or not _HEX.fullmatch(color):
        color = ""
    try:
        border = int(float(raw.get("border_width", 6)))
    except (ValueError, TypeError, OverflowError):
        border = 6
    try:
        size = int(float(raw.get("game_size", 53)))
    except (ValueError, TypeError, OverflowError):
        size = 53
    return {
        "layout": layout,
        "frame_rate": frame_rate,
        "theme": theme,
        "border_color": color.lower(),
        "border_width": max(2, min(16, border)),
        "game_size": max(30, min(70, size)),
        "swap_screens": raw.get("swap_screens") is True,
        "show_labels": raw.get("show_labels") is not False,
    }


@lru_cache(maxsize=48)
def _font(size, *, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, max(10, int(size)))
    except OSError:
        return ImageFont.load_default()


def _contained(image, bounds, *, nearest=False):
    """Fit an input image inside a rect, never crop or distort game pixels."""
    if image is None:
        return None
    x0, y0, x1, y1 = bounds
    width, height = max(1, x1 - x0), max(1, y1 - y0)
    original_w, original_h = image.size
    if original_w < 1 or original_h < 1:
        return None
    scale = min(width / original_w, height / original_h)
    dest_w = max(1, min(width, round(original_w * scale)))
    dest_h = max(1, min(height, round(original_h * scale)))
    # Game and camera snapshots normally arrive as RGB PIL images.
    # Avoid a full-sized color-space copy on every newly animated frame.
    # The actual scaling filter and pixel geometry stay exactly the same.
    prepared = image if image.mode == "RGB" else image.convert("RGB")
    if prepared.size == (dest_w, dest_h):
        fitted = prepared
    else:
        fitted = prepared.resize(
            (dest_w, dest_h),
            Image.Resampling.NEAREST if nearest else Image.Resampling.BILINEAR,
        )
    return (
        fitted,
        x0 + (width - dest_w) // 2,
        y0 + (height - dest_h) // 2,
    )



# Strict scalar allowlist: never export a camera frame, path or device name.
_STREAM_QA_FIELDS = (
    "stream_target_refresh_fps",
    "stream_observed_refresh_fps",
    "stream_refresh_intervals",
    "stream_max_refresh_gap_ms",
    "stream_observed_publication_fps",
    "stream_publication_intervals",
    "stream_published_images",
    "stream_unchanged_ticks",
    "stream_failed_ticks",
    "stream_render_samples",
    "stream_render_mean_ms",
    "stream_render_max_ms",
    "stream_render_p95_bucket_code",
    "stream_render_over_budget_ticks",
    "stream_resize_cache_hits",
    "stream_resize_cache_misses",
    "stream_stale_camera_clears",
    "stream_session_faults",
    "stream_session_recoveries",
    "stream_recovery_pending",
)


def stream_safe_qa_report(snapshot):
    """Only finite aggregate scalars; never claim camera/OBS/hardware QA."""
    if not isinstance(snapshot, dict):
        return None
    incoming = snapshot.get("metrics")
    if not isinstance(incoming, dict):
        return None
    safe = {}
    for name in _STREAM_QA_FIELDS:
        value = incoming.get(name)
        if name == "stream_recovery_pending":
            if type(value) is bool:
                safe[name] = value
        elif type(value) in (int, float):
            try:
                if math.isfinite(value) and (
                        value >= 0 or
                        (name == "stream_render_p95_bucket_code" and value == -1)
                ):
                    safe[name] = value
            except (OverflowError, ValueError, TypeError):
                pass
    if not safe:
        return None
    return {
        "format": "anything-plays-stream-qa-aggregate",
        "version": 1,
        "scope": "tk_refresh_and_changed_images_not_obs_or_camera_fps",
        "physical_camera_verified_by_report": False,
        "native_gamecube_verified_by_report": False,
        "obs_encoder_verified_by_report": False,
        "metrics": safe,
    }


class StreamPanelResizeCache:
    """At most one fitted PIL image per source; never retain frame history.

    When a game animates against an unchanged camera (or vice versa),
    repeatedly scaling both sources wastes UI-thread time. Cached fits are
    keyed by the *actual source image object*, panel dimensions and sampling
    method; a new camera/game image invalidates only its own slot. Offsets
    are recomputed for each panel, so swapping screens is safe.

    Entries are owned by a single Stream Mode window and released on Stop,
    camera disconnect, or window close. Cache never changes source pixels.
    """

    def __init__(self):
        self._entries = {}
        self.hits = 0
        self.misses = 0

    def clear(self, channel=None):
        if channel is None:
            self._entries.clear()
        else:
            self._entries.pop(channel, None)

    def contained(self, channel, image, bounds, *, nearest=False):
        if channel not in ("GAME", "CAMERA"):
            # Only the two local capture sources may retain a fitted image.
            return _contained(image, bounds, nearest=nearest)
        if image is None:
            self.clear(channel)
            return None
        x0, y0, x1, y1 = bounds
        width, height = max(1, x1 - x0), max(1, y1 - y0)
        prior = self._entries.get(channel)
        if (prior is not None and prior[0] is image
                and prior[1] == width and prior[2] == height
                and prior[3] == nearest):
            fitted = prior[4]
            self.hits += 1
        else:
            fitted = _contained(
                image, (0, 0, width, height), nearest=nearest,
            )
            # Replace, never append: even hours of streaming keep at most
            # the two most recently needed resized sources in memory.
            self._entries[channel] = (image, width, height, nearest, fitted)
            self.misses += 1
        if fitted is None:
            return None
        scaled, offset_x, offset_y = fitted
        return scaled, x0 + offset_x, y0 + offset_y

    def snapshot(self):
        # Allowlisted scalar metrics; never include images or source names.
        return {
            "stream_resize_cache_hits": self.hits,
            "stream_resize_cache_misses": self.misses,
        }


def stream_panel_boxes(size, layout="DS stacked", game_size=53):
    """Pure panel geometry shared by rendering and deterministic tests."""
    width, height = (max(320, int(size[0])), max(400, int(size[1])))
    edge = max(10, min(width, height) // 28)
    header = max(32, min(56, height // 20))
    bottom = max(20, height // 30)
    gap = max(18, min(width, height) // 26)
    share = max(30, min(70, int(game_size))) / 100
    if layout == "Side by side":
        usable = width - edge * 2 - gap
        a = max(100, round(usable * share))
        return (
            (edge, edge + header, edge + a, height - edge - bottom),
            (edge + a + gap, edge + header, width - edge, height - edge - bottom),
        )
    usable = height - 2 * edge - header - bottom - gap
    a = max(100, round(usable * share))
    return (
        (edge, edge + header, width - edge, edge + header + a),
        (edge, edge + header + a + gap, width - edge,
         height - edge - bottom),
    )


def stream_render_delay_ms(interval_ms, render_seconds):
    """Schedule stream refresh from render *start*, not render completion.

    Allow a small minimum idle period when composition is overloaded, so a
    slow OBS capture never creates a busy-loop in Tk or steals native input
    processing time. The timer controls capture only, never emulator FPS.
    """
    try:
        elapsed_ms = float(render_seconds) * 1000
    except (ValueError, TypeError, OverflowError):
        elapsed_ms = 0
    if not math.isfinite(elapsed_ms) or elapsed_ms < 0:
        elapsed_ms = 0
    return max(8, round(interval_ms - elapsed_ms))


class StreamCadenceTracker:
    """Bounded Stream Mode timer and changed-image publication cadence.

    A static scene may keep the Tk refresh timer on time without publishing
    a new photo. Report both rates separately; neither is native game FPS,
    camera sensor FPS or the frame rate recorded by OBS.
    """

    def __init__(self):
        self.mode = None
        self.last_tick = None
        self.last_published = None
        self.tick_intervals = 0
        self.tick_elapsed = 0.0
        self.max_tick_gap = 0.0
        self.publication_intervals = 0
        self.publication_elapsed = 0.0
        self.max_publication_gap = 0.0
        self.publications = 0
        self.unchanged = 0
        self.failures = 0
        self.render_samples = 0
        self.render_total_seconds = 0.0
        self.render_max_seconds = 0.0
        self.render_over_budget = 0
        self.render_histogram = [0] * (len(_STREAM_RENDER_BIN_UPPER_MS) + 1)

    def reset_for(self, mode):
        mode = mode if mode in FRAME_RATES else DEFAULT_STREAM["frame_rate"]
        if mode != self.mode:
            self.__init__()
            self.mode = mode

    def record_failed_without_clock(self, mode):
        """Count a failed UI update without inventing a timer observation."""
        self.reset_for(mode)
        self.failures += 1

    def record_tick(self, now, mode, *, published=False, failed=False,
                    render_seconds=None):
        self.reset_for(mode)
        if type(now) not in (float, int):
            return
        try:
            if not math.isfinite(now) or now < 0:
                return
        except (OverflowError, TypeError, ValueError):
            return
        if self.last_tick is not None:
            delta = now - self.last_tick
            if not math.isfinite(delta) or delta < 0 or delta > 3600:
                # A clock discontinuity or hours-long suspended window
                # cannot safely be blended into the current FPS average.
                # Keep the next valid tick but begin a fresh segment.
                self.__init__()
                self.mode = (
                    mode if mode in FRAME_RATES
                    else DEFAULT_STREAM["frame_rate"]
                )
            elif delta > 0:
                self.tick_intervals += 1
                self.tick_elapsed += delta
                self.max_tick_gap = max(self.max_tick_gap, delta)
        self.last_tick = now
        # Record composition cost independently of changed-image cadence;
        # even an unchanged frame has some work. No trace buffers grow.
        if type(render_seconds) in (float, int):
            try:
                valid_cost = math.isfinite(render_seconds) and 0 <= render_seconds <= 3600
            except (OverflowError, TypeError, ValueError):
                valid_cost = False
            if valid_cost:
                cost_ms = render_seconds * 1000
                index = next(
                    (i for i, upper in enumerate(_STREAM_RENDER_BIN_UPPER_MS)
                     if cost_ms <= upper),
                    len(_STREAM_RENDER_BIN_UPPER_MS),
                )
                self.render_histogram[index] += 1
                self.render_samples += 1
                self.render_total_seconds += render_seconds
                self.render_max_seconds = max(self.render_max_seconds, render_seconds)
                target = int(self.mode.split()[0])
                if render_seconds > 1 / target:
                    self.render_over_budget += 1
        if failed:
            self.failures += 1
        elif published:
            if self.last_published is not None:
                delta = now - self.last_published
                if delta > 0:
                    self.publication_intervals += 1
                    self.publication_elapsed += delta
                    self.max_publication_gap = max(self.max_publication_gap, delta)
            self.last_published = now
            self.publications += 1
        else:
            self.unchanged += 1

    def snapshot(self):
        target = int(self.mode.split()[0]) if self.mode is not None else 0
        percentile = -1
        if self.render_samples:
            rank = math.ceil(self.render_samples * 0.95)
            cumulative = 0
            for index, count in enumerate(self.render_histogram):
                cumulative += count
                if cumulative >= rank:
                    percentile = index
                    break
        tick_rate = (
            self.tick_intervals / self.tick_elapsed
            if self.tick_intervals and self.tick_elapsed > 0 else 0.0
        )
        publication_rate = (
            self.publication_intervals / self.publication_elapsed
            if self.publication_intervals and self.publication_elapsed > 0 else 0.0
        )
        return {
            "stream_target_refresh_fps": target,
            "stream_observed_refresh_fps": round(tick_rate, 2),
            "stream_refresh_intervals": self.tick_intervals,
            "stream_max_refresh_gap_ms": round(self.max_tick_gap * 1000, 2),
            "stream_observed_publication_fps": round(publication_rate, 2),
            "stream_publication_intervals": self.publication_intervals,
            "stream_published_images": self.publications,
            "stream_unchanged_ticks": self.unchanged,
            "stream_failed_ticks": self.failures,
            "stream_render_samples": self.render_samples,
            "stream_render_mean_ms": (
                round(self.render_total_seconds * 1000 / self.render_samples, 2)
                if self.render_samples else 0.0
            ),
            "stream_render_max_ms": round(self.render_max_seconds * 1000, 2),
            "stream_render_p95_bucket_code": percentile,
            "stream_render_over_budget_ticks": self.render_over_budget,
        }


def stream_camera_frame_is_stale(last_success, now):
    """Decide only OBS preview freshness, never camera/control liveness.

    A capture backend can claim that its device remains open while frames
    stop arriving. Do not label an old image as live indefinitely. Static
    reference images bypass this check at the caller.
    """
    if type(last_success) not in (float, int) or type(now) not in (float, int):
        return False
    try:
        if not math.isfinite(last_success) or not math.isfinite(now):
            return False
    except (OverflowError, ValueError, TypeError):
        return False
    return (now < last_success
            or now - last_success > STREAM_CAMERA_STALE_AFTER_SECONDS)


def stream_camera_snapshot_due(previous, now, mode):
    """Throttle *only* OBS-preview RGB conversion, never source tracking.

    Camera controls/zone detection and the primary camera preview still run
    for every source frame. Only Stream Mode's extra PIL snapshot is skipped
    if its previous snapshot is fresh enough for the requested output rate.
    """
    selected = (
        mode if isinstance(mode, str) and mode in FRAME_RATES
        else DEFAULT_STREAM["frame_rate"]
    )
    period = 1 / int(selected.split()[0])
    # This is the optional OBS conversion policy, called from the *real*
    # camera tracking tick. A malformed clock or legacy value must never
    # raise and disarm/release the user's native game controls.
    if type(now) not in (int, float):
        return False
    try:
        if not math.isfinite(now) or now < 0:
            return False
    except (TypeError, ValueError, OverflowError):
        return False
    if previous is None or type(previous) not in (int, float):
        return True
    try:
        if not math.isfinite(previous) or previous < 0:
            return True
    except (TypeError, ValueError, OverflowError):
        return True
    if now < previous:
        return True
    return now - previous >= period - 0.001


def compose_stream_output(game, camera, *, size, settings, themes,
                          game_active=False, camera_active=False,
                          camera_reference=False, resize_cache=None):
    """Render one complete OBS-capturable DS-style frame as a PIL RGB image.

    Includes custom borders and both sources, but no settings widgets or
    private source paths. Frames are read-only and never altered in place.
    """
    options = validate_stream_settings(settings, themes)
    width = max(320, min(1920, int(size[0])))
    height = max(400, min(1600, int(size[1])))
    outer, surface, foreground, accent, housing, well = themes[options["theme"]]
    line = options["border_color"] or accent
    img = Image.new("RGB", (width, height), outer)
    painter = ImageDraw.Draw(img)
    edge = max(10, min(width, height) // 28)
    title_font = _font(min(19, max(12, width // 38)), bold=True)
    label_font = _font(min(16, max(11, width // 55)), bold=True)
    micro = _font(10)
    painter.text((edge + 4, edge // 2 + 3), "ANYTHING PLAYS  /  STREAM DECK",
                 fill=foreground, font=title_font)
    painter.text((width - edge - 104, edge // 2 + 7), "DUAL DISPLAY",
                 fill=line, font=micro)
    boxes = stream_panel_boxes(
        (width, height), options["layout"], options["game_size"],
    )
    screens = [
        ("GAME", game if game_active else None,
         "GAMEPLAY" if game_active else "NO GAME LOADED", True),
        ("CAMERA", camera if camera_active or camera_reference else None,
         "CAMERA LIVE" if camera_active and camera is not None else
         "CAMERA WAITING" if camera_active else
         "REFERENCE IMAGE" if camera_reference else "CAMERA OFF", False),
    ]
    if options["swap_screens"]:
        screens.reverse()

    border = options["border_width"]
    for index, (bounds, (name, source, status, nearest)) in enumerate(
        zip(boxes, screens)
    ):
        x0, y0, x1, y1 = bounds
        radius = max(10, min(24, (x1 - x0) // 24))
        # Chassis shadow and subtly inset display, themed independently.
        painter.rounded_rectangle((x0+2, y0+4, x1+2, y1+4),
                                  radius=radius, fill=well)
        painter.rounded_rectangle(bounds, radius=radius, fill=housing,
                                  outline=line, width=border)
        inner = (
            x0 + border + 5, y0 + border + 5,
            x1 - border - 5, y1 - border - 5,
        )
        painter.rounded_rectangle(inner, radius=max(4, radius - 6),
                                  fill="#050a11")
        label_height = min(34, max(20, (y1-y0) // 12)) if options["show_labels"] else 0
        if label_height:
            painter.rectangle((inner[0] + 2, inner[1] + 2,
                               inner[2] - 2, inner[1] + label_height),
                              fill=surface)
            painter.text((inner[0] + 12, inner[1] + 4),
                         "TOP SCREEN" if index == 0 and options["layout"] == "DS stacked"
                         else "BOTTOM SCREEN" if options["layout"] == "DS stacked"
                         and index == 1 else name,
                         fill=foreground, font=label_font)
            # Status is factual, not a fake recording indicator.
            status_box = painter.textbbox((0, 0), status, font=micro)
            painter.text((max(inner[0] + 85,
                              inner[2] - (status_box[2]-status_box[0]) - 10),
                          inner[1] + 6), status, fill=line, font=micro)
        video = (
            inner[0] + 4, inner[1] + label_height + 4,
            inner[2] - 4, inner[3] - 4,
        )
        if video[2] > video[0] and video[3] > video[1]:
            sized = (
                resize_cache.contained(name, source, video, nearest=nearest)
                if resize_cache is not None
                else _contained(source, video, nearest=nearest)
            )
            if sized is not None:
                resized, x, y = sized
                img.paste(resized, (x, y))
            else:
                # A neutral, truthful placeholder until a live source exists.
                msg = (
                    "Load a game to begin" if name == "GAME"
                    else "Waiting for camera frames" if camera_active
                    else "Start a camera to begin"
                )
                box = painter.textbbox((0, 0), msg, font=label_font)
                cx = (video[0] + video[2] - (box[2]-box[0])) // 2
                cy = (video[1] + video[3] - (box[3]-box[1])) // 2
                painter.text((cx, cy), msg, fill=foreground, font=label_font)

    if options["layout"] == "DS stacked":
        # A tasteful hinge between the two framed screens, modeled after a
        # hinged handheld without using proprietary Nintendo branding.
        mid = (boxes[0][3] + boxes[1][1]) // 2
        painter.rounded_rectangle(
            (width // 2 - 42, mid - 3, width // 2 + 42, mid + 3),
            radius=3, fill=line,
        )
        for i in range(3):
            x = edge + 12 + i*9
            painter.ellipse((x, mid-2, x+3, mid+1), fill=surface)
    else:
        mid = (boxes[0][2] + boxes[1][0]) // 2
        painter.rounded_rectangle((mid-3, height//2-40, mid+3, height//2+40),
                                  radius=3, fill=line)
    painter.text((edge + 4, height - edge - 15),
                 "STREAM OUTPUT  /  OBS WINDOW CAPTURE",
                 fill=foreground, font=micro)
    return img


class StreamMixin:
    """Manage a clean capture-only window plus a separate control surface."""

    def initialize_stream_mode(self, preferences):
        default_theme = self.theme_name.get()
        self._stream_options = validate_stream_settings(
            preferences.get("stream_mode"), self.THEMES, default_theme,
        )
        self._stream_output_window = None
        self._stream_controls_window = None
        self._stream_canvas = None
        self._stream_photo = None
        self._stream_canvas_item = None
        self._stream_frame_job = None
        self._stream_save_job = None
        self._stream_last_render = None
        self._stream_cadence = None
        self._stream_resize_cache = None
        self._stream_camera_last_snapshot = None
        self._stream_camera_force_next_snapshot = False
        self._stream_camera_frame = None
        self._stream_camera_serial = 0
        # A disconnect must revoke even an IN-FLIGHT preview when no
        # previous camera image existed to advance the render serial.
        self._stream_camera_epoch = 0
        self._stream_stale_camera_clears = 0
        self._stream_session_faults = 0
        self._stream_session_recoveries = 0
        self._stream_recovery_pending = False
        self._stream_game_frame = None
        self._stream_game_serial = None

    def open_stream_mode(self):
        existing = getattr(self, "_stream_output_window", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    self._open_stream_controls()
                    return
            except tk.TclError:
                pass
        output = tk.Toplevel(self.root)
        self._stream_output_window = output
        output.title("Anything Plays · Stream Output — capture this window")
        screen_w = max(450, output.winfo_screenwidth())
        screen_h = max(500, output.winfo_screenheight())
        width, height = (760, 980) if self._stream_options["layout"] == "DS stacked" else (1180, 720)
        width = min(width, screen_w - 65)
        height = min(height, screen_h - 90)
        output.geometry(f"{max(450, width)}x{max(480, height)}")
        output.minsize(360, 440)
        output.configure(bg="#050a11")
        canvas = tk.Canvas(
            output, bg="#050a11", highlightthickness=0, borderwidth=0,
        )
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", lambda _event: self._invalidate_stream())
        output.protocol("WM_DELETE_WINDOW", self.close_stream_mode)
        self._stream_canvas = canvas
        self._stream_photo = None
        self._stream_last_render = None
        self._stream_camera_last_snapshot = None
        self._stream_camera_force_next_snapshot = True
        self._stream_cadence = StreamCadenceTracker()
        self._stream_cadence.reset_for(self._stream_options["frame_rate"])
        self._stream_resize_cache = StreamPanelResizeCache()
        self._stream_stale_camera_clears = 0
        self._stream_session_faults = 0
        self._stream_session_recoveries = 0
        self._stream_recovery_pending = False
        self._open_stream_controls()
        self._stream_render_tick()

    def _open_stream_controls(self):
        window = getattr(self, "_stream_controls_window", None)
        if window is not None:
            try:
                if window.winfo_exists():
                    window.deiconify()
                    window.lift()
                    return
            except tk.TclError:
                pass
        panel = tk.Toplevel(self.root)
        self._stream_controls_window = panel
        panel.title("Anything Plays · Stream Settings")
        panel.geometry("400x610")
        panel.minsize(340, 520)
        panel.protocol("WM_DELETE_WINDOW", self._close_stream_controls)
        root = ttk.Frame(panel, padding=16)
        root.pack(fill="both", expand=True)
        ttk.Label(root, text="Stream Mode", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            root,
            text="OBS: add Window Capture, then select Anything Plays · Stream Output. "
                 "These controls stay outside the captured window.",
            style="Helper.TLabel", wraplength=360,
        ).pack(fill="x", pady=(4, 14))
        self._stream_vars = {}
        for name, title, choices in (
            ("layout", "Screen arrangement", LAYOUTS),
            ("theme", "Stream color theme", tuple(self.THEMES)),
            ("frame_rate", "Output refresh", FRAME_RATES),
        ):
            row = ttk.Frame(root)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=title).pack(anchor="w")
            var = tk.StringVar(value=self._stream_options[name])
            self._stream_vars[name] = var
            box = ttk.Combobox(row, textvariable=var, values=choices,
                               state="readonly")
            box.pack(fill="x", pady=(4, 0))
            var.trace_add("write", lambda *_: self._stream_controls_changed())
        for name, title, low, high in (
            ("border_width", "Border thickness", 2, 16),
            ("game_size", "Game screen share (%)", 30, 70),
        ):
            row = ttk.Frame(root)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=title).pack(anchor="w")
            var = tk.DoubleVar(value=self._stream_options[name])
            self._stream_vars[name] = var
            ttk.Scale(
                row, from_=low, to=high, orient="horizontal",
                variable=var,
            ).pack(fill="x", pady=(4, 0))
            # Tk's trace fires for drag, keys and programmatic changes;
            # relying on Scale(command=...) misses keyboard-driven updates.
            var.trace_add("write", lambda *_: self._stream_controls_changed())
        for name, title in (
            ("swap_screens", "Swap game and camera positions"),
            ("show_labels", "Show screen headers and live status"),
        ):
            var = tk.BooleanVar(value=self._stream_options[name])
            self._stream_vars[name] = var
            ttk.Checkbutton(
                root, text=title, variable=var,
            ).pack(anchor="w", pady=(5, 1))
            # Tk Checkbutton(command=...) only fires on a physical click.
            # Trace the underlying BooleanVar as with layout/sliders so
            # programmatic accessibility changes and preference restores
            # update the real Stream Output consistently.
            var.trace_add("write", lambda *_: self._stream_controls_changed())
        colors = ttk.Frame(root)
        colors.pack(fill="x", pady=(12, 4))
        ttk.Button(colors, text="Choose border color…",
                   command=self._choose_stream_border_color).pack(side="left")
        ttk.Button(colors, text="Use theme accent",
                   command=self._reset_stream_border_color).pack(side="right")
        self._stream_diagnostic = tk.StringVar(value="Stream output ready")
        ttk.Label(root, textvariable=self._stream_diagnostic,
                  style="Helper.TLabel", wraplength=360).pack(anchor="w", pady=(4, 0))
        ttk.Label(
            root,
            text="Resize the output window directly. Stream Mode mirrors your "
                 "current game and camera; it never launches another device.",
            style="Helper.TLabel", wraplength=360,
        ).pack(fill="x", pady=(7, 0))
        actions = ttk.Frame(root)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(
            actions, text="Copy safe diagnostics",
            command=self._copy_stream_diagnostics,
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(
            actions, text="Close Stream Mode",
            command=self.close_stream_mode,
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))

    def _close_stream_controls(self):
        panel = getattr(self, "_stream_controls_window", None)
        self._stream_controls_window = None
        self._stream_vars = {}
        if panel is not None:
            try:
                panel.destroy()
            except tk.TclError:
                pass

    def _choose_stream_border_color(self):
        theme = self._stream_options["theme"]
        default = self._stream_options["border_color"] or self.THEMES[theme][3]
        try:
            result = colorchooser.askcolor(
                color=default, parent=self._stream_controls_window,
                title="Stream border color",
            )
        except (tk.TclError, RuntimeError, OSError):
            # The dialog or its parent can be destroyed while Stream Mode
            # keeps running. Treat it as a canceled *optional* style edit.
            return
        chosen = result[1] if result and len(result) > 1 else None
        if not isinstance(chosen, str) or not _HEX.fullmatch(chosen):
            return
        color = chosen.lower()
        if color != self._stream_options["border_color"]:
            self._stream_options["border_color"] = color
            # A border-only repaint must reuse existing annotated camera
            # pixels, not bypass the preview conversion FPS throttle.
            self._stream_options_updated(force_camera_snapshot=False)

    def _reset_stream_border_color(self):
        if self._stream_options["border_color"]:
            self._stream_options["border_color"] = ""
            self._stream_options_updated(force_camera_snapshot=False)

    def _stream_controls_changed(self):
        if not getattr(self, "_stream_vars", None):
            return
        options = dict(self._stream_options)
        for key, var in self._stream_vars.items():
            try:
                options[key] = var.get()
            except Exception:
                # The settings dialog can close independently of output.
                # A destroyed/custom Tk variable must not unwind the
                # main UI event loop or erase a healthy stream image.
                return
        previous_layout = self._stream_options["layout"]
        previous_rate = self._stream_options["frame_rate"]
        updated = validate_stream_settings(
            options, self.THEMES, self.theme_name.get(),
        )
        if updated == self._stream_options:
            # Tk traces and scale controls may fire without a real change.
            # Avoid unnecessary full-canvas work, camera snapshots and
            # preferences writes in the live UI loop.
            return
        self._stream_options = updated
        if self._stream_options["layout"] != previous_layout:
            # Present a natural portrait/landscape capture window on layout
            # change. Manual resizing afterwards remains fully supported.
            popup = getattr(self, "_stream_output_window", None)
            if popup is not None:
                try:
                    natural = (
                        (760, 980) if self._stream_options["layout"] == "DS stacked"
                        else (1180, 720)
                    )
                    width = min(
                        natural[0], max(450, popup.winfo_screenwidth() - 65)
                    )
                    height = min(
                        natural[1], max(480, popup.winfo_screenheight() - 90)
                    )
                    popup.geometry(f"{width}x{height}")
                except Exception:
                    # A destroyed window or foreign Tk wrapper can fail
                    # during layout resizing. Persist the new selection
                    # and invalidate composition; only geometry is optional.
                    pass
        self._stream_options_updated(
            force_camera_snapshot=(
                self._stream_options["frame_rate"] != previous_rate
            )
        )

    def _stream_options_updated(self, *, force_camera_snapshot=True):
        # Styling, screen layout and panel-size changes can reuse the
        # current annotated camera pixels. Forcing a fresh BGR->RGB
        # conversion for every slider step can defeat the chosen 15/24/30
        # FPS camera-preview limit. Only a changed refresh cap requires
        # an immediate next source conversion, while direct API callers
        # still request the historical immediate refresh by default.
        # Never erase the successful freshness timestamp: live-preview
        # privacy expiry still depends on the last real camera frame.
        if force_camera_snapshot:
            self._stream_camera_force_next_snapshot = True
        cadence = getattr(self, "_stream_cadence", None)
        if cadence is not None:
            cadence.reset_for(self._stream_options["frame_rate"])
        self._invalidate_stream()
        if self._stream_save_job is None and not getattr(self, "_closing", False):
            try:
                self._stream_save_job = self.root.after(
                    600, self._save_stream_options
                )
            except (tk.TclError, RuntimeError, OSError):
                # The root may be destroyed between a variable trace and
                # its deferred preferences write. Rendering and input are
                # independent of this best-effort settings timer.
                self._stream_save_job = None

    def _save_stream_options(self):
        self._stream_save_job = None
        if not getattr(self, "_closing", False):
            try:
                self.save_preferences()
            except (OSError, ValueError, tk.TclError):
                pass

    def _invalidate_stream(self):
        self._stream_last_render = None

    def stream_camera_snapshot(self, frame):
        """Accept an existing *annotated* BGR frame, never open a new capture."""
        output = self._stream_output_window
        if output is None:
            return
        if frame is None:
            self.stream_clear_camera()
            return
        # OpenCV/PIL conversion may yield to a disconnect, a newer frame or
        # a closed/reopened OBS output. Capture identity BEFORE conversion,
        # including camera-off notifications with no prior cached pixels.
        camera_serial = self._stream_camera_serial
        camera_epoch = getattr(self, "_stream_camera_epoch", 0)

        def current_camera_output():
            return (
                self._stream_output_window is output
                and self._stream_camera_serial == camera_serial
                and getattr(self, "_stream_camera_epoch", 0) == camera_epoch
                and not getattr(self, "_closing", False)
            )

        try:
            now = time.monotonic()
            valid_now = (
                type(now) in (int, float) and math.isfinite(now) and now >= 0
            )
        except Exception:
            valid_now = False
        if not valid_now:
            if not current_camera_output():
                return
            # A failed optional clock must not leave a previous private
            # webcam image indefinitely visible in OBS. Keep native game
            # controls untouched; clear only the stream's camera snapshot.
            if self._stream_camera_frame is not None:
                self.stream_clear_camera()
            return
        last = getattr(self, "_stream_camera_last_snapshot", None)
        if not stream_camera_snapshot_due(
            None if getattr(self, "_stream_camera_force_next_snapshot", False)
            else last,
            now, self._stream_options["frame_rate"]
        ):
            # Never skip the original camera tracking/control pipeline,
            # only the extra conversion for the optional OBS output window.
            return
        # This conversion is OPTIONAL. A broken OpenCV resize/color frame
        # must not propagate into the primary camera tick and interrupt
        # tracking, controller release or the normal in-app camera view.
        try:
            # Bound temporary RGB memory independent of high-res webcams.
            height, width = frame.shape[:2]
            if max(height, width) > 1280:
                scale = 1280 / max(height, width)
                frame = cv2.resize(
                    frame, (max(1, round(width*scale)),
                            max(1, round(height*scale)))
                )
            preview = Image.fromarray(
                cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            )
        except Exception:
            if not current_camera_output():
                # A late failure from the old conversion must not clear a
                # newer camera image or change its refresh timestamp.
                return
            # The OBS-only conversion is best-effort. Some native OpenCV
            # wrappers raise RuntimeError, AttributeError or MemoryError
            # instead of cv2.error; none may escape into the camera-tracking
            # input tick or leave an old camera image on the stream.
            # Revoke any previous private camera image immediately instead
            # of leaving it frozen in OBS after a corrupt/invalid source.
            if self._stream_camera_frame is not None:
                self.stream_clear_camera()
            # Retry at the selected Stream FPS, not on every high-rate
            # tracking frame, to avoid a conversion-error hot loop.
            self._stream_camera_last_snapshot = now
            self._stream_camera_force_next_snapshot = False
            return
        if not current_camera_output():
            # Preserve newer camera pixels and never republish a disconnected
            # frame or attach a preview to a newly opened Stream window.
            return
        self._stream_camera_frame = preview
        self._stream_camera_serial += 1
        self._stream_camera_last_snapshot = now
        self._stream_camera_force_next_snapshot = False

    def stream_clear_camera(self):
        """Revoke cached webcam pixels without redrawing an already-blank view.

        Repeated disconnect/empty-frame notifications can arrive while the
        camera is stopped. They should not turn static game-only Stream Mode
        output into a continuous Tk/PIL redraw workload. A real old image,
        valid capture timestamp, pending forced refresh or cached resize is
        still revoked immediately and accepts the next reconnect.
        """
        # Advance even when already blank: an earlier BGR->PIL conversion
        # could still be running with NO previously published camera frame.
        # This epoch never enters the render-state key, so idle disconnect
        # polls remain redraw-idempotent.
        self._stream_camera_epoch = getattr(
            self, "_stream_camera_epoch", 0
        ) + 1
        cache = getattr(self, "_stream_resize_cache", None)
        try:
            cache_entries = getattr(cache, "_entries", None)
        except Exception:
            # Cache wrappers are strictly optional; an extension-defined
            # property error must not escape a webcam disconnect path.
            cache_entries = None
        had_camera_pixels = (
            self._stream_camera_frame is not None
            or (isinstance(cache_entries, dict) and "CAMERA" in cache_entries)
        )
        had_pixels_or_state = (
            had_camera_pixels
            or self._stream_camera_last_snapshot is not None
            or bool(getattr(self, "_stream_camera_force_next_snapshot", False))
        )
        self._stream_camera_last_snapshot = None
        self._stream_camera_force_next_snapshot = False
        self._stream_camera_frame = None
        cache_failed = False
        if cache is not None:
            try:
                cache.clear("CAMERA")
            except Exception:
                # Fail closed: drop the whole resized-image cache reference
                # rather than keeping any old private webcam pixels. Never
                # interrupt native P1/P2 disarm, reconnect or Stream Output.
                self._stream_resize_cache = None
                cache_failed = True
        if had_pixels_or_state or cache_failed:
            self._stream_camera_serial += 1
            if (had_camera_pixels or cache_failed) and getattr(
                self, "_stream_photo", None
            ) is not None:
                # Never leave previously displayed private camera pixels in
                # OBS while waiting for a later refresh/backoff timer. Keep
                # the independent game image and fitted cache intact.
                self._stream_blank_output()
            else:
                self._invalidate_stream()

    def stream_performance_snapshot(self):
        """Only current active Stream Mode, no camera frames or Tk details."""
        cadence = getattr(self, "_stream_cadence", None)
        if getattr(self, "_stream_output_window", None) is None or cadence is None:
            return None
        cache = getattr(self, "_stream_resize_cache", None)
        cache_stats = {}
        # Diagnostics must not invoke untrusted native/custom cache hooks or
        # include arbitrary plugin data. Only the first-party bounded cache
        # may supply its two aggregate hit/miss counters; if it breaks,
        # the useful Stream cadence data still remains available.
        if type(cache) is StreamPanelResizeCache:
            try:
                cache_stats = cache.snapshot()
            except Exception:
                cache_stats = {}
        return {
            "format": "anything-plays-stream-cadence",
            "version": 1,
            "scope": "tk_refresh_and_changed_image_publications_not_obs_fps",
            "metrics": {
                **cadence.snapshot(),
                **cache_stats,
                "stream_stale_camera_clears": getattr(
                    self, "_stream_stale_camera_clears", 0
                ),
                "stream_session_faults": getattr(
                    self, "_stream_session_faults", 0
                ),
                "stream_session_recoveries": getattr(
                    self, "_stream_session_recoveries", 0
                ),
                "stream_recovery_pending": bool(getattr(
                    self, "_stream_recovery_pending", False
                )),
            },
        }

    def _copy_stream_diagnostics(self):
        """User-initiated clipboard copy of aggregate Tk metrics only."""
        try:
            report = stream_safe_qa_report(self.stream_performance_snapshot())
        except Exception:
            report = None
        if report is None:
            self._stream_update_diagnostic("No active stream metrics to copy")
            return False
        try:
            encoded = json.dumps(report, indent=2, sort_keys=True,
                                 ensure_ascii=True, allow_nan=False)
            self.root.clipboard_clear()
            self.root.clipboard_append(encoded)
            self.root.update_idletasks()
        except Exception:
            # No raw exception/driver string may appear in the UI.
            self._stream_update_diagnostic("Could not copy stream diagnostics")
            return False
        self._stream_update_diagnostic(
            "Copied Tk stream metrics (not OBS or physical-camera FPS)"
        )
        return True

    def _stream_update_diagnostic(self, message):
        """Avoid changing Tk state every frame when the text is identical."""
        status = getattr(self, "_stream_diagnostic", None)
        if status is None:
            return
        try:
            if status.get() != message:
                status.set(message)
        except Exception:
            # The uncaptured settings dialog may close independently of
            # the stream canvas. Third-party Tk variable wrappers can raise
            # RuntimeError, OSError or custom errors in addition to
            # TclError. This status label is best-effort: never classify its
            # failure as a bad game/camera frame or expose exception text.
            pass

    def _stream_blank_output(self):
        """Remove the OBS-facing image after a failed composition.

        A Tk PhotoImage may already be partly updated when paste() fails.
        Clear the canvas item *and* native image reference so the next OBS
        capture cannot keep showing stale webcam/game pixels. Camera capture,
        tracking and native emulator input remain entirely untouched.
        """
        canvas = getattr(self, "_stream_canvas", None)
        self._stream_photo = None
        self._stream_canvas_item = None
        self._invalidate_stream()
        if canvas is not None:
            try:
                canvas.delete("all")
            except Exception:
                # A window may already be destroyed; never send a native
                # widget/driver exception into the original game loop.
                pass

    def _stream_render_tick(self):
        self._stream_frame_job = None
        output = self._stream_output_window
        if output is None or getattr(self, "_closing", False):
            return
        # A slow/reentrant compositor may close this output and open another
        # while the old Tk callback is still on the stack. That old callback
        # must not record metrics, blank, close or schedule a second timer on
        # the new capture session.
        # Stream Mode clocks and canvas composition are optional. Neither
        # may stall the native emulator's independent video/audio/input loop.
        raw_mode = self._stream_options.get("frame_rate")
        mode = (
            raw_mode if isinstance(raw_mode, str) and raw_mode in FRAME_RATES
            else DEFAULT_STREAM["frame_rate"]
        )
        interval = round(1000 / int(mode.split()[0]))
        started = stream_optional_perf_clock()
        try:
            if started is None:
                raise RuntimeError("Stream composition timer unavailable")
            published = self._render_stream_frame() is True
            if self._stream_output_window is not output:
                return
            finished = stream_optional_perf_clock()
            if self._stream_output_window is not output:
                return
            if finished is None or finished < started:
                raise RuntimeError("Stream composition timer unavailable")
            elapsed = finished - started
            interval = stream_render_delay_ms(interval, elapsed)
            cadence = getattr(self, "_stream_cadence", None)
            if cadence is not None:
                cadence.record_tick(
                    finished, mode, published=published,
                    render_seconds=elapsed,
                )
            if self._stream_output_window is not output:
                return
            if published and getattr(self, "_stream_recovery_pending", False):
                self._stream_session_recoveries = (
                    getattr(self, "_stream_session_recoveries", 0) + 1
                )
                self._stream_recovery_pending = False
            self._stream_update_diagnostic(
                "Output ready · Game and camera are mirrored, not restarted."
            )
        except tk.TclError:
            if self._stream_output_window is output:
                self.close_stream_mode()
            return
        except Exception as exc:
            if self._stream_output_window is not output:
                return
            cadence = getattr(self, "_stream_cadence", None)
            if cadence is not None:
                finished = stream_optional_perf_clock()
                if finished is None:
                    cadence.record_failed_without_clock(mode)
                else:
                    measured = (
                        finished - started
                        if started is not None and finished >= started else None
                    )
                    cadence.record_tick(
                        finished, mode, failed=True, render_seconds=measured,
                    )
            # Session-wide fault evidence survives output-rate switches.
            self._stream_session_faults = (
                getattr(self, "_stream_session_faults", 0) + 1
            )
            self._stream_recovery_pending = True
            # A corrupt PIL/driver frame must never remain visible in OBS
            # while the optional compositor retries. Do not stop the
            # underlying camera or emulator; back off to one attempt/sec.
            self._stream_blank_output()
            interval = 1000
            self._stream_update_diagnostic(
                "Stream preview retrying ("
                + stream_safe_failure_class(exc) + ")."
            )
        if self._stream_output_window is output and not self._closing:
            try:
                self._stream_frame_job = self.root.after(
                    interval, self._stream_render_tick
                )
            except (tk.TclError, RuntimeError):
                if self._stream_output_window is output:
                    self.close_stream_mode()

    def _render_stream_frame(self):
        canvas = self._stream_canvas
        if canvas is None or not canvas.winfo_exists():
            self.close_stream_mode()
            return False
        output = self._stream_output_window
        w = max(320, min(1920, canvas.winfo_width()))
        h = max(400, min(1600, canvas.winfo_height()))
        active_game = bool(self.emu.running and self.uses_embedded_emulator())
        if active_game:
            # Protect only the native-owned pixel snapshot. Converting a
            # possibly large NumPy array to a PIL image can allocate/copy
            # more memory; doing that under the emulator lock blocks native
            # frame publishing and adds avoidable gameplay latency.
            changed = False
            fresh = None
            with self.emu.lock:
                serial = getattr(self.emu, "frame_serial", 0)
                if serial != self._stream_game_serial:
                    fresh = (None if self.emu.frame is None
                             else self.emu.frame[:, :, :3].copy())
                    changed = True
            if changed:
                converted = Image.fromarray(fresh) if fresh is not None else None
                # Stop/ROM replacement may have revoked this source while
                # PIL converted a large copied frame outside the native
                # lock. Never reattach that old PIL image after cleanup.
                stop = getattr(self.emu, "stop_event", None)
                with self.emu.lock:
                    still_current = (
                        self.emu.running
                        and getattr(self.emu, "frame_serial", 0) == serial
                        and not (
                            isinstance(stop, threading.Event)
                            and stop.is_set()
                        )
                    )
                # A reentrant preview hook can also close/reopen Stream
                # Mode during PIL conversion. Do not attach a copied frame
                # to a new output generation even if the native serial
                # itself has not changed.
                same_output = (
                    self._stream_output_window is output
                    and self._stream_canvas is canvas
                )
                if not same_output:
                    return False
                if not still_current:
                    # Merely receiving the NEXT healthy native frame does
                    # not revoke the previously displayed game image.
                    # Actual Stop/core exit does: blank its OBS-facing Tk
                    # photo immediately, rather than leave the old image
                    # visible until a later Stream tick.
                    stopped = (
                        not self.emu.running
                        or (isinstance(stop, threading.Event)
                            and stop.is_set())
                    )
                    if stopped:
                        self._stream_game_frame = None
                        self._stream_game_serial = None
                        cache = getattr(self, "_stream_resize_cache", None)
                        if cache is not None:
                            try:
                                cache.clear("GAME")
                            except Exception:
                                self._stream_resize_cache = None
                        self._stream_blank_output()
                    else:
                        self._stream_last_render = None
                    return False
                self._stream_game_frame = converted
                self._stream_game_serial = serial
        else:
            serial = None
            self._stream_game_frame = None
            self._stream_game_serial = None
            # Native cores can finish or crash without an explicit Library
            # Stop/ROM-switch command. In that case the visible stream game
            # goes blank, but the resize cache can still retain both the old
            # PIL source image and its fitted pixels. Discard only GAME;
            # the live camera cache and camera snapshot remain untouched.
            cache = getattr(self, "_stream_resize_cache", None)
            if cache is not None:
                try:
                    cache.clear("GAME")
                except Exception:
                    # An optional/customized cache must not break Stream
                    # Output or expose private driver exception details.
                    self._stream_resize_cache = None
        # An unplugged or misbehaving webcam may throw from isOpened()
        # before the main camera tick processes its disconnect. Treat that
        # driver failure as camera-off for OBS; never leave a stale private
        # frame visible while the stream preview backs off on errors.
        camera_active = False
        if self.cap is not None:
            try:
                camera_active = bool(self.cap.isOpened())
            except Exception:
                # isOpened() may raise arbitrary third-party wrapper errors.
                # Only the optional OBS preview is affected.
                pass
        camera_ref = bool(self.reference_image and self.frame is not None)
        if (camera_active and not camera_ref
                and self._stream_camera_frame is not None):
            try:
                observed_at = time.monotonic()
                clock_valid = (
                    type(observed_at) in (float, int)
                    and math.isfinite(observed_at) and observed_at >= 0
                )
            except Exception:
                clock_valid = False
            last_success = getattr(
                self, "_stream_camera_last_snapshot", None
            )
            try:
                last_valid = (
                    type(last_success) in (int, float)
                    and math.isfinite(last_success) and last_success >= 0
                )
            except (OverflowError, TypeError, ValueError):
                last_valid = False
            if (not clock_valid or not last_valid
                    or stream_camera_frame_is_stale(last_success, observed_at)):
                # A device-open flag and a cached PIL image do not prove a
                # recent, successful capture. A malformed/missing previous
                # timestamp also invalidates the OBS-facing webcam image.
                # Intentional static reference art bypasses this guard.
                # Neither the camera tracking nor native buttons are touched.
                self._stream_stale_camera_clears = (
                    getattr(self, "_stream_stale_camera_clears", 0) + 1
                )
                self.stream_clear_camera()
        if not camera_active and not camera_ref and self._stream_camera_frame is not None:
            self.stream_clear_camera()
        status = (active_game, camera_active, camera_ref)
        state = (
            w, h, serial, self._stream_camera_serial, status,
            tuple(self._stream_options.items()),
        )
        if state == self._stream_last_render:
            return False
        frame = compose_stream_output(
            self._stream_game_frame if active_game else None,
            self._stream_camera_frame if camera_active or camera_ref else None,
            size=(w, h), settings=self._stream_options, themes=self.THEMES,
            game_active=active_game,
            camera_active=camera_active, camera_reference=camera_ref,
            resize_cache=getattr(self, "_stream_resize_cache", None),
        )
        # Compositing and resizing happen OUTSIDE the native frame lock.
        # Stop, camera unplug, changed settings or a closed/reopened window
        # may invalidate those pixels during a slow PIL operation. Before
        # mutating an existing Tk PhotoImage (which OBS may be capturing),
        # verify that the source generations and target still match.
        if (self._stream_output_window is not output
                or self._stream_canvas is not canvas):
            return False  # The old window is already retired.
        changed_camera = self._stream_camera_serial != state[3]
        changed_settings = tuple(self._stream_options.items()) != state[5]
        still_active = bool(
            self.emu.running and self.uses_embedded_emulator()
        )
        changed_game = still_active != active_game
        if active_game:
            stop = getattr(self.emu, "stop_event", None)
            with self.emu.lock:
                changed_game = changed_game or (
                    getattr(self.emu, "frame_serial", 0) != serial
                    or not self.emu.running
                    or (isinstance(stop, threading.Event) and stop.is_set())
                )
        if changed_game or changed_camera or changed_settings:
            cache = getattr(self, "_stream_resize_cache", None)
            if changed_game and self._stream_game_serial == serial:
                self._stream_game_frame = None
                self._stream_game_serial = None
            if cache is not None and (changed_game or changed_camera):
                try:
                    if changed_game:
                        cache.clear("GAME")
                    if changed_camera:
                        cache.clear("CAMERA")
                except Exception:
                    # No old privacy-sensitive fitted source may survive a
                    # failed optional cache eviction.
                    self._stream_resize_cache = None
            self._stream_blank_output()
            return False
        photo = self._stream_photo
        if photo is None or photo.width() != w or photo.height() != h:
            photo = ImageTk.PhotoImage(frame, master=self._stream_output_window)
            self._stream_photo = photo
        else:
            photo.paste(frame)
        item = self._stream_canvas_item
        if item is None or not canvas.type(item):
            canvas.delete("all")
            item = canvas.create_image(0, 0, image=photo, anchor="nw")
            self._stream_canvas_item = item
        else:
            canvas.itemconfigure(item, image=photo)
        self._stream_last_render = state
        return True

    def close_stream_mode(self):
        job = getattr(self, "_stream_frame_job", None)
        self._stream_frame_job = None
        if job is not None:
            try:
                self.root.after_cancel(job)
            except tk.TclError:
                pass
        save_job = getattr(self, "_stream_save_job", None)
        self._stream_save_job = None
        if save_job is not None:
            try:
                self.root.after_cancel(save_job)
            except tk.TclError:
                pass
            # App.close() sets _closing before cleaning auxiliary windows.
            # Persist the last user style change even during that shutdown.
            try:
                self.save_preferences()
            except (OSError, ValueError, tk.TclError):
                pass
        self._close_stream_controls()
        output = getattr(self, "_stream_output_window", None)
        self._stream_output_window = None
        self._stream_canvas = None
        self._stream_photo = None
        self._stream_canvas_item = None
        self._stream_camera_frame = None
        self._stream_camera_last_snapshot = None
        self._stream_camera_force_next_snapshot = False
        self._stream_game_frame = None
        self._stream_game_serial = None
        self._stream_last_render = None
        self._stream_cadence = None
        cache = getattr(self, "_stream_resize_cache", None)
        self._stream_resize_cache = None
        if cache is not None:
            try:
                cache.clear()
            except Exception:
                # The output references have already been revoked. A
                # third-party cache failure must not prevent destroying
                # the capture window or clearing the rest of its state.
                pass
        self._stream_stale_camera_clears = 0
        self._stream_session_faults = 0
        self._stream_session_recoveries = 0
        self._stream_recovery_pending = False
        if output is not None:
            try:
                output.destroy()
            except tk.TclError:
                pass
