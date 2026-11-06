"""Exercise Tk startup and shutdown without real cameras or user preferences.

Run under Xvfb on Linux. Every configuration write goes to a temporary home
folder so CI and developer smoke tests never alter real console profiles.
"""

from pathlib import Path
import tempfile
import tkinter as tk
from unittest.mock import patch

import numpy as np

from app import App


def main():
    with tempfile.TemporaryDirectory(prefix="anything-plays-ui-") as temp_home:
        # Both settings and application-support directory lookups use Path.home.
        with patch("pathlib.Path.home", return_value=Path(temp_home)):
            with patch("anything_plays.ui_camera.discover", return_value=[]):
                root = tk.Tk()
                app = None
                try:
                    app = App(root)
                    root.update_idletasks()
                    assert app.library_canvas.winfo_exists()
                    assert app.game_canvas.winfo_exists()
                    assert len(app.THEMES) == 16
                    assert app.system_key.get() in {
                        "gb", "gbc", "gba", "snes", "nes", "genesis", "n64", "gamecube"
                    }
                    assert app.zone_border_width.get() >= 2
                    assert app.view_mode.get() == "Windowed"
                    app.set_view_mode("Borderless", persist=False)
                    assert app.view_mode.get() == "Borderless"
                    app.set_view_mode("Windowed", persist=False)
                    app.set_view_mode("Game only", persist=False)
                    assert app._game_only_canvas is not None
                    app.set_view_mode("Windowed", persist=False)
                    assert app._game_only_canvas is None

                    app.theme_name.set("Light")
                    app.system_key.set("snes")
                    app.switch_system()
                    assert app.system_description.cget("text") == "Super Nintendo"
                    assert app.system_key.get() == "snes"
                    app.system_key.set("n64")
                    app.switch_system()
                    assert app.external_setup.winfo_manager()
                    app.set_view_mode("Game only", persist=False)
                    assert app.view_mode.get() == "Windowed"
                    assert app._game_only_canvas is None
                    app.system_key.set("genesis")
                    app.switch_system()
                    assert not app.external_setup.winfo_manager()
                    assert app.mapping_vars["C"].get() == "C"

                    # Rendering a camera frame is independent from live hardware.
                    app.frame = np.zeros((160, 240, 3), dtype=np.uint8)
                    app.draw_camera()
                    assert app.camera_photo is not None
                    root.after(200, app.close)
                    root.mainloop()
                    assert app._closing
                finally:
                    if app is not None and not app._closing:
                        app.close()
                    elif app is None:
                        root.destroy()

    print("Tk GUI smoke test passed")


if __name__ == "__main__":
    main()
