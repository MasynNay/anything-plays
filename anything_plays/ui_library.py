"""Browse user-supplied ROMs and manage the interactive cartridge shelf."""

from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk
from anything_plays.systems import SYSTEMS
from anything_plays.cartridge_art import cartridge_image, cartridge_font
from anything_plays.rom_library import scan_rom_directory, find_cover_art
from anything_plays.launch_error_messages import safe_launch_failure


MAX_VISIBLE_CARTRIDGES = 300
CARTRIDGES_PER_BATCH = 12


def stable_missing_core_guidance(system):
    """Version-independent repair instructions without ROM or host paths."""
    if system == 'gamecube':
        return (
            'The installed GameCube emulator or its required '
            'Dolphin system files are missing. Repair or '
            'reinstall Anything Plays. No separate Dolphin '
            'or emulator download is required.'
        )
    return (
        'A bundled emulator core is missing or damaged. '
        'Repair or reinstall Anything Plays; all supported '
        'console emulators are bundled for offline use.'
    )


def native_worker_alive(emu):
    """Treat an unfinished native worker as active even during final teardown.

    Libretro may set running=False before the Python thread exits. Do not
    switch the library pointer or discard the previous frame during that
    gap. A broken third-party thread probe fails closed.
    """
    worker = getattr(emu, "thread", None)
    if worker is None:
        return False
    probe = getattr(worker, "is_alive", None)
    if not callable(probe):
        return False
    try:
        return probe() is True
    except Exception:
        return True


