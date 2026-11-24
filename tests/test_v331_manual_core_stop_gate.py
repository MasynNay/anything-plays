"""3.3.1: manual libretro core picker must await actual native worker exit.

All core paths are synthetic. Does not load a DLL, open a ROM, change
preferences, launch Tk, access cameras, or start external processes.
"""
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_gameplay import GameplayMixin


class Value:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class PickerHost(GameplayMixin):
    def __init__(self, stop_result=True):
        self.emu = Mock()
        self.emu.core_path = "/synthetic/old-core.so"
        self.emu.stop.return_value = stop_result
        self.system_key = Value("gba")
        self.game_status = Value("Playing previous game")
        self.stop_controls = Mock()
        self.save_preferences = Mock()


class ManualCoreSelectionTests(unittest.TestCase):
    def choose(self, host, file="/synthetic/custom-core.so"):
        with patch("anything_plays.ui_gameplay.filedialog.askopenfilename",
                   return_value=file) as dialog:
            result = host.choose_core()
        dialog.assert_called_once()
        return result

    def test_cancel_does_not_stop_active_emulator_or_save_preferences(self):
        host = PickerHost()
        self.assertIs(self.choose(host, ""), False)
        host.stop_controls.assert_not_called()
        host.emu.stop.assert_not_called()
        host.save_preferences.assert_not_called()
        self.assertEqual(host.emu.core_path, "/synthetic/old-core.so")
        self.assertEqual(host.game_status.get(), "Playing previous game")

    def test_successful_stop_switches_core_and_saves_preference(self):
        host = PickerHost(stop_result=True)
        self.assertIs(self.choose(host), True)
        host.stop_controls.assert_called_once()
        host.emu.stop.assert_called_once()
        host.save_preferences.assert_called_once_with(
            core_path="/synthetic/custom-core.so"
        )
        self.assertEqual(host.emu.core_path, "/synthetic/custom-core.so")
        self.assertEqual(host.game_status.get(), "Core selected: custom-core.so")

    def test_timed_out_stop_does_not_change_core_or_persist_selection(self):
        host = PickerHost(stop_result=False)
        self.assertIs(self.choose(host), False)
        host.stop_controls.assert_called_once()
        host.emu.stop.assert_called_once()
        host.save_preferences.assert_not_called()
        self.assertEqual(host.emu.core_path, "/synthetic/old-core.so")
        self.assertIn("still shutting down", host.game_status.get())
        self.assertIn("Core unchanged", host.game_status.get())

    def test_failed_stop_exception_never_exposes_private_path(self):
        host = PickerHost()
        host.emu.stop.side_effect = RuntimeError(
            "PRIVATE /Users/owner/cores/custom.dylib"
        )
        self.assertIs(self.choose(host), False)
        self.assertEqual(host.emu.core_path, "/synthetic/old-core.so")
        host.save_preferences.assert_not_called()
        self.assertIn("Could not stop", host.game_status.get())
        self.assertNotIn("PRIVATE", host.game_status.get())
        self.assertNotIn("/Users/", host.game_status.get())

    def test_preferences_failure_rolls_back_native_core_path(self):
        host = PickerHost()
        host.save_preferences.side_effect = OSError(
            "PRIVATE /home/person/preferences.json"
        )
        self.assertIs(self.choose(host), False)
        host.emu.stop.assert_called_once()
        self.assertEqual(host.emu.core_path, "/synthetic/old-core.so")
        self.assertIn("Previous core retained", host.game_status.get())
        self.assertNotIn("PRIVATE", host.game_status.get())
        self.assertNotIn("/home/", host.game_status.get())

    def test_legacy_mock_stop_returning_none_still_accepts_selection(self):
        # Existing third-party emulator facades did not return a bool.
        host = PickerHost(stop_result=None)
        self.assertIs(self.choose(host), True)
        self.assertEqual(host.emu.core_path, "/synthetic/custom-core.so")

    def test_retry_after_native_worker_exits_succeeds(self):
        host = PickerHost(stop_result=False)
        self.assertIs(self.choose(host), False)
        self.assertEqual(host.emu.core_path, "/synthetic/old-core.so")
        host.emu.stop.return_value = True
        self.assertIs(self.choose(host), True)
        host.save_preferences.assert_called_once()
        self.assertEqual(host.emu.core_path, "/synthetic/custom-core.so")

    def test_original_stop_is_always_attempted_before_core_change(self):
        host = PickerHost()
        seen = []
        host.stop_controls.side_effect = lambda: seen.append("controls")
        host.emu.stop.side_effect = lambda: (seen.append("native-stop") or True)
        def save(**kwargs):
            self.assertEqual(host.emu.core_path, kwargs["core_path"])
            seen.append("persist")
        host.save_preferences.side_effect = save
        self.assertIs(self.choose(host), True)
        self.assertEqual(seen, ["controls", "native-stop", "persist"])


if __name__ == "__main__":
    unittest.main()
