"""Native ABI and core search tests that require no camera or ROM."""

import ctypes
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core_locator import find_core
from libretro_abi import AVInfo, CoreInfo, GameInfo, Geometry, Timing


class LibretroBoundaryTests(unittest.TestCase):
    def test_native_structures_have_expected_fields(self):
        self.assertEqual([name for name, _ in GameInfo._fields_],
                         ['path', 'data', 'size', 'meta'])
        self.assertEqual([name for name, _ in CoreInfo._fields_],
                         ['library_name', 'library_version', 'valid_extensions',
                          'need_fullpath', 'block_extract'])
        self.assertEqual([name for name, _ in AVInfo._fields_],
                         ['geometry', 'timing'])
        self.assertGreaterEqual(ctypes.sizeof(AVInfo),
                                ctypes.sizeof(Geometry) + ctypes.sizeof(Timing))

    def test_system_core_mapping_is_preserved(self):
        from systems import SYSTEMS
        self.assertEqual(SYSTEMS['gb'].core, SYSTEMS['gbc'].core)
        self.assertEqual(SYSTEMS['gba'].core, 'mgba')
        self.assertEqual(SYSTEMS['snes'].core, 'snes9x')

    def test_missing_core_returns_none(self):
        with patch('pathlib.Path.is_file', return_value=False):
            self.assertIsNone(find_core('snes'))

    def test_unknown_system_raises_key_error(self):
        with self.assertRaises(KeyError):
            find_core('unknown')


if __name__ == '__main__':
    unittest.main()
