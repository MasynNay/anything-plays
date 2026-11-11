"""Theme-aware studio camera monitor and game-console screen bezels.

Decorative native Tk widgets surround the original Canvas surfaces. No
bezel child overlays camera pixels or emulator video, intercepts game focus,
starts a timer, or implies a camera/controller is currently recording.
"""
from __future__ import annotations

import tkinter as tk


def bezel_colors(palette, *, kind="camera"):
    """Derive distinct chassis finishes from the six existing theme slots.

    The default camera layout preserves the original bezel color contract.
    Both finishes change with the selected theme; neither adds hard-coded
    dark-mode-only chrome.
    """
    if (not isinstance(palette, (tuple, list)) or len(palette) != 6
            or kind not in ("camera", "game")):
        raise ValueError("Expected a supported display and complete theme palette")
    outer, surface, foreground, accent, button, field = palette
    return {
        "housing": button if kind == "camera" else field,
        "header": field if kind == "camera" else button,
        "label": foreground,
        "accent": accent,
        "well": outer,
        "lip": surface,
    }


class DisplayBezel(tk.Frame):
    """A light chassis around the existing interactive camera/game Canvas."""

    TITLES = {"camera": "CAMERA  /  TRACKING",
              "game": "GAME  /  OUTPUT"}
    SIGNATURES = {"camera": "OPTICAL SENSOR",
                  "game": "LOCAL PLAY"}

    def __init__(self, parent, *, kind, palette):
        if kind not in self.TITLES:
            raise ValueError("Unknown bezel display kind")
        super().__init__(parent, borderwidth=0, highlightthickness=0,
                         padx=3, pady=3)
        self.kind = kind

        # A restrained header, always outside the video viewport.
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
            self.header, text="◎" if kind == "camera" else "◆",
            font=("TkDefaultFont", 9), borderwidth=0,
            highlightthickness=0, padx=8, pady=2,
        )
        self.marker.pack(side="right")

        # The accent line and padded inset suggest real monitor glass
        # while preserving every pixel and coordinate on the video Canvas.
        self.rail = tk.Frame(self, height=2, borderwidth=0,
                             highlightthickness=0)
        self.rail.pack(fill="x", pady=(1, 3))
        self.screen = tk.Frame(self, borderwidth=0, highlightthickness=0,
                               padx=2, pady=2)
        self.screen.pack(fill="both", expand=True)
        self.lip = tk.Frame(self, height=3, borderwidth=0,
                            highlightthickness=0)
        self.lip.pack(fill="x", pady=(3, 0))

        # Two personalities, one visual system:
        #  camera -> three subtle lens/sensor ticks
        #  game   -> five slim ventilation-slot ticks
        # All ticks are purely physical housing detail, not fake status LEDs.
        self.footer = tk.Frame(self, height=13, borderwidth=0,
                               highlightthickness=0)
        self.footer.pack(fill="x", pady=(1, 0))
        self.footer_caption = tk.Label(
            self.footer, text=self.SIGNATURES[kind],
            font=("TkDefaultFont", 8), anchor="e",
            borderwidth=0, highlightthickness=0, padx=7, pady=0,
        )
        self.footer_caption.pack(side="right")
        self.signature = tk.Frame(self.footer, borderwidth=0,
                                  highlightthickness=0)
        self.signature.pack(side="left", padx=(8, 0), pady=(4, 0))
        self.signature_ticks = []
        for _ in range(3 if kind == "camera" else 5):
            tick = tk.Frame(
                self.signature, width=5 if kind == "camera" else 10,
                height=4 if kind == "camera" else 3,
                borderwidth=0, highlightthickness=0,
            )
            tick.pack(side="left", padx=(0, 3))
            tick.pack_propagate(False)
            self.signature_ticks.append(tick)

        self.apply_palette(palette)

    def apply_palette(self, palette):
        """Recolor existing chrome; don't rebuild labels or video canvases."""
        c = bezel_colors(palette, kind=self.kind)
        self.configure(bg=c["housing"])
        self.header.configure(bg=c["header"])
        self.caption.configure(bg=c["header"], fg=c["label"])
        self.marker.configure(bg=c["header"], fg=c["accent"])
        self.rail.configure(bg=c["accent"])
        self.screen.configure(bg=c["well"])
        self.lip.configure(bg=c["lip"])
        self.footer.configure(bg=c["housing"])
        self.footer_caption.configure(bg=c["housing"], fg=c["label"])
        self.signature.configure(bg=c["housing"])
        for index, tick in enumerate(self.signature_ticks):
            # Sensor ticks have a bright middle lens; game vent slots
            # alternate subtle highlight and recess for console character.
            use_accent = (index == 1 if self.kind == "camera"
                          else index in (0, 4))
            tick.configure(bg=c["accent"] if use_accent else c["lip"])
