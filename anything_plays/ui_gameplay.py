"""Coordinate manual game input, safe camera controls, and game frames."""

import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
from PIL import Image, ImageTk

from anything_plays.systems import SYSTEMS
from anything_plays.shortcuts import button_for_key


class GameplayMixin:
    """Own the manual-input focus policy and the game's UI refresh cycle.

    Callbacks use the controls built by ``LayoutMixin``; the Libretro worker
    remains solely responsible for native frame generation and sound.
    """

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
        canvas = getattr(self, '_game_only_canvas', None) or self.game_canvas
        canvas.focus_set()
        self.manual_label.set('MANUAL PLAY ACTIVE · Open Game Controls to view or edit keys')

    def deactivate_manual(self, event=None):
        self.manual_active = False
        self.emu.release_manual()
        if self.external_input is not None:
            self.external_input.release_manual()
        self.manual_label.set('Click game screen to use editable keyboard controls')

    def deactivate_on_outside_click(self, event):
        if event.widget not in (self.game_canvas, getattr(self, '_game_only_canvas', None)) and self.manual_active:
            self.deactivate_manual()

    def manual_key_down(self, event):
        button = button_for_key(self.system_key.get(), self._shortcut_bindings.get(self.system_key.get()), event.keysym)
        if button and self.manual_active:
            if self.external_input is not None:
                self.external_input.set_manual(button, True)
                return 'break'
            if self.uses_embedded_emulator():
                self.emu.set_manual(button, True)
                return 'break'

    def manual_key_up(self, event):
        button = button_for_key(self.system_key.get(), self._shortcut_bindings.get(self.system_key.get()), event.keysym)
        if button:
            self.emu.set_manual(button, False)
            if self.external_input is not None:
                self.external_input.set_manual(button, False)
            return 'break'

    def _camera_is_open(self):
        """Handle native USB driver errors without crashing Tk callbacks.

        Some capture backends throw from isOpened() on unplug rather than
        returning False. Both the arm button and frame scheduler need a
        reliable status without interrupting keyboard or gamepad play.
        """
        cap = getattr(self, "cap", None)
        if cap is None:
            return False
        try:
            return bool(cap.isOpened())
        except (cv2.error, OSError, RuntimeError):
            return False

    def toggle(self):
        if self.armed:
            self.stop_controls()
            return
        backend = (
            "libretro" if self.uses_embedded_emulator()
            else SYSTEMS[self.system_key.get()].backend
        )
        if backend == "dolphin" and self.external_input is None:
            messagebox.showinfo(
                'GameCube camera input',
                'This Dolphin installation does not have an active camera '
                'controller bridge. Launch a GameCube game first.'
            )
            return
        if not GameplayMixin._camera_is_open(self):
            messagebox.showinfo('Camera required', 'Choose and start a webcam first.')
            return
        if backend == "libretro" and not self.emu.running:
            worker = getattr(self.emu, "thread", None)
            if (getattr(self.emu, "launching", False)
                    and worker is not None and worker.is_alive()):
                # A cold N64 boot may take several seconds. The earlier UI
                # incorrectly said "no emulator" during this valid startup,
                # misleading people into thinking they had broken the game.
                if getattr(self, "_pending_object_controls", False):
                    self.stop_controls()
                else:
                    self._pending_object_controls = True
                    self.action.set(
                        "Waiting for the game to start. Object controls "
                        "will enable automatically when it is ready."
                    )
                    self.arm_button.config(text="Cancel pending object controls")
                return
            detail = getattr(self.emu, "last_error", None)
            if detail:
                self.game_status.set("Emulator launch failed: " + detail)
                messagebox.showwarning(
                    "Game did not start",
                    "The emulator stopped during loading.\n\n"
                    + detail[:350]
                    + "\n\nUse Restart game to try again, or "
                      "Restore previous / bundled in Emulator maintenance.",
                    parent=self.root,
                )
            else:
                self.game_status.set(
                    "No game running. Open a game ROM or choose Restart game."
                )
                messagebox.showinfo(
                    "Start a game first",
                    "The selected emulator is not currently running. "
                    "Open a game ROM, or use Restart game if one is selected.",
                    parent=self.root,
                )
            return
        if backend in ("retroarch", "dolphin"):
            process = self.external_process
            if self.external_input is None or process is None or process.poll() is not None:
                title = 'N64 emulator required' if backend == 'retroarch' else 'GameCube emulator required'
                messagebox.showinfo(
                    title, 'Launch a game for this console through Anything Plays first.'
                )
                return
        try:
            self.read_settings()
        except (ValueError, tk.TclError):
            messagebox.showerror('Settings', 'Please correct the numeric settings.')
            return
        self._pending_object_controls = False
        self.armed = True
        self.emu.armed = backend == "libretro"
        self.last_action = time.monotonic()
        self.arm_button.config(text='Pause object controls')
        self.action.set(
            'ACTIVE — external camera controller bridge'
            if backend != 'libretro' else
            'ACTIVE — object controls embedded emulator only'
        )

    def stop_controls(self):
        self._pending_object_controls = False
        self.armed = False
        self.emu.disarm()
        if hasattr(self, "_last_camera_pulses"):
            self._last_camera_pulses.clear()
        if self.external_input is not None:
            self.external_input.release_camera()
        if hasattr(self, 'arm_button'):
            label = ('Enable object controls'
                     if self.uses_embedded_emulator()
                     or SYSTEMS[self.system_key.get()].backend == 'retroarch'
                     or self.external_input is not None
                     else 'Camera controls unavailable for Dolphin')
            self.arm_button.config(text=label)
        if hasattr(self, 'action'):
            self.action.set('PREVIEW ONLY — no keyboard events are sent')

    def tick(self):
        """Process one UI frame, and always schedule another while the window lives."""
        if self._closing:
            return
        try:
            if self.cap is not None:
                # Some USB drivers switch isOpened() to false on unplug,
                # without returning a failed read(). Treat both signals as
                # the same disconnect, clearing the bezel and held controls
                # through stop_camera() before queuing a bounded retry.
                camera_open = GameplayMixin._camera_is_open(self)
                ok, frame = self.cap.read() if camera_open else (False, None)
                if ok:
                    self.frame = cv2.flip(frame, 1) if self.mirror.get() else frame
                else:
                    chosen = self.camera_name.get()
                    self.stop_camera()
                    self._queue_camera_retry(chosen)
            if self.frame is not None:
                # A still reference image needs only periodic redraw. Without
                # a live camera, repeatedly detecting the same pixels wastes
                # CPU and makes a week-long session unnecessarily expensive.
                now = time.monotonic()
                live = GameplayMixin._camera_is_open(self)
                if live or now >= getattr(self, "_static_preview_next_draw", 0):
                    self.draw_camera()
                    self._static_preview_next_draw = now + 0.5
            # Finish a user-requested arm only when the background native
            # core is actually ready. No global keyboard injection occurs.
            if getattr(self, "_pending_object_controls", False):
                if self.emu.running and GameplayMixin._camera_is_open(self):
                    self._pending_object_controls = False
                    self.toggle()
                elif not getattr(self.emu, "launching", False):
                    self.stop_controls()
            # Render game video on its own faster timer, not at camera speed.
            if self.emu.error:
                bezel = getattr(self, "game_bezel", None)
                if bezel is not None:
                    bezel.set_active(False)
                self.game_status.set(
                    'Emulator stopped: ' + self.emu.error
                    + ' · Select Restart game to recover.'
                )
                self._save_warning_until = time.monotonic() + 3600
                self.stop_controls()
                self.emu.error = None
            elif self.emu.save_warning:
                # Do not bury a disk/save failure beneath a continuously
                # refreshed "Playing" status during a long session.
                self.game_status.set(self.emu.save_warning)
                self._save_warning_until = time.monotonic() + 20
                self.emu.save_warning = None
            elif getattr(self.emu, "audio_warning", None):
                # Native audio output errors must be visible in packaged GUI
                # builds where users cannot read a terminal log.
                self.game_status.set("Audio unavailable: " + self.emu.audio_warning)
                self._save_warning_until = time.monotonic() + 20
                self.emu.audio_warning = None
            elif getattr(self.emu, "resume_info", None):
                # Tell the player a real, integrity-checked core recovery
                # resumed their session; do not overwrite it with the
                # normal Playing text on the next GUI timer callback.
                self.game_status.set(self.emu.resume_info)
                self._save_warning_until = time.monotonic() + 20
                self.emu.resume_info = None
            elif self.emu.running:
                if (self.current_rom and
                        time.monotonic() >= getattr(self, "_save_warning_until", 0)):
                    playing = 'Playing ' + Path(self.current_rom).stem
                    # Tk variable traces and widget relayouts are unnecessary
                    # if the status is unchanged across thousands of frames.
                    if self.game_status.get() != playing:
                        self.game_status.set(playing)
        except Exception as exc:
            self.stop_controls()
            # A capture or image-processing failure must not cause the same
            # exception to be thrown 20 times per second indefinitely.
            if self.cap is not None:
                self.stop_camera()
            self.status.set('Tracking error: ' + str(exc)[:120])
        finally:
            if not self._closing:
                active_camera = GameplayMixin._camera_is_open(self)
                interval = 45 if active_camera else (
                    500 if self.reference_image else 200
                )
                self._camera_tick_job = self.root.after(interval, self.tick)

    def game_render_tick(self):
        """Refresh game video, keeping idle resource use and errors bounded."""
        if self._closing:
            return
        now = time.monotonic()
        try:
            if now >= getattr(self, "_game_render_retry_at", 0):
                self.draw_game()
        except tk.TclError:
            # A game-only window can disappear between two scheduled frames.
            self._game_render_retry_at = now + 0.5
        except Exception as exc:
            # A bad frame should not produce thousands of exceptions while
            # the emulator stays open. Retry later and surface a readable status.
            self._game_render_retry_at = now + 2.0
            if now >= getattr(self, "_game_render_warning_at", 0):
                self._game_render_warning_at = now + 30.0
                self.game_status.set("Display error (retrying): " + str(exc)[:100])
        finally:
            if not self._closing:
                # A 3D preview does not need 60 Tk refresh timers when
                # GPU readbacks are deliberately budgeted at 20 or 30 FPS.
                # The native emulator and sound worker keep their own pace.
                interval = 16 if self.emu.running else 250
                if self.emu.running and self.system_key.get() == "gamecube":
                    from anything_plays.gamecube_preview import preview_fps
                    mode = getattr(self.emu, "gamecube_preview_mode", "")
                    interval = round(1000 / preview_fps(mode))
                self._game_tick_job = self.root.after(
                    interval, self.game_render_tick
                )

    def draw_game(self):
        """Render a fresh frame only when the game or canvas changed."""
        canvas = getattr(self, '_game_only_canvas', None) or self.game_canvas
        canvas_width = max(1, canvas.winfo_width())
        canvas_height = max(1, canvas.winfo_height())
        with self.emu.lock:
            serial = getattr(self.emu, "frame_serial", 0)
            revision = (serial, id(canvas), canvas_width, canvas_height)
            if revision == getattr(self, "_last_game_render", None):
                return
            frame = None if self.emu.frame is None else self.emu.frame.copy()
        if frame is None:
            return
        scale = min(canvas_width / frame.shape[1], canvas_height / frame.shape[0])
        width = max(1, int(frame.shape[1] * scale))
        height = max(1, int(frame.shape[0] * scale))
        image = Image.fromarray(frame[:, :, :3]).resize(
            (width, height), Image.Resampling.NEAREST
        )
        photo = self.game_photo
        if (photo is None or photo.width() != width or
                photo.height() != height):
            # Recreate Tk's native image only when resolution changes. A new
            # PhotoImage every 16 ms churns native/Tcl allocations over days.
            photo = ImageTk.PhotoImage(image)
        else:
            photo.paste(image)
        x = (canvas_width - width) // 2
        y = (canvas_height - height) // 2
        item = getattr(self, "_game_image_item", None)
        if (getattr(self, "_game_image_canvas", None) is not canvas
                or item is None or not canvas.type(item)):
            # A new canvas (e.g. Game only) needs one image item. Reuse it
            # across frames to keep Tk's item count permanently bounded.
            canvas.delete("all")
            item = canvas.create_image(x, y, image=photo, anchor="nw")
            self._game_image_item = item
            self._game_image_canvas = canvas
        else:
            canvas.coords(item, x, y)
            canvas.itemconfigure(item, image=photo)
        self.game_photo = photo
        self._last_game_render = revision
