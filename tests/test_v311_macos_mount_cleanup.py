"""macOS temporary-DMG cleanup must distinguish auto-unmount from real leaks.

Tests never mount any device, release artifact or user volume.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tools.assemble_v31_full_macos import _detach_owned_ci_mount, mount


class ScopedDmgMountCleanupTests(unittest.TestCase):
    def test_already_unmounted_ci_path_never_calls_hdiutil(self):
        with (
            TemporaryDirectory() as home,
            patch("tools.assemble_v31_full_macos.os.path.ismount", return_value=False),
            patch("tools.assemble_v31_full_macos.subprocess.run") as runner,
        ):
            _detach_owned_ci_mount(Path(home) / "stale")
            runner.assert_not_called()

    def test_hdiutil_error_is_acceptable_only_when_volume_actually_gone(self):
        with (
            TemporaryDirectory() as home,
            patch("tools.assemble_v31_full_macos.os.path.ismount",
                  side_effect=[True, False]) as mounted,
            patch("tools.assemble_v31_full_macos.subprocess.run",
                  return_value=SimpleNamespace(returncode=1,
                                               stderr="No such file or directory",
                                               stdout="")) as runner,
        ):
            _detach_owned_ci_mount(Path(home) / "stable")
            self.assertEqual(mounted.call_count, 2)
            runner.assert_called_once()
            self.assertEqual(runner.call_args.args[0][:2],
                             ["hdiutil", "detach"])

    def test_successful_detach_and_actual_unmount(self):
        with (
            TemporaryDirectory() as home,
            patch("tools.assemble_v31_full_macos.os.path.ismount",
                  side_effect=[True, False]),
            patch("tools.assemble_v31_full_macos.subprocess.run",
                  return_value=SimpleNamespace(returncode=0, stderr="", stdout=""))
                  as runner,
        ):
            _detach_owned_ci_mount(Path(home) / "stable")
            self.assertEqual(runner.call_count, 1)

    def test_attached_busy_volume_raises_after_bounded_force_attempt(self):
        with (
            TemporaryDirectory() as home,
            patch("tools.assemble_v31_full_macos.os.path.ismount", return_value=True),
            patch("tools.assemble_v31_full_macos.subprocess.run",
                  return_value=SimpleNamespace(returncode=1,
                                               stderr="Device busy",
                                               stdout="")) as runner,
            patch("tools.assemble_v31_full_macos.time.sleep") as sleeper,
        ):
            with self.assertRaisesRegex(RuntimeError, "remains mounted"):
                _detach_owned_ci_mount(Path(home) / "stable", attempts=2)
            self.assertEqual(runner.call_count, 3)
            self.assertEqual(sleeper.call_count, 1)
            self.assertEqual(runner.call_args.args[0][2], "-force")

    def test_force_failure_can_succeed_if_ci_mount_disappears(self):
        with (
            TemporaryDirectory() as home,
            patch("tools.assemble_v31_full_macos.os.path.ismount",
                  side_effect=[True, True, False]),
            patch("tools.assemble_v31_full_macos.subprocess.run",
                  return_value=SimpleNamespace(returncode=1,
                                               stderr="Device busy", stdout=""))
                  as runner,
        ):
            _detach_owned_ci_mount(Path(home) / "stable", attempts=1)
            self.assertEqual(runner.call_count, 2)

    def test_mount_context_always_cleans_up_after_body_error(self):
        with (
            TemporaryDirectory() as home,
            patch("tools.assemble_v31_full_macos.command") as attach,
            patch("tools.assemble_v31_full_macos._detach_owned_ci_mount") as detach,
        ):
            location = Path(home) / "scratch"
            with self.assertRaisesRegex(ValueError, "intentional body failure"):
                with mount(Path(home) / "source.dmg", location):
                    self.assertTrue(location.is_dir())
                    raise ValueError("intentional body failure")
            attach.assert_called_once()
            self.assertEqual(attach.call_args.args[:2],
                             ("hdiutil", "attach"))
            detach.assert_called_once_with(location)

    def test_negative_retry_budget_rejected_before_touching_volume(self):
        with patch("tools.assemble_v31_full_macos.subprocess.run") as runner:
            with self.assertRaisesRegex(ValueError, "Bounded"):
                _detach_owned_ci_mount("/unused", attempts=0)
            runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
