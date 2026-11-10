"""Edit game key mappings in a modal, keyboard-capture shortcut dialog."""
import tkinter as tk
from tkinter import messagebox, ttk

from anything_plays.shortcuts import normalize_bindings, rebind
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM
from anything_plays.systems import SYSTEMS


class ShortcutsMixin:
    def _read_shortcut_bindings(self):
        record = self.read_preferences().get("key_bindings", {})
        return record if isinstance(record, dict) else {}

    def active_key_bindings(self):
        system = self.system_key.get()
        return normalize_bindings(system, self._shortcut_bindings.get(system))

    def configure_shortcuts(self):
        if getattr(self, "_shortcut_window", None) is not None:
            if self._shortcut_window.winfo_exists():
                self._shortcut_window.lift()
                return
        window = tk.Toplevel(self.root)
        self._shortcut_window = window
        window.title("Game Controls · " + SYSTEMS[self.system_key.get()].title)
        window.transient(self.root)
        window.geometry("450x620")
        window.minsize(360, 400)
        window.protocol("WM_DELETE_WINDOW", window.destroy)

        ttk.Label(window, text="Custom keyboard controls", font=("DejaVu Sans", 14, "bold")).pack(
            anchor="w", padx=15, pady=(15, 3)
        )
        ttk.Label(window, text="Select Change, then press the desired key.\n"
                  "Shortcuts apply to Anything Plays' embedded emulators only.\n"
                  "F11 = fullscreen • F10 = borderless • Esc = exit/stop",
                  justify="left").pack(anchor="w", padx=15, pady=(0, 12))
        # Controller controls remain accessible above the scrollable list of
        # keyboard shortcuts. SDL is not initialized until the player opts in.
        controller_frame = ttk.LabelFrame(window, text="Manual controller", padding=9)
        controller_frame.pack(fill="x", padx=12, pady=(0, 9))
        ttk.Checkbutton(
            controller_frame, text="Enable connected gamepad",
            variable=self.gamepad_enabled, command=self.toggle_gamepad
        ).pack(anchor="w")
        ttk.Label(controller_frame, textvariable=self.gamepad_status,
                  wraplength=375).pack(anchor="w", pady=4)
        pad_buttons = ttk.Frame(controller_frame)
        pad_buttons.pack(fill="x")
        ttk.Button(pad_buttons, text="Rescan", command=self.refresh_gamepad).pack(side="left")
        ttk.Button(pad_buttons, text="Controller mappings",
                   command=lambda: self.configure_gamepad_mappings(system, window)
                   ).pack(side="left", padx=(8, 0))
        ttk.Label(window, text="Keyboard shortcuts",
                  font=("DejaVu Sans", 11, "bold")).pack(anchor="w", padx=13, pady=(3, 2))
        list_frame = ttk.Frame(window)
        list_frame.pack(fill="both", expand=True, padx=12)
        canvas = tk.Canvas(list_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas)
        item = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(item, width=e.width))
        system = self.system_key.get()
        bindings = self.active_key_bindings()
        for name in BUTTONS_BY_SYSTEM[system]:
            row = ttk.Frame(inner)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=name, width=13).pack(side="left")
            label = ttk.Label(row, text=bindings[name], width=17)
            label.pack(side="left")
            ttk.Button(row, text="Change",
                       command=lambda n=name, target=label: self._capture_shortcut(
                           system, n, target, window)).pack(side="right")
        ttk.Button(window, text="Reset this console's keys",
                   command=lambda: self._reset_shortcuts(system, window)).pack(
                       fill="x", padx=15, pady=12)

    def _capture_shortcut(self, system, button, label, parent):
        prompt = tk.Toplevel(parent)
        prompt.transient(parent)
        prompt.title("Press a key for " + button)
        prompt.geometry("320x125")
        ttk.Label(prompt, text="Press the new key for " + button,
                  font=("DejaVu Sans", 11, "bold")).pack(pady=14)
        ttk.Label(prompt, text="Escape to cancel").pack()

        def handle(event):
            if event.keysym == "Escape":
                prompt.destroy()
                return "break"
            try:
                current = self._shortcut_bindings.get(system, {})
                updated = rebind(system, current, button, event.keysym)
            except ValueError as exc:
                messagebox.showwarning("Shortcut unavailable", str(exc), parent=prompt)
                return "break"
            self._shortcut_bindings[system] = updated
            label.config(text=updated[button])
            self.save_preferences()
            prompt.destroy()
            return "break"

        prompt.bind("<KeyPress>", handle)
        prompt.grab_set()
        prompt.focus_force()

    def _reset_shortcuts(self, system, parent):
        self._shortcut_bindings.pop(system, None)
        self.save_preferences()
        parent.destroy()
        self._shortcut_window = None
        self.configure_shortcuts()
