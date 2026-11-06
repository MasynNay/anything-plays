"""Anything Plays: cross-platform, camera-controlled retro gaming studio.

``App`` owns the Tk root and coordinates focused UI modules. The modules are
mixins so callbacks can still share the historical Tk state without rebuilding
the layout or migrating a user's settings. No OS-level keyboard injection occurs.
"""

import copy
from pathlib import Path
import sys
import tkinter as tk

from anything_plays.gba_emulator import Emulator
from anything_plays.settings_defaults import DEFAULT
from anything_plays.test_preferences import prepare_test_preferences
from anything_plays.system_profiles import ProfileStore
from anything_plays.ui_camera import CameraMixin
from anything_plays.ui_gameplay import GameplayMixin
from anything_plays.ui_layout import LayoutMixin
from anything_plays.ui_panels import AuxiliaryPanelsMixin
from anything_plays.ui_library import LibraryMixin
from anything_plays.ui_profiles import ProfilesMixin
from anything_plays.ui_theme import ThemeMixin
from anything_plays.ui_zones import ZonesMixin
from anything_plays.ui_view import ViewMixin
from anything_plays.ui_shortcuts import ShortcutsMixin
from anything_plays.ui_external import ExternalBackendMixin
from anything_plays.ui_updates import UpdatesMixin


class App(ThemeMixin, LayoutMixin, AuxiliaryPanelsMixin, CameraMixin, GameplayMixin,
          ProfilesMixin, LibraryMixin, ZonesMixin, ViewMixin,
          ShortcutsMixin, ExternalBackendMixin, UpdatesMixin):
    """Own application state and delegate UI behavior to focused modules."""

    def __init__(self, root):
        self.root = root
        root.title('Anything Plays 2.1 · Testing')
        self.set_app_icon()
        root.geometry('1400x880')
        root.minsize(820, 540)
        self.cfg = copy.deepcopy(DEFAULT)
        self.cap = None
        self.frame = None
        self.reference_image = False
        self.camera_options = {}
        self.camera_scanning = False
        self.pick_mode = False
        self.drag_start = None
        self.custom_draw_enabled = tk.BooleanVar(value=False)
        self.camera_photo = None
        self.game_photo = None
        self.manual_active = False
        self.last_action = 0
        self._shuffle_latched = False
        self.armed = False
        self._closing = False
        self._updates_busy = False
        self._emulator_update_status = tk.StringVar(
            value='Emulator update checks run automatically every 24 hours'
        )
        self.emu = Emulator()
        # Preserve stable 2.0 preferences; make an independent alpha copy.
        self.preferences_path = prepare_test_preferences()
        self.profile_store = ProfileStore(self.preferences_path.with_name('system_profiles.json'), DEFAULT)
        preferences = self.read_preferences()
        self._shortcut_bindings = preferences.get('key_bindings', {})
        if not isinstance(self._shortcut_bindings, dict):
            self._shortcut_bindings = {}
        self.external_emulators = preferences.get('external_emulators', {})
        if not isinstance(self.external_emulators, dict):
            self.external_emulators = {}
        self.n64_core_override = preferences.get('n64_core_path', '')
        if not isinstance(self.n64_core_override, str):
            self.n64_core_override = ''
        self.external_process = None
        self.external_input = None  # Local camera/keyboard bridge for N64
        self._game_only_window = None
        self._game_only_canvas = None
        self._shortcut_window = None
        self._windowed_geometry = root.geometry()
        self._current_view_mode = 'Windowed'
        self._view_transition = False
        saved_view_mode = preferences.get('view_mode', 'Windowed')
        self.view_mode = tk.StringVar(value=saved_view_mode if saved_view_mode in ('Windowed', 'Borderless', 'Fullscreen') else 'Windowed')
        self.theme_name = tk.StringVar(value=self.read_theme_preference())
        self.apply_theme(self.theme_name.get())
        self.system_key = tk.StringVar(value=self.read_selected_system())
        self.rom_directories = self.read_rom_directories()
        self.rom_directory = self.rom_directories.get(self.system_key.get(), '')
        self.emu.system = self.system_key.get()
        self.emu.core_path = self.emu.find_system_core()
        self.shelf_drag = None
        self.shelf_momentum_job = None
        self.shelf_velocity = 0.0
        self.shelf_button_job = None
        self.shelf_button_direction = 0
        self.shelf_animation_job = None
        self.shelf_animation_target = None
        self.library_images = []
        self.current_rom = None
        self.status = tk.StringVar(value='Searching for cameras…')
        self.action = tk.StringVar(value='PREVIEW ONLY — no keyboard events are sent')
        self.game_status = tk.StringVar(value='Load your own game ROM')
        self.camera_name = tk.StringVar()
        self.zone_name = tk.StringVar(value='Up')
        self.color_text = tk.StringVar()
        self.mapping_vars = {}
        self.zone_font_size = tk.IntVar(value=44)
        self.zone_opacity = tk.IntVar(value=85)
        self.zone_style = tk.StringVar(value='Bold')
        self.zone_border_width = tk.IntVar(value=6)
        self.zone_label_position = tk.StringVar(value='Center')
        self.shuffle_enabled = tk.BooleanVar(value=True)
        self.zone_image_path = tk.StringVar(value='')
        self._zone_art = None
        self.cfg = self.profile_store.get(self.system_key.get())
        self.build()
        self.refresh_settings()
        self.refresh_system_buttons()
        self.update_external_setup()
        self.show_external_placeholder()
        self._active_profile_system = self.system_key.get()
        if self.view_mode.get() != 'Windowed':
            self.set_view_mode(self.view_mode.get(), persist=False)
        root.bind('<Control-Alt-F11>', lambda _: self.toggle())
        root.bind('<Control-Alt-F12>', lambda _: self.stop_controls())
        root.bind('<Escape>', self.exit_view_or_stop)
        root.bind('<F10>', self.toggle_borderless)
        root.bind('<F11>', self.toggle_fullscreen)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.scan_cameras)
        root.after(45, self.tick)
        root.after(8000, lambda: self.check_emulator_updates(automatic=True))

    def set_app_icon(self):
        """Use the same branded icon for source and frozen applications."""
        base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        icon = base / 'assets' / 'anything_plays.png'
        if icon.is_file():
            try:
                self._app_icon = tk.PhotoImage(file=str(icon))
                self.root.iconphoto(True, self._app_icon)
            except tk.TclError:
                pass

    def close(self):
        """Persist settings, release devices, and stop scheduling UI callbacks."""
        if self._closing:
            return
        self._closing = True
        pending_rom_scan = getattr(self, "_rom_scan_cancel", None)
        if pending_rom_scan is not None:
            pending_rom_scan.set()
        try:
            self.persist_system_profile()
        except (OSError, ValueError, tk.TclError):
            pass
        self.deactivate_manual()
        self.stop_controls()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        for job_name in ('shelf_button_job', 'shelf_animation_job',
                         'shelf_momentum_job'):
            job = getattr(self, job_name, None)
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
        self.emu.stop()
        self.stop_external_emulator()
        self.root.destroy()


def main():
    """Start the Tkinter event loop when launched from source or a bundle."""
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
