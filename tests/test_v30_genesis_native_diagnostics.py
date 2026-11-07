"""Keep a native Genesis debugger trace when an original homebrew ROM faults."""
import inspect
import unittest
from pathlib import Path
from tools import probe_genesis_homebrew

ROOT = Path(__file__).resolve().parents[1]


class GenesisNativeDiagnosticsTests(unittest.TestCase):
    def test_isolated_crash_probe_preserves_native_trace(self):
        source = inspect.getsource(probe_genesis_homebrew._parent)
        self.assertIn('shutil.which("gdb")', source)
        self.assertIn("Program received signal", source)
        self.assertIn('"native_fault_trace"', source)
        self.assertIn("timeout=seconds + 25", source)

    def test_ci_reruns_failed_genesis_under_gdb(self):
        source = (ROOT / ".github/workflows/v30-lab.yml").read_text("utf-8")
        block = source.split("  genesis-original-homebrew-video-audio-experiment:", 1)[1].split(
            "  gamecube-cross-platform-gpu:", 1
        )[0]
        self.assertIn("gdb libgl1", block)
        self.assertIn("probe_genesis_homebrew.py --debugger", block)


if __name__ == "__main__":
    unittest.main()
