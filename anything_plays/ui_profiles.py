"""Read, validate, migrate and save per-console settings and input mappings."""

import copy
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from anything_plays.atomic_storage import write_json_atomically
from anything_plays.portable_profiles import (
    load_bundle, save_bundle, make_bundle, merge_portable_profile,
)
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

    def save_preferences(self, core_path=None, *, strict=False):
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
            # Explicit import/undo transactions need the failure to reach
            # their rollback handler; routine preference updates still show
            # a nonfatal warning as before.
            if strict:
                raise
            messagebox.showwarning('Preferences', f'Could not save preferences: {exc}')
            return False
        return True

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

    def confirm_unsaved_exit(self):
        """Protect unsaved console edits when final persistence fails.

        Never leak exception text (which may contain private paths), and
        never destroy the window if even the confirmation cannot be shown.
        """
        try:
            discard = messagebox.askyesno(
                "Unsaved console controls",
                "Anything Plays could not save your current console "
                "controls. Closing now may lose your recent edits.\n\n"
                "Exit without saving?",
                parent=self.root,
            )
        except (tk.TclError, RuntimeError):
            discard = False
        if not discard:
            self.status.set(
                "Exit canceled: console controls were not saved. "
                "Check profile storage and retry closing when ready."
            )
            return False
        return True

    def switch_system(self, event=None):
        calibration_was_open = getattr(self, '_calibration_window', None) is not None
        close_guide = getattr(self, 'close_camera_calibration', None)
        if callable(close_guide):
            close_guide(restore=True)
        key = self.system_key.get()
        if key not in SYSTEMS:
            return
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
            # Probe the destination while the previous profile and game
            # window are still intact. A broken profile must not switch the
            # picker, discard the editor, or close a running emulator.
            incoming = self.profile_store.get(key)
            if not isinstance(incoming, dict):
                raise ValueError("Destination profile is invalid")
            self.profile_store.put(previous, self.cfg)
        except (ValueError, TypeError, tk.TclError, OSError):
            # Never discard an unsaved layout if storage is full/unavailable
            # or the active spinboxes cannot be serialized. The Tk selector
            # has already moved; restore it without emitting another event.
            self.system_key.set(previous)
            self.status.set(
                "Could not save the previous console controls. "
                "Switch canceled; correct the settings or storage and retry."
            )
            return False
        # A damaged destination Tk profile can also fail while applying it.
        # Keep game/video teardown and view transitions AFTER the new editor
        # is ready, so a failed switch remains on the prior console.
        old_editor = copy.deepcopy(self.cfg)
        try:
            self.cfg = incoming
            self.refresh_settings()
            self.refresh_system_buttons()
        except (ValueError, TypeError, tk.TclError, RuntimeError):
            self.system_key.set(previous)
            self.cfg = old_editor
            try:
                self.refresh_settings()
                self.refresh_system_buttons()
            except (ValueError, TypeError, tk.TclError, RuntimeError):
                # A failing Tcl widget should not turn recovery into another
                # uncaught exception or close an otherwise usable game.
                pass
            self.status.set(
                "Could not display the selected console controls. "
                "Switch canceled; previous controls were retained."
            )
            return False
        # Only commit the input handoff after the destination profile was
        # loaded, the previous profile was persisted, and the new editor was
        # successfully rendered. If any of those steps fail, the selector
        # rolls back while the existing game and camera-controlled buttons
        # stay active. A successful console switch still releases every
        # held camera input before stopping the old native game.
        self.stop_controls()
        # External games have their own window. Change the overlay only
        # after the incoming controls have been displayed successfully.
        if not self.uses_embedded_emulator(key) and self.view_mode.get() == "Game only":
            self.set_view_mode("Windowed")
        self._active_profile_system = key
        prepare = getattr(self, "prepare_gamepad_for_game_transition", None)
        if callable(prepare):
            prepare()
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
        return True

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
        """Validate every visible control before replacing the active cfg.

        A malformed late spinbox must not leave a half-read mix of old and
        new values in the live profile.
        """
        candidate = copy.deepcopy(self.cfg)
        candidate['tolerance'] = max(1, min(90, int(self.tolerance.get())))
        candidate['min_area'] = max(5, int(self.min_area.get()))
        candidate['hold_frames'] = max(1, min(60, int(self.hold_frames.get())))
        candidate['cooldown_ms'] = max(50, int(self.cooldown.get()))
        candidate['mirror'] = self.mirror.get()
        candidate['color2_enabled'] = bool(self.color2_enabled.get())
        candidate['color2_player'] = (
            self.color2_player.get() if self.color2_player.get()
            in ('Player 1', 'Player 2') else 'Player 2'
        )
        candidate['multi_fish_enabled'] = bool(self.multi_fish_enabled.get())
        candidate['camera_input_mode'] = (
            self.camera_input_mode.get() if self.camera_input_mode.get()
            in ('Held while visible', 'Pulse (classic)')
            else 'Held while visible'
        )
        candidate['zone_font_size'] = max(8, min(160, int(self.zone_font_size.get())))
        candidate['zone_opacity'] = max(75, min(100, int(self.zone_opacity.get())))
        candidate['zone_style'] = self.zone_style.get()
        candidate['zone_border_width'] = max(2, min(16, int(self.zone_border_width.get())))
        candidate['zone_label_position'] = self.zone_label_position.get()
        candidate['shuffle_enabled'] = bool(self.shuffle_enabled.get())
        candidate['zone_image'] = self.zone_image_path.get()
        # The UI has fields for all console families; a portable profile
        # must contain mappings for the selected console only.
        # The combobox may already show the NEXT console during a switch.
        # Persist the old console's visible mappings under its own identity.
        selected = system if system in BUTTONS_BY_SYSTEM else self.system_key.get()
        allowed = BUTTONS_BY_SYSTEM[selected]
        candidate['mapping'] = {
            name: self.mapping_vars[name].get() for name in allowed
        }

        self.cfg = candidate

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
            # Exporting a backup is a read-only operation on local
            # profile storage. A successful backup must not turn into
            # an apparent failure because the source settings disk is
            # full or read-only.
            save_bundle(
                path, self.system_key.get(), self.cfg,
                theme=self.theme_name.get(), allowed_themes=self.THEMES,
            )
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror(
                'Export controls', f'Could not export controls: {exc}',
                parent=self.root,
            )
            return
        self.status.set(
            'Control profile exported. Local control settings were not '
            'changed. ROMs, personal paths, saves and camera footage '
            'were not included.'
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
        from anything_plays.portable_profile_library import portable_restore_delta
        try:
            self.read_settings()
            selected = self.system_key.get()
            prior = {
                system: self.profile_store.get(system)
                for system in BUTTONS_BY_SYSTEM
            }
            prior[selected] = copy.deepcopy(self.cfg)
            changes = portable_restore_delta(prior, imported)
            differences = tuple(changes)
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
        selected_changed = selected in changes
        previous_changed = {system: prior[system] for system in differences}
        try:
            self.profile_store.put_many(changes)
            if selected_changed:
                self.cfg = self.profile_store.get(selected)
                self.refresh_settings()
        except (OSError, ValueError, TypeError, tk.TclError) as exc:
            try:
                self.profile_store.put_many(previous_changed)
                if selected_changed:
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
        self._last_profile_archive_import = previous_changed
        # Keep the exact committed profiles as a conflict baseline.
        # A later user edit must never be overwritten by a blind Undo.
        self._last_profile_archive_applied = {
            system: self.profile_store.get(system) for system in differences
        }
        undo = getattr(self, "_undo_all_profile_restore_button", None)
        if undo is not None:
            undo.configure(state="normal")
        # Any older one-console undo snapshot no longer reflects this state.
        self._last_profile_import = None
        self._last_profile_import_applied = None
        single_undo = getattr(self, "_undo_import_button", None)
        if single_undo is not None:
            single_undo.configure(state="disabled")
        self.status.set(
            f"Controls restored for {len(changes)} of 18 consoles. "
            "Object input remains paused. Use Undo all restore "
            "to return to the previous layouts."
        )

    def undo_all_profile_restore(self):
        """Undo only restored portable controls; protect newer user edits."""
        prior = getattr(self, "_last_profile_archive_import", None)
        applied = getattr(self, "_last_profile_archive_applied", None)
        if prior is None:
            return
        if getattr(self, "_calibration_window", None) is not None:
            messagebox.showinfo(
                "Undo all restore",
                "Finish or cancel camera calibration before undoing a restore.",
                parent=self.root,
            )
            return
        from anything_plays.portable_profile_library import prepare_restore_undo
        try:
            current = {
                system: self.profile_store.get(system) for system in prior
            }
            selected = self.system_key.get()
            if selected in prior:
                # Include edits visible in Tk but not yet persisted.
                self.read_settings()
                current[selected] = copy.deepcopy(self.cfg)
            changes, conflicts = prepare_restore_undo(current, applied, prior)
        except (ValueError, TypeError, tk.TclError) as exc:
            messagebox.showerror(
                "Undo all restore", f"Cannot review the undo safely: {exc}",
                parent=self.root,
            )
            return
        if conflicts:
            preview = ", ".join(SYSTEMS[key].title for key in conflicts[:7])
            remaining = len(conflicts) - 7
            if remaining:
                preview += f" (+{remaining} more)"
            if not messagebox.askyesno(
                "Review newer control edits",
                f"Controls were edited after the backup restore in "
                f"{len(conflicts)} console(s):\n{preview}\n\n"
                "Undo will replace those newer control edits with their "
                "pre-restore layouts. Local backgrounds and other private "
                "settings will be kept.\n\nContinue with Undo?",
                parent=self.root,
            ):
                self.status.set("Undo canceled; newer control edits were kept.")
                return
        # A committed disk write followed by a failed Tk refresh must not
        # leave the application with half-applied undo state. Keep both the
        # durable profiles and the unsaved active editor values for rollback.
        saved_before = {
            system: self.profile_store.get(system) for system in prior
        }
        active_before = copy.deepcopy(self.cfg) if selected in prior else None
        self.stop_controls()
        committed = False
        try:
            self.profile_store.put_many(changes)
            committed = True
            if selected in prior:
                self.cfg = self.profile_store.get(selected)
                self.refresh_settings()
        except (OSError, ValueError, TypeError, tk.TclError, RuntimeError):
            rollback_failed = False
            if committed:
                try:
                    self.profile_store.put_many(saved_before)
                except (OSError, ValueError, TypeError):
                    rollback_failed = True
            if active_before is not None:
                self.cfg = active_before
                try:
                    self.refresh_settings()
                except (ValueError, TypeError, tk.TclError, RuntimeError):
                    # A repeatedly broken UI refresh should not re-raise
                    # from the failure handler or consume the Undo snapshot.
                    pass
            self.status.set(
                "Undo failed; check the saved console controls before playing."
                if rollback_failed else
                "Undo was not completed. Previous controls are still available."
            )
            messagebox.showerror(
                "Undo all restore",
                "Undo could not finish. Check profile storage before retrying."
                if rollback_failed else
                "Undo could not finish; your imported layouts were restored. "
                "You can retry the Undo.",
                parent=self.root,
            )
            return
        self._last_profile_archive_import = None
        self._last_profile_archive_applied = None
        undo = getattr(self, "_undo_all_profile_restore_button", None)
        if undo is not None:
            undo.configure(state="disabled")
        self.status.set(
            f"Previous layouts restored for {len(prior)} consoles. "
            "Object input remains paused."
        )

    def load_profile(self):
        """Validate, preview and merge portable controls into one console."""
        if getattr(self, "_calibration_window", None) is not None:
            messagebox.showinfo(
                'Import controls',
                'Finish or cancel camera calibration before importing controls.',
                parent=self.root,
            )
            return
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
            'This replaces camera controls for the selected console only. '
            'Local zone backgrounds, ROMs, saves, device settings and other '
            'consoles are not changed.\n\n'
            'Object controls remain stopped until you enable them again. '
            'You can undo this import afterward.\n\n'
            'Apply these settings?'
        )
        if not messagebox.askyesno(
                'Review control-profile import', description,
                parent=self.root):
            return

        try:
            if self.system_key.get() != system:
                raise ValueError('Selected console changed during import.')
            self.read_settings()
            previous = copy.deepcopy(self.cfg)
            candidate = merge_portable_profile(system, previous, imported)
        except (ValueError, TypeError, tk.TclError) as exc:
            messagebox.showerror(
                'Import controls', f'Could not prepare current settings: {exc}',
                parent=self.root,
            )
            return
        previous_saved = self.profile_store.get(system)
        previous_theme = self.theme_name.get()
        self.stop_controls()
        try:
            self.profile_store.put(system, candidate)
            self.cfg = self.profile_store.get(system)
            self.refresh_settings()
            if theme is not None and theme != previous_theme:
                self.theme_name.set(theme)
                self.apply_theme(theme)
            self.save_preferences(strict=True)
        except Exception as exc:
            try:
                self.profile_store.put(system, previous_saved)
            except (OSError, ValueError, TypeError):
                pass
            self.cfg = previous
            try:
                self.refresh_settings()
                self.theme_name.set(previous_theme)
                self.apply_theme(previous_theme)
            except (ValueError, tk.TclError):
                pass
            messagebox.showerror(
                'Import controls',
                f'Import failed; check your controls before playing: {exc}',
                parent=self.root,
            )
            return
        self._last_profile_import = (system, previous, previous_theme)
        self._last_profile_import_applied = (
            self.profile_store.get(system), self.theme_name.get(),
        )
        undo = getattr(self, '_undo_import_button', None)
        if undo is not None:
            undo.configure(state='normal')
        self.status.set(
            f'{system.upper()} controls imported. Local zone artwork was kept. '
            'Object input is paused; use Undo import to restore your layout.'
        )

    def undo_profile_import(self):
        """Undo a portable profile without silently losing later local edits."""
        snapshot = getattr(self, '_last_profile_import', None)
        if snapshot is None:
            return
        system, previous, prior_theme = snapshot
        if self.system_key.get() != system:
            messagebox.showinfo(
                'Undo import', f'Switch back to {system.upper()} to undo.',
                parent=self.root,
            )
            return
        if getattr(self, '_calibration_window', None) is not None:
            messagebox.showinfo(
                'Undo import',
                'Finish or cancel camera calibration before undoing an import.',
                parent=self.root,
            )
            return
        applied = getattr(self, '_last_profile_import_applied', None)
        if applied is None:
            messagebox.showerror(
                'Undo import',
                'Cannot safely verify the imported profile. Nothing was changed.',
                parent=self.root,
            )
            return
        applied_profile, applied_theme = applied
        theme_was_imported = applied_theme != prior_theme
        try:
            self.read_settings()
            current = copy.deepcopy(self.cfg)
            previous_controls = make_bundle(system, previous)['profile']
            applied_controls = make_bundle(system, applied_profile)['profile']
            current_controls = make_bundle(system, current)['profile']
            changed_controls = current_controls != applied_controls
            changed_theme = (
                theme_was_imported and self.theme_name.get() != applied_theme
            )
            target = merge_portable_profile(
                system, current, previous_controls,
            )
        except (ValueError, TypeError, tk.TclError) as exc:
            messagebox.showerror(
                'Undo import', f'Cannot review current settings: {exc}',
                parent=self.root,
            )
            return
        if changed_controls or changed_theme:
            if not messagebox.askyesno(
                'Review newer control edits',
                'You edited controls or changed the imported theme after '
                'importing this profile. Undo will replace those newer '
                'control edits with the pre-import layout. Local zone '
                'backgrounds, ROMs and saves will be preserved.\n\n'
                'Continue with Undo?',
                parent=self.root,
            ):
                self.status.set(
                    'Undo import canceled; newer controls were preserved.'
                )
                return

        previous_saved = self.profile_store.get(system)
        current_theme = self.theme_name.get()
        self.stop_controls()
        try:
            self.profile_store.put(system, target)
            self.cfg = self.profile_store.get(system)
            self.refresh_settings()
            if theme_was_imported and current_theme != prior_theme:
                self.theme_name.set(prior_theme)
                self.apply_theme(prior_theme)
            self.save_preferences(strict=True)
        except (OSError, ValueError, TypeError, tk.TclError) as exc:
            try:
                self.profile_store.put(system, previous_saved)
            except (OSError, ValueError, TypeError):
                pass
            self.cfg = current
            try:
                self.refresh_settings()
                self.theme_name.set(current_theme)
                self.apply_theme(current_theme)
            except (ValueError, tk.TclError):
                pass
            messagebox.showerror(
                'Undo import',
                'Could not undo controls; check profile storage and retry.',
                parent=self.root,
            )
            return
        self._last_profile_import = None
        self._last_profile_import_applied = None
        undo = getattr(self, '_undo_import_button', None)
        if undo is not None:
            undo.configure(state='disabled')
        self.status.set(
            'Previous camera controls restored. Local artwork was kept; '
            'object input remains paused.'
        )

    def reset_profile(self):
        """Confirm resetting portable controls while retaining local-only data."""
        system = self.system_key.get()
        if getattr(self, "_calibration_window", None) is not None:
            messagebox.showinfo(
                "Reset controls",
                "Finish or cancel camera calibration before resetting controls.",
                parent=getattr(self, "root", None),
            )
            return False
        if not messagebox.askyesno(
            "Reset console controls",
            f"Reset {SYSTEMS[system].title} camera controls to their "
            "original layout and detection settings?\n\n"
            "Your custom zone artwork, ROM libraries, saved games, "
            "controller preferences and other consoles will be kept.\n\n"
            "Continue with reset?",
            parent=getattr(self, "root", None),
        ):
            self.status.set("Reset canceled; current controls were kept.")
            return False
        # Reset may follow unsaved edits to advanced spinboxes. Capture
        # validated visible values when possible so Undo reset can recover
        # the player's exact pre-reset layout. Invalid settings can still
        # be reset using the last validated in-memory control profile.
        try:
            self.read_settings()
        except (ValueError, TypeError, tk.TclError, AttributeError):
            pass
        prior_ui = copy.deepcopy(self.cfg)
        prior_saved = self.profile_store.get(system)
        # Zone artwork can have changed in Tk without being copied into cfg.
        # Reset *controls*, not the player's local artwork or device paths.
        local_profile = copy.deepcopy(prior_ui)
        image_path = getattr(self, "zone_image_path", None)
        if image_path is not None:
            local_profile["zone_image"] = image_path.get()
        candidate = merge_portable_profile(
            system, local_profile,
            make_bundle(system, default_for(system, DEFAULT))["profile"],
        )
        self.stop_controls()
        committed = False
        try:
            self.profile_store.put(system, candidate)
            committed = True
            self.cfg = self.profile_store.get(system)
            self.refresh_settings()
        except (OSError, ValueError, TypeError, tk.TclError):
            # A failed write never changes the visible profile; if the UI
            # refresh failed after a successful write, try to revert both.
            if committed:
                try:
                    self.profile_store.put(system, prior_saved)
                except (OSError, ValueError, TypeError):
                    pass
            self.cfg = prior_ui
            if committed:
                try:
                    self.refresh_settings()
                except (ValueError, TypeError, tk.TclError):
                    pass
            self.status.set(
                "Control reset was not saved. Previous settings are retained "
                "in the editor; check profile storage before continuing."
            )
            return False
        self._last_profile_reset = (
            system, copy.deepcopy(local_profile), copy.deepcopy(self.cfg),
        )
        undo_reset = getattr(self, "_undo_profile_reset_button", None)
        if undo_reset is not None:
            undo_reset.configure(state="normal")
        self.status.set(
            f"{SYSTEMS[system].title} controls reset to defaults. "
            "Local artwork was kept. Use Undo reset to restore your previous "
            "controls; camera-controlled input remains stopped."
        )
        return True

    def undo_profile_reset(self):
        """Restore the last reset without discarding newer private settings."""
        snapshot = getattr(self, "_last_profile_reset", None)
        if snapshot is None:
            return False
        system, previous, applied = snapshot
        if self.system_key.get() != system:
            messagebox.showinfo(
                "Undo reset", f"Switch back to {SYSTEMS[system].title} to undo reset.",
                parent=getattr(self, "root", None),
            )
            return False
        if getattr(self, "_calibration_window", None) is not None:
            messagebox.showinfo(
                "Undo reset", "Finish or cancel camera calibration before undoing.",
                parent=getattr(self, "root", None),
            )
            return False
        try:
            self.read_settings()
            current = copy.deepcopy(self.cfg)
            old_controls = make_bundle(system, previous)["profile"]
            applied_controls = make_bundle(system, applied)["profile"]
            current_controls = make_bundle(system, current)["profile"]
            target = merge_portable_profile(system, current, old_controls)
        except (ValueError, TypeError, tk.TclError) as exc:
            messagebox.showerror(
                "Undo reset", "Cannot review current controls. Correct invalid "
                "settings before retrying Undo reset.",
                parent=getattr(self, "root", None),
            )
            return False
        if current_controls != applied_controls:
            if not messagebox.askyesno(
                "Review newer control edits",
                "Camera controls changed after Reset. Undo reset will "
                "replace those newer control changes with the pre-reset "
                "layout. Local artwork and ROM paths will be kept.\n\n"
                "Continue with Undo reset?",
                parent=getattr(self, "root", None),
            ):
                self.status.set(
                    "Undo reset canceled; newer control edits were kept."
                )
                return False
        saved_before = self.profile_store.get(system)
        self.stop_controls()
        committed = False
        try:
            self.profile_store.put(system, target)
            committed = True
            self.cfg = self.profile_store.get(system)
            self.refresh_settings()
        except (OSError, ValueError, TypeError, tk.TclError, RuntimeError):
            rollback_failed = False
            if committed:
                try:
                    self.profile_store.put(system, saved_before)
                except (OSError, ValueError, TypeError):
                    rollback_failed = True
            self.cfg = current
            try:
                self.refresh_settings()
            except (ValueError, TypeError, tk.TclError, RuntimeError):
                pass
            self.status.set(
                "Undo reset failed; inspect profile storage before playing."
                if rollback_failed else
                "Undo reset did not finish. Previous controls were retained."
            )
            messagebox.showerror(
                "Undo reset",
                "Undo failed and saved profile recovery was unsuccessful."
                if rollback_failed else
                "Undo reset could not be completed. You may retry.",
                parent=getattr(self, "root", None),
            )
            return False
        self._last_profile_reset = None
        undo_reset = getattr(self, "_undo_profile_reset_button", None)
        if undo_reset is not None:
            undo_reset.configure(state="disabled")
        self.status.set(
            "Pre-reset controls restored. Later local artwork and private "
            "settings were kept; object controls remain paused."
        )
        return True
