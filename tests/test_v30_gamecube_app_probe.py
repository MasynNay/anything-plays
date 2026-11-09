"""App GameCube probe must never confuse an isolated native crash with success."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import CompletedProcess
from unittest import TestCase
from unittest.mock import patch
from tools.probe_gamecube_app import _parent


class ProductionGameCubeProbeTests(TestCase):
    def test_native_probe_tracks_synchronous_gpu_readback_overhead(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        production = (root / "anything_plays/gamecube_gpu.py").read_text("utf-8")
        diagnostic = (root / "tools/probe_gamecube_app.py").read_text("utf-8")
        self.assertIn("gpu_readback_seconds", production)
        self.assertIn("gpu_readback_max_seconds", production)
        self.assertIn("time.perf_counter()", production)
        for field in ("gpu_readback_calls", "gpu_readback_total_seconds",
                      "gpu_readback_mean_ms", "gpu_readback_max_ms",
                      "gpu_readback_fraction_elapsed"):
            self.assertIn(field, diagnostic)

    def test_endurance_probe_reports_real_native_rss_growth(self):
        source = (Path(__file__).resolve().parents[1] /
                  "tools/probe_gamecube_app.py").read_text("utf-8")
        for value in ("linux_rss_mb", "native_rss_growth_mb",
                      "native_rss_growth_verified", "and memory_ok",
                      "--max-growth-mb"):
            self.assertIn(value, source)
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/v30-endurance.yml").read_text("utf-8")
        self.assertIn("--seconds 600", workflow)
        self.assertIn("--max-growth-mb 192", workflow)
        self.assertIn("--seconds 900", workflow)

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
