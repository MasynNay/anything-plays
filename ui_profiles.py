"""Read, validate, migrate and save per-console settings and input mappings."""

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from settings_defaults import DEFAULT
from system_profiles import (BUTTONS_BY_SYSTEM, DISABLED_MAPPING,
                             default_for, normalize)
from systems import DEFAULT_SYSTEM, SYSTEMS


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
        if core_path:
            paths = prefs.get('core_paths', {})
            paths = paths if isinstance(paths, dict) else {}
            paths[self.system_key.get()] = core_path
            prefs['core_paths'] = paths
        try:
            self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
            self.preferences_path.write_text(json.dumps(prefs, indent=2), encoding='utf-8')
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
                combo.grid()
                combo.configure(values=[DISABLED_MAPPING, *names])
            else:
                label.grid_remove()
                combo.grid_remove()

    def persist_system_profile(self):
        self.read_settings()
        self.profile_store.put(self.system_key.get(), self.cfg)

    def switch_system(self, event=None):
        key = self.system_key.get()
        if key not in SYSTEMS:
            return
        self.stop_controls()
        # The combobox has already changed, so save the previous system explicitly.
        previous = getattr(self, '_active_profile_system', DEFAULT_SYSTEM)
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
        self.emu.system = key
        self.emu.core_path = self.emu.find_system_core()
        self.rom_directory = self.rom_directories.get(key, '')
        self.system_description.configure(text=SYSTEMS[key].title)
        self.current_rom = None
        self.game_canvas.delete('all')
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
        for name, var in self.mapping_vars.items():
            var.set(self.cfg.get('mapping', {}).get(name, name))
        self.zone_font_size.set(max(8, min(160, self.cfg.get('zone_font_size', 44))))
        self.zone_opacity.set(max(75, min(100, self.cfg.get('zone_opacity', 85))))
        self.zone_style.set(self.cfg.get('zone_style', 'Outline'))
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
        self.cfg['zone_font_size'] = max(8, min(160, int(self.zone_font_size.get())))
        self.cfg['zone_opacity'] = max(75, min(100, int(self.zone_opacity.get())))
        self.cfg['zone_style'] = self.zone_style.get()
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
