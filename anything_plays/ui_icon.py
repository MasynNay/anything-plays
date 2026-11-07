"""Load the corrected fish icon without modifying the 2.0 artwork.

Keep app identity and native icon lifetime separate from startup and
emulator logic. Tk's PhotoImage must remain referenced until app shutdown.
"""

from pathlib import Path
import sys
import tkinter as tk
from PIL import Image, ImageTk
from anything_plays.icon_cleanup import clean_icon_background


class IconMixin:
    def set_app_icon(self):
        """Use the corrected 2.1 artwork, with a safe legacy PNG fallback."""
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        artwork = base / "assets" / "anything_plays_v21.webp"
        if artwork.is_file():
            try:
                with Image.open(artwork) as source:
                    icon = clean_icon_background(source)
                self._app_icon = ImageTk.PhotoImage(icon, master=self.root)
                self.root.iconphoto(True, self._app_icon)
                return
            except (OSError, ValueError, tk.TclError):
                pass
        original = base / "assets" / "anything_plays.png"
        if original.is_file():
            try:
                self._app_icon = tk.PhotoImage(file=str(original))
                self.root.iconphoto(True, self._app_icon)
            except tk.TclError:
                pass
