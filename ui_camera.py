"""Manage camera selection, sampling and preview without touching global input."""

import os
from queue import Empty, Queue
import threading
import time
from tkinter import colorchooser, filedialog, messagebox

import cv2
from PIL import Image, ImageTk

from cameras import discover
from system_profiles import DISABLED_MAPPING
from tracking import locate_target, zone_at


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
        self._camera_scan_results = Queue(maxsize=1)

        def worker():
            try:
                self._camera_scan_results.put((discover(), None))
            except Exception as exc:
                self._camera_scan_results.put(([], str(exc)))

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

    def start_camera(self):
        name = self.camera_name.get()
        if name not in self.camera_options:
            messagebox.showinfo('Camera', 'Select an available webcam first.')
            return
        self.stop_camera()
        self.reference_image = False
        index = self.camera_options[name]
        self.cap = cv2.VideoCapture(
            index, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY
        )
        if not self.cap.isOpened():
            self.stop_camera()
            messagebox.showerror('Camera', 'Unable to open this webcam. Close other apps using it, or refresh the list.')
            return
        self.status.set(f'Camera ready: {name}. Click Pick color from video, then click your target.')

    def stop_camera(self):
        self.stop_controls()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
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
        self.pick_mode = True
        self.status.set('Click the target color in the reference image. Start the webcam afterward.')

    def choose_color(self):
        color = colorchooser.askcolor(color='#%02x%02x%02x' % tuple(self.cfg['rgb']))
        if color[0]:
            self.cfg['rgb'] = [int(x) for x in color[0]]
            self.refresh_color()

    def refresh_color(self):
        self.color_text.set('Selected target color: #%02X%02X%02X' % tuple(self.cfg['rgb']))

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
            self.cfg['rgb'] = [int(v) for v in rgb]
            self.refresh_color()
            self.pick_mode = False
            self.status.set('Target color selected. Adjust tolerance if needed.')
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
                self.emu.press(button, self.hold_frames.get())
                self.last_action = time.monotonic()
                self.action.set(f'Object zone: {active} → game button: {button} (isolated)')
        geom = self.geometry()
        if geom:
            x, y, dw, dh, _, _ = geom
            rgb = cv2.cvtColor(cv2.resize(frame, (dw, dh)), cv2.COLOR_BGR2RGB)
            self.camera_photo = ImageTk.PhotoImage(Image.fromarray(rgb))
            self.canvas.delete('all')
            self.canvas.create_image(x, y, anchor='nw', image=self.camera_photo)
