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


MAX_VISIBLE_CARTRIDGES = 300
CARTRIDGES_PER_BATCH = 12


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
            except OSError as exc:
                result.put(([], str(exc)))

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
            self.library_summary.set(f"ROM LIBRARY · Could not scan folder: {error}")
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

    def unload_rom(self):
        self.stop_external_emulator()
        self.deactivate_manual()
        self.stop_controls()
        self.emu.stop()
        with self.emu.lock:
            self.emu.frame = None
        self.current_rom = None
        self.game_photo = None
        self.game_canvas.delete('all')
        self.game_status.set('No ROM loaded')
        self.show_library()

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
        self.deactivate_manual()
        self.stop_controls()
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
                self.emu.core_path = self.emu.find_system_core()
                if not self.emu.core_path:
                    if self.system_key.get() == 'gamecube':
                        raise RuntimeError(
                            'The installed GameCube emulator or its required '
                            'Dolphin system files are missing. The complete '
                            'Anything Plays 3.0 installer includes both. '
                            'Repair or reinstall the application. No separate '
                            'Dolphin or emulator download is required.'
                        )
                    raise RuntimeError(
                        'A bundled emulator core is missing or damaged. '
                        'Repair or reinstall Anything Plays 3.0; every console '
                        'is included and must work offline.'
                    )
                self.emu.start(str(path))
            self.current_rom = str(path)
            if self.uses_embedded_emulator():
                self.game_status.set('Starting ' + Path(path).stem)
            self.show_playing_info()
        except Exception as exc:
            messagebox.showerror('ROM', f'Could not start game: {exc}')

    def load_rom(self):
        system = SYSTEMS[self.system_key.get()]
        path = filedialog.askopenfilename(filetypes=[(system.title + ' ROMs', ' '.join('*' + ext for ext in system.extensions))])
        if not path:
            return
        self.start_rom(path)
