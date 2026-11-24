"""3.3.1: an incomplete native Stop must never kill an existing external game.

All emulator processes, input pipes, ROM paths, and dialogs are synthetic.
No real Dolphin/RetroArch session, native core, camera or file is accessed.
"""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_external import ExternalBackendMixin


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Host(ExternalBackendMixin):
    def __init__(self, native_stop=False):
        self.system_key = Value("n64")
        self.emu = Mock()
        self.emu.stop.return_value = native_stop
        self.external_input = Mock()
        self.external_process = Mock()
        self.external_process.poll.return_value = None
        self.game_status = Value("External game running")
        self.preferences_path = Path("/synthetic/preferences.json")
        self.external_emulators = {"n64": "/synthetic/retroarch"}
        self.n64_core_override = None
        self.view_mode = Value("Windowed")
        self.root = Mock()
        self.show_external_placeholder = Mock()


class ExternalLaunchStopTests(unittest.TestCase):
    def test_stuck_native_worker_preserves_external_process_and_bridge(self):
        app = Host(native_stop=False)
        previous_process, previous_bridge = app.external_process, app.external_input
        with patch("anything_plays.ui_external.launch") as launch, patch(
            "anything_plays.ui_external.write_retroarch_config"
        ) as config:
            self.assertIs(app.start_external_rom("/synthetic/other.z64"), False)
        self.assertIs(app.external_process, previous_process)
        self.assertIs(app.external_input, previous_bridge)
        previous_process.terminate.assert_not_called()
        previous_bridge.close.assert_not_called()
        launch.assert_not_called()
        config.assert_not_called()
        app.show_external_placeholder.assert_not_called()
        self.assertIn("retained", app.game_status.get())

    def test_native_stop_exception_does_not_expose_private_path(self):
        app = Host()
        app.emu.stop.side_effect = RuntimeError("PRIVATE /home/person/game.z64")
        with patch("anything_plays.ui_external.launch") as launch:
            self.assertIs(app.start_external_rom("/synthetic/next.z64"), False)
        self.assertNotIn("PRIVATE", app.game_status.get())
        self.assertNotIn("/home/", app.game_status.get())
        app.external_process.terminate.assert_not_called()
        app.external_input.close.assert_not_called()
        launch.assert_not_called()

    def test_successful_native_stop_retires_old_external_then_launches_new(self):
        app = Host(native_stop=True)
        events = []
        app.emu.stop.side_effect = lambda: (events.append("native-stop") or True)
        previous_process, previous_bridge = app.external_process, app.external_input
        previous_bridge.close.side_effect = lambda: events.append("bridge-close")
        previous_process.poll.side_effect = lambda: (events.append("process-poll") or None)
        previous_process.terminate.side_effect = lambda: events.append("process-terminate")
        new_process, new_bridge = Mock(), Mock()
        with patch("anything_plays.ui_external.write_retroarch_config",
                   return_value="/synthetic/n64-retropad.cfg"), patch(
            "anything_plays.ui_external.launch",
            side_effect=lambda *args, **kwargs: (events.append("launch") or new_process)
        ), patch("anything_plays.ui_external.N64RemoteController",
                 return_value=new_bridge):
            self.assertIs(app.start_external_rom("/synthetic/next.z64"), True)
        self.assertEqual(events, [
            "native-stop", "bridge-close", "process-poll",
            "process-terminate", "launch",
        ])
        self.assertIs(app.external_process, new_process)
        self.assertIs(app.external_input, new_bridge)
        new_bridge.start.assert_called_once()
        app.show_external_placeholder.assert_called_once()

    def test_legacy_native_stop_none_is_a_completed_stop(self):
        app = Host(native_stop=None)
        with patch("anything_plays.ui_external.write_retroarch_config",
                   return_value="/synthetic/n64-retropad.cfg"), patch(
            "anything_plays.ui_external.launch", return_value=Mock()
        ), patch("anything_plays.ui_external.N64RemoteController",
                 return_value=Mock()):
            self.assertIs(app.start_external_rom("/synthetic/next.z64"), True)
        app.emu.stop.assert_called_once()
        self.assertIn("Launched next", app.game_status.get())

    def test_retry_after_timeout_replaces_external_session(self):
        app = Host(native_stop=False)
        with patch("anything_plays.ui_external.write_retroarch_config",
                   return_value="/synthetic/n64-retropad.cfg"), patch(
            "anything_plays.ui_external.launch", return_value=Mock()
        ) as launch, patch("anything_plays.ui_external.N64RemoteController",
                           return_value=Mock()):
            self.assertIs(app.start_external_rom("/synthetic/new.z64"), False)
            launch.assert_not_called()
            app.emu.stop.return_value = True
            self.assertIs(app.start_external_rom("/synthetic/new.z64"), True)
            launch.assert_called_once()

    def test_failed_native_stop_preserves_gamecube_external_session_too(self):
        app = Host(native_stop=False)
        app.system_key.set("gamecube")
        previous_process, previous_bridge = app.external_process, app.external_input
        with patch("anything_plays.ui_external.launch") as launch:
            self.assertIs(app.start_external_rom("/synthetic/other.iso"), False)
        self.assertIs(app.external_process, previous_process)
        self.assertIs(app.external_input, previous_bridge)
        launch.assert_not_called()
        previous_process.terminate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
