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
        except (cv2.error, OSError) as exc:
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
        if self.cap is not None:
            try:
                self.cap.release()
            finally:
                self.cap = None
        if not self.reference_image:
            self.frame = None
            self.camera_photo = None
            if hasattr(self, "canvas"):
                self.canvas.delete("all")
            self._camera_canvas_item = None
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
                'Choose Player 1 for Color 2.'
            )
        elif self.color2_enabled.get():
            self.status.set(
                'Color 2 is tracking; each matching fish can press its own zone.'
            )
        else:
            self.status.set('Color 2 disabled; primary color tracking continues.')

    def refresh_color(self):
        self.color_text.set(
            'Color 1 · #%02X%02X%02X' % tuple(self.cfg['rgb'])
        )
        self.color2_text.set(
            'Color 2 · #%02X%02X%02X' %
            tuple(self.cfg.get('rgb2', [255, 30, 180]))
        )

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
                self.status.set('Color 2 sampled and enabled. Choose its player.')
            else:
                self.status.set('Color 1 sampled. Multiple matching fish are supported.')
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
        frame = self.frame.copy()
        h, w = frame.shape[:2]
        tol = max(1, min(90, int(self.tolerance.get())))
        area = max(5, int(self.min_area.get()))
        center, contour = locate_target(frame, self.cfg['rgb'], tol, area)
        if center is not None:
            cv2.circle(frame, center, 8, (0, 255, 0), -1)
            cv2.drawContours(frame, [contour], -1, (0, 255, 255), 2)
        mapping = {name: var.get() for name, var in self.mapping_vars.items()}
        active = zone_at(
            center, (w, h), self.cfg['zones'], mapping, self.shuffle_enabled.get()
        )
        frame = self.render_zones(frame, active)
        if active != 'Shuffle':
            self._shuffle_latched = False
        if active == 'Shuffle':
            if self.armed and self.shuffle_enabled.get() and not self._shuffle_latched:
                self._shuffle_latched = True
                self.shuffle_zones()
                self.action.set('Object activated Shuffle — controls rearranged')
        elif active and self.armed and time.monotonic() - self.last_action >= max(.05, int(self.cooldown.get()) / 1000):
            button = self.mapping_vars[active].get()
            if button != DISABLED_MAPPING:
                if self.external_input is not None:
                    self.external_input.press(button, self.hold_frames.get())
                else:
                    self.emu.press(button, self.hold_frames.get())
                self.last_action = time.monotonic()
                self.action.set(f'Object zone: {active} → game button: {button} (isolated)')
        geom = self.geometry()
        if geom:
            x, y, dw, dh, _, _ = geom
            rgb = cv2.cvtColor(cv2.resize(frame, (dw, dh)), cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            photo = self.camera_photo
            if (photo is None or photo.width() != dw or
                    photo.height() != dh):
                # Reuse the Tcl image buffer while webcam dimensions stay
                # stable; don't allocate 20 new native images per second.
                photo = ImageTk.PhotoImage(image)
            else:
                photo.paste(image)
            item = getattr(self, "_camera_canvas_item", None)
            # Reuse one Tk canvas item rather than allocating and deleting
            # ~20 canvas objects a second for days at a time.
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
