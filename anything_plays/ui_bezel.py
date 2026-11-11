"""Lightweight, theme-aware studio bezels for camera and game displays.

These are ordinary Tk widgets around the existing Canvas; they never draw on
camera frames, change emulator pixels, intercept focus, or create animation
timers.  The original camera/game Canvas instances remain the interaction
surfaces, preserving click coordinates and native input bindings.
"""
from __future__ import annotations

import tkinter as tk


def bezel_colors(palette):
    """Use only the six existing theme slots; no hard-coded dark-only chrome."""
    if not isinstance(palette, (tuple, list)) or len(palette) != 6:
        raise ValueError("Expected one complete application theme palette")
    outer, surface, foreground, accent, button, field = palette
    return {
        "housing": button,
        "header": field,
        "label": foreground,
        "accent": accent,
        "well": outer,
        "lip": surface,
    }


class DisplayBezel(tk.Frame):
    """A slim physical-screen housing; caller packs the real Canvas in screen."""

    TITLES = {"camera": "CAMERA  /  TRACKING",
              "game": "GAME  /  OUTPUT"}

    def __init__(self, parent, *, kind, palette):
        if kind not in self.TITLES:
            raise ValueError("Unknown bezel display kind")
        super().__init__(parent, borderwidth=0, highlightthickness=0,
                         padx=3, pady=3)
        self.kind = kind

        # Small fixed chrome rail, not a second content panel. Text remains
        # outside the video so pixels, tracking zones and focus stay intact.
        self.header = tk.Frame(self, height=20, borderwidth=0,
                               highlightthickness=0)
        self.header.pack(fill="x")
        self.caption = tk.Label(
            self.header, text=self.TITLES[kind], anchor="w",
            font=("TkDefaultFont", 9, "bold"), borderwidth=0,
            highlightthickness=0, padx=8, pady=2,
        )
        self.caption.pack(side="left")
        self.marker = tk.Label(
            self.header, text="◆", font=("TkDefaultFont", 9),
            borderwidth=0, highlightthickness=0, padx=8, pady=2,
        )
        self.marker.pack(side="right")

        # Thin accent line and dark inset suggest a monitor or console
        # screen, without obscuring or changing the real video Canvas.
        self.rail = tk.Frame(self, height=2, borderwidth=0,
                             highlightthickness=0)
        self.rail.pack(fill="x", pady=(1, 3))
        self.screen = tk.Frame(
            self, borderwidth=0, highlightthickness=0,
            padx=2, pady=2,
        )
        self.screen.pack(fill="both", expand=True)
        self.lip = tk.Frame(self, height=3, borderwidth=0,
                            highlightthickness=0)
        self.lip.pack(fill="x", pady=(3, 0))
        self.apply_palette(palette)

    def apply_palette(self, palette):
        """Update chrome on theme selection, never touch the video Canvas."""
        c = bezel_colors(palette)
        self.configure(bg=c["housing"])
        self.header.configure(bg=c["header"])
        self.caption.configure(bg=c["header"], fg=c["label"])
        self.marker.configure(bg=c["header"], fg=c["accent"])
        self.rail.configure(bg=c["accent"])
        self.screen.configure(bg=c["well"])
        self.lip.configure(bg=c["lip"])
