"""Anything Plays: cross-platform, camera-controlled retro gaming studio.

``App`` owns the Tk root and coordinates focused UI modules. The modules are
mixins so callbacks can still share the historical Tk state without rebuilding
the layout or migrating a user's settings. No OS-level keyboard injection occurs.
"""

import copy
import os
import sys
import tkinter as tk

from anything_plays.gba_emulator import Emulator
from anything_plays.systems import SYSTEMS
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
from anything_plays.ui_icon import IconMixin


class App(ThemeMixin, LayoutMixin, AuxiliaryPanelsMixin, CameraMixin, GameplayMixin,
          ProfilesMixin, LibraryMixin, ZonesMixin, ViewMixin,
          ShortcutsMixin, ExternalBackendMixin, UpdatesMixin, IconMixin):
    """Own application state and delegate UI behavior to focused modules."""

    def __init__(self, root):
        self.root = root
        root.title('Anything Plays 3.0 · Preview')
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
        self._selected_emulator_status = tk.StringVar(value='')
        self._core_install_busy = False
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
        # Players need a single self-contained game window. External
        # launchers remain an opt-in diagnostic for developers only.
        self.external_fallback_enabled = (
            os.environ.get("AP_V21_DEVELOPER_EXTERNAL", "") == "1"
        )
        self.n64_embedded = tk.BooleanVar(value=(
            preferences.get("n64_embedded", True) is True
            if self.external_fallback_enabled else True
        ))
        self.gamecube_embedded = tk.BooleanVar(value=(
            preferences.get("gamecube_embedded", True) is True
            if self.external_fallback_enabled else True
        ))
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
        self.color2_text = tk.StringVar()
        self.color2_enabled = tk.BooleanVar(value=False)
        self.color2_player = tk.StringVar(value="Player 2")
        self.multi_fish_enabled = tk.BooleanVar(value=True)
        self.camera_input_mode = tk.StringVar(value="Held while visible")
        self._last_camera_pulses = {}
        # Saved independently from every ROM, with safe defaults on invalid
        # or older preferences. Do not modify the OS master volume.
        saved_volume = preferences.get("volume", 35)
        if (type(saved_volume) not in (int, float)
                or not 0 <= saved_volume <= 100):
            saved_volume = 35
        self.volume_percent = tk.IntVar(value=int(saved_volume))
        self.volume_label = tk.StringVar(value=f"{int(saved_volume)}%")
        self._volume_before_mute = max(1, int(saved_volume))
        self.emu.set_volume(int(saved_volume) / 100.0)
        self.mapping_vars = {}
        self.zone_font_size = tk.IntVar(value=44)
        self.zone_opacity = tk.IntVar(value=85)
        self.zone_style = tk.StringVar(value='Bold')
        self.zone_border_width = tk.IntVar(value=6)
        self.zone_label_position = tk.StringVar(value='Center')
        self.shuffle_enabled = tk.BooleanVar(value=True)
        self.zone_image_path = tk.StringVar(value='')
        self._zone_art = None
        self._zone_thumbnail_cache = {}  # Bounded to 12 resized assets.
        self.cfg = self.profile_store.get(self.system_key.get())
        self.build()
        self.refresh_settings()
        self.refresh_system_buttons()
        self.update_external_setup()
        self.refresh_selected_emulator_state()
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
        # Keep exactly one camera timer and one game timer alive. Record their
        # identifiers so all pending callbacks can be cancelled on shutdown.
        self._camera_tick_job = root.after(45, self.tick)
        self._game_tick_job = root.after(16, self.game_render_tick)
        self._updates_start_job = root.after(
            8000, self.schedule_emulator_update_checks
        )

    def uses_embedded_emulator(self, system=None):
        """Choose in-panel video for each console; keep GPU fallback explicit."""
        key = self.system_key.get() if system is None else system
        if key in SYSTEMS and key not in ('n64', 'gamecube'):
            return True
        if key == 'n64':
            return self.n64_embedded.get()
        if key == 'gamecube':
            return self.gamecube_embedded.get()
        return False

    def close(self):
        """Persist settings, release devices, and stop scheduling UI callbacks."""
        if self._closing:
            return
        self._closing = True
        # Stopping a camera manually or closing the app always cancels retries.
        self.cancel_camera_reconnect()
        # A long-lived window may have several pending after() callbacks.
        # Cancel the periodic loops before destroying Tk widgets.
        for job_name in ("_camera_tick_job", "_game_tick_job",
                         "_updates_start_job", "_updates_repeat_job"):
            job = getattr(self, job_name, None)
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, job_name, None)
        pending_rom_scan = getattr(self, "_rom_scan_cancel", None)
        if pending_rom_scan is not None:
            pending_rom_scan.set()
        try:
            self.persist_system_profile()
        except (OSError, ValueError, tk.TclError):
            pass
        # Cleanup each driver separately: a USB camera can fail while
        # releasing without blocking native emulators or Tk shutdown.
        def cleanup(label, callback):
            try:
                callback()
            except Exception as exc:
                print(f"Shutdown {label}: {exc}", file=sys.stderr)

        for job_name in ('shelf_button_job', 'shelf_animation_job',
                         'shelf_momentum_job'):
            job = getattr(self, job_name, None)
            if job is not None:
                cleanup(job_name, lambda job=job: self.root.after_cancel(job))

        cleanup("manual input", self.deactivate_manual)
        cleanup("camera controls", self.stop_controls)
        capture, self.cap = self.cap, None
        if capture is not None:
            cleanup("camera", capture.release)
        cleanup("embedded emulator", self.emu.stop)
        cleanup("external emulator", self.stop_external_emulator)
        try:
            with self.emu.lock:
                self.emu.frame = None
            self.frame = None
            self.game_photo = None
            self.camera_photo = None
            self._zone_art = None
            self._zone_thumbnail_cache.clear()
            self.library_images.clear()
        finally:
            try:
                self.root.destroy()
            except tk.TclError:
                pass

def main():
    """Start the Tkinter event loop when launched from source or a bundle."""
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
