"""Bounded, failure-transparent real-game test harness contracts.

No emulator, copyrighted game, or internet access is needed for these tests.
The integration workflow separately runs an actual pinned homebrew DOL.
"""
import json
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from tools.probe_gamecube_homebrew import _parent, main, evaluate_video_probe


def make_fixture(destination):
    destination.write_bytes(b"synthetic fixture, not an executable")
    return destination


class GameCubePlaybackProbeTests(unittest.TestCase):
    def test_three_slow_frames_cannot_be_reported_as_playable(self):
        evidence = evaluate_video_probe(None, 3, 1, 12.0)
        self.assertTrue(evidence["frames_valid"])
        self.assertFalse(evidence["fps_target_met"])
        self.assertEqual(evidence["frames_per_second_observed"], 0.25)

    def test_nonblank_frames_and_usable_speed_both_required(self):
        self.assertFalse(evaluate_video_probe(None, 300, 0, 12)["fps_target_met"])
        self.assertFalse(evaluate_video_probe("load error", 300, 2, 12)["fps_target_met"])
        self.assertTrue(evaluate_video_probe(None, 300, 2, 12)["fps_target_met"])

    def test_native_timeout_still_produces_explicit_failed_evidence(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"synthetic")
            report = root / "report.json"
            with patch("tools.probe_gamecube_homebrew.verified_homebrew",
                       side_effect=make_fixture), patch(
                           "tools.probe_gamecube_homebrew.subprocess.run",
                           side_effect=TimeoutExpired("core", timeout=10,
                                                      output=b"booting..."),
                       ):
                self.assertEqual(_parent(core, 1, report), 1)
            saved = json.loads(report.read_text())
            self.assertFalse(saved["probe_passed"])
            self.assertTrue(saved["timed_out"])
            self.assertIn("booting", saved["console_tail"])
            self.assertIsNone(saved["details"])

    def test_native_crash_does_not_count_as_playback_success(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"synthetic")
            report = root / "report.json"
            with patch("tools.probe_gamecube_homebrew.verified_homebrew",
                       side_effect=make_fixture), patch(
                           "tools.probe_gamecube_homebrew.subprocess.run",
                           return_value=CompletedProcess(["native"], -11,
                                                        stdout="segmentation fault"),
                       ):
                self.assertEqual(_parent(core, 1, report), 1)
            saved = json.loads(report.read_text())
            self.assertEqual(saved["child_returncode"], -11)
            self.assertFalse(saved["probe_passed"])

    def test_only_child_frame_evidence_can_mark_playback_success(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"synthetic")
            report = root / "report.json"

            def fake_subprocess(command, **kwargs):
                location = Path(command[command.index("--report") + 1])
                location.write_text(
                    json.dumps({
                        "playback_probe_passed": True,
                        "video_callback_frames": 6,
                        "nonblank_sampled_frames": 1,
                        "frames_per_second_observed": 3.0,
                    })
                )
                return CompletedProcess(command, 0, stdout="native success")

            with patch("tools.probe_gamecube_homebrew.verified_homebrew",
                       side_effect=make_fixture), patch(
                           "tools.probe_gamecube_homebrew.subprocess.run",
                           side_effect=fake_subprocess,
                       ):
                self.assertEqual(_parent(core, 1, report), 0)
            saved = json.loads(report.read_text())
            self.assertTrue(saved["probe_passed"])
            self.assertEqual(saved["details"]["video_callback_frames"], 6)
            # Even a successful experimental probe is not a release approval.

    def test_cached_interpreter_mode_is_forwarded_to_isolated_child(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"synthetic")
            report = root / "report.json"

            def fake_child(args, **kwargs):
                self.assertIn("--cpu-core", args)
                self.assertEqual(args[args.index("--cpu-core") + 1], "5")
                return CompletedProcess(args, -11, stdout="cached interpreter crash")

            with patch("tools.probe_gamecube_homebrew.verified_homebrew",
                       side_effect=make_fixture), patch(
                           "tools.probe_gamecube_homebrew.subprocess.run",
                           side_effect=fake_child):
                self.assertEqual(_parent(core, 1, report, cpu_core="5"), 1)
            saved = json.loads(report.read_text())
            self.assertEqual(saved["cpu_core_mode"], "5")
            self.assertFalse(saved["probe_passed"])

    def test_fast_controller_stimulus_is_an_isolated_probe_option(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"synthetic")
            report = root / "report.json"
            def check_command(args, **kwargs):
                self.assertIn("--fast-controls", args)
                self.assertIn("--exercise-controls", args)
                return CompletedProcess(args, -11, stdout="simulated native failure")
            with patch("tools.probe_gamecube_homebrew.verified_homebrew",
                       side_effect=make_fixture), patch(
                           "tools.probe_gamecube_homebrew.subprocess.run",
                           side_effect=check_command):
                self.assertEqual(_parent(
                    core, 1, report, cpu_core="5", fast_controls=True
                ), 1)
            saved = json.loads(report.read_text())
            self.assertTrue(saved["fast_controller_stimulus"])
            self.assertFalse(saved["probe_passed"])

    def test_synchronous_cpu_gpu_flag_reaches_child_without_installing_dolphin(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"synthetic")
            report = root / "report.json"
            def inspect(args, **kwargs):
                self.assertIn("--single-core", args)
                self.assertEqual(args[args.index("--cpu-core") + 1], "5")
                return CompletedProcess(args, -11, stdout="simulated native failure")
            with patch("tools.probe_gamecube_homebrew.verified_homebrew",
                       side_effect=make_fixture), patch(
                           "tools.probe_gamecube_homebrew.subprocess.run",
                           side_effect=inspect):
                self.assertEqual(
                    _parent(core, 1, report, cpu_core="5",
                            exercise_controls=True, single_core=True), 1
                )
            saved = json.loads(report.read_text())
            self.assertTrue(saved["single_core"])
            self.assertFalse(saved["probe_passed"])

    def test_controller_stimulus_is_forwarded_to_native_child(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"synthetic")
            report = root / "report.json"

            def check_command(args, **kwargs):
                self.assertIn("--exercise-controls", args)
                return CompletedProcess(args, -11, stdout="native crash")

            with patch("tools.probe_gamecube_homebrew.verified_homebrew",
                       side_effect=make_fixture), patch(
                           "tools.probe_gamecube_homebrew.subprocess.run",
                           side_effect=check_command):
                self.assertEqual(
                    _parent(core, 1, report, cpu_core="5",
                            exercise_controls=True), 1
                )
            self.assertTrue(json.loads(report.read_text())[
                "controller_input_exercised"
            ])

    def test_native_debugger_keeps_gdb_failure_evidence(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            core = root / "dolphin_libretro.so"
            core.write_bytes(b"synthetic")
            report = root / "report.json"

            def fake_gdb(args, **kwargs):
                self.assertEqual(args[0], "/usr/bin/gdb")
                self.assertIn("thread apply all bt 24", args)
                return CompletedProcess(args, 0, stdout="#0 fatal_native_frame()")

            with patch("tools.probe_gamecube_homebrew.verified_homebrew",
                       side_effect=make_fixture), patch(
                           "tools.probe_gamecube_homebrew.shutil.which",
                           return_value="/usr/bin/gdb",
                       ), patch("tools.probe_gamecube_homebrew.subprocess.run",
                                side_effect=fake_gdb):
                # gdb exits successfully after printing a crash stack; that
                # must never count as successful software-rendered gameplay.
                self.assertEqual(_parent(core, 1, report, debugger=True), 1)
            evidence = json.loads(report.read_text())
            self.assertEqual(evidence["debugger"], "gdb")
            self.assertIn("fatal_native_frame", evidence["console_tail"])
            self.assertFalse(evidence["probe_passed"])

    def test_missing_core_fails_without_downloading_anything(self):
        with TemporaryDirectory() as folder:
            report = Path(folder) / "missing.json"
            with patch("tools.probe_gamecube_homebrew.verified_homebrew") as net:
                self.assertEqual(
                    main(["--core", str(Path(folder) / "missing.dylib"),
                          "--seconds", "1", "--report", str(report)]),
                    1,
                )
                net.assert_not_called()
            self.assertIn("missing", json.loads(report.read_text())["error"])


if __name__ == "__main__":
    unittest.main()
