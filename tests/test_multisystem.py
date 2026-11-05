"""Regression tests for v2 bundled-core integration (no ROMs required)."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MultiSystemContracts(unittest.TestCase):
    def test_supported_systems_and_extensions(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from systems import SYSTEMS
        self.assertEqual(set(SYSTEMS), {'gb', 'gbc', 'gba', 'snes'})
        self.assertEqual(SYSTEMS['gb'].core, SYSTEMS['gbc'].core)
        self.assertEqual(SYSTEMS['gba'].core, 'mgba')
        self.assertEqual(SYSTEMS['snes'].core, 'snes9x')

    def test_snes_button_ids(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from gba_emulator import BUTTONS, IDS
        for name in ('X', 'Y', 'L', 'R'):
            self.assertIn(name, BUTTONS)
            self.assertIn(name, IDS)

    def test_every_platform_bundles_all_cores(self):
        for filename in ('build_windows.bat', 'build_macos_dmg.sh', 'build_linux_deb.sh'):
            script = (ROOT / filename).read_text()
            for name in ('gambatte', 'mgba', 'snes9x'):
                with self.subTest(script=filename, core=name):
                    self.assertIn(name, script)
        fetcher = (ROOT / 'fetch_mgba_core.py').read_text()
        self.assertIn('CORE_NAMES = ("gambatte", "mgba", "snes9x")', fetcher)

    def test_no_manual_core_selection_button(self):
        source = (ROOT / 'app.py').read_text()
        self.assertNotIn("text='Select emulator core (optional)'", source)


if __name__ == '__main__':
    unittest.main()
