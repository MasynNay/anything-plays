"""Gamepad polling and UI commands, owned entirely by Tk's main thread."""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

from anything_plays.gamepad import (
    DISABLED, SOURCES, GamepadReader, normalize_bindings,
)
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM
from anything_plays.ui_controller_art import draw_gamepad


class GamepadMixin:
    def _controller_palette(self):
        name = self.theme_name.get()
        return self.THEMES.get(name, self.THEMES["Dark"])

    def refresh_controller_artwork(self):
        """Redraw small and large icons on theme or connection changes."""
        reader = getattr(self, "_gamepad", None)
        connected = (reader is not None and reader.controller is not None
                     and self.gamepad_enabled.get())
        for attr, large in (("gamepad_quick_canvas", False),
                            ("gamepad_setup_canvas", True)):
            canvas = getattr(self, attr, None)
            if canvas is not None:
                try:
                    if canvas.winfo_exists():
                        draw_gamepad(canvas, self._controller_palette(),
                                     connected=connected, expanded=large)
                except tk.TclError:
                    pass

    def build_gamepad_quick_panel(self, parent):
        """Compact manual-play controls beside display and volume settings.

        Keep status, enable switch and configuration visible on the right.
        The pictogram is art, not a hidden click target; every action is a
        clearly named native Tk button/checkbutton.
        """
        panel = ttk.LabelFrame(
            parent, text="CONTROLLER · MANUAL PLAY", padding=(11, 9)
        )
        panel.pack(fill="x", pady=(0, 10))
        summary = ttk.Frame(panel)
        summary.pack(fill="x")
        self.gamepad_quick_canvas = tk.Canvas(
            summary, width=105, height=68, highlightthickness=0,
            borderwidth=0
        )
        self.gamepad_quick_canvas.pack(side="left", padx=(0, 10))
        description = ttk.Frame(summary)
        description.pack(side="left", fill="x", expand=True)
        ttk.Label(
            description, text="Play with a game controller",
            style="Value.TLabel"
        ).pack(anchor="w")
        ttk.Label(
            description, textvariable=self.gamepad_status,
            style="Helper.TLabel", wraplength=345
        ).pack(anchor="w", pady=(4, 0))

        actions = ttk.Frame(panel)
        actions.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(
            actions, text="Enable gamepad",
            variable=self.gamepad_enabled, command=self.toggle_gamepad
        ).pack(side="left")
        ttk.Button(
            actions, text="Configure…",
            command=self.open_controller_settings, style="Compact.TButton"
        ).pack(side="right")
        ttk.Button(
            actions, text="Rescan", command=self.refresh_gamepad,
            style="Compact.TButton"
        ).pack(side="right", padx=(0, 6))
        self.refresh_controller_artwork()
        return panel

    def initialize_gamepad_preferences(self, preferences):
        """Load optional controller preferences without initializing SDL."""
        self._gamepad = GamepadReader()
        self.gamepad_enabled = tk.BooleanVar(
            value=preferences.get("gamepad_enabled", False) is True
        )
        self.gamepad_status = tk.StringVar(value="Controller disabled")
        # Separate clipboard feedback from the 65ms live connection status,
        # otherwise a successful copy would visually disappear immediately.
        self.gamepad_diagnostics_status = tk.StringVar(value="")
        self.gamepad_live_input = tk.StringVar(
            value="Enable gamepad input to test its buttons."
        )
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
        self._refresh_gamepad_live_input()
        self.refresh_controller_artwork()

    def refresh_gamepad(self):
        # Rescanning closes the previous SDL handle immediately. Also clear
        # its emulated held buttons now, rather than waiting for the next tick.
        self.emu.release_gamepad()
        if self.gamepad_enabled.get():
            self._gamepad.refresh()
            self.gamepad_status.set("Looking for a controller…")
        else:
            self.gamepad_status.set("Enable controller input to scan")
        self._refresh_gamepad_live_input()
        self.refresh_controller_artwork()

    def _gamepad_live_message(self):
        """Read-only diagnostic; raw buttons never inject emulated input."""
        if not self.gamepad_enabled.get():
            return "Enable gamepad input to test its buttons."
        if self._gamepad.controller is None:
            return "Connect a compatible controller, then press a button."
        if self.root.focus_get() is None:
            return "Focus Anything Plays to see live controller input."
        pressed = self._gamepad.physical_buttons
        if not pressed:
            return "Connected. Press a button or move a stick to test."
        labels = [source.replace("_", " ").title()
                  for source in SOURCES if source in pressed]
        shown = ", ".join(labels[:4])
        if len(labels) > 4:
            shown += f" (+{len(labels) - 4} more)"
        return "Detected: " + shown

    def _refresh_gamepad_live_input(self):
        label = getattr(self, "gamepad_live_input", None)
        if label is not None:
            message = self._gamepad_live_message()
            if label.get() != message:
                label.set(message)

    def copy_gamepad_diagnostics(self):
        """Copy a sanitized controller snapshot. Never open a network connection.

        Useful even with no controller attached; the user explicitly chooses
        to share the clipboard contents. Avoid ROM paths and Bluetooth names.
        """
        from anything_plays.controller_diagnostics import make_controller_report

        try:
            focused = self.root.focus_get() is not None
            system = self.system_key.get()
            report = make_controller_report(
                self._gamepad,
                system=system,
                mappings=self._gamepad_bindings.get(system),
                enabled=self.gamepad_enabled.get(),
                focused=focused,
                emulator_running=bool(self.emu.running),
                camera_armed=bool(self.armed),
            )
            self.root.clipboard_clear()
            self.root.clipboard_append(json.dumps(report, indent=2) + "\n")
            self.root.update_idletasks()
        except (tk.TclError, RuntimeError, ValueError, OSError) as exc:
            self.gamepad_diagnostics_status.set(
                "Could not copy diagnostics: " + str(exc)[:105]
            )
            return False
        self.gamepad_diagnostics_status.set(
            "Controller diagnostics copied. No ROMs, file paths or camera images."
        )
        return True

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
                    self.refresh_controller_artwork()
                self._refresh_gamepad_live_input()
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
            self._refresh_gamepad_live_input()
            self.refresh_controller_artwork()
        finally:
            if not self._closing:
                self._gamepad_tick_job = self.root.after(65, self.gamepad_tick)

    def open_controller_settings(self, system=None, parent=None):
        """Show a visual controller setup for one console.

        The right-hand controller card is the primary entrance; the Game
        Controls / Step 8 keyboard dialog links here as a secondary route.
        Configurations are independent of whether a controller is connected.
        """
        previous = getattr(self, "_gamepad_setup_window", None)
        if previous is not None:
            try:
                if previous.winfo_exists():
                    previous.lift()
                    previous.focus_set()
                    return
            except tk.TclError:
                pass

        system = system if system in BUTTONS_BY_SYSTEM else self.system_key.get()
        window = tk.Toplevel(self.root)
        self._gamepad_setup_window = window
        window.title("Controller setup · " + system.upper())
        window.transient(parent or self.root)
        window.geometry("560x700")
        window.minsize(455, 485)

        def close():
            self.gamepad_setup_canvas = None
            self._gamepad_setup_window = None
            window.destroy()

        window.protocol("WM_DELETE_WINDOW", close)
        content = ttk.Frame(window, padding=(14, 12))
        content.pack(fill="both", expand=True)
        ttk.Label(content, text="Controller setup",
                  font=("TkDefaultFont", 16, "bold")).pack(anchor="w")
        ttk.Label(
            content,
            text="Standard gamepad layout · mappings for " + system.upper(),
            style="Helper.TLabel"
        ).pack(anchor="w", pady=(2, 10))

        visual = ttk.LabelFrame(content, text="YOUR CONTROLLER", padding=(9, 7))
        visual.pack(fill="x")
        self.gamepad_setup_canvas = tk.Canvas(
            visual, width=278, height=150,
            highlightthickness=0, borderwidth=0
        )
        self.gamepad_setup_canvas.pack(anchor="center")
        self.refresh_controller_artwork()
        ttk.Label(
            visual,
            text="D-pad   ·   Twin sticks   ·   Face buttons   ·   Triggers",
            style="Helper.TLabel"
        ).pack(pady=(0, 5))

        state = ttk.Frame(content)
        state.pack(fill="x", pady=(10, 8))
        ttk.Checkbutton(
            state, text="Enable gamepad",
            variable=self.gamepad_enabled, command=self.toggle_gamepad
        ).pack(side="left")
        ttk.Button(
            state, text="Rescan", command=self.refresh_gamepad,
            style="Compact.TButton"
        ).pack(side="right")
        ttk.Button(
            state, text="Copy diagnostics",
            command=self.copy_gamepad_diagnostics,
            style="Compact.TButton"
        ).pack(side="right", padx=(0, 6))
        ttk.Label(
            content, textvariable=self.gamepad_diagnostics_status,
            style="Helper.TLabel", wraplength=515
        ).pack(fill="x")
        ttk.Label(content, textvariable=self.gamepad_status,
                  style="Helper.TLabel", wraplength=515).pack(
                      fill="x", pady=(0, 9))

        # Live detection is independent of each console's button mappings and
        # works with no ROM loaded. This is a diagnostic, not button capture.
        tester = ttk.LabelFrame(
            content, text="LIVE CONTROLLER TEST", padding=(9, 7)
        )
        tester.pack(fill="x", pady=(0, 9))
        ttk.Label(
            tester, textvariable=self.gamepad_live_input,
            style="Helper.TLabel", wraplength=490
        ).pack(anchor="w")
        self._refresh_gamepad_live_input()

        group = ttk.LabelFrame(
            content, text="BUTTON MAPPING · " + system.upper(), padding=(8, 7)
        )
        group.pack(fill="both", expand=True)
        ttk.Label(
            group,
            text="Physical controller input                   In-game action",
            style="Helper.TLabel"
        ).pack(anchor="w", pady=(0, 5))
        holder = ttk.Frame(group)
        holder.pack(fill="both", expand=True)
        canvas = tk.Canvas(holder, borderwidth=0, highlightthickness=0)
        scroll = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        rows = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=rows, anchor="nw")
        rows.bind("<Configure>", lambda _e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(
            window_id, width=e.width))

        # Separate physical buttons into recognizable regions of the graphic,
        # instead of an undifferentiated 22-control vertical list.
        sections = (
            ("D-PAD", ("DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT")),
            ("FACE BUTTONS", ("A", "B", "X", "Y")),
            ("MENU BUTTONS", ("BACK", "START")),
            ("ANALOG STICKS", (
                "LEFT_STICK_UP", "LEFT_STICK_DOWN",
                "LEFT_STICK_LEFT", "LEFT_STICK_RIGHT",
                "RIGHT_STICK_UP", "RIGHT_STICK_DOWN",
                "RIGHT_STICK_LEFT", "RIGHT_STICK_RIGHT"
            )),
            ("SHOULDERS & TRIGGERS", (
                "LEFT_SHOULDER", "RIGHT_SHOULDER",
                "LEFT_TRIGGER", "RIGHT_TRIGGER"
            )),
        )
        descriptions = {
            "BACK": "Back / Select", "START": "Start / Menu",
            "LEFT_SHOULDER": "Left bumper", "RIGHT_SHOULDER": "Right bumper",
            "LEFT_TRIGGER": "Left trigger", "RIGHT_TRIGGER": "Right trigger",
        }
        arrows = {"UP": "↑", "DOWN": "↓", "LEFT": "←", "RIGHT": "→"}
        available = (DISABLED, *BUTTONS_BY_SYSTEM[system])
        selected = normalize_bindings(
            system, self._gamepad_bindings.get(system)
        )
        for heading, physical_controls in sections:
            section = ttk.LabelFrame(rows, text=heading, padding=(7, 4))
            section.pack(fill="x", pady=(3, 7), padx=(2, 5))
            for physical in physical_controls:
                row = ttk.Frame(section)
                row.pack(fill="x", pady=3)
                name = descriptions.get(physical)
                if name is None:
                    fragments = physical.split("_")
                    if physical.startswith("DPAD_"):
                        name = "D-pad " + arrows[fragments[-1]]
                    elif physical.startswith(("LEFT_STICK_", "RIGHT_STICK_")):
                        name = fragments[0].title() + " stick " + arrows[fragments[-1]]
                    else:
                        name = physical
                ttk.Label(row, text=name, width=19).pack(side="left")
                value = tk.StringVar(
                    master=window, value=selected.get(physical, DISABLED)
                )
                choice = ttk.Combobox(
                    row, textvariable=value, state="readonly",
                    values=available, width=18
                )
                choice.pack(side="right", fill="x", expand=True)
                choice.bind(
                    "<<ComboboxSelected>>",
                    lambda _event, source=physical, v=value:
                    self._save_gamepad_binding(system, source, v.get())
                )

        footer = ttk.Frame(content)
        footer.pack(fill="x", pady=(9, 0))
        ttk.Button(
            footer, text="Restore defaults",
            style="Compact.TButton",
            command=lambda: self._reset_gamepad_mappings(system, close)
        ).pack(side="left")
        ttk.Button(
            footer, text="Done", command=close,
            style="Accent.TButton"
        ).pack(side="right")
        ttk.Label(
            content, text="Changes are saved immediately for this console.",
            style="Helper.TLabel"
        ).pack(anchor="w", pady=(5, 0))

    def _reset_gamepad_mappings(self, system, close):
        """Reset just the selected console; leave other console maps alone."""
        self._gamepad_bindings.pop(system, None)
        self.save_preferences()
        close()
        self.open_controller_settings(system)

    def configure_gamepad_mappings(self, system, parent):
        """Compatibility alias for existing controller-map entry points."""
        return self.open_controller_settings(system, parent)

    def _save_gamepad_binding(self, system, source, button):
        if source not in SOURCES or button not in (DISABLED, *BUTTONS_BY_SYSTEM[system]):
            return
        saved = self._gamepad_bindings.get(system)
        if not isinstance(saved, dict):
            saved = {}
            self._gamepad_bindings[system] = saved
        saved[source] = button
        self.save_preferences()
