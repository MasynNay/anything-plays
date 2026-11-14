"""3.2 setup truthfulness and safe ROM launch with a limited native core set.

These tests use a fake game path, a mock native emulator and no camera, file
selector, controller, ROM contents or actual native core. Stable behavior
must remain unchanged, including recoverable errors for genuinely missing
public-package cores.
"""

import unittest
from threading import Lock
from unittest.mock import Mock, patch

from anything_plays.setup_health import (
    PREVIEW_BUNDLED_SYSTEMS, build_setup_report,
    preview_missing_core_guidance,
)
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM
from anything_plays.ui_library import LibraryMixin


class Value:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeApp(LibraryMixin):
    def __init__(self, system, *, core=None):
        self.system_key = Value(system)
        self.game_status = Value("No ROM loaded")
        self.current_rom = None
        self._core_install_busy = False
        self._save_warning_until = 0
        self.root = object()
        self.game_bezel = Mock()
        self.emu = Mock()
        self.emu.core_path = None
        self.emu.lock = Lock()
        self.emu.frame = object()
        self.emu.find_system_core.return_value = core
        self.game_canvas = Mock()
        self.game_photo = object()
        self.uses_embedded_emulator = lambda: True
        self.deactivate_manual = Mock()
        self.stop_controls = Mock()
        self.stop_external_emulator = Mock()
        self.show_library = Mock()
        self.show_playing_info = Mock()


