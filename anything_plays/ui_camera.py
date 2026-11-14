"""Manage camera selection, sampling and preview without touching global input."""

import os
from queue import Empty, Queue
import threading
import time
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox

import cv2
from PIL import Image, ImageTk

from anything_plays.cameras import discover
from anything_plays.system_profiles import DISABLED_MAPPING
from anything_plays.tracking import locate_target, locate_targets, zone_at
from anything_plays.libretro_input import TWO_PLAYER_SYSTEMS


class CameraMixin:
    """Tkinter behavior shared with the main application controller.

    These methods use widgets and state initialized by ``App.__init__``
    and ``LayoutMixin.build``. They are not standalone widgets.
    """

    def scan_cameras(self):
        """Probe off the UI thread; consume the result on Tk's main thread."""
        if self.camera_scanning:
            return
        self.stop_camera()
        self.camera_scanning = True
        self.status.set('Searching for available webcams…')
        results = Queue(maxsize=1)
        self._camera_scan_results = results

        def worker():
            # Capture this scan's queue, not the mutable App reference.
            # An old discovery thread must never send into a newer scan's
            # queue or keep the entire interface alive after it closes.
            try:
                results.put((discover(), None))
            except Exception as exc:
                results.put(([], str(exc)))

        threading.Thread(target=worker, daemon=True, name='camera-discovery').start()
        self.root.after(80, self._poll_camera_scan)

    def _poll_camera_scan(self):
        """Keep every Tk widget update on the main event-loop thread."""
        if self._closing:
            return
        try:
            cameras, error = self._camera_scan_results.get_nowait()
        except Empty:
            self.root.after(80, self._poll_camera_scan)
        else:
            self.finish_scan(cameras, error)

    def finish_scan(self, found, error=None):
        self.camera_scanning = False
        self.camera_options = {f'{name} (device {index})': index for index, name in found}
        self.camera_combo['values'] = list(self.camera_options)
        if found:
            self.camera_name.set(next(iter(self.camera_options)))
            self.status.set(f'{len(found)} camera(s) found. Select one, then click Use camera.')
        else:
            self.camera_name.set('')
            self.status.set('No usable cameras found.' + (f' {error}' if error else ' Check permissions or click Refresh cameras.'))

    def cancel_camera_reconnect(self):
        """Cancel any pending retry when the user chooses Stop or another camera."""
        job = getattr(self, "_camera_reconnect_job", None)
        self._camera_reconnect_job = None
        self._camera_reconnect_name = None
        self._camera_reconnect_attempts = 0
        if job is not None:
            try:
                self.root.after_cancel(job)
            except tk.TclError:
                pass

    def _queue_camera_retry(self, name):
        """Recover temporary webcam disconnects without spawning extra timers."""
        if self._closing or name not in self.camera_options:
            return
        if getattr(self, "_camera_reconnect_job", None) is not None:
            return
        attempt = getattr(self, "_camera_reconnect_attempts", 0) + 1
        self._camera_reconnect_attempts = attempt
        delay_seconds = min(30, 2 ** min(attempt, 5))
        self._camera_reconnect_name = name
        self.status.set(
            f'Camera disconnected. Retrying {name} in {delay_seconds}s; '
            'object controls remain paused.'
        )
        self._camera_reconnect_job = self.root.after(
            delay_seconds * 1000, lambda: self._retry_camera(name)
        )

    def _retry_camera(self, name):
        """Reconnect only the previously chosen webcam, never a new device."""
        self._camera_reconnect_job = None
        if (self._closing or
                getattr(self, "_camera_reconnect_name", None) != name or
                self.camera_name.get() != name):
            return
        try:
            self.start_camera(reconnecting=True)
        except Exception as exc:
            # Device drivers can briefly throw while reattaching. No modal
            # dialog, thread growth, or automatic rearming of game controls.
            self._queue_camera_retry(name)

    def start_camera(self, *, reconnecting=False):
        """Open the selected device, with silent bounded retries on hot-unplug."""
        name = self.camera_name.get()
        if name not in self.camera_options:
            if not reconnecting:
                messagebox.showinfo('Camera', 'Select an available webcam first.')
            return
        self.stop_camera(keep_reconnect=reconnecting)
        self.reference_image = False
        self.frame = None
        self._static_preview_next_draw = 0
        index = self.camera_options[name]
        try:
            self.cap = cv2.VideoCapture(
                index, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY
            )
            opened = self.cap is not None and self.cap.isOpened()
        except (cv2.error, OSError, RuntimeError):
            opened = False
        if not opened:
            self.stop_camera(keep_reconnect=reconnecting)
            if reconnecting:
                self._queue_camera_retry(name)
            else:
                messagebox.showerror(
                    'Camera', 'Unable to open this webcam. Close other apps '
                    'using it, or refresh the list.'
                )
            return
        bezel = getattr(self, "camera_bezel", None)
        if bezel is not None:
            bezel.set_active(True)
        if reconnecting:
            self._camera_reconnect_job = None
            self._camera_reconnect_name = None
            self._camera_reconnect_attempts = 0
            self.status.set(
                f'Camera reconnected: {name}. Object controls are paused; '
                'enable them again when ready.'
            )
        else:
            self.status.set(
                f'Camera ready: {name}. Click Pick color from video, '
                'then click your target.'
            )

    def stop_camera(self, *, keep_reconnect=False):
        """Release camera, stale frames, and pending reconnect when requested."""
        if not keep_reconnect:
            self.cancel_camera_reconnect()
        self.stop_controls()
        # Detach the handle before calling into the native driver. Some
        # drivers raise while closing a just-unplugged device; those errors
        # must not strand the Tk preview, bezel or Stream Mode on screen.
        cap, self.cap = self.cap, None
        if cap is not None:
            try:
                cap.release()
            except (cv2.error, OSError, RuntimeError):
                pass
        if not self.reference_image:
            self.frame = None
            self.camera_photo = None
            if hasattr(self, "canvas"):
                self.canvas.delete("all")
            self._camera_canvas_item = None
        # Legacy camera harnesses and nonstream clients do not mix in StreamMixin.
        # A real Stream Mode session always clears its stale preview on Stop.
        clear_stream = getattr(self, "stream_clear_camera", None)
        if callable(clear_stream):
            clear_stream()
        bezel = getattr(self, "camera_bezel", None)
        if bezel is not None:
            bezel.set_active(False)
        self.status.set('Camera stopped')

    def pick_color(self):
        if self.frame is None:
            messagebox.showinfo('Target color', 'Start a webcam first.')
            return
        self.pick_mode = True
        self.status.set('Click your target in the camera preview to sample its color.')

    def pick_image(self):
        path = filedialog.askopenfilename(filetypes=[('Images', '*.png *.jpg *.jpeg *.bmp *.webp')])
        if not path:
            return
        frame = cv2.imread(path)
        if frame is None:
            messagebox.showerror('Image', 'Unable to read this image.')
            return
        self.stop_camera()
        self.frame = frame
        self.reference_image = True
        self._static_preview_next_draw = 0
        self.pick_mode = True
        self.status.set('Click the target color in the reference image. Start the webcam afterward.')

    def choose_color(self):
        color = colorchooser.askcolor(color='#%02x%02x%02x' % tuple(self.cfg['rgb']))
        if color[0]:
            self.cfg['rgb'] = [int(x) for x in color[0]]
            self.refresh_color()

    def pick_second_color(self):
        if self.frame is None:
            messagebox.showinfo('Color 2', 'Start a webcam first.')
            return
        self.pick_mode = 'color2'
        self.status.set('Click a second target in the camera preview to sample Color 2.')

    def choose_second_color(self):
        rgb = self.cfg.get('rgb2', [255, 30, 180])
        color = colorchooser.askcolor(
            color='#%02x%02x%02x' % tuple(rgb)
        )
        if color[0]:
            self.cfg['rgb2'] = [int(x) for x in color[0]]
            self.refresh_color()
            self.update_tracking_preferences()

    def update_tracking_preferences(self, event=None):
        """Persist independent color and controller settings per console."""
        self.read_settings()
        self.profile_store.put(self.system_key.get(), self.cfg)
        self._last_camera_pulses.clear()
        if (self.color2_enabled.get()
                and self.color2_player.get() == 'Player 2'
                and self.system_key.get() not in TWO_PLAYER_SYSTEMS):
            self.status.set(
                'This console has no two-controller mode. '
                'Route the secondary object to Player 1.'
            )
        elif self.color2_enabled.get():
            self.status.set(
                'Secondary object enabled. Turn on multiple objects per color to track more than one.'
            )
        else:
            self.status.set('Secondary object disabled; primary tracking remains active.')

    def refresh_color(self):
        self.color_text.set(
            'Primary object color  ·  #%02X%02X%02X' % tuple(self.cfg['rgb'])
        )
        self.color2_text.set(
            'Secondary object color  ·  #%02X%02X%02X' %
            tuple(self.cfg.get('rgb2', [255, 30, 180]))
        )
        from anything_plays.ui_tracking_panel import (
            refresh_color_swatches, update_secondary_controls,
        )
        refresh_color_swatches(self)
        update_secondary_controls(self)

    def geometry(self):
        if self.frame is None:
            return None
        h, w = self.frame.shape[:2]
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        scale = min(cw / w, ch / h)
        dw, dh = max(1, int(w * scale)), max(1, int(h * scale))
        return ((cw - dw) // 2, (ch - dh) // 2, dw, dh, w, h)

    def xy(self, event):
        geom = self.geometry()
        if not geom:
            return None
        x, y, dw, dh, w, h = geom
        if not (x <= event.x < x + dw and y <= event.y < y + dh):
            return None
        return (min(w - 1, int((event.x - x) * w / dw)), min(h - 1, int((event.y - y) * h / dh)))

    def on_click(self, event):
        point = self.xy(event)
        if point is None:
            return
        if self.pick_mode:
            rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)[point[1], point[0]]
            secondary = self.pick_mode == 'color2'
            self.cfg['rgb2' if secondary else 'rgb'] = [int(v) for v in rgb]
            self.refresh_color()
            self.pick_mode = False
            if secondary:
                self.color2_enabled.set(True)
                self.update_tracking_preferences()
                self.status.set('Secondary object color sampled. Choose its player.')
            else:
                self.status.set('Primary object color sampled. Multi-object tracking is optional.')
                sampled = getattr(self, 'calibration_color_sampled', None)
                if callable(sampled):
                    sampled()
        elif self.custom_draw_enabled.get():
            self.drag_start = point

    def on_release(self, event):
        if not self.custom_draw_enabled.get() or self.drag_start is None:
            return
        end, start = self.xy(event), self.drag_start
        self.drag_start = None
        if end is None or self.frame is None:
            return
        h, w = self.frame.shape[:2]
        x1, x2 = sorted((start[0] / w, end[0] / w))
        y1, y2 = sorted((start[1] / h, end[1] / h))
        if (x2 - x1) * (y2 - y1) > .002:
            self.cfg['zones'][self.zone_name.get()] = [x1, y1, x2, y2]

    def draw_camera(self):
        """Detect all matching fish and route every occupied zone concurrently.

        This operates only on our current webcam frame, with no global OS
        keyboard injection. An absent fish releases its held button on the
        following camera frame; STOP clears both players immediately.
        """
        frame = self.frame.copy()
        h, w = frame.shape[:2]
        tol = max(1, min(90, int(self.tolerance.get())))
        area = max(5, int(self.min_area.get()))
        limit = 16 if self.multi_fish_enabled.get() else 1
        primary = locate_targets(
            frame, self.cfg['rgb'], tol, area, max_targets=limit
        )
        secondary = (
            locate_targets(
                frame, self.cfg.get('rgb2', [255, 30, 180]),
                tol, area, max_targets=limit,
            ) if self.color2_enabled.get() else []
        )
        mapping = {name: var.get() for name, var in self.mapping_vars.items()}
        active_zones = set()
        buttons = {0: set(), 1: set()}
        shuffle_seen = False
        second_player_allowed = self.system_key.get() in TWO_PLAYER_SYSTEMS
        second_player_requested = self.color2_player.get() == 'Player 2'

        for tracker, matches in ((0, primary), (1, secondary)):
            # OpenCV's BGR preview: bright green for Color 1, bright
            # magenta for Color 2. The actual image used for tracking is
            # never replaced with this drawn visualization.
            contour_color = (50, 245, 90) if tracker == 0 else (220, 65, 255)
            port = 0 if tracker == 0 or not second_player_requested else 1
            valid_port = port == 0 or (
                second_player_allowed and self.external_input is None
            )
            for center, contour in matches:
                cv2.circle(frame, center, 7, contour_color, -1)
                cv2.drawContours(frame, [contour], -1, contour_color, 2)
                zone = zone_at(
                    center, (w, h), self.cfg['zones'], mapping,
                    self.shuffle_enabled.get(),
                )
                if zone is None:
                    continue
                active_zones.add(zone)
                if zone == 'Shuffle':
                    shuffle_seen = True
                elif valid_port:
                    button = mapping.get(zone, zone)
                    if button != DISABLED_MAPPING:
                        buttons[port].add(button)

        if not shuffle_seen:
            self._shuffle_latched = False
        if (shuffle_seen and self.armed and self.shuffle_enabled.get()
                and not self._shuffle_latched):
            self._shuffle_latched = True
            self.shuffle_zones()

        if self.armed:
            if self.external_input is not None:
                # Developer-only external controller bridges do not support
                # a second port. Use bounded classic pulses for P1 only.
                now = time.monotonic()
                cooldown = max(.05, int(self.cooldown.get()) / 1000.0)
                for button in sorted(buttons[0]):
                    key = (0, button)
                    if now - self._last_camera_pulses.get(key, -1e9) >= cooldown:
                        self.external_input.press(button, self.hold_frames.get())
                        self._last_camera_pulses[key] = now
            elif self.camera_input_mode.get() == 'Pulse (classic)':
                # Each button has an independent cooldown; multiple objects
                # trigger multiple keys on the same emulator frame.
                self.emu.set_camera_buttons((), ())
                now = time.monotonic()
                cooldown = max(.05, int(self.cooldown.get()) / 1000.0)
                for port in (0, 1):
                    for button in sorted(buttons[port]):
                        key = (port, button)
                        if now - self._last_camera_pulses.get(key, -1e9) >= cooldown:
                            self.emu.press(
                                button, self.hold_frames.get(), port=port
                            )
                            self._last_camera_pulses[key] = now
            else:
                # Continuous per-frame input with no per-fish queue growth.
                # This is the ideal mode for a tank with several moving fish.
                self.emu.set_camera_buttons(buttons[0], buttons[1])
                self._last_camera_pulses.clear()

            if self.color2_enabled.get() and second_player_requested and (
                    not second_player_allowed or self.external_input is not None):
                message = (
                    'Secondary object cannot use Player 2 on this console/backend; '
                    'choose Player 1 or a two-controller embedded game.'
                )
            else:
                message = (
                    f'Primary objects: {len(primary)} · '
                    f'Secondary objects: {len(secondary)} · '
                    f'P1: {", ".join(sorted(buttons[0])) or "idle"} · '
                    f'P2: {", ".join(sorted(buttons[1])) or "idle"}'
                )
            if self.action.get() != message:
                self.action.set(message)

        # Calibration consumes observations from the same tracking pass.
        # Never open another webcam or duplicate color processing.
        note = getattr(self, "calibration_note_frame", None)
        if callable(note):
            note(primary, mapping, (w, h))

        frame = self.render_zones(frame, active_zones)
        # Reuse this already-annotated camera frame in the OBS capture view.
        # No second VideoCapture instance, camera permissions or tracking run.
        if getattr(self, "_stream_output_window", None) is not None:
            self.stream_camera_snapshot(frame)
        geom = self.geometry()
        if geom:
            x, y, dw, dh, _, _ = geom
            rgb = cv2.cvtColor(cv2.resize(frame, (dw, dh)), cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            photo = self.camera_photo
            if (photo is None or photo.width() != dw or
                    photo.height() != dh):
                # Reuse the Tcl image buffer while webcam dimensions stay
                # stable, preventing native allocation growth for long runs.
                photo = ImageTk.PhotoImage(image)
            else:
                photo.paste(image)
            item = getattr(self, "_camera_canvas_item", None)
            if item is None or not self.canvas.type(item):
                self.canvas.delete("all")
                item = self.canvas.create_image(
                    x, y, anchor="nw", image=photo
                )
                self._camera_canvas_item = item
            else:
                self.canvas.coords(item, x, y)
                self.canvas.itemconfigure(item, image=photo)
            self.camera_photo = photo
