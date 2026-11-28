"""Coordinate manual game input, safe camera controls, and game frames."""

import math
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
from PIL import Image, ImageTk

from anything_plays.systems import SYSTEMS
from anything_plays.shortcuts import button_for_key
from anything_plays.cameras import usable_bgr_frame
from anything_plays.launch_error_messages import safe_worker_failure


_SAFE_GUI_ERROR_CLASSES = frozenset((
    "OSError", "RuntimeError", "ValueError", "TypeError", "IndexError",
    "AttributeError", "MemoryError", "TclError", "error",
))


def safe_gui_failure_class(exc):
    """Allowlisted error category; never display exception/device text."""
    category = type(exc).__name__
    return category if category in _SAFE_GUI_ERROR_CLASSES else "UnexpectedError"


def optional_game_render_clock():
    """Read the UI display clock without risking a permanently dead timer.

    Invalid monotonic timestamps can occur after suspend/VM resume, or from
    a native timing wrapper. Skip only that optional render update; keep
    scheduling a safe retry while the emulator/audio worker keeps running.
    """
    try:
        now = time.monotonic()
        if (type(now) in (int, float)
                and math.isfinite(now) and 0 <= now <= 1_000_000_000_000):
            return now
    except Exception:
        pass
    return None


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
        if not path:
            return False
        # Legacy manual-core selection must obey the same native worker
        # acknowledgement as ROM replacement and console switching.
        # A stuck retro_run() can outlive the bounded Stop join; never
        # change its loaded DLL pointer while the worker still owns it.
        self.stop_controls()
        try:
            stopped = self.emu.stop()
        except Exception:
            self.game_status.set(
                'Could not stop the previous emulator. Core unchanged.'
            )
            return False
        if stopped is False:
            self.game_status.set(
                'Previous emulator is still shutting down. '
                'Core unchanged; retry after it finishes.'
            )
            return False
        prior_core = self.emu.core_path
        self.emu.core_path = path
        try:
            self.save_preferences(core_path=path)
        except Exception:
            # A failed preferences write must not silently commit a core
            # selector inconsistent with the saved installed configuration.
            # Never copy private path/permission exception text to Tk.
            self.emu.core_path = prior_core
            self.game_status.set(
                'Could not save emulator selection. Previous core retained.'
            )
            return False
        self.game_status.set('Core selected: ' + Path(path).name)
        return True

    def activate_manual(self, event=None):
        self.manual_active = True
        canvas = getattr(self, '_game_only_canvas', None) or self.game_canvas
        canvas.focus_set()
        self.manual_label.set('MANUAL PLAY ACTIVE · Open Game Controls to view or edit keys')

    def _release_manual_native(self):
        """Revoke native keyboard input even if its facade was replaced."""
        try:
            self.emu.release_manual()
        except Exception:
            inputs = getattr(self.emu, "inputs", None)
            release = getattr(inputs, "release_manual", None)
            if callable(release):
                try:
                    release()
                except Exception:
                    pass

    def _release_manual_external(self):
        """Never leave a disconnected external bridge holding a game key.

        Release errors may mean an IPC pipe is unusable. Retire its emulator
        process rather than allowing a stuck held button to continue after
        a focus loss or failed Tk key event.
        """
        bridge = getattr(self, "external_input", None)
        if bridge is None:
            return
        try:
            bridge.release_manual()
        except Exception:
            stop = getattr(self, "stop_external_emulator", None)
            if callable(stop):
                try:
                    stop()
                    return
                except Exception:
                    pass
            # A custom host may have no external Stop hook. Close the
            # damaged pipe and detach it, so future key events cannot
            # continue delivering to an already broken controller.
            try:
                bridge.close()
            except Exception:
                pass
            self.external_input = None

    def deactivate_manual(self, event=None):
        self.manual_active = False
        # Both release paths are independent: a broken native facade must
        # not skip an external bridge, or vice versa. A destroyed Tk label
        # cannot prevent either physical input channel being released.
        self._release_manual_native()
        self._release_manual_external()
        try:
            self.manual_label.set(
                'Click game screen to use editable keyboard controls'
            )
        except Exception:
            pass

    def deactivate_on_outside_click(self, event):
        if event.widget not in (self.game_canvas, getattr(self, '_game_only_canvas', None)) and self.manual_active:
            self.deactivate_manual()

    def _manual_key_failure(self):
        self.deactivate_manual()
        try:
            self.manual_label.set(
                'Manual input paused after controller error. Click game screen to retry.'
            )
        except Exception:
            pass

    def manual_key_down(self, event):
        button = button_for_key(self.system_key.get(), self._shortcut_bindings.get(self.system_key.get()), event.keysym)
        if button and self.manual_active:
            if self.external_input is not None:
                try:
                    self.external_input.set_manual(button, True)
                except Exception:
                    self._manual_key_failure()
                return 'break'
            if self.uses_embedded_emulator():
                try:
                    self.emu.set_manual(button, True)
                except Exception:
                    self._manual_key_failure()
                return 'break'

    def manual_key_up(self, event):
        button = button_for_key(self.system_key.get(), self._shortcut_bindings.get(self.system_key.get()), event.keysym)
        if button:
            failed = False
            try:
                self.emu.set_manual(button, False)
            except Exception:
                failed = True
            bridge = getattr(self, "external_input", None)
            if bridge is not None:
                try:
                    bridge.set_manual(button, False)
                except Exception:
                    failed = True
            if failed:
                self._manual_key_failure()
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
        except Exception:
            # Some camera extensions use vendor-specific exception classes
            # during unplug. Treat *any* isOpened failure as disconnected;
            # the caller must release held controls before retrying.
            return False

    def toggle(self):
        if self.armed:
            self.stop_controls()
            return
        if getattr(self, "_calibration_window", None) is not None:
            # Calibration is intentionally non-modal so users can click the
            # camera preview. Never arm gameplay input during that workflow.
            self.action.set(
                "Finish or cancel calibration before enabling object controls."
            )
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
                # Legacy native workers may retain exception detail for
                # compatibility, including ROM paths and device identifiers.
                # Status and warning dialogs may only contain fixed guidance.
                safe_detail = safe_worker_failure(detail, starting=True)
                self.game_status.set(safe_detail)
                messagebox.showwarning(
                    "Game did not start",
                    safe_detail
                    + "\n\nCheck the game and bundled emulator files, or "
                      "restore the bundled emulator in Emulator maintenance.",
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
        """Release camera input even when a native hook or Tk widget fails.

        Stop is a safety action and is also called before ROM shutdown.
        An expired Libretro wrapper, detached external bridge or destroyed
        status widget must not prevent the other input sources from being
        released. Never display native exception text or device paths.
        """
        self._pending_object_controls = False
        self.armed = False
        try:
            self.emu.disarm()
        except Exception:
            # If a replaced native facade faults, revoke its arm flag and
            # clear the real InputBuffer directly. The independent camera
            # generation and queued P1/P2 pulses are reset there.
            try:
                self.emu.armed = False
            except Exception:
                pass
            inputs = getattr(self.emu, "inputs", None)
            fallback = getattr(inputs, "disarm", None)
            if callable(fallback):
                try:
                    fallback()
                except Exception:
                    pass
        pulses = getattr(self, "_last_camera_pulses", None)
        if pulses is not None:
            try:
                pulses.clear()
            except Exception:
                # Optional frame deduplication state cannot block Stop.
                self._last_camera_pulses = {}
        bridge = getattr(self, "external_input", None)
        if bridge is not None:
            try:
                bridge.release_camera()
            except Exception:
                # An external native pipe/UDP bridge may be offline during
                # teardown; camera and embedded input remain disarmed.
                pass
        if hasattr(self, 'arm_button'):
            try:
                label = ('Enable object controls'
                         if self.uses_embedded_emulator()
                         or SYSTEMS[self.system_key.get()].backend == 'retroarch'
                         or bridge is not None
                         else 'Camera controls unavailable for Dolphin')
                self.arm_button.config(text=label)
            except Exception:
                pass
        if hasattr(self, 'action'):
            try:
                self.action.set('PREVIEW ONLY — no keyboard events are sent')
            except Exception:
                pass

    def tick(self):
        """Process one UI frame, and always schedule another while the window lives."""
        if self._closing:
            return
        try:
            if self.cap is not None:
                # A native read/flip can yield to a Stop, webcam replacement
                # or Tk teardown. Bind this capture tick to its original
                # device, never attach old pixels to a newly opened camera.
                capture = self.cap
                # Some USB drivers switch isOpened() to false on unplug,
                # without returning a failed read(). Treat both signals as
                # the same disconnect, clearing the bezel and held controls
                # through stop_camera() before queuing a bounded retry.
                camera_open = GameplayMixin._camera_is_open(self)
                try:
                    ok, frame = capture.read() if camera_open else (False, None)
                    # A reported successful native read can contain invalid
                    # pixels during a USB transition; mirrored output must
                    # satisfy the same contract before reaching tracking.
                    ok = bool(ok) and usable_bgr_frame(frame)
                    if ok and self.mirror.get():
                        frame = cv2.flip(frame, 1)
                        ok = usable_bgr_frame(frame)
                except Exception:
                    # Vendor-native read()/flip()/shape helpers may raise a
                    # custom exception outside OpenCV's documented family.
                    # Keep every failure on the *same* bounded reconnect
                    # path that releases held camera controls first. Never
                    # surface its message (device paths/serials) in the UI.
                    ok, frame = False, None
                if getattr(self, "_closing", False):
                    # Do not render or schedule another frame after shutdown
                    # started while the native driver was processing a frame.
                    return
                if self.cap is not capture:
                    # The old read may have succeeded OR failed after Stop /
                    # reconnection. Neither result can publish stale pixels,
                    # disarm the new session or queue an old-device retry.
                    pass
                elif ok:
                    self.frame = frame
                else:
                    # The dropdown may have changed without pressing Use
                    # camera. Reconnect only the original active device,
                    # never another one that happened to be selected.
                    chosen = getattr(self, "_active_camera_name", None)
                    chosen = chosen or self.camera_name.get()
                    self.stop_camera()
                    if chosen == self.camera_name.get():
                        self._queue_camera_retry(chosen)
                    else:
                        self.status.set(
                            "Camera disconnected after selection changed. "
                            "Click Use camera to start the chosen device; "
                            "object controls remain paused."
                        )
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
                self.game_status.set(safe_worker_failure(self.emu.error))
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
                # A timed-out native Stop may retain running=True until the
                # worker returns from retro_run(). Never replace the explicit
                # "still shutting down" status with a false "Playing" label.
                # New sessions clear stop_event before launching the worker.
                stop_event = getattr(self.emu, "stop_event", None)
                try:
                    stopping = (stop_event is not None
                                and stop_event.is_set() is True)
                except Exception:
                    stopping = True
                if (not stopping and self.current_rom and
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
            self.status.set(
                'Tracking error (' + safe_gui_failure_class(exc)
                + '). Camera controls paused; check connection or permissions.'
            )
        finally:
            if not self._closing:
                active_camera = GameplayMixin._camera_is_open(self)
                interval = 45 if active_camera else (
                    500 if self.reference_image else 200
                )
                self._camera_tick_job = self.root.after(interval, self.tick)

    def game_render_tick(self):
        """Keep native game video repainting after timer, Tk or GPU faults."""
        if self._closing:
            return
        now = optional_game_render_clock()
        try:
            if now is None:
                # Do not feed NaN/Infinity to retry thresholds or spin
                # repeated native image failures at 60 FPS. Try the clock
                # again on a slower Tk tick; the game/audio worker is alive.
                return
            last = getattr(self, "_game_render_last_clock", None)
            if type(last) in (int, float) and now < last:
                # A suspended/restored VM or broken monotonic source can
                # jump backwards. Old retry deadlines would otherwise freeze
                # the video for minutes or hours after a clock reset.
                self._game_render_retry_at = 0
                self._game_render_warning_at = 0
            self._game_render_last_clock = now
            retry_at = getattr(self, "_game_render_retry_at", 0)
            if (type(retry_at) not in (int, float)
                    or not math.isfinite(retry_at)):
                retry_at = 0
            if now >= retry_at:
                self.draw_game()
        except tk.TclError:
            # A game-only window can disappear between two scheduled frames.
            self._game_render_retry_at = now + 0.5 if now is not None else 0
        except Exception as exc:
            # A bad frame should not produce thousands of exceptions while
            # the emulator stays open. Retry later and surface a readable
            # status without leaking ROM paths or driver identifiers.
            self._game_render_retry_at = now + 2.0 if now is not None else 0
            warning_at = getattr(self, "_game_render_warning_at", 0)
            if type(warning_at) not in (int, float) or not math.isfinite(warning_at):
                warning_at = 0
            if now is not None and now >= warning_at:
                self._game_render_warning_at = now + 30.0
                try:
                    self.game_status.set(
                        "Display error (retrying: "
                        + safe_gui_failure_class(exc) + ")."
                    )
                except Exception:
                    # Tk may have disposed its status variable during a
                    # window transition. Do not kill the future repaint loop.
                    pass
        finally:
            if not self._closing:
                # Keep GameCube's explicit 20/30/60 FPS preview pacing on
                # healthy timers; invalid timestamps or disposed widgets
                # fall back to a low-cost 250ms recovery poll.
                interval = 250
                if now is not None:
                    try:
                        running = bool(self.emu.running)
                        interval = 16 if running else 250
                        if running and self.system_key.get() == "gamecube":
                            from anything_plays.gamecube_preview import preview_fps
                            mode = getattr(self.emu, "gamecube_preview_mode", "")
                            interval = round(1000 / preview_fps(mode))
                    except Exception:
                        interval = 250
                try:
                    self._game_tick_job = self.root.after(
                        interval, self.game_render_tick
                    )
                except Exception:
                    # The root may already have been destroyed in a nested
                    # GUI callback; a failed timer must not escape into Tk.
                    self._game_tick_job = None

    def draw_game(self):
        """Render a fresh frame only when the game or canvas changed."""
        # The native worker may exit on its own after an error or a core
        # shutdown, without the user requesting Library Stop. The last
        # PhotoImage can otherwise remain visible forever because there is
        # no new frame serial to trigger a redraw. Fail closed for old game
        # pixels, but never blank a still-launching core or an independent
        # Stream Mode camera-only composition.
        if not self.emu.running and not getattr(self.emu, "launching", False):
            with self.emu.lock:
                stale_native = self.emu.frame is not None
            stale_game = (
                stale_native
                or getattr(self, "game_photo", None) is not None
                or getattr(self, "_last_game_render", None) is not None
            )
            if stale_game:
                from anything_plays.game_display_lifecycle import clear_game_video
                clear_game_video(self)
            return

        canvas = getattr(self, '_game_only_canvas', None) or self.game_canvas
        canvas_width = max(1, canvas.winfo_width())
        canvas_height = max(1, canvas.winfo_height())
        # Capture the original frame's session and already-published image
        # BEFORE any Tk/PIL work. Stop, a ROM replacement or Game only view
        # switching can reenter while PIL scales the snapshot or Tcl creates
        # a PhotoImage. The native lock is never held around those calls.
        previous_render = getattr(self, "_last_game_render", None)
        previous_photo = getattr(self, "game_photo", None)
        with self.emu.lock:
            serial = getattr(self.emu, "frame_serial", 0)
            generation = getattr(self.emu, "session_generation", None)
            revision = (serial, id(canvas), canvas_width, canvas_height)
            if revision == previous_render:
                return
            frame = None if self.emu.frame is None else self.emu.frame.copy()
        if frame is None:
            return

        def still_current():
            # Only the game image is fenced: unrelated camera/OBS pixels and
            # native input/audio must not be touched by an outdated UI tick.
            if getattr(self, "_closing", False):
                return False
            selected = getattr(self, "_game_only_canvas", None) or self.game_canvas
            if selected is not canvas:
                return False
            if (getattr(self, "game_photo", None) is not previous_photo
                    or getattr(self, "_last_game_render", None)
                    != previous_render):
                return False
            stop = getattr(self.emu, "stop_event", None)
            try:
                if stop is not None and stop.is_set() is True:
                    return False
            except Exception:
                return False
            with self.emu.lock:
                current_serial = getattr(self.emu, "frame_serial", 0)
                # Native publication may advance every 16ms while Tk is
                # resizing or pasting a frame. Requiring equality at every
                # checkpoint can starve the canvas forever on a slow host.
                # A known unchanged session may finish its owned snapshot;
                # commit the captured serial, not the newer native serial,
                # so the next tick still draws the latest available frame.
                # Legacy adapters without a generation retain strict serial
                # equality, and backwards serial changes are always fenced.
                same_or_newer_frame = (
                    current_serial == serial
                    or (type(generation) is int
                        and type(serial) is int
                        and type(current_serial) is int
                        and current_serial > serial)
                )
                return (
                    getattr(self.emu, "session_generation", None) == generation
                    and same_or_newer_frame
                    and self.emu.frame is not None
                    and (self.emu.running
                         or getattr(self.emu, "launching", False))
                )

        scale = min(canvas_width / frame.shape[1], canvas_height / frame.shape[0])
        width = max(1, int(frame.shape[1] * scale))
        height = max(1, int(frame.shape[0] * scale))
        image = Image.fromarray(frame[:, :, :3]).resize(
            (width, height), Image.Resampling.NEAREST
        )
        if not still_current():
            return
        photo = previous_photo
        if (photo is None or photo.width() != width or
                photo.height() != height):
            # Recreate Tk's native image only when resolution changes. Never
            # attach an old ROM's new PhotoImage after a reentrant Stop.
            photo = ImageTk.PhotoImage(image)
        else:
            # This mutates an already displayed Tcl image; a Stop during
            # paste() must be fenced before we touch the canvas afterward.
            photo.paste(image)
        if not still_current():
            return

        x = (canvas_width - width) // 2
        y = (canvas_height - height) // 2
        item = getattr(self, "_game_image_item", None)
        needs_item = (
            getattr(self, "_game_image_canvas", None) is not canvas
            or item is None or not canvas.type(item)
        )
        if not still_current():
            return
        if needs_item:
            # One Tk item per canvas, even after 30-minute game sessions.
            canvas.delete("all")
            if not still_current():
                return
            item = canvas.create_image(x, y, image=photo, anchor="nw")
            if not still_current():
                # A Stop may have cleared the canvas INSIDE create_image().
                # Remove only our newly created item, not the new session's
                # other canvas or its independently published frames.
                try:
                    canvas.delete(item)
                except Exception:
                    pass
                return
            self._game_image_item = item
            self._game_image_canvas = canvas
        else:
            canvas.coords(item, x, y)
            if not still_current():
                return
            canvas.itemconfigure(item, image=photo)
            if not still_current():
                return
        self.game_photo = photo
        self._last_game_render = revision