class PreviewCoreLaunchTests(unittest.TestCase):
    def test_inventory_is_one_core_for_three_system_profiles(self):
        self.assertEqual(PREVIEW_BUNDLED_SYSTEMS, {"gb", "gbc", "gba"})
        self.assertEqual(len(BUTTONS_BY_SYSTEM), 18)

    def test_each_missing_preview_console_gives_correct_nonrepair_message(self):
        for console in BUTTONS_BY_SYSTEM:
            with self.subTest(console=console):
                app = FakeApp(console)
                fake_path = "/synthetic/does-not-exist/user-game.bin"
                with patch(
                    "anything_plays.preview_storage.is_v32_preview",
                    return_value=True,
                ), patch(
                    "anything_plays.ui_library.messagebox.showinfo",
                ) as info, patch(
                    "anything_plays.ui_library.messagebox.showerror",
                ) as error:
                    app.start_rom(fake_path)
                self.assertIsNone(app.current_rom)
                self.assertEqual(app.game_status.get(), preview_missing_core_guidance(
                    console,
                )[0])
                self.assertEqual(app.show_library.call_count, 1)
                app.show_playing_info.assert_not_called()
                app.emu.start.assert_not_called()
                app.emu.stop.assert_called_once()
                self.assertIsNone(app.emu.frame)
                self.assertIsNone(app.game_photo)
                app.game_canvas.delete.assert_called_once_with("all")
                app.stop_external_emulator.assert_called()
                app.stop_controls.assert_called()
                error.assert_not_called()
                info.assert_called_once()
                self.assertEqual(
                    info.call_args.args[0],
                    "3.2 preview emulator availability",
                )
                message = info.call_args.args[1]
                self.assertNotIn(fake_path, message)
                self.assertNotIn("repair or reinstall Anything Plays 3.0",
                                 message)
                self.assertNotIn("every console is included", message)
                if console in PREVIEW_BUNDLED_SYSTEMS:
                    self.assertIn("mGBA", message)
                    self.assertIn("missing", app.game_status.get().lower())
                else:
                    self.assertIn("not bundled", app.game_status.get().lower())
                    self.assertIn("not a damaged installation", message)

    def test_missing_core_closes_an_existing_game_without_stale_video(self):
        app = FakeApp("snes")
        app.current_rom = "/synthetic/previous-game.gba"
        app.emu.running = True
        stale_frame = app.emu.frame
        with patch(
            "anything_plays.preview_storage.is_v32_preview",
            return_value=True,
        ), patch("anything_plays.ui_library.messagebox.showinfo"):
            app.start_rom("/synthetic/unbundled-game.sfc")
        app.emu.stop.assert_called_once()
        self.assertIsNotNone(stale_frame)
        self.assertIsNone(app.emu.frame)
        self.assertIsNone(app.game_photo)
        self.assertIsNone(app.current_rom)
        app.game_canvas.delete.assert_called_once_with("all")
        app.show_library.assert_called_once()
        self.assertIn("Not bundled", app.game_status.get())

    def test_preview_restart_refuses_stale_rom_after_unload(self):
        app = FakeApp("snes")
        app.emu.rom = "/synthetic/previous-game.gba"
        with patch(
            "anything_plays.preview_storage.is_v32_preview",
            return_value=True,
        ):
            app.retry_current_rom()
        self.assertEqual(
            app.game_status.get(), "Choose a game ROM before restarting.",
        )
        app.emu.start.assert_not_called()
        app.emu.find_system_core.assert_not_called()

    def test_published_stable_restart_fallback_is_unchanged(self):
        app = FakeApp("snes", core="/synthetic/core.so")
        app.emu.rom = "/synthetic/previous-game.sfc"
        with patch(
            "anything_plays.preview_storage.is_v32_preview",
            return_value=False,
        ):
            app.retry_current_rom()
        app.emu.start.assert_called_once_with("/synthetic/previous-game.sfc")

    def test_existing_user_core_can_launch_even_when_not_bundled(self):
        app = FakeApp("snes", core="/synthetic/user-approved-core.so")
        with patch("anything_plays.ui_library.messagebox.showinfo") as info:
            app.start_rom("/synthetic/user-game.sfc")
        app.emu.start.assert_called_once_with("/synthetic/user-game.sfc")
        app.emu.stop.assert_not_called()
        info.assert_not_called()
        app.show_playing_info.assert_called_once()
        self.assertEqual(app.current_rom, "/synthetic/user-game.sfc")
        self.assertIn("Starting", app.game_status.get())

    def test_stable_full_core_missing_messages_unchanged(self):
        for console, excerpt in (
            ("snes", "every console is included"),
            ("gamecube", "Dolphin system files"),
        ):
            with self.subTest(console=console):
                app = FakeApp(console)
                with patch(
                    "anything_plays.preview_storage.is_v32_preview",
                    return_value=False,
                ), patch(
                    "anything_plays.ui_library.messagebox.showerror",
                ) as error, patch(
                    "anything_plays.ui_library.messagebox.showinfo",
                ) as info:
                    app.start_rom("/synthetic/stable-game.rom")
                error.assert_called_once()
                self.assertIn(excerpt, error.call_args.args[1])
                info.assert_not_called()
                self.assertEqual(
                    app.current_rom, "/synthetic/stable-game.rom",
                )
                app.show_playing_info.assert_called_once()

    def test_setup_diagnostics_matches_launch_and_omits_private_details(self):
        for console in BUTTONS_BY_SYSTEM:
            with self.subTest(console=console):
                summary, guidance = preview_missing_core_guidance(console)
                report = build_setup_report(
                    system=console, camera_count=0, camera_selected=False,
                    camera_active=False, core_found=False,
                    controller_enabled=False, controller_detected=False,
                    embedded_mode=True, preview_minimal=True,
                )
                self.assertEqual(report["checks"]["emulator"], {
                    "status": summary, "next": guidance,
                })
                self.assertNotIn("synthetic", repr(report))
                self.assertNotIn("/home/", repr(report))
                self.assertNotIn("damaged", repr(report) if
                                 console in PREVIEW_BUNDLED_SYSTEMS else "")

    def test_detected_native_core_is_not_mislabeled_unbundled(self):
        report = build_setup_report(
            system="snes", camera_count=0, camera_selected=False,
            camera_active=False, core_found=True,
            controller_enabled=False, controller_detected=False,
            embedded_mode=True, preview_minimal=True,
        )
        self.assertEqual(report["checks"]["emulator"]["status"],
                         "Core file located")

    def test_unrecognized_console_is_rejected(self):
        with self.assertRaises(ValueError):
            preview_missing_core_guidance("../../hidden")


if __name__ == "__main__":
    unittest.main()
