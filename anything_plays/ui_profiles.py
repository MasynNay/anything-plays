"""Read, validate, migrate and save per-console settings and input mappings."""

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from anything_plays.atomic_storage import write_json_atomically
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import (BUTTONS_BY_SYSTEM, DISABLED_MAPPING,
                             default_for, normalize)
from anything_plays.systems import DEFAULT_SYSTEM, SYSTEMS


class ProfilesMixin:
    """Tkinter behavior shared with the main application controller.

    These methods use widgets and state initialized by ``App.__init__``
    and ``LayoutMixin.build``. They are not standalone widgets.
    """

    def read_preferences(self):
        try:
            data = json.loads(self.preferences_path.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def read_selected_system(self):
        key = self.read_preferences().get('system', DEFAULT_SYSTEM)
        return key if key in SYSTEMS else DEFAULT_SYSTEM

    def read_rom_directories(self):
        prefs = self.read_preferences()
        directories = prefs.get('rom_directories', {})
        directories = directories if isinstance(directories, dict) else {}
        directories.setdefault('gba', str(prefs.get('rom_directory', '')))
        return {key: str(value) for key, value in directories.items() if key in SYSTEMS and isinstance(value, str)}

    def read_core_paths(self):
        paths = self.read_preferences().get('core_paths', {})
        return paths if isinstance(paths, dict) else {}

    def save_preferences(self, core_path=None):
        prefs = self.read_preferences()
        prefs['theme'] = self.theme_name.get()
        prefs['system'] = self.system_key.get()
        prefs['rom_directories'] = dict(self.rom_directories)
        prefs['rom_directory'] = self.rom_directories.get('gba', '')  # legacy compatibility
        prefs['key_bindings'] = dict(self._shortcut_bindings)
        prefs['gamepad_enabled'] = bool(self.gamepad_enabled.get())
        prefs['gamepad_bindings'] = dict(self._gamepad_bindings)
        prefs['external_emulators'] = dict(self.external_emulators)
        prefs['n64_core_path'] = self.n64_core_override
        prefs['n64_embedded'] = bool(self.n64_embedded.get())
        prefs['gamecube_embedded'] = bool(self.gamecube_embedded.get())
        prefs['gamecube_preview_mode'] = self.gamecube_preview_mode.get()
        prefs['view_mode'] = self.view_mode.get()
        # Stream composition is independent of the regular camera/game
        # display theme. Save only sanitized, simple style preferences.
        if hasattr(self, "_stream_options"):
            from anything_plays.ui_stream import validate_stream_settings
            prefs['stream_mode'] = validate_stream_settings(
                self._stream_options, self.THEMES, self.theme_name.get(),
            )
        prefs['volume'] = max(0, min(100, int(self.volume_percent.get())))
        prefs['last_nonzero_volume'] = max(
            1, min(100, int(self._volume_before_mute))
        )
        if core_path:
            paths = prefs.get('core_paths', {})
            paths = paths if isinstance(paths, dict) else {}
            paths[self.system_key.get()] = core_path
            prefs['core_paths'] = paths
        try:
            write_json_atomically(self.preferences_path, prefs)
        except OSError as exc:
            messagebox.showwarning('Preferences', f'Could not save preferences: {exc}')

    def update_button_mapping(self, name):
        self.cfg.setdefault('mapping', {})[name] = self.mapping_vars[name].get()
        self.profile_store.put(self.system_key.get(), self.cfg)
        self.status.set(f'{name} mapping updated. Use Fit buttons to grid to rearrange enabled zones.')

    def refresh_system_buttons(self):
        names = BUTTONS_BY_SYSTEM[self.system_key.get()]
        self.zone_combo.configure(values=[*names, 'Shuffle'])
        if self.zone_name.get() not in (*names, 'Shuffle'):
            self.zone_name.set(names[0])
        for name, (label, combo) in self.mapping_widgets.items():
            if name in names:
                label.grid()
                if combo.winfo_manager() == 'grid':
                    combo.grid()
                combo.configure(values=[DISABLED_MAPPING, *names])
            else:
                label.grid_remove()
                if combo.winfo_manager() == 'grid':
                    combo.grid_remove()

    def persist_system_profile(self):
        self.read_settings()
        self.profile_store.put(self.system_key.get(), self.cfg)

    def switch_system(self, event=None):
        # Finish calibration on its original console before persisting
        # the old profile; a changed combobox already contains the new key.
        close_calibration = getattr(self, 'close_camera_calibration', None)
        if callable(close_calibration):
            close_calibration(restore=True)
        key = self.system_key.get()
        if key not in SYSTEMS:
            return
        self.stop_controls()
        # External games have their own window. Close any blank game-only overlay.
        if not self.uses_embedded_emulator(key) and self.view_mode.get() == "Game only":
            self.set_view_mode("Windowed")
        # The combobox has already changed, so save the previous system explicitly.
        previous = getattr(self, '_active_profile_system', DEFAULT_SYSTEM)
        # Flush any pending size change against the previous console before
        # switching profiles; the combobox already contains the new key.
        pending = getattr(self, '_zone_label_save_job', None)
        if pending is not None:
            self.root.after_cancel(pending)
            self._zone_label_save_job = None
        try:
            self.read_settings()
            self.profile_store.put(previous, self.cfg)
        except (ValueError, tk.TclError, OSError):
            pass
        self.cfg = self.profile_store.get(key)
        self.refresh_settings()
        self.refresh_system_buttons()
        self._active_profile_system = key
        self.emu.stop()
        self.stop_external_emulator()
        self.emu.system = key
        self.emu.core_path = self.emu.find_system_core()
        self.rom_directory = self.rom_directories.get(key, '')
        self.system_description.configure(text=SYSTEMS[key].title)
        self.update_external_setup()
        self.refresh_selected_emulator_state()
        self.current_rom = None
        self.game_canvas.delete('all')
        self.show_external_placeholder()
        self.game_status.set('Load your own ' + SYSTEMS[key].title + ' ROM')
        self.show_library()
        self.populate_inline_library()
        self.save_preferences()

    def refresh_settings(self):
        """Update every Tk variable from one validated, per-console profile."""
        self.cfg = normalize(self.system_key.get(), self.cfg, DEFAULT)
        self.tolerance.set(self.cfg['tolerance'])
        self.min_area.set(self.cfg['min_area'])
        self.hold_frames.set(self.cfg['hold_frames'])
        self.cooldown.set(self.cfg['cooldown_ms'])
        self.mirror.set(self.cfg['mirror'])
        self.color2_enabled.set(self.cfg.get('color2_enabled', False))
        self.color2_player.set(self.cfg.get('color2_player', 'Player 2'))
        self.multi_fish_enabled.set(self.cfg.get('multi_fish_enabled', False))
        self.camera_input_mode.set(
            self.cfg.get('camera_input_mode', 'Held while visible')
        )
        self._last_camera_pulses.clear()
        for name, var in self.mapping_vars.items():
            var.set(self.cfg.get('mapping', {}).get(name, name))
        self.zone_font_size.set(max(8, min(160, self.cfg.get('zone_font_size', 44))))
        self.zone_opacity.set(max(75, min(100, self.cfg.get('zone_opacity', 85))))
        self.zone_style.set(self.cfg.get('zone_style', 'Bold'))
        self.zone_border_width.set(max(2, min(16, int(self.cfg.get('zone_border_width', 6)))))
        self.zone_label_position.set(self.cfg.get('zone_label_position', 'Center'))
        self.shuffle_enabled.set(self.cfg.get('shuffle_enabled', True))
        self.zone_image_path.set(self.cfg.get('zone_image', ''))
        self.load_zone_art(silent=True)
        self.refresh_color()

    def read_settings(self):
        self.cfg['tolerance'] = max(1, min(90, int(self.tolerance.get())))
        self.cfg['min_area'] = max(5, int(self.min_area.get()))
        self.cfg['hold_frames'] = max(1, min(60, int(self.hold_frames.get())))
        self.cfg['cooldown_ms'] = max(50, int(self.cooldown.get()))
        self.cfg['mirror'] = self.mirror.get()
        self.cfg['color2_enabled'] = bool(self.color2_enabled.get())
        self.cfg['color2_player'] = (
            self.color2_player.get() if self.color2_player.get()
            in ('Player 1', 'Player 2') else 'Player 2'
        )
        self.cfg['multi_fish_enabled'] = bool(self.multi_fish_enabled.get())
        self.cfg['camera_input_mode'] = (
            self.camera_input_mode.get() if self.camera_input_mode.get()
            in ('Held while visible', 'Pulse (classic)')
            else 'Held while visible'
        )
        self.cfg['zone_font_size'] = max(8, min(160, int(self.zone_font_size.get())))
        self.cfg['zone_opacity'] = max(75, min(100, int(self.zone_opacity.get())))
        self.cfg['zone_style'] = self.zone_style.get()
        self.cfg['zone_border_width'] = max(2, min(16, int(self.zone_border_width.get())))
        self.cfg['zone_label_position'] = self.zone_label_position.get()
        self.cfg['shuffle_enabled'] = bool(self.shuffle_enabled.get())
        self.cfg['zone_image'] = self.zone_image_path.get()
        self.cfg['mapping'] = {name: var.get() for name, var in self.mapping_vars.items()}

    def save_profile(self):
        try:
            self.read_settings()
        except Exception:
            messagebox.showerror('Profile', 'Correct the settings first.')
            return
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON profile', '*.json')])
        if path:
            Path(path).write_text(json.dumps(self.cfg, indent=2), encoding='utf-8')
            self.profile_store.put(self.system_key.get(), self.cfg)

    def load_profile(self):
        path = filedialog.askopenfilename(filetypes=[('JSON profile', '*.json')])
        if not path:
            return
        try:
            cfg = json.loads(Path(path).read_text(encoding='utf-8'))
            if not isinstance(cfg, dict) or not isinstance(cfg.get('zones'), dict):
                raise ValueError('Invalid profile: missing zones')
            self.stop_controls()
            self.cfg = normalize(self.system_key.get(), cfg, DEFAULT)
            self.profile_store.put(self.system_key.get(), self.cfg)
            self.refresh_settings()
        except Exception as exc:
            messagebox.showerror('Profile', str(exc))

    def reset_profile(self):
        self.stop_controls()
        self.cfg = default_for(self.system_key.get(), DEFAULT)
        self.refresh_settings()
        self.profile_store.put(self.system_key.get(), self.cfg)
