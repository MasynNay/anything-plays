"""Read, validate, migrate and save per-console settings and input mappings."""

import copy
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from anything_plays.atomic_storage import write_json_atomically
from anything_plays.portable_profiles import load_bundle, save_bundle
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
        # The combobox already contains the new value when this callback runs.
        # A failed profile write must restore both the selected row and the
        # in-progress config; never tell the player a mapping was saved.
        system = self.system_key.get()
        previous = self.cfg.get('mapping', {}).get(name, name)
        chosen = self.mapping_vars[name].get()
        self.cfg.setdefault('mapping', {})[name] = chosen
        try:
            self.profile_store.put(system, self.cfg)
        except (OSError, ValueError, TypeError):
            self.cfg['mapping'][name] = previous
            self.mapping_vars[name].set(previous)
            self.status.set(
                'Button mapping was not saved. Check profile storage and retry.'
            )
            return False
        self.status.set(
            f'{name} mapping updated. Use Fit buttons to grid to rearrange enabled zones.'
        )
        return True

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

    def persist_on_exit(self):
        """Rollback an unfinished calibration before saving on shutdown.

        A guide may have sampled a color or changed advanced controls, but
        those are not committed unless the user explicitly chose Save.
        """
        if getattr(self, '_calibration_window', None) is not None:
            self.close_camera_calibration(restore=True)
        self.persist_system_profile()

    def switch_system(self, event=None):
        calibration_was_open = getattr(self, '_calibration_window', None) is not None
        close_guide = getattr(self, 'close_camera_calibration', None)
        if callable(close_guide):
            close_guide(restore=True)
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
            if not calibration_was_open:
                self.read_settings(previous)
            self.profile_store.put(previous, self.cfg)
        except (ValueError, tk.TclError, OSError):
            pass
        self.cfg = self.profile_store.get(key)
        self.refresh_settings()
        self.refresh_system_buttons()
        self._active_profile_system = key
        self.deactivate_manual()
        self.emu.stop()
        self.stop_external_emulator()
        from anything_plays.game_display_lifecycle import clear_game_video
        clear_game_video(self)
        self.emu.system = key
        self.emu.core_path = self.emu.find_system_core()
        self.rom_directory = self.rom_directories.get(key, '')
        self.system_description.configure(text=SYSTEMS[key].title)
        self.update_external_setup()
        self.refresh_selected_emulator_state()
        self.current_rom = None
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

    def read_settings(self, system=None):
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
        # The UI has fields for all console families; a portable profile
        # must contain mappings for the selected console only.
        # The combobox may already show the NEXT console during a switch.
        # Persist the old console's visible mappings under its own identity.
        selected = system if system in BUTTONS_BY_SYSTEM else self.system_key.get()
        allowed = BUTTONS_BY_SYSTEM[selected]
        self.cfg['mapping'] = {
            name: self.mapping_vars[name].get() for name in allowed
        }

    def save_profile(self):
        """Export only portable control settings, never paths or ROM metadata."""
        try:
            self.read_settings()
            # Validate before displaying the save picker, so malformed
            # in-progress spinbox values cannot produce an invalid file.
            from anything_plays.portable_profiles import make_bundle
            make_bundle(
                self.system_key.get(), self.cfg,
                theme=self.theme_name.get(), allowed_themes=self.THEMES,
            )
        except (ValueError, TypeError, tk.TclError) as exc:
            messagebox.showerror(
                'Export controls', f'Correct the settings first: {exc}',
                parent=self.root,
            )
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension='.json',
            filetypes=[('Anything Plays control profile', '*.json')],
            initialfile=f'anything-plays-{self.system_key.get()}-controls.json',
        )
        if not path:
            return
        try:
            save_bundle(
                path, self.system_key.get(), self.cfg,
                theme=self.theme_name.get(), allowed_themes=self.THEMES,
            )
            self.profile_store.put(self.system_key.get(), self.cfg)
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror(
                'Export controls', f'Could not export controls: {exc}',
                parent=self.root,
            )
            return
        self.status.set(
            'Control profile exported. ROMs, personal paths, saves and '
            'camera footage were not included.'
        )

    def export_all_profiles(self):
        """Back up all 18 camera-control layouts, excluding private settings."""
        if getattr(self, "_calibration_window", None) is not None:
            messagebox.showinfo(
                "Back up all controls",
                "Finish or cancel camera calibration before backing up controls.",
                parent=self.root,
            )
            return
        from anything_plays.portable_profile_library import (
            make_library_archive, save_library_archive,
        )
        try:
            self.read_settings()
            profiles = {
                system: self.profile_store.get(system)
                for system in BUTTONS_BY_SYSTEM
            }
            profiles[self.system_key.get()] = copy.deepcopy(self.cfg)
            make_library_archive(profiles)  # validate before opening a picker
        except (ValueError, TypeError, tk.TclError) as exc:
            messagebox.showerror(
                "Back up all controls", f"Cannot export these layouts: {exc}",
                parent=self.root,
            )
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, defaultextension=".json",
            filetypes=[("Anything Plays all-console backup", "*.json")],
            initialfile="anything-plays-all-18-console-controls.json",
        )
        if not path:
            return
        try:
            save_library_archive(path, profiles)
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror(
                "Back up all controls", f"Could not save the backup: {exc}",
                parent=self.root,
            )
            return
        self.status.set(
            "All console control layouts backed up. No ROMs, saves, "
            "camera images, device names or private file paths included."
        )

    def restore_all_profiles(self):
        """Confirm one validated all-console backup and apply it atomically."""
        if getattr(self, "_calibration_window", None) is not None:
            messagebox.showinfo(
                "Restore all controls",
                "Finish or cancel camera calibration before restoring controls.",
                parent=self.root,
            )
            return
        from anything_plays.portable_profile_library import load_library_archive
        path = filedialog.askopenfilename(
            parent=self.root,
            filetypes=[("Anything Plays all-console backup", "*.json")],
        )
        if not path:
            return
        try:
            imported = load_library_archive(path)
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror(
                "Restore all controls", f"Could not validate this backup: {exc}",
                parent=self.root,
            )
            return
        from anything_plays.portable_profile_library import changed_systems
        try:
            self.read_settings()
            selected = self.system_key.get()
            prior = {
                system: self.profile_store.get(system)
                for system in BUTTONS_BY_SYSTEM
            }
            prior[selected] = copy.deepcopy(self.cfg)
            differences = changed_systems(prior, imported)
        except (ValueError, TypeError, tk.TclError) as exc:
            messagebox.showerror(
                "Restore all controls", f"Cannot compare current settings: {exc}",
                parent=self.root,
            )
            return
        if not differences:
            self.status.set(
                "This backup already matches all 18 console controls. "
                "No changes were made."
            )
            return

        # Show only built-in console titles, not file paths or profile values.
        preview = ", ".join(SYSTEMS[key].title for key in differences[:7])
        remaining = len(differences) - 7
        if remaining:
            preview += f" (+{remaining} more)"
        if not messagebox.askyesno(
            "Review all-console restore",
            f"Change controls for {len(differences)} of {len(imported)} "
            f"consoles:\n{preview}\n\n"
            "Camera-controlled gameplay will be stopped. ROMs, native saves, "
            "controller mappings and other preferences are not changed.\n\n"
            "You can undo the restore afterward. Apply these changes?",
            parent=self.root,
        ):
            return
        self.stop_controls()
        try:
            self.profile_store.put_many(imported)
            self.cfg = self.profile_store.get(selected)
            self.refresh_settings()
        except (OSError, ValueError, TypeError, tk.TclError) as exc:
            try:
                self.profile_store.put_many(prior)
                self.cfg = self.profile_store.get(selected)
                self.refresh_settings()
            except (OSError, ValueError, TypeError, tk.TclError):
                self.status.set(
                    "Restore failed. Check your control profiles before playing."
                )
            messagebox.showerror(
                "Restore all controls",
                f"Restore was not completed: {exc}", parent=self.root,
            )
            return
        self._last_profile_archive_import = prior
        undo = getattr(self, "_undo_all_profile_restore_button", None)
        if undo is not None:
            undo.configure(state="normal")
        # Any older one-console undo snapshot no longer reflects this state.
        self._last_profile_import = None
        single_undo = getattr(self, "_undo_import_button", None)
        if single_undo is not None:
            single_undo.configure(state="disabled")
        self.status.set(
            "All console controls restored. Object input remains paused. "
            "Use Undo all restore to return to the previous layouts."
        )

    def undo_all_profile_restore(self):
        """Restore the entire pre-import set in one atomic write."""
        prior = getattr(self, "_last_profile_archive_import", None)
        if prior is None:
            return
        self.stop_controls()
        try:
            self.profile_store.put_many(prior)
            self.cfg = self.profile_store.get(self.system_key.get())
            self.refresh_settings()
        except (OSError, ValueError, TypeError, tk.TclError) as exc:
            messagebox.showerror(
                "Undo all restore", f"Could not undo control restore: {exc}",
                parent=self.root,
            )
            return
        self._last_profile_archive_import = None
        undo = getattr(self, "_undo_all_profile_restore_button", None)
        if undo is not None:
            undo.configure(state="disabled")
        self.status.set(
            "Previous control layouts restored for all consoles. "
            "Object input remains paused."
        )

    def load_profile(self):
        """Preview and confirm safe settings; preserve an undo snapshot."""
        path = filedialog.askopenfilename(
            parent=self.root,
            filetypes=[('Anything Plays control profile', '*.json')],
        )
        if not path:
            return
        system = self.system_key.get()
        try:
            imported, theme, legacy = load_bundle(
                path, selected_system=system, allowed_themes=self.THEMES,
            )
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror(
                'Import controls', f'Could not read this profile: {exc}',
                parent=self.root,
            )
            return
        description = (
            f'Console: {system.upper()}\n'
            f'Button zones: {len(imported["zones"])}\n'
            f'Mapped controls: {len(imported["mapping"])}\n'
            f'Appearance theme: {theme or "keep current"}\n'
            f'Format: {"legacy profile (review console carefully)" if legacy else "version 1"}\n\n'
            'This replaces the selected console’s camera control settings. '
            'Your other consoles, ROMs, saves and controller preferences '
            'are not changed.\n\n'
            'Object controls will remain stopped until you enable them again. '
            'You can undo this import afterward.\n\n'
            'Apply these settings?'
        )
        if not messagebox.askyesno(
                'Review control-profile import', description,
                parent=self.root):
            return

        try:
            self.read_settings()
            previous = copy.deepcopy(self.cfg)
        except (ValueError, TypeError, tk.TclError) as exc:
            messagebox.showerror(
                'Import controls', f'Could not read current settings: {exc}',
                parent=self.root,
            )
            return
        previous_saved = self.profile_store.get(system)
        previous_theme = self.theme_name.get()
        self.stop_controls()
        try:
            self.profile_store.put(system, imported)
            self.cfg = self.profile_store.get(system)
            self.refresh_settings()
            if theme is not None and theme != previous_theme:
                self.theme_name.set(theme)
                self.apply_theme(theme)
            self.save_preferences()
        except Exception as exc:
            # Storage writes are transactional, but a later theme/UI failure
            # can still occur after the profile commit. Roll back that commit
            # and the visible controls together.
            try:
                self.profile_store.put(system, previous_saved)
            except OSError:
                pass
            self.cfg = previous
            try:
                self.refresh_settings()
                self.theme_name.set(previous_theme)
                self.apply_theme(previous_theme)
            except (ValueError, tk.TclError):
                pass
            messagebox.showerror(
                'Import controls', f'Import failed; previous controls restored: {exc}',
                parent=self.root,
            )
            return
        self._last_profile_import = (system, previous, previous_theme)
        undo = getattr(self, '_undo_import_button', None)
        if undo is not None:
            undo.configure(state='normal')
        self.status.set(
            f'{system.upper()} controls imported. Object input is paused. '
            'Use Undo import to restore your previous layout.'
        )

    def undo_profile_import(self):
        """Undo the most recent profile import without changing other consoles."""
        snapshot = getattr(self, '_last_profile_import', None)
        if snapshot is None:
            return
        system, previous, theme = snapshot
        if self.system_key.get() != system:
            messagebox.showinfo(
                'Undo import', f'Switch back to {system.upper()} to undo.',
                parent=self.root,
            )
            return
        self.stop_controls()
        try:
            self.profile_store.put(system, previous)
            self.cfg = self.profile_store.get(system)
            self.refresh_settings()
            if self.theme_name.get() != theme:
                self.theme_name.set(theme)
                self.apply_theme(theme)
            self.save_preferences()
        except (OSError, ValueError, tk.TclError) as exc:
            messagebox.showerror(
                'Undo import', f'Could not restore the previous controls: {exc}',
                parent=self.root,
            )
            return
        self._last_profile_import = None
        undo = getattr(self, '_undo_import_button', None)
        if undo is not None:
            undo.configure(state='disabled')
        self.status.set('Previous control settings restored. Object input remains paused.')

    def reset_profile(self):
        self.stop_controls()
        self.cfg = default_for(self.system_key.get(), DEFAULT)
        self.refresh_settings()
        self.profile_store.put(self.system_key.get(), self.cfg)
