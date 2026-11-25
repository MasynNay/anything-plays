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
from anything_plays.controller_capture import newly_pressed_source
from anything_plays.ui_setup_theme import bind_theme_canvas


class GamepadMixin:
    def _controller_palette(self):
        name = self.theme_name.get()
        return self.THEMES.get(name, self.THEMES["Dark"])

    def refresh_controller_artwork(self):
        """Redraw small and large icons on theme or connection changes."""
        reader = getattr(self, "_gamepad", None)
        connected = (reader is not None and reader.controller is not None
                     and self.gamepad_enabled.get())
        raw = (reader.physical_buttons if connected else frozenset())
        pressed = frozenset(raw)
        for attr, large in (("gamepad_quick_canvas", False),
                            ("gamepad_setup_canvas", True)):
            canvas = getattr(self, attr, None)
            if canvas is not None:
                try:
                    if canvas.winfo_exists():
                        draw_gamepad(canvas, self._controller_palette(),
                                     connected=connected, expanded=large,
                                     pressed=pressed)
                except tk.TclError:
                    pass
        # Only repaint on an actual connection/input change. The live
        # poll runs every 65ms; idle canvases should not constantly redraw.
        self._last_controller_art_snapshot = (connected, pressed)

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
        ttk.Button(
            panel, text="Guided setup · controller or keyboard",
            command=self.open_controller_setup_guide, style="Accent.TButton",
        ).pack(fill="x", pady=(10, 0))
        self.refresh_controller_artwork()
        return panel

    def open_controller_setup_guide(self):
        """Explain connection, testing and remapping without changing input."""
        from anything_plays.ui_controller_guide import show_controller_guide
        return show_controller_guide(self)

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
        self._controller_capture = None
        self._controller_capture_release_pending = False
        # An SDL disconnect or device swap must never inject an already
        # held button into gameplay. Only the next neutral sample from
        # the new connected device may unlock controller input.
        self._gamepad_last_controller = None
        self._gamepad_seen_controller = False
        self._gamepad_reconnect_release_pending = False
        # A held button while no embedded game is running must not carry
        # into the next newly started game. First-ever active play is unchanged.
        self._gamepad_game_resume_release_pending = False

    def _release_emulated_gamepad(self):
        """Clear native held buttons even if a replaced emulator hook fails."""
        try:
            self.emu.release_gamepad()
        except Exception:
            inputs = getattr(self.emu, "inputs", None)
            release = getattr(inputs, "release_gamepad", None)
            if callable(release):
                try:
                    release()
                except Exception:
                    pass

    def _release_gamepad_after_failure(self):
        """Best-effort safe release, even if an extension/SDL hook raises.

        Never let a broken controller or an already disposed native session
        prevent cleanup of the other resource. The reader clears its
        physical-button latches independently of the emulator input buffer.
        """
        self._release_emulated_gamepad()
        reader = getattr(self, "_gamepad", None)
        if reader is not None:
            try:
                reader.stop()
            except Exception:
                # Native SDL wrappers may fail during USB removal or quit.
                pass

    def close_gamepad(self):
        """Release gamepad state even for partially constructed App objects."""
        self._gamepad_game_resume_release_pending = False
        self._gamepad_last_controller = None
        self._gamepad_seen_controller = False
        self._gamepad_reconnect_release_pending = False
        try:
            self._cancel_controller_capture()
        except Exception:
            self._controller_capture = None
        close_guide = getattr(self, "_controller_guide_close", None)
        if callable(close_guide):
            try:
                close_guide()
            except Exception:
                pass
        self._release_gamepad_after_failure()

    def toggle_gamepad(self):
        """Enable an optional local gamepad; keep keyboard play available."""
        self._gamepad_game_resume_release_pending = False
        self._gamepad_last_controller = None
        self._gamepad_seen_controller = False
        self._gamepad_reconnect_release_pending = False
        if self.gamepad_enabled.get():
            try:
                self._gamepad.start()
                self._gamepad.refresh()
                self.gamepad_status.set("Looking for a controller…")
            except Exception:
                self.gamepad_enabled.set(False)
                # SDL exception strings can include Bluetooth identifiers,
                # USB serials or private driver paths. Keep this fixed text.
                self.gamepad_status.set(
                    "Controller unavailable. Check the connection and retry."
                )
                self._release_gamepad_after_failure()
        else:
            # Disabling during USB/Bluetooth removal must not leave held
            # emulated buttons or SDL handles behind when quit() fails.
            self._release_gamepad_after_failure()
            self.gamepad_status.set("Controller disabled")
        if not self.gamepad_enabled.get():
            self._cancel_controller_capture("Controller disabled; mapping canceled.")
        self.save_preferences()
        self._refresh_gamepad_live_input()
        self.refresh_controller_artwork()

    def prepare_gamepad_for_game_transition(self):
        """Release controller state before unloading or replacing a game.

        ROM and console switches may finish between the 65 ms SDL polls. Do
        not carry a button held in the old title into the next title even if
        no tick observed the gap. Only an explicit neutral sample unlocks
        the next game, without delaying an ordinary fresh press.
        """
        enabled = getattr(self, "gamepad_enabled", None)
        if enabled is not None and enabled.get():
            self._gamepad_game_resume_release_pending = True
        # Use the same native release fallback as Disable and Rescan.
        # A stale SDL/native extension may throw during ROM handoff; never
        # strand the old worker or block the next game because the facade's
        # release hook failed. The underlying input buffer still clears.
        self._release_emulated_gamepad()

    def refresh_gamepad(self):
        try:
            self._cancel_controller_capture(
                "Controller rescan; choose Press to assign again."
            )
        except Exception:
            # A destroyed remapping status widget cannot keep a capture
            # active or abort a physical controller handoff.
            self._controller_capture = None
            self._controller_capture_release_pending = True
        # Rescan is an explicit handoff. A newly enumerated device may already
        # have held buttons; do not hand them to a live game until neutral.
        self._gamepad_last_controller = None
        self._gamepad_seen_controller = bool(self.gamepad_enabled.get())
        self._gamepad_reconnect_release_pending = bool(self.gamepad_enabled.get())
        # Clear both ports now, even if an extension has replaced the usual
        # emulator release hook with one that throws during teardown.
        self._release_emulated_gamepad()
        if self.gamepad_enabled.get():
            try:
                self._gamepad.refresh()
            except Exception:
                # A failed explicit SDL rescan must revoke the old handle,
                # latch state and enabled checkbox rather than leave an
                # unpredictable device feeding the next GUI tick.
                self._release_gamepad_after_failure()
                self.gamepad_enabled.set(False)
                self._gamepad_reconnect_release_pending = False
                self.gamepad_status.set(
                    "Controller unavailable. Check the connection and retry."
                )
                self.save_preferences()
            else:
                self.gamepad_status.set("Looking for a controller…")
        else:
            self.gamepad_status.set("Enable controller input to scan")
        self._refresh_gamepad_live_input()
        self.refresh_controller_artwork()

    def _gamepad_window_focused(self):
        """Fail closed on a disappearing Tk window, without disabling SDL."""
        try:
            return self.root.focus_get() is not None
        except Exception:
            # A destroyed/closing focus widget is not a physical USB fault.
            # Keep the controller enabled, but never publish held input.
            return False

    def _gamepad_live_message(self):
        """Read-only diagnostic; raw buttons never inject emulated input."""
        if not self.gamepad_enabled.get():
            return "Enable gamepad input to test its buttons."
        if self._gamepad.controller is None:
            return "Connect a compatible controller, then press a button."
        if not self._gamepad_window_focused():
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
        except Exception:
            # The clipboard/SDL exception message may contain local ROM
            # paths or device identifiers. Never echo it to a UI label.
            self.gamepad_diagnostics_status.set(
                "Could not copy controller diagnostics. Try again."
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
                connected_device = self._gamepad.controller
                previous_device = getattr(self, "_gamepad_last_controller", None)
                if connected_device is not previous_device:
                    # This is not a first-ever connection: the prior device
                    # disconnected or was replaced. Keep both game ports'
                    # controller state neutral until the newly connected
                    # physical input returns to a fully released snapshot.
                    if (previous_device is not None or
                            (getattr(self, "_gamepad_seen_controller", False)
                             and connected_device is not None)):
                        self._gamepad_reconnect_release_pending = True
                        # Remapping belongs to a particular physical device.
                        # A hotplug or swap during capture must never map a
                        # fresh pad's first press using the old pad's baseline.
                        self._cancel_controller_capture(
                            "Controller changed; choose Press to assign again."
                        )
                    self._gamepad_last_controller = connected_device
                    if connected_device is not None:
                        self._gamepad_seen_controller = True
                if getattr(self, "_gamepad_reconnect_release_pending", False):
                    if (connected_device is not None and
                            not self._gamepad.physical_buttons):
                        self._gamepad_reconnect_release_pending = False
                    else:
                        buttons = frozenset()
                        if connected_device is not None:
                            status += " · Release controller inputs after reconnecting"
                self._controller_capture_tick(system)
                if (getattr(self, "_controller_capture", None) is not None
                        or getattr(self, "_controller_capture_release_pending", False)):
                    # Remapping must never inject the captured press into a
                    # running game, including the frame after assignment.
                    buttons = frozenset()
                    if (getattr(self, "_controller_capture", None) is None
                            and not self._gamepad.physical_buttons):
                        self._controller_capture_release_pending = False
                # Focus loss releases game controls immediately. Regaining
                # focus is NOT permission to replay a button held while
                # another application was active. Require a neutral physical
                # controller sample before game input resumes. This is
                # independent of the remapping press/release guard above.
                unfocused = not self._gamepad_window_focused()
                if unfocused:
                    self._gamepad_focus_release_pending = True
                elif getattr(self, "_gamepad_focus_release_pending", False):
                    if self._gamepad.physical_buttons:
                        buttons = frozenset()
                        status += " · Release controller inputs after refocusing"
                    else:
                        self._gamepad_focus_release_pending = False
                # A controller held while no embedded game is active must
                # return to neutral before controlling a newly started game.
                # This prevents Start/A being carried from a loading screen
                # or external backend into the new title. It never delays a
                # normal first press during a running game.
                embedded = self.uses_embedded_emulator()
                playing = embedded and bool(self.emu.running)
                if not playing:
                    self._gamepad_game_resume_release_pending = bool(
                        self._gamepad.physical_buttons
                    )
                    buttons = frozenset()
                    if not embedded:
                        status += " · Embedded emulators only"
                elif getattr(self, "_gamepad_game_resume_release_pending", False):
                    if self._gamepad.physical_buttons:
                        buttons = frozenset()
                        status += " · Release controller inputs after starting game"
                    else:
                        self._gamepad_game_resume_release_pending = False
                if unfocused:
                    buttons = frozenset()
                self.emu.set_gamepad_buttons(buttons)
                # Tk labels and optional live preview canvases are not SDL
                # input devices. A destroyed status widget or decorative
                # renderer must never trigger the device-failure handler,
                # uncheck the saved controller preference, or revoke a
                # working native gamepad snapshot.
                status_changed = False
                try:
                    status_changed = status != self.gamepad_status.get()
                    if status_changed:
                        self.gamepad_status.set(status)
                except Exception:
                    status_changed = False
                # Redraw live highlighted inputs even when the device
                # connection label stays unchanged. Skip steady idle polls.
                connected = self._gamepad.controller is not None
                snapshot = (connected,
                            frozenset(self._gamepad.physical_buttons)
                            if connected else frozenset())
                if (status_changed or
                        snapshot != getattr(self, "_last_controller_art_snapshot", None)):
                    try:
                        self.refresh_controller_artwork()
                    except Exception:
                        # Avoid retrying a faulty decorative canvas every
                        # 65 ms until the device inputs actually change.
                        self._last_controller_art_snapshot = snapshot
                try:
                    self._refresh_gamepad_live_input()
                except Exception:
                    # Live-test text is advisory, not input transport.
                    pass
            # Off-state is handled immediately in toggle_gamepad(), not on
            # the next timer callback.
        except Exception:
            self._gamepad_game_resume_release_pending = False
            self._gamepad_last_controller = None
            self._gamepad_seen_controller = False
            self._gamepad_reconnect_release_pending = False
            try:
                self._cancel_controller_capture(
                    "Controller error; mapping canceled."
                )
            except Exception:
                self._controller_capture = None
            self._release_gamepad_after_failure()
            self.gamepad_enabled.set(False)
            self.gamepad_status.set(
                "Controller disconnected or unavailable. Reconnect and retry."
            )
            # Preferences and optional artwork must never interrupt the
            # primary gamepad-release path or erase a useful error message.
            for callback in (
                self.save_preferences,
                self._refresh_gamepad_live_input,
                self.refresh_controller_artwork,
            ):
                try:
                    callback()
                except Exception:
                    pass
        finally:
            if not self._closing:
                try:
                    self._gamepad_tick_job = self.root.after(
                        65, self.gamepad_tick
                    )
                except Exception:
                    # Tk can be destroyed during a final SDL hot-unplug.
                    # We cannot safely reschedule against a dead window.
                    self._gamepad_tick_job = None

    @staticmethod
    def _set_controller_capture_status(capture, message):
        """Optional mapping feedback must never interrupt SDL/gameplay."""
        try:
            capture["status"].set(message)
        except Exception:
            # A dismissed mapping dialog can dispose its Tk variables
            # between the 65 ms poll and the pending status update.
            pass

    def _cancel_controller_capture(self, message=None):
        capture = getattr(self, "_controller_capture", None)
        self._controller_capture = None
        if capture is not None:
            self._controller_capture_release_pending = True
            if message:
                self._set_controller_capture_status(capture, message)

    def _controller_capture_tick(self, system):
        """Use an SDL physical-input edge to assign a game action safely."""
        capture = getattr(self, "_controller_capture", None)
        if capture is None:
            return
        if (capture["system"] != system
                or self._gamepad.controller is None):
            self._cancel_controller_capture(
                "Console changed or controller disconnected; mapping canceled."
            )
            return
        if not self._gamepad_window_focused():
            # Never learn a mapping from another app or an unattended pad.
            # Require a fresh edge after the window regains focus.
            capture["baseline"] = frozenset(self._gamepad.physical_buttons)
            self._set_controller_capture_status(capture,
                "Focus Anything Plays, then release and press the control."
            )
            return
        source, baseline, ambiguous = newly_pressed_source(
            capture["baseline"], self._gamepad.physical_buttons
        )
        capture["baseline"] = baseline
        if ambiguous:
            self._set_controller_capture_status(capture,
                "Multiple inputs detected. Release them, then press one control."
            )
        if source is not None:
            target = capture["target"]
            if self._save_gamepad_binding(system, source, target) is False:
                self._set_controller_capture_status(capture,
                    "Controller mapping could not be saved. Check preferences "
                    "storage, release the input and press again to retry."
                )
                return
            row = capture["rows"].get(source)
            if row is not None:
                try:
                    row.set(target)
                except Exception:
                    # Mapping is already persisted; a stale dialog widget
                    # cannot disable a good controller or repeat assignment.
                    pass
            self._set_controller_capture_status(capture,
                f"{source.replace('_', ' ').title()} assigned to {target}. "
                "Release the controller input before playing."
            )
            self._controller_capture = None

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
            self._cancel_controller_capture()
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
            text="Quick remap at top. Scroll down for individual controller mappings.",
            style="Helper.TLabel"
        ).pack(anchor="w", pady=(0, 5))
        holder = ttk.Frame(group)
        holder.pack(fill="both", expand=True)
        canvas = tk.Canvas(holder, borderwidth=0, highlightthickness=0)
        bind_theme_canvas(self, window, canvas)
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
        quick = ttk.LabelFrame(
            rows, text="QUICK REMAP · PRESS A BUTTON", padding=(9, 7),
        )
        quick.pack(fill="x", pady=(0, 9))
        ttk.Label(
            quick, text="Choose a game action, then press ONE physical "
                        "button, D-pad direction, trigger or stick direction.",
            style="Helper.TLabel", wraplength=500,
        ).pack(anchor="w", pady=(0, 6))
        remap_actions = ttk.Frame(quick)
        remap_actions.pack(fill="x")
        target_action = tk.StringVar(
            master=window,
            value="A" if "A" in BUTTONS_BY_SYSTEM[system]
            else BUTTONS_BY_SYSTEM[system][0],
        )
        ttk.Combobox(
            remap_actions, textvariable=target_action, state="readonly",
            values=BUTTONS_BY_SYSTEM[system], width=15,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        capture_feedback = tk.StringVar(
            master=window,
            value="Enable a controller, then choose Press to assign.",
        )
        remap_rows = {}

        def begin_capture():
            if (not self.gamepad_enabled.get()
                    or self._gamepad.controller is None):
                capture_feedback.set(
                    "Controller not connected. Enable it and press Rescan."
                )
                return
            if self.system_key.get() != system:
                capture_feedback.set(
                    "This console has changed. Close and reopen its controls."
                )
                return
            self._controller_capture = {
                "system": system, "target": target_action.get(),
                "baseline": frozenset(self._gamepad.physical_buttons),
                "status": capture_feedback, "rows": remap_rows,
            }
            self._controller_capture_release_pending = True
            # Remapping is another handoff: don't let a faulty native
            # facade resurrect held input or prevent the release gate.
            self._release_emulated_gamepad()
            capture_feedback.set(
                "Waiting for ONE new press. Release any held controls first."
            )

        ttk.Button(
            remap_actions, text="Press to assign", command=begin_capture,
            style="Accent.TButton",
        ).pack(side="left")
        ttk.Button(
            remap_actions, text="Cancel",
            command=lambda: self._cancel_controller_capture(
                "Mapping canceled; existing settings kept."
            ),
        ).pack(side="left", padx=(7, 0))
        ttk.Label(
            quick, textvariable=capture_feedback, style="Helper.TLabel",
            wraplength=500,
        ).pack(anchor="w", pady=(7, 0))


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
                remap_rows[physical] = value
                choice = ttk.Combobox(
                    row, textvariable=value, state="readonly",
                    values=available, width=18
                )
                choice.pack(side="right", fill="x", expand=True)
                choice.bind(
                    "<<ComboboxSelected>>",
                    lambda _event, source=physical, v=value:
                    self._save_gamepad_binding(
                        system, source, v.get(), display_var=v,
                    )
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
        """Reset only one console after its preferences write succeeds."""
        previous = self._gamepad_bindings.get(system)
        self._gamepad_bindings.pop(system, None)
        try:
            persisted = self.save_preferences()
        except (OSError, ValueError, TypeError, tk.TclError):
            persisted = False
        if persisted is False:
            if previous is not None:
                self._gamepad_bindings[system] = previous
            notice = getattr(self, "gamepad_diagnostics_status", None)
            if notice is not None:
                notice.set("Controller defaults were not saved. Check storage and retry.")
            return False
        close()
        self.open_controller_settings(system)
        return True

    def configure_gamepad_mappings(self, system, parent):
        """Compatibility alias for existing controller-map entry points."""
        return self.open_controller_settings(system, parent)

    def _save_gamepad_binding(self, system, source, button, display_var=None):
        """Do not claim assignment when disk persistence was rejected."""
        if (system not in BUTTONS_BY_SYSTEM or source not in SOURCES
                or button not in (DISABLED, *BUTTONS_BY_SYSTEM[system])):
            return False
        previous = self._gamepad_bindings.get(system)
        candidate = dict(previous) if isinstance(previous, dict) else {}
        previous_button = normalize_bindings(system, previous).get(source, DISABLED)
        candidate[source] = button
        self._gamepad_bindings[system] = candidate
        try:
            persisted = self.save_preferences()
        except (OSError, ValueError, TypeError, tk.TclError):
            persisted = False
        if persisted is False:
            if previous is None:
                self._gamepad_bindings.pop(system, None)
            else:
                self._gamepad_bindings[system] = previous
            if display_var is not None:
                display_var.set(previous_button)
            notice = getattr(self, "gamepad_diagnostics_status", None)
            if notice is not None:
                notice.set(
                    "Controller mapping could not be saved. Check preferences storage."
                )
            return False
        return True
