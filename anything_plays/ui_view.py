"""Keep windowed, borderless and fullscreen views distinct from game input.

Game-only view uses its own Tk canvas; it leaves the main app and camera
tracking alive without moving or destroying the original game canvas.
"""
import tkinter as tk
from tkinter import ttk
from anything_plays.systems import SYSTEMS

VIEW_MODES = ("Windowed", "Borderless", "Fullscreen", "Game only")


class ViewMixin:
    def set_view_mode(self, mode=None, *, persist=True):
        mode = mode or self.view_mode.get()
        if mode not in VIEW_MODES:
            mode = "Windowed"
        # An external emulator renders in its own GPU window. A fullscreen
        # Tk canvas here would cover that window with a blank game display.
        if mode == "Game only" and not self.uses_embedded_emulator():
            self.view_mode.set(getattr(self, "_current_view_mode", "Windowed"))
            self.game_status.set(
                "Game only requires built-in video. Enable experimental "
                "N64 software graphics, or use an embedded 2D console."
            )
            return
        if getattr(self, "_view_transition", False):
            return
        self._view_transition = True
        try:
            self._close_game_only()
            if mode == "Windowed":
                self.root.attributes("-fullscreen", False)
                self.root.overrideredirect(False)
                self.root.geometry(getattr(self, "_windowed_geometry", "1400x880"))
            elif mode == "Borderless":
                if getattr(self, "_current_view_mode", "Windowed") == "Windowed":
                    self._windowed_geometry = self.root.geometry()
                self.root.attributes("-fullscreen", False)
                self.root.overrideredirect(True)
                self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
            elif mode == "Fullscreen":
                if getattr(self, "_current_view_mode", "Windowed") == "Windowed":
                    self._windowed_geometry = self.root.geometry()
                self.root.overrideredirect(False)
                self.root.attributes("-fullscreen", True)
            elif mode == "Game only":
                if getattr(self, "_current_view_mode", "Windowed") == "Windowed":
                    self._windowed_geometry = self.root.geometry()
                self.root.overrideredirect(False)
                self.root.attributes("-fullscreen", False)
                self._open_game_only()
            self._current_view_mode = mode
            self.view_mode.set(mode)
            if persist:
                self.save_preferences()
        finally:
            self._view_transition = False

    def _open_game_only(self):
        popup = tk.Toplevel(self.root)
        self._game_only_window = popup
        popup.title("Anything Plays · Game only")
        popup.attributes("-fullscreen", True)
        popup.configure(bg="#030a14")
        canvas = tk.Canvas(popup, bg="#030a14", borderwidth=0,
                           highlightthickness=0, takefocus=1)
        self._game_only_canvas = canvas
        canvas.pack(fill="both", expand=True)
        # Game-only mode still needs a mouse-accessible sound control.
        # Keep a compact overlay at the bottom instead of leaving the game
        # entirely to access volume or change OS master volume.
        sound = ttk.Frame(popup)
        sound.place(relx=0.5, rely=1.0, anchor="s", y=-12)
        ttk.Label(sound, text="Game audio").pack(side="left", padx=(8, 5))
        sound_scale = ttk.Scale(
            sound, from_=0, to=100, orient="horizontal",
            length=170, variable=self.volume_percent,
            command=self.set_game_volume,
        )
        sound_scale.pack(side="left", padx=(2, 6), pady=5)
        sound_scale.bind(
            "<ButtonRelease-1>", lambda _: self.set_game_volume(save=True)
        )
        ttk.Label(sound, textvariable=self.volume_label, width=5).pack(
            side="left"
        )
        ttk.Button(
            sound, textvariable=self.mute_button_text,
            command=self.toggle_game_mute,
        ).pack(side="left", padx=(4, 8))
        canvas.bind("<Button-1>", self.activate_manual)
        canvas.bind("<KeyPress>", self.manual_key_down)
        canvas.bind("<KeyRelease>", self.manual_key_up)
        canvas.bind("<FocusOut>", self.deactivate_manual)
        popup.bind("<Escape>", self.exit_view_or_stop)  # Also disarms camera input.
        popup.bind("<F10>", lambda _: self.set_view_mode("Borderless"))
        popup.bind("<F11>", lambda _: self.set_view_mode("Windowed"))
        popup.protocol("WM_DELETE_WINDOW", lambda: self.set_view_mode("Windowed"))
        canvas.focus_set()

    def _close_game_only(self):
        popup = getattr(self, "_game_only_window", None)
        self._game_only_window = None
        self._game_only_canvas = None
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass
        self.deactivate_manual()

    def toggle_fullscreen(self, event=None):
        if self.view_mode.get() in ("Fullscreen", "Game only"):
            self.set_view_mode("Windowed")
        else:
            self.set_view_mode("Fullscreen")
        return "break"

    def toggle_borderless(self, event=None):
        self.set_view_mode("Windowed" if self.view_mode.get() == "Borderless"
                           else "Borderless")
        return "break"

    def exit_view_or_stop(self, event=None):
        if self.view_mode.get() != "Windowed":
            self.set_view_mode("Windowed")
        self.stop_controls()
        return "break"