class LibraryMixin:
    """Tkinter behavior shared with the main application controller.

    These methods use widgets and state initialized by ``App.__init__``
    and ``LayoutMixin.build``. They are not standalone widgets.
    """

    def read_rom_directory(self):
        return self.read_rom_directories().get('gba', '')

    def set_rom_directory(self):
        initial = self.rom_directory
        if not initial or not Path(initial).is_dir():
            initial = str(Path.home())
        directory = filedialog.askdirectory(
            parent=self.root,
            title='Choose your ' + SYSTEMS[self.system_key.get()].title + ' ROM folder',
            initialdir=initial)
        if not directory:
            return
        # Choosing the entire home directory or filesystem by accident used
        # to freeze the Tk interface while scanning thousands of files.
        broad_roots = {Path.home().resolve(), Path("/"),
                       Path.home().parent.resolve(), Path("/Volumes")}
        if Path(directory).resolve() in broad_roots:
            if not messagebox.askyesno(
                    "Very large ROM folder",
                    "This is a very broad folder and may contain thousands of "
                    "unrelated files. Choose a dedicated ROM folder instead? "
                    "Select Yes to browse again, or No to cancel.",
                    parent=self.root):
                return
            self.root.after_idle(self.set_rom_directory)
            return
        self.rom_directory = directory
        self.rom_directories[self.system_key.get()] = directory
        self.save_preferences()
        self.populate_inline_library()

    def scan_roms(self):
        """List files supported by the currently selected console."""
        extensions = SYSTEMS[self.system_key.get()].extensions
        return scan_rom_directory(self.rom_directory, extensions)

    # Keep the original public helpers for extensions and existing callers.
    cartridge_image = staticmethod(cartridge_image)
    cartridge_font = staticmethod(cartridge_font)

    def choose_or_rescan_library(self):
        # If no directory exists, ask for one; otherwise refresh without a popup.
        if not self.rom_directory or not Path(self.rom_directory).is_dir():
            self.set_rom_directory()
        else:
            self.populate_inline_library()

    def cancel_shelf_animation(self):
        if self.shelf_animation_job is not None:
            self.root.after_cancel(self.shelf_animation_job)
            self.shelf_animation_job = None
        self.shelf_animation_target = None

    def shelf_button_press(self, direction):
        """Click advances a page; holding continues moving the shelf."""
        self.shelf_button_release()
        self.cancel_shelf_momentum()
        self.cancel_shelf_animation()
        self.shelf_button_direction = direction
        self.scroll_cartridges(direction, pages=0.85)
        self.shelf_button_job = self.root.after(360, self.shelf_button_repeat)
        return 'break'

    def shelf_button_repeat(self):
        self.shelf_button_job = None
        if not self.shelf_button_direction:
            return
        self.scroll_cartridges(self.shelf_button_direction, pages=0.65)
        self.shelf_button_job = self.root.after(190, self.shelf_button_repeat)

    def shelf_button_release(self, event=None):
        self.shelf_button_direction = 0
        if self.shelf_button_job is not None:
            self.root.after_cancel(self.shelf_button_job)
            self.shelf_button_job = None
        return 'break'

    def scroll_cartridges(self, direction, pages=0.85):
        """Smoothly advance by a fraction of the visible shelf, not tiny Tk units."""
        self.cancel_shelf_momentum()
        total = max(1, self.library_grid.winfo_width())
        viewport = self.library_canvas.winfo_width()
        if total <= viewport:
            return
        left, right = self.library_canvas.xview()
        current = self.shelf_animation_target if self.shelf_animation_target is not None else left
        max_left = max(0.0, 1.0 - viewport / total)
        target = max(0.0, min(max_left, current + direction * viewport * pages / total))
        self.shelf_animation_target = target
        if self.shelf_animation_job is None:
            self.animate_shelf()

    def animate_shelf(self):
        target = self.shelf_animation_target
        if target is None:
            self.shelf_animation_job = None
            return
        current = self.library_canvas.xview()[0]
        delta = target - current
        if abs(delta) < 0.0005:
            self.library_canvas.xview_moveto(target)
            self.shelf_animation_job = None
            self.shelf_animation_target = None
            return
        self.library_canvas.xview_moveto(current + delta * 0.28)
        self.shelf_animation_job = self.root.after(16, self.animate_shelf)

    def on_library_wheel(self, event):
        self.scroll_cartridges(-1 if event.delta > 0 else 1)
        return 'break'

    def cancel_shelf_momentum(self):
        if self.shelf_momentum_job is not None:
            self.root.after_cancel(self.shelf_momentum_job)
            self.shelf_momentum_job = None

    def shelf_press(self, event, rom):
        """Begin a gesture on a cartridge; do not launch until mouse release."""
        self.cancel_shelf_momentum()
        self.cancel_shelf_animation()
        self.shelf_drag = {'start': event.x_root, 'last': event.x_root,
                           'last_time': time.monotonic(), 'distance': 0,
                           'rom': rom, 'velocity': 0.0}

    def shelf_motion(self, event):
        drag = self.shelf_drag
        if drag is None:
            return
        now = time.monotonic()
        dx = event.x_root - drag['last']
        drag['distance'] = max(drag['distance'], abs(event.x_root - drag['start']))
        dt = max(0.008, now - drag['last_time'])
        if drag['distance'] >= 7:
            width = max(1, self.library_grid.winfo_width())
            self.library_canvas.xview_moveto(self.library_canvas.xview()[0] - dx / width)
            drag['velocity'] = max(-32.0, min(32.0, dx / dt / 60.0))
        drag['last'] = event.x_root
        drag['last_time'] = now

    def shelf_release(self, event):
        drag = self.shelf_drag
        if drag is None:
            return
        self.shelf_drag = None
        if drag['distance'] < 7 and abs(event.x_root - drag['start']) < 7:
            # A release outside the shelf must not launch a game.
            left = self.library_canvas.winfo_rootx()
            top = self.library_canvas.winfo_rooty()
            if (left <= event.x_root < left + self.library_canvas.winfo_width()
                    and top <= event.y_root < top + self.library_canvas.winfo_height()):
                self.start_rom(drag['rom'])
        elif time.monotonic() - drag['last_time'] < .12:
            self.shelf_velocity = drag['velocity']
            self.shelf_coast()

    def shelf_coast(self):
        if abs(self.shelf_velocity) < 0.35 or not self.library_strip.winfo_ismapped():
            self.shelf_momentum_job = None
            return
        width = max(1, self.library_grid.winfo_width())
        before = self.library_canvas.xview()[0]
        self.library_canvas.xview_moveto(before - self.shelf_velocity / width)
        if abs(self.library_canvas.xview()[0] - before) < 0.000001:
            self.shelf_momentum_job = None
            return
        self.shelf_velocity *= .88
        self.shelf_momentum_job = self.root.after(16, self.shelf_coast)

    def clear_rom_directory(self):
        """Recover from an oversized or incorrect directory without editing JSON."""
        self.rom_directory = ""
        self.rom_directories[self.system_key.get()] = ""
        self.save_preferences()
        self.populate_inline_library()

    def populate_inline_library(self):
        """Scan on a worker; never block the Tk thread on a large directory."""
        previous = getattr(self, "_rom_scan_cancel", None)
        if previous is not None:
            previous.set()
        generation = getattr(self, "_rom_scan_generation", 0) + 1
        self._rom_scan_generation = generation

        for widget in self.library_grid.winfo_children():
            widget.destroy()
        self.cancel_shelf_momentum()
        self.cancel_shelf_animation()
        self.shelf_drag = None
        self.library_images.clear()

        folder = self.rom_directory
        if not folder or not Path(folder).is_dir():
            self.library_summary.set("ROM LIBRARY · Choose a ROM folder above")
            ttk.Label(
                self.library_grid,
                text="No ROM folder selected. Browse to a dedicated game folder.",
            ).pack(padx=8, pady=40)
            return

        system = self.system_key.get()
        extensions = SYSTEMS[system].extensions
        cancel = Event()
        self._rom_scan_cancel = cancel
        result = Queue(maxsize=1)
        self.library_summary.set(
            "ROM LIBRARY · Scanning in background. Change or clear the folder any time."
        )

        def scan_worker():
            try:
                games = scan_rom_directory(folder, extensions, cancelled=cancel.is_set)
                result.put((games, None))
            except Exception:
                # A bad filesystem adapter, unplugged share, or canceled
                # scanner may fail with more than OSError. Always publish a
                # terminal result, otherwise the Tk timer polls forever.
                # Never copy exception text containing private file paths,
                # user names or device identifiers to the visible shelf.
                result.put(([], "unavailable"))

        Thread(target=scan_worker, daemon=True, name="rom-library-scan").start()
        self.root.after(60, lambda: self._poll_rom_scan(generation, result))

    def _poll_rom_scan(self, generation, result):
        if generation != self._rom_scan_generation or self._closing:
            return
        try:
            games, error = result.get_nowait()
        except Empty:
            self.root.after(90, lambda: self._poll_rom_scan(generation, result))
            return

        if error:
            self.library_summary.set(
                "ROM LIBRARY · Could not scan folder. "
                "Check the folder or drive and refresh."
            )
            return
        if not games:
            self.library_summary.set("ROM LIBRARY · No compatible games found")
            ttk.Label(
                self.library_grid,
                text="No compatible ROMs. Choose a different folder above.",
            ).pack(padx=8, pady=40)
            return

        visible = games[:MAX_VISIBLE_CARTRIDGES]
        if len(games) > len(visible):
            suffix = (
                f" · Showing first {len(visible)}; choose a smaller ROM folder"
            )
        else:
            suffix = ""
        self.library_summary.set(
            f"ROM LIBRARY · {len(games)} game(s){suffix} · Drag or use Previous / Next"
        )
        self._render_rom_batch(visible, 0, generation)

    def _render_rom_batch(self, games, index, generation):
        """Create a small number of thumbnails per UI tick to retain responsiveness."""
        if generation != self._rom_scan_generation or self._closing:
            return
        for rom in games[index:index + CARTRIDGES_PER_BATCH]:
            tile = ttk.Frame(self.library_grid, padding=(5, 0))
            tile.pack(side="left", anchor="n")
            art_path = find_cover_art(rom)
            art = self.cartridge_image(
                rom.stem, self.system_key.get(), art_path
            ).resize((176, 133), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(art)
            self.library_images.append(photo)
            cartridge = tk.Label(
                tile, image=photo,
                bg=self.THEMES.get(self.theme_name.get(), self.THEMES["Dark"])[1],
                cursor="hand2", bd=0, highlightthickness=0,
            )
            cartridge.is_cartridge_tile = True
            cartridge.pack()
            caption = ttk.Label(
                tile, text=rom.stem, width=24, anchor="center", cursor="hand2",
            )
            caption.pack()
            for widget in (cartridge, caption, tile):
                widget.bind(
                    "<ButtonPress-1>", lambda e, p=rom: self.shelf_press(e, p)
                )
        next_index = index + CARTRIDGES_PER_BATCH
        if next_index < len(games):
            self.root.after(
                10, lambda: self._render_rom_batch(games, next_index, generation)
            )
        else:
            self.library_canvas.configure(
                scrollregion=self.library_canvas.bbox("all")
            )
            self.library_canvas.xview_moveto(0)

    def show_library(self):
        self.playing_info.pack_forget()
        self.library_strip.pack(fill='x')

    def show_playing_info(self):
        self.library_strip.pack_forget()
        self.playing_info.pack(fill='x')

    def retry_current_rom(self):
        """Recover a failed/stalled native emulator without restarting the UI."""
        # In the 3.2 preview, the native worker may still remember a ROM
        # after its session was stopped or a missing core was rejected.
        # Only the explicitly selected current game is safe to retry.
        # Preserve the published stable channel's existing fallback.
        path = self.current_rom
        if not path and not getattr(self, "_retry_requires_rom_selection", False):
            from anything_plays.preview_storage import is_v32_preview
            if not is_v32_preview():
                path = getattr(self.emu, "rom", None)
        if not path:
            self.game_status.set("Choose a game ROM before restarting.")
            return
        if getattr(self, "_core_install_busy", False):
            self.game_status.set("Finish emulator updates before restarting.")
            return
        self.start_rom(str(path))

    def unload_rom(self):
        """Retire the native game even when optional input cleanup breaks.

        Unloading must not stop halfway because a dead HID/IPC wrapper or Tk
        status widget threw during teardown. Preserve each independent
        release action and then run the mandatory native stop. A failure of
        the actual native stop is NOT masked or reported as a clean unload.
        """
        prepare = getattr(self, "prepare_gamepad_for_game_transition", None)
        if callable(prepare):
            try:
                prepare()
            except Exception:
                # Even a swapped/broken controller wrapper must not block
                # shutting down the currently running game.
                pass
        try:
            self.stop_external_emulator()
        except Exception:
            # External developer fallback is separate from native Libretro.
            pass
        try:
            self.deactivate_manual()
        except Exception:
            # Directly clear the underlying manual input latch if a custom
            # native facade throws while unloading. The mandatory core stop
            # below also releases its native input resources.
            inputs = getattr(self.emu, "inputs", None)
            release = getattr(inputs, "release_manual", None)
            if callable(release):
                try:
                    release()
                except Exception:
                    pass
        try:
            self.stop_controls()
        except Exception:
            # Camera Stop has its own protected input-buffer release path.
            # Do not let a damaged custom hook block the core's shutdown.
            pass
        # A native callback can remain inside retro_run() after the
        # bounded Stop join. Do not claim "No ROM loaded" or blank the old
        # pixels while that worker still owns them; another Stop/Restart may
        # be attempted once the worker exits. Camera and gamepad are already
        # disarmed above, independently of native shutdown progress.
        if self.emu.stop() is False:
            self.game_status.set(
                "Emulator is still shutting down. Wait before changing games."
            )
            return False
        from anything_plays.game_display_lifecycle import clear_game_video
        clear_game_video(self)
        self.current_rom = None
        self.game_status.set('No ROM loaded')
        self.show_library()
        return True

    def start_rom(self, path):
        # Never open a native core while a verified core-pack transaction is
        # staging or switching its active manifest pointer.
        if getattr(self, "_core_install_busy", False):
            messagebox.showwarning(
                "Emulator updating",
                "Core updates are being installed. Open the ROM after the "
                "update finishes.",
                parent=self.root,
            )
            return
        prior_rom = getattr(self, "current_rom", None)
        prior_core_path = getattr(self.emu, "core_path", None)
        prior_running = (getattr(self.emu, "running", False) is True
                         or getattr(self.emu, "launching", False) is True
                         or native_worker_alive(self.emu))
        # Preflight the new core BEFORE releasing a healthy, currently
        # playing session's controls, camera input or native worker. A
        # requested unavailable console is not permission to disarm the old
        # session, and should not change its ROM or Stream Output.
        if prior_running and self.uses_embedded_emulator():
            from anything_plays.preview_storage import is_v32_preview
            if not is_v32_preview() and not self.emu.find_system_core():
                self.game_status.set(
                    'New emulator unavailable · previous game retained'
                )
                messagebox.showerror(
                    'Emulator unavailable',
                    stable_missing_core_guidance(self.system_key.get()),
                    parent=self.root,
                )
                return
        # An explicit shelf selection may recover from a rejected missing-
        # core launch. Never reuse the old native ROM during the rejected
        # state; users can deliberately choose a new game once repaired.
        self._retry_requires_rom_selection = False
        # Switching directly between ROMs can finish before the next SDL
        # poll; explicitly disarm the outgoing controller snapshot now.
        prepare = getattr(self, "prepare_gamepad_for_game_transition", None)
        if callable(prepare):
            prepare()
        self.deactivate_manual()
        self.stop_controls()
        bezel = getattr(self, "game_bezel", None)
        if bezel is not None:
            try:
                bezel.set_active(False)
            except Exception:
                # A destroyed or customized bezel must never prevent the
                # previous ROM from stopping and the new core from loading.
                pass
        # Save the selected path before starting a background Libretro worker.
        # A failure in retro_init/retro_load_game can then be retried in-place.
        self.current_rom = str(path)
        self._save_warning_until = 0
        try:
            if not self.uses_embedded_emulator():
                if not self.start_external_rom(str(path)):
                    return
            else:
                # All normal gameplay, including accelerated GameCube,
                # stays in the application canvas. External launchers are
                # only an explicitly enabled developer diagnostic.
                self.stop_external_emulator()
                # Resolve the selected core on every game launch. A vetted
                # in-app update or rollback takes effect here without an app
                # restart; an already-loaded native DLL is never replaced.
                selected_core_path = self.emu.find_system_core()
                if not selected_core_path:
                    # Public 3.1.1 contains the full approved console set,
                    # but the 3.2 QA installer intentionally contains only
                    # mGBA. An unbundled preview core is NOT file corruption.
                    # Reject the attempted launch before opening any native
                    # library, and return the user to the game shelf instead
                    # of offering a Restart action that cannot succeed.
                    from anything_plays.preview_storage import is_v32_preview
                    if is_v32_preview():
                        from anything_plays.setup_health import (
                            preview_missing_core_guidance,
                        )
                        title, guidance = preview_missing_core_guidance(
                            self.system_key.get()
                        )
                        # If a previous game was already running, a now-
                        # missing core must also stop its worker and clear
                        # stale video. Use the normal shutdown path so save
                        # state, canvas, and native resources are released.
                        if self.unload_rom() is False:
                            self.current_rom = prior_rom
                            return False
                        self.game_status.set(title)
                        messagebox.showinfo(
                            "3.2 preview emulator availability",
                            guidance,
                            parent=self.root,
                        )
                        return
                    # A missing core is an unrecoverable *launch*, not a
                    # running game. Earlier versions left current_rom set and
                    # could display an old frozen game frame with a Restart
                    # suggestion, even though no native core could start.
                    # Retire the outgoing worker and all GAME-only pixels;
                    # preserve independent Stream Mode camera imagery.
                    guidance = stable_missing_core_guidance(
                        self.system_key.get()
                    )
                    if prior_running:
                        # A missing *new* system must not terminate a real
                        # session already playing. Restore its selection and
                        # core metadata rather than leaving the failed ROM
                        # as the next Restart target.
                        self.current_rom = prior_rom
                        if bezel is not None:
                            try:
                                bezel.set_active(True)
                            except Exception:
                                pass
                        self.game_status.set(
                            'New emulator unavailable · previous game retained'
                        )
                        messagebox.showerror('Emulator unavailable', guidance,
                                             parent=self.root)
                        return
                    if self.unload_rom() is False:
                        self.current_rom = prior_rom
                        return False
                    self._retry_requires_rom_selection = True
                    self.game_status.set(
                        'Emulator files missing · repair or reinstall Anything Plays'
                    )
                    messagebox.showerror('Emulator unavailable', guidance,
                                         parent=self.root)
                    return
                # Existing native sessions must be fully stopped before any
                # framebuffer cleanup. CoreSession.start() already stops an
                # inactive session, so avoid an extra stop on first launch.
                # Keep missing-core preview's own unload/stop path unchanged.
                if prior_running:
                    if self.emu.stop() is False:
                        # Do not switch the core path or use the new ROM for
                        # Restart while the previous worker remains alive.
                        # The stop request has disarmed camera and gamepad,
                        # but the previous session still owns native state.
                        self.current_rom = prior_rom
                        self.game_status.set(
                            "Previous game is still shutting down. "
                            "Try changing games after it finishes."
                        )
                        return False
                # Only clear a prior *rendered* game. On first launch the
                # canvas is already empty, and headless UI hosts may not
                # have an emulator frame lock or stream widgets yet.
                prior_render = any(
                    getattr(self, attr, None) is not None for attr in (
                        "game_photo", "_last_game_render",
                        "_stream_game_frame", "_stream_photo",
                    )
                )
                # Stream Mode also retains an independent PIL source and
                # fitted image for GAME. They can outlive the visible photo
                # refs when the output is blanked or a window is detached.
                # A ROM replacement must clear those pixels before native
                # startup even if no Tk photo is currently displayed. Do
                # not destroy an unrelated, still-live CAMERA resize entry.
                cache = getattr(self, "_stream_resize_cache", None)
                entries = getattr(cache, "_entries", None)
                prior_game_cache = (
                    isinstance(entries, dict) and "GAME" in entries
                )
                if prior_render or prior_game_cache:
                    from anything_plays.game_display_lifecycle import clear_game_video
                    clear_game_video(self)
                self.emu.core_path = selected_core_path
                self.emu.start(str(path))
            self.current_rom = str(path)
            if self.uses_embedded_emulator():
                self.game_status.set('Starting ' + Path(path).stem)
            if bezel is not None:
                try:
                    bezel.set_active(True)
                except Exception:
                    # Decorative failures are independent of a running game.
                    pass
            self.show_playing_info()
        except Exception as exc:
            if bezel is not None:
                try:
                    bezel.set_active(False)
                except Exception:
                    # Report the launch failure, not bezel teardown.
                    pass
            # Core/ROM exceptions often embed full personal paths or a
            # private native device identifier. Do not call str(exc) here
            # (a faulty extension may even raise from __str__).
            detail = safe_launch_failure(exc)
            self.game_status.set(detail)
            self.show_playing_info()
            messagebox.showerror('ROM', detail, parent=self.root)

    def load_rom(self):
        system = SYSTEMS[self.system_key.get()]
        path = filedialog.askopenfilename(filetypes=[(system.title + ' ROMs', ' '.join('*' + ext for ext in system.extensions))])
        if not path:
            return
        self.start_rom(path)
