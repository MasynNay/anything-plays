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
from functools import lru_cache
import tkinter as tk
from tkinter import colorchooser, ttk

import cv2
from PIL import Image, ImageDraw, ImageFont, ImageTk

LAYOUTS = ("DS stacked", "Side by side")
FRAME_RATES = ("15 FPS", "24 FPS", "30 FPS")
_HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")
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
    return (
        image.convert("RGB").resize(
            (dest_w, dest_h),
            Image.Resampling.NEAREST if nearest else Image.Resampling.BILINEAR,
        ),
        x0 + (width - dest_w) // 2,
        y0 + (height - dest_h) // 2,
    )


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


def compose_stream_output(game, camera, *, size, settings, themes,
                          game_active=False, camera_active=False,
                          camera_reference=False):
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
         "CAMERA LIVE" if camera_active else
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
            sized = _contained(source, video, nearest=nearest)
            if sized is not None:
                resized, x, y = sized
                img.paste(resized, (x, y))
            else:
                # A neutral, truthful placeholder until a live source exists.
                msg = "Load a game to begin" if name == "GAME" else "Start a camera to begin"
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
        self._stream_camera_frame = None
        self._stream_camera_serial = 0
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
        ttk.Button(root, text="Close Stream Mode",
                   command=self.close_stream_mode).pack(fill="x", pady=(10, 0))

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
        result = colorchooser.askcolor(
            color=default, parent=self._stream_controls_window,
            title="Stream border color",
        )
        if result[1] and _HEX.fullmatch(result[1]):
            self._stream_options["border_color"] = result[1].lower()
            self._stream_options_updated()

    def _reset_stream_border_color(self):
        self._stream_options["border_color"] = ""
        self._stream_options_updated()

    def _stream_controls_changed(self):
        if not getattr(self, "_stream_vars", None):
            return
        options = dict(self._stream_options)
        for key, var in self._stream_vars.items():
            try:
                options[key] = var.get()
            except tk.TclError:
                return
        previous_layout = self._stream_options["layout"]
        self._stream_options = validate_stream_settings(
            options, self.THEMES, self.theme_name.get(),
        )
        if self._stream_options["layout"] != previous_layout:
            # Present a natural portrait/landscape capture window on layout
            # change. Manual resizing afterwards remains fully supported.
            popup = getattr(self, "_stream_output_window", None)
            if popup is not None:
                natural = ((760, 980) if self._stream_options["layout"] == "DS stacked"
                           else (1180, 720))
                width = min(natural[0], max(450, popup.winfo_screenwidth()-65))
                height = min(natural[1], max(480, popup.winfo_screenheight()-90))
                popup.geometry(f"{width}x{height}")
        self._stream_options_updated()

    def _stream_options_updated(self):
        self._invalidate_stream()
        if self._stream_save_job is None:
            self._stream_save_job = self.root.after(600, self._save_stream_options)

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
        if self._stream_output_window is None:
            return
        if frame is None:
            self.stream_clear_camera()
            return
        # Bound temporary RGB memory independent of high-resolution webcams.
        height, width = frame.shape[:2]
        if max(height, width) > 1280:
            scale = 1280 / max(height, width)
            frame = cv2.resize(frame,
                               (max(1, round(width*scale)),
                                max(1, round(height*scale))))
        self._stream_camera_frame = Image.fromarray(
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        )
        self._stream_camera_serial += 1

    def stream_clear_camera(self):
        self._stream_camera_frame = None
        self._stream_camera_serial += 1
        self._invalidate_stream()

    def _stream_render_tick(self):
        self._stream_frame_job = None
        if self._stream_output_window is None or getattr(self, "_closing", False):
            return
        # Streamers can pick smooth motion or lower CPU usage without
        # changing the underlying emulator/camera sampling rates.
        interval = round(1000 / int(self._stream_options["frame_rate"].split()[0]))
        try:
            self._render_stream_frame()
            if hasattr(self, "_stream_diagnostic"):
                self._stream_diagnostic.set(
                    "Output ready · Game and camera are mirrored, not restarted."
                )
        except tk.TclError:
            self.close_stream_mode()
            return
        except Exception as exc:
            # A corrupt driver frame must not spin at the selected output FPS.
            # Back off, show a useful diagnostic, and retry without stopping
            # the original camera or emulator session.
            self._invalidate_stream()
            interval = 1000
            if hasattr(self, "_stream_diagnostic"):
                self._stream_diagnostic.set(
                    "Stream preview retrying: " + str(exc)[:100]
                )
        if self._stream_output_window is not None and not self._closing:
            self._stream_frame_job = self.root.after(interval, self._stream_render_tick)

    def _render_stream_frame(self):
        canvas = self._stream_canvas
        if canvas is None or not canvas.winfo_exists():
            self.close_stream_mode()
            return
        w = max(320, min(1920, canvas.winfo_width()))
        h = max(400, min(1600, canvas.winfo_height()))
        active_game = bool(self.emu.running and self.uses_embedded_emulator())
        if active_game:
            with self.emu.lock:
                serial = getattr(self.emu, "frame_serial", 0)
                if serial != self._stream_game_serial:
                    fresh = (None if self.emu.frame is None
                             else self.emu.frame[:, :, :3].copy())
                    self._stream_game_frame = (
                        Image.fromarray(fresh) if fresh is not None else None
                    )
                    self._stream_game_serial = serial
        else:
            serial = None
            self._stream_game_frame = None
            self._stream_game_serial = None
        # An unplugged or misbehaving webcam may throw from isOpened()
        # before the main camera tick processes its disconnect. Treat that
        # driver failure as camera-off for OBS; never leave a stale private
        # frame visible while the stream preview backs off on errors.
        camera_active = False
        if self.cap is not None:
            try:
                camera_active = bool(self.cap.isOpened())
            except (cv2.error, OSError, RuntimeError):
                pass
        camera_ref = bool(self.reference_image and self.frame is not None)
        if not camera_active and not camera_ref and self._stream_camera_frame is not None:
            self.stream_clear_camera()
        status = (active_game, camera_active, camera_ref)
        state = (
            w, h, serial, self._stream_camera_serial, status,
            tuple(self._stream_options.items()),
        )
        if state == self._stream_last_render:
            return
        frame = compose_stream_output(
            self._stream_game_frame if active_game else None,
            self._stream_camera_frame if camera_active or camera_ref else None,
            size=(w, h), settings=self._stream_options, themes=self.THEMES,
            game_active=active_game,
            camera_active=camera_active, camera_reference=camera_ref,
        )
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
        self._stream_game_frame = None
        self._stream_game_serial = None
        self._stream_last_render = None
        if output is not None:
            try:
                output.destroy()
            except tk.TclError:
                pass
