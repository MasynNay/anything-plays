"""Exercise Tk startup and shutdown without real cameras or user preferences.

Run under Xvfb on Linux. Every configuration write goes to a temporary home
folder so CI and developer smoke tests never alter real console profiles.
"""

from pathlib import Path
import tempfile
import time
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
                    # Real 3.1 chrome surrounds, but never replaces, the
                    # original interactive camera and emulator Canvas widgets.
                    assert app.camera_bezel.winfo_exists()
                    assert app.game_bezel.winfo_exists()
                    assert app.canvas.master is app.camera_bezel.screen
                    assert app.game_canvas.master is app.game_bezel.screen
                    assert app.canvas.bind('<Button-1>')
                    assert app.game_canvas.bind('<KeyPress>')
                    assert app.game_canvas.cget('takefocus') == '1'
                    assert app.camera_bezel.marker.cget('text') == '◎'
                    assert app.game_bezel.marker.cget('text') == '◆'
                    assert app.camera_bezel.footer_caption.cget('text') == 'OPTICAL SENSOR'
                    assert app.game_bezel.footer_caption.cget('text') == 'LOCAL PLAY'
                    assert len(app.camera_bezel.signature_ticks) == 3
                    assert len(app.game_bezel.signature_ticks) == 5
                    # Decorative vent and lens details are native Tk children,
                    # never canvas items that accumulate during video rendering.
                    initial_chrome_children = (
                        len(app.camera_bezel.winfo_children()),
                        len(app.game_bezel.winfo_children()),
                    )
                    # 3.1: the controller belongs in the right-hand game
                    # panel, and should be a real, theme-aware Tk interface.
                    assert app.gamepad_quick_canvas.winfo_exists()
                    assert len(app.gamepad_quick_canvas.find_all()) > 10
                    assert app.gamepad_status.get() == "Controller disabled"
                    app.open_controller_settings()
                    root.update_idletasks()
                    assert app._gamepad_setup_window.winfo_exists()
                    assert app.gamepad_setup_canvas.winfo_exists()
                    assert len(app.gamepad_setup_canvas.find_all()) > 15
                    assert app.gamepad_live_input.get().startswith("Enable gamepad")
                    # The right-side shortcut and the setup window must
                    # survive a theme change without duplicating canvas art.
                    original_icon_count = len(app.gamepad_quick_canvas.find_all())
                    app.theme_name.set("Plum Dark")
                    root.update_idletasks()
                    assert app.gamepad_quick_canvas.cget("bg") == app.THEMES["Plum Dark"][1]
                    assert len(app.gamepad_quick_canvas.find_all()) == original_icon_count
                    assert app.camera_bezel.cget('bg') == app.THEMES["Plum Dark"][4]
                    assert app.game_bezel.cget('bg') == app.THEMES["Plum Dark"][5]
                    assert app.camera_bezel.header.cget('bg') == app.THEMES["Plum Dark"][5]
                    assert app.game_bezel.header.cget('bg') == app.THEMES["Plum Dark"][4]
                    for bezel in (app.camera_bezel, app.game_bezel):
                        assert bezel.rail.cget('bg') == app.THEMES["Plum Dark"][3]
                        assert bezel.caption.cget('fg') == app.THEMES["Plum Dark"][2]
                        assert len(bezel.signature_ticks) in (3, 5)
                    assert app.camera_bezel.signature_ticks[1].cget('bg') == app.THEMES["Plum Dark"][3]
                    assert app.game_bezel.signature_ticks[0].cget('bg') == app.THEMES["Plum Dark"][3]
                    assert app.game_bezel.signature_ticks[1].cget('bg') == app.THEMES["Plum Dark"][1]
                    app._save_gamepad_binding("gba", "A", "B")
                    assert app._gamepad_bindings["gba"]["A"] == "B"

                    def find_widgets(widget):
                        yield widget
                        for child in widget.winfo_children():
                            yield from find_widgets(child)

                    from tkinter import ttk
                    done = [
                        button for button in find_widgets(app._gamepad_setup_window)
                        if isinstance(button, ttk.Button)
                        and button.cget("text") == "Done"
                    ]
                    assert len(done) == 1
                    done[0].invoke()
                    assert app._gamepad_setup_window is None
                    assert app.gamepad_setup_canvas is None
                    assert len(app.THEMES) == 16
                    assert app.system_key.get() in {
                        "gb", "gbc", "gba", "snes", "nes", "genesis", "n64", "gamecube"
                    }
                    assert app.zone_border_width.get() >= 2
                    # Newly installed profiles remain single-fish by default.
                    # Enabling multi-input is a conscious per-console choice.
                    assert app.multi_fish_enabled.get() is False
                    assert app.color2_enabled.get() is False
                    assert app.volume_slider.winfo_exists()
                    app.volume_percent.set(19)
                    app.set_game_volume(save=False)
                    assert abs(app.emu.volume - .19) < .001
                    app.toggle_game_mute()
                    assert app.volume_percent.get() == 0
                    assert app.emu.volume == 0
                    app.toggle_game_mute()
                    assert app.volume_percent.get() == 19
                    app.color2_enabled.set(True)
                    app.color2_player.set('Player 1')
                    app.multi_fish_enabled.set(True)
                    app.update_tracking_preferences()
                    assert app.cfg['multi_fish_enabled'] is True
                    assert app.cfg['color2_enabled'] is True
                    assert app.cfg['color2_player'] == 'Player 1'
                    app.reset_profile()
                    assert app.multi_fish_enabled.get() is False
                    assert app.color2_enabled.get() is False
                    assert app.view_mode.get() == "Windowed"
                    app.set_view_mode("Borderless", persist=False)
                    assert app.view_mode.get() == "Borderless"
                    app.set_view_mode("Windowed", persist=False)
                    app.set_view_mode("Game only", persist=False)
                    assert app._game_only_canvas is not None
                    app.set_view_mode("Windowed", persist=False)
                    assert app._game_only_canvas is None

                    app.theme_name.set("Light")
                    assert app.camera_bezel.rail.cget('bg') == app.THEMES["Light"][3]
                    assert app.game_bezel.rail.cget('bg') == app.THEMES["Light"][3]
                    assert app.game_canvas.cget('highlightcolor') == app.THEMES["Light"][3]
                    assert app.camera_bezel.cget('bg') == app.THEMES["Light"][4]
                    assert app.game_bezel.cget('bg') == app.THEMES["Light"][5]
                    assert app.camera_bezel.footer_caption.cget('fg') == app.THEMES["Light"][2]
                    assert app.game_bezel.footer_caption.cget('fg') == app.THEMES["Light"][2]
                    assert initial_chrome_children == (
                        len(app.camera_bezel.winfo_children()),
                        len(app.game_bezel.winfo_children()),
                    )
                    app.system_key.set("snes")
                    app.switch_system()
                    assert app.system_description.cget("text") == "Super Nintendo"
                    assert app.system_key.get() == "snes"
                    app.system_key.set("n64")
                    app.switch_system()
                    # Experimental ParaLLEl-N64 software frames use the same
                    # game canvas. RetroArch remains an explicit fallback.
                    assert app.uses_embedded_emulator()
                    assert not app.external_setup.winfo_manager()
                    assert not app.n64_mode_row.winfo_manager()
                    assert not app.arm_button.instate(("disabled",))
                    assert not app.shortcuts_button.instate(("disabled",))
                    app.set_view_mode("Game only", persist=False)
                    assert app._game_only_canvas is not None
                    app.set_view_mode("Windowed", persist=False)
                    app.n64_embedded.set(False)
                    app.switch_n64_backend()
                    # Normal players cannot be pushed into an extra download.
                    assert app.uses_embedded_emulator()
                    assert not app.external_setup.winfo_manager()
                    app.external_fallback_enabled = True
                    app.update_external_setup()
                    assert app.n64_mode_row.winfo_manager()
                    app.n64_embedded.set(False)
                    app.switch_n64_backend()
                    assert not app.uses_embedded_emulator()
                    assert app.external_setup.winfo_manager()
                    app.set_view_mode("Game only", persist=False)
                    assert app.view_mode.get() == "Windowed"
                    assert app._game_only_canvas is None
                    app.n64_embedded.set(True)
                    app.switch_n64_backend()
                    assert not app.external_setup.winfo_manager()
                    app.system_key.set("gamecube")
                    app.switch_system()
                    assert app.uses_embedded_emulator()
                    assert app.gamecube_mode_row.winfo_manager()
                    assert not app.external_setup.winfo_manager()
                    app.set_view_mode("Game only", persist=False)
                    assert app._game_only_canvas is not None
                    app.set_view_mode("Windowed", persist=False)
                    app.gamecube_embedded.set(False)
                    app.switch_gamecube_backend()
                    assert not app.uses_embedded_emulator()
                    assert app.external_setup.winfo_manager()
                    app.gamecube_embedded.set(True)
                    app.switch_gamecube_backend()
                    assert app.uses_embedded_emulator()
                    assert not app.external_setup.winfo_manager()
                    app.external_fallback_enabled = False
                    app.update_external_setup()
                    assert not app.gamecube_mode_row.winfo_manager()
                    app.system_key.set("genesis")
                    app.switch_system()
                    assert not app.external_setup.winfo_manager()
                    assert app.mapping_vars["C"].get() == "C"
                    assert not app.arm_button.instate(("disabled",))
                    assert not app.shortcuts_button.instate(("disabled",))

                    # Every 2.1 console must be switchable inside the same
                    # application, with its own controls and without opening
                    # an external emulator or losing the Tk game panel.
                    from anything_plays.systems import SYSTEMS
                    from anything_plays.system_profiles import BUTTONS_BY_SYSTEM
                    for console, profile in SYSTEMS.items():
                        app.system_key.set(console)
                        app.switch_system()
                        assert app.system_description.cget("text") == profile.title
                        assert app.uses_embedded_emulator()
                        assert not app.external_setup.winfo_manager()
                        assert app.game_canvas.winfo_exists()
                        assert all(
                            name in app.cfg["mapping"]
                            for name in BUTTONS_BY_SYSTEM[console]
                        ), console
                    app.system_key.set("genesis")
                    app.switch_system()

                    # Selecting the wrong ROM directory must not block Tk.
                    roms = Path(temp_home) / "roms"
                    roms.mkdir()
                    (roms / "Demo.gen").write_bytes(b"test fixture")
                    app.rom_directory = str(roms)
                    app.rom_directories["genesis"] = str(roms)
                    app.populate_inline_library()
                    assert "Scanning" in app.library_summary.get()
                    deadline = time.monotonic() + 3
                    while not app.library_images and time.monotonic() < deadline:
                        root.update()
                        time.sleep(0.02)
                    assert len(app.library_images) == 1
                    app.clear_rom_directory()
                    assert app.rom_directory == ""
                    assert app.rom_directories["genesis"] == ""
                    assert "Choose a ROM folder" in app.library_summary.get()

                    # A previously custom-positioned Shuffle must snap to
                    # exactly the same cells as enabled console buttons.
                    app.cfg["zones"]["Shuffle"] = [.13, .21, .41, .56]
                    app.shuffle_enabled.set(True)
                    app.make_symmetric_grid()
                    zones = app.cfg["zones"]
                    from anything_plays.system_profiles import enabled_zones
                    names = enabled_zones(app.cfg, app.system_key.get()) + ["Shuffle"]
                    sizes = {
                        (round(zones[name][2] - zones[name][0], 8),
                         round(zones[name][3] - zones[name][1], 8))
                        for name in names
                    }
                    assert len(sizes) == 1
                    assert "Shuffle" in app.status.get()
                    app.shuffle_enabled.set(False)
                    unchanged = zones["Shuffle"][:]
                    app.make_symmetric_grid()
                    assert zones["Shuffle"] == unchanged
                    app.shuffle_enabled.set(True)

                    # Simulate many repeated draws. The Tk canvas item count
                    # must remain bounded during an overnight session.
                    app.frame = np.zeros((160, 240, 3), dtype=np.uint8)
                    app.draw_camera()
                    assert app.camera_photo is not None
                    first_camera_image = app.camera_photo
                    for _ in range(50):
                        app.draw_camera()
                    # One native photo buffer + one canvas item, irrespective
                    # of how long the video preview runs.
                    assert app.camera_photo is first_camera_image
                    assert len(app.canvas.find_all()) == 1
                    app.reference_image = False
                    app.stop_camera()
                    assert app.frame is None
                    assert app.camera_photo is None
                    assert not app.canvas.find_all()

                    with app.emu.lock:
                        app.emu.frame = np.zeros((180, 240, 3), dtype=np.uint8)
                        app.emu.frame_serial += 1
                    app.draw_game()
                    first_game_image = app.game_photo
                    for _ in range(100):
                        with app.emu.lock:
                            app.emu.frame_serial += 1
                        app.draw_game()
                    assert app.game_photo is first_game_image
                    assert len(app.game_canvas.find_all()) == 1
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
