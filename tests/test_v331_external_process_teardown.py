"""3.3.1 external GPU-process cleanup must survive broken poll and wait.

Only synthetic process handles and controller bridges are exercised. No
Dolphin, RetroArch, ROM, USB camera, real process, or user data is touched.
"""
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call

from anything_plays.ui_external import ExternalBackendMixin


class Host(ExternalBackendMixin):
    def __init__(self):
        self.external_input = Mock()
        self.external_process = Mock()
        self.external_process.poll.return_value = None


class ProcessTerminationTests(unittest.TestCase):
    def test_normal_shutdown_closes_bridge_terminates_and_reaps(self):
        app = Host()
        process, bridge = app.external_process, app.external_input
        app.stop_external_emulator()
        bridge.close.assert_called_once()
        process.poll.assert_called_once()
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=0.6)
        process.kill.assert_not_called()
        self.assertIsNone(app.external_process)
        self.assertIsNone(app.external_input)

    def test_completed_process_never_receives_new_signals(self):
        app = Host()
        process = app.external_process
        process.poll.return_value = 0
        app.stop_external_emulator()
        process.terminate.assert_not_called()
        process.kill.assert_not_called()
        process.wait.assert_not_called()

    def test_poll_exception_still_attempts_termination(self):
        app = Host()
        process = app.external_process
        process.poll.side_effect = RuntimeError("PRIVATE /Users/name/game.iso")
        app.stop_external_emulator()
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=0.6)
        process.kill.assert_not_called()
        self.assertIsNone(app.external_process)

    def test_grace_timeout_forces_kill_and_bounded_reap(self):
        app = Host()
        process = app.external_process
        process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="dolphin", timeout=0.6),
            137,
        ]
        app.stop_external_emulator()
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_args_list, [
            call(timeout=0.6), call(timeout=0.25),
        ])

    def test_kill_failure_does_not_bypass_detaching_or_raise(self):
        app = Host()
        process, bridge = app.external_process, app.external_input
        process.wait.side_effect = subprocess.TimeoutExpired(
            cmd="retroarch", timeout=0.6
        )
        process.kill.side_effect = PermissionError("PRIVATE /home/person")
        app.stop_external_emulator()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_count, 2)
        bridge.close.assert_called_once()
        self.assertIsNone(app.external_process)
        self.assertIsNone(app.external_input)

    def test_terminate_raises_after_process_exits_no_unneeded_kill(self):
        app = Host()
        process = app.external_process
        process.poll.side_effect = [None, 0]
        process.terminate.side_effect = ProcessLookupError("already exited")
        app.stop_external_emulator()
        process.terminate.assert_called_once()
        process.kill.assert_not_called()
        process.wait.assert_not_called()

    def test_terminate_failure_on_live_process_attempts_kill(self):
        app = Host()
        process = app.external_process
        process.terminate.side_effect = OSError("PRIVATE process path")
        app.stop_external_emulator()
        process.kill.assert_called_once()
        process.wait.assert_not_called()

    def test_wait_failure_on_live_process_attempts_kill(self):
        app = Host()
        process = app.external_process
        process.wait.side_effect = RuntimeError("PRIVATE wait handle")
        app.stop_external_emulator()
        process.kill.assert_called_once()
        self.assertIsNone(app.external_process)

    def test_wait_failure_after_confirmed_exit_skips_kill(self):
        app = Host()
        process = app.external_process
        process.poll.side_effect = [None, 0]
        process.wait.side_effect = RuntimeError("reaped by another caller")
        app.stop_external_emulator()
        process.kill.assert_not_called()

    def test_bridge_close_failure_does_not_skip_forceful_cleanup(self):
        app = Host()
        process, bridge = app.external_process, app.external_input
        bridge.close.side_effect = RuntimeError("PRIVATE /pipe")
        process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="retroarch", timeout=0.6), 1
        ]
        app.stop_external_emulator()
        process.kill.assert_called_once()
        self.assertIsNone(app.external_input)

    def test_no_wait_extension_keeps_legacy_best_effort_terminate(self):
        app = Host()
        process = Mock(spec=["poll", "terminate", "kill"])
        process.poll.return_value = None
        app.external_process = process
        app.stop_external_emulator()
        process.terminate.assert_called_once()
        process.kill.assert_not_called()

    def test_repeat_stop_is_idempotent_and_has_no_second_signal(self):
        app = Host()
        process, bridge = app.external_process, app.external_input
        app.stop_external_emulator()
        app.stop_external_emulator()
        process.terminate.assert_called_once()
        bridge.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
