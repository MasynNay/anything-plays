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
        canvas.bind("<Button-1>", self.activate_manual)
        canvas.bind("<KeyPress>", self.manual_key_down)
        canvas.bind("<KeyRelease>", self.manual_key_up)
        canvas.bind("<FocusOut>", self.deactivate_manual)
        popup.bind("<Escape>", lambda _: self.set_view_mode("Windowed"))
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
