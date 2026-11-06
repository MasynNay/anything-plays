"""Coordinate manual game input, safe camera controls, and game frames."""

import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
from PIL import Image, ImageTk

from systems import SYSTEMS


class GameplayMixin:
    """Own the manual-input focus policy and the game's UI refresh cycle.

    Callbacks use the controls built by ``LayoutMixin``; the Libretro worker
    remains solely responsible for native frame generation and sound.
    """

    KEYMAP = {
        'Up': 'Up', 'Down': 'Down', 'Left': 'Left', 'Right': 'Right',
        'z': 'A', 'x': 'B', 'a': 'Y', 's': 'X',
        'q': 'L', 'w': 'R', 'Return': 'Start', 'KP_Enter': 'Start',
    }

    def choose_core(self):
        """Retain the manual-core hook for existing integrations.

        The normal interface selects each console's core automatically.
        """
        path = filedialog.askopenfilename(
            title='Select libretro core for ' + SYSTEMS[self.system_key.get()].title,
            filetypes=[
                ('Native libraries', '*.so *.dll *.dylib'),
                ('All files', '*'),
            ],
        )
        if path:
            self.stop_controls()
            self.emu.stop()
            self.emu.core_path = path
            self.save_preferences(core_path=path)
            self.game_status.set('Core selected: ' + Path(path).name)

    def activate_manual(self, event=None):
        self.manual_active = True
        self.game_canvas.focus_set()
        self.manual_label.set('MANUAL PLAY ACTIVE · Arrows D-pad · Z/X A/B · A/S Y/X · Q/W L/R · Enter Start')

    def deactivate_manual(self, event=None):
        self.manual_active = False
        self.emu.release_manual()
        self.manual_label.set('Click game screen · Arrows D-pad · Z/X A/B · A/S Y/X · Q/W L/R · Enter Start')

    def deactivate_on_outside_click(self, event):
        if event.widget is not self.game_canvas and self.manual_active:
            self.deactivate_manual()

    def manual_key_down(self, event):
        button = self.KEYMAP.get(event.keysym)
        if button and self.manual_active:
            self.emu.set_manual(button, True)
            return 'break'

    def manual_key_up(self, event):
        button = self.KEYMAP.get(event.keysym)
        if button:
            self.emu.set_manual(button, False)
            return 'break'

    def toggle(self):
        if self.armed:
            self.stop_controls()
            return
        if self.cap is None or not self.cap.isOpened():
            messagebox.showinfo('Camera required', 'Choose and start a webcam first.')
            return
        if not self.emu.running:
            messagebox.showinfo('Emulator required', 'Open a compatible ROM first. No system-wide keyboard fallback is available.')
            return
        try:
            self.read_settings()
        except (ValueError, tk.TclError):
            messagebox.showerror('Settings', 'Please correct the numeric settings.')
            return
        self.armed = True
        self.emu.armed = True
        self.last_action = time.monotonic()
        self.arm_button.config(text='Pause object controls')
        self.action.set('ACTIVE — object controls embedded emulator only')

    def stop_controls(self):
        self.armed = False
        self.emu.disarm()
        if hasattr(self, 'arm_button'):
            self.arm_button.config(text='Enable object controls')
        if hasattr(self, 'action'):
            self.action.set('PREVIEW ONLY — no keyboard events are sent')

    def tick(self):
        """Process one UI frame, and always schedule another while the window lives."""
        if self._closing:
            return
        try:
            if self.cap is not None and self.cap.isOpened():
                ok, frame = self.cap.read()
                if ok:
                    self.frame = cv2.flip(frame, 1) if self.mirror.get() else frame
                else:
                    self.stop_camera()
                    self.status.set('Camera disconnected. Refresh and select another.')
            if self.frame is not None:
                self.draw_camera()
            self.draw_game()
            if self.emu.error:
                self.game_status.set('Emulator error: ' + self.emu.error)
                self.stop_controls()
                self.emu.error = None
            elif self.emu.running:
                if self.current_rom:
                    self.game_status.set('Playing ' + Path(self.current_rom).stem)
        except Exception as exc:
            self.stop_controls()
            self.status.set('Tracking error: ' + str(exc)[:120])
        finally:
            if not self._closing:
                self.root.after(45, self.tick)

    def draw_game(self):
        """Copy the worker's latest RGB frame before touching Tk image state."""
        with self.emu.lock:
            frame = None if self.emu.frame is None else self.emu.frame.copy()
        if frame is None:
            return

        canvas_width = max(1, self.game_canvas.winfo_width())
        canvas_height = max(1, self.game_canvas.winfo_height())
        scale = min(canvas_width / frame.shape[1], canvas_height / frame.shape[0])
        width = max(1, int(frame.shape[1] * scale))
        height = max(1, int(frame.shape[0] * scale))
        image = Image.fromarray(frame[:, :, :3]).resize(
            (width, height), Image.Resampling.NEAREST
        )
        self.game_photo = ImageTk.PhotoImage(image)
        self.game_canvas.delete('all')
        self.game_canvas.create_image(
            (canvas_width - width) // 2,
            (canvas_height - height) // 2,
            image=self.game_photo,
            anchor='nw',
        )
