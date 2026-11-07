"""App GameCube probe must never confuse an isolated native crash with success."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import CompletedProcess
from unittest import TestCase
from unittest.mock import patch
from tools.probe_gamecube_app import _parent


class ProductionGameCubeProbeTests(TestCase):
    def test_native_crash_is_reported_without_marking_embedded_playback_ready(self):
        with TemporaryDirectory() as root:
            folder = Path(root)
            core = folder / "dolphin_libretro.so"
            core.write_bytes(b"synthetic")
            report = folder / "report.json"
            def fixture(path):
                path.write_bytes(b"synthetic test")
                return path
            with patch("tools.probe_gamecube_app.verified_homebrew",
                       side_effect=fixture), patch(
                        "tools.probe_gamecube_app.subprocess.run",
                        return_value=CompletedProcess([], -11, stdout="native segfault")):
                self.assertEqual(_parent(core, report, 2), 1)
            saved = json.loads(report.read_text())
            self.assertEqual(saved["native_exit_code"], -11)
            self.assertFalse(saved["passed"])
            self.assertIsNone(saved["details"])

    def test_positive_evidence_requires_successful_child_exit(self):
        with TemporaryDirectory() as root:
            folder = Path(root)
            core = folder / "dolphin_libretro.so"
            core.write_bytes(b"synthetic")
            report = folder / "report.json"
            def fixture(path):
                path.write_bytes(b"synthetic test")
                return path
            def child(args, **kwargs):
                path = Path(args[args.index("--report") + 1])
                path.write_text(json.dumps({"passed": True}))
                self.assertIn("--child", args)
                return CompletedProcess(args, -11, stdout="crashed after video")
            with patch("tools.probe_gamecube_app.verified_homebrew",
                       side_effect=fixture), patch(
                        "tools.probe_gamecube_app.subprocess.run",
                        side_effect=child):
                self.assertEqual(_parent(core, report, 2), 1)
            self.assertFalse(json.loads(report.read_text())["passed"])
