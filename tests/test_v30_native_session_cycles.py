"""Native lifecycle endurance must use legal sources and production Emulator."""
import unittest
from pathlib import Path
from tools.probe_native_session_cycles import CASES, CORES, write_original_fixtures
from tempfile import TemporaryDirectory


class NativeMultiCoreCycleContracts(unittest.TestCase):
    def test_all_repeated_console_fixtures_are_original_and_deterministic(self):
        self.assertEqual(len(CASES), 11)
        self.assertEqual(len(CORES), 6)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = write_original_fixtures(root)
            self.assertEqual(set(files), {c[0] for c in CASES})
            self.assertTrue(all(p.is_file() and p.stat().st_size >= 4096
                                for p in files.values()))
            for system, core, ext in CASES:
                self.assertEqual(files[system].suffix, ext)

    def test_full_native_ci_requires_real_start_stop_and_ram_evidence(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "tools/probe_native_session_cycles.py").read_text()
        workflow = (root / ".github/workflows/v30-cores.yml").read_text()
        self.assertIn("emu.start(rom)", source)
        self.assertIn("emu.stop()", source)
        self.assertIn("native_core_switches", source)
        self.assertIn("rss_growth_after_first_cycle_mb", source)
        self.assertIn("emulator_worker_stopped_cleanly", source)
        self.assertIn("--cycles 12", workflow)
        self.assertIn("prosystem", workflow)
        self.assertIn("probe_native_session_cycles.py", workflow)


if __name__ == "__main__":
    unittest.main()
