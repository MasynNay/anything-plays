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
        self.assertIn("received signal", source)
        self.assertIn('"native_fault_trace"', source)
        self.assertIn('"native_faulted"', source)
        self.assertIn("not result.get(\"native_faulted\", False)", source)
        self.assertIn("timeout=seconds + 25", source)

    def test_original_genesis_test_cart_has_safe_supervisor_stack(self):
        from tools.genesis_homebrew_fixture import build_genesis_probe_rom
        rom = build_genesis_probe_rom()
        self.assertEqual(len(rom), 64 * 1024)
        sp = int.from_bytes(rom[:4], "big")
        self.assertGreaterEqual(sp, 0x00FFF000)
        self.assertLess(sp, 0x01000000)
        self.assertEqual(sp % 2, 0)
        self.assertEqual(int.from_bytes(rom[4:8], "big"), 0x200)

    def test_ci_reruns_failed_genesis_under_gdb(self):
        source = (ROOT / ".github/workflows/v30-lab.yml").read_text("utf-8")
        block = source.split("  genesis-original-homebrew-video-audio-experiment:", 1)[1].split(
            "  gamecube-cross-platform-gpu:", 1
        )[0]
        self.assertIn("gdb libgl1", block)
        self.assertIn("probe_genesis_homebrew.py --debugger", block)


if __name__ == "__main__":
    unittest.main()
