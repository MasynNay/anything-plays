"""Gamepad polling and UI commands, owned entirely by Tk's main thread."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from anything_plays.gamepad import (
    DISABLED, SOURCES, GamepadReader, normalize_bindings,
)
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM


class GamepadMixin:
    def initialize_gamepad_preferences(self, preferences):
        """Load optional controller preferences without initializing SDL."""
        self._gamepad = GamepadReader()
        self.gamepad_enabled = tk.BooleanVar(
            value=preferences.get("gamepad_enabled", False) is True
        )
        self.gamepad_status = tk.StringVar(value="Controller disabled")
        settings = preferences.get("gamepad_bindings", {})
        self._gamepad_bindings = settings if isinstance(settings, dict) else {}

    def close_gamepad(self):
        """Release gamepad state even for partially constructed App objects."""
        try:
            self.emu.release_gamepad()
        finally:
            reader = getattr(self, "_gamepad", None)
            if reader is not None:
                reader.stop()

    def toggle_gamepad(self):
        """Enable an optional local gamepad; keep keyboard play available."""
        if self.gamepad_enabled.get():
            try:
                self._gamepad.start()
                self._gamepad.refresh()
                self.gamepad_status.set("Looking for a controller…")
            except Exception as exc:
                self.gamepad_enabled.set(False)
                self.gamepad_status.set(
                    "Controller unavailable: " + str(exc)[:130]
                )
                self.emu.release_gamepad()
                self._gamepad.stop()
        else:
            self.emu.release_gamepad()
            self._gamepad.stop()
            self.gamepad_status.set("Controller disabled")
        self.save_preferences()

    def refresh_gamepad(self):
        if self.gamepad_enabled.get():
            self._gamepad.refresh()
            self.gamepad_status.set("Looking for a controller…")
        else:
            self.gamepad_status.set("Enable controller input to scan")

    def gamepad_tick(self):
        """Keep manual control independent of camera arming and keyboard focus.

        A background game cannot receive stale held buttons while another
        application is focused. No threads and no global OS key hooks.
        """
        if self._closing:
            return
        try:
            if self.gamepad_enabled.get():
                # A saved enabled preference also needs SDL initialization
                # after startup; the checkbox callback is not run by Tk.
                if self._gamepad.api is None:
                    self._gamepad.start()
                system = self.system_key.get()
                settings = self._gamepad_bindings.get(system)
                buttons, status = self._gamepad.poll(system, settings)
                if not self.uses_embedded_emulator():
                    buttons = frozenset()
                    status += " · Embedded emulators only"
                elif not self.emu.running:
                    buttons = frozenset()
                elif self.root.focus_get() is None:
                    buttons = frozenset()
                self.emu.set_gamepad_buttons(buttons)
                if status != self.gamepad_status.get():
                    self.gamepad_status.set(status)
            # Off-state is handled immediately in toggle_gamepad(), not on
            # the next timer callback.
        except Exception as exc:
            self.emu.release_gamepad()
            self._gamepad.stop()
            self.gamepad_enabled.set(False)
            self.gamepad_status.set(
                "Controller disconnected or unavailable: " + str(exc)[:130]
            )
            self.save_preferences()
        finally:
            if not self._closing:
                self._gamepad_tick_job = self.root.after(65, self.gamepad_tick)

    def configure_gamepad_mappings(self, system, parent):
        """Editable per-console map of SDL's normalized physical controls."""
        window = tk.Toplevel(parent)
        window.title("Controller buttons · " + system.upper())
        window.transient(parent)
        window.geometry("450x570")
        window.minsize(350, 400)
        ttk.Label(window, text="Controller button mapping",
                  font=("DejaVu Sans", 14, "bold")).pack(
                      anchor="w", padx=14, pady=(12, 4))
        ttk.Label(window, text="Choose which in-game button each physical control presses.\n"
                  "Changes are saved for this console only.",
                  justify="left").pack(anchor="w", padx=14, pady=(0, 9))

        frame = ttk.Frame(window)
        frame.pack(fill="both", expand=True, padx=12)
        canvas = tk.Canvas(frame, borderwidth=0, highlightthickness=0)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas)
        item = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(
            item, width=e.width))

        saved = self._gamepad_bindings.get(system)
        values = (DISABLED, *BUTTONS_BY_SYSTEM[system])
        active = normalize_bindings(system, saved)
        for physical in SOURCES:
            row = ttk.Frame(inner)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=physical.replace("_", " ").title(),
                      width=20).pack(side="left")
            value = tk.StringVar(value=active.get(physical, DISABLED))
            choice = ttk.Combobox(row, textvariable=value, values=values,
                                  state="readonly", width=16)
            choice.pack(side="right", fill="x", expand=True)
            choice.bind("<<ComboboxSelected>>", lambda _event,
                        source=physical, v=value:
                        self._save_gamepad_binding(system, source, v.get()))

        def reset():
            self._gamepad_bindings.pop(system, None)
            self.save_preferences()
            window.destroy()
            self.configure_gamepad_mappings(system, parent)

        ttk.Button(window, text="Restore defaults for this console",
                   command=reset).pack(fill="x", padx=12, pady=12)

    def _save_gamepad_binding(self, system, source, button):
        if source not in SOURCES or button not in (DISABLED, *BUTTONS_BY_SYSTEM[system]):
            return
        saved = self._gamepad_bindings.get(system)
        if not isinstance(saved, dict):
            saved = {}
            self._gamepad_bindings[system] = saved
        saved[source] = button
        self.save_preferences()
