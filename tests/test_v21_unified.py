"""2.1 integrated feature regressions with no commercial game images."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

import cv2
import numpy as np

from anything_plays.external_emulators import (
    ExternalLaunchError, command_for, launch,
)
from anything_plays.libretro_input import GENESIS_IDS, IDS, InputBuffer
from anything_plays.shortcuts import (
    DEFAULT_KEYS, RESERVED_KEYS, button_for_key, normalize_bindings,
    rebind,
)
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM, default_for
from anything_plays.systems import SYSTEMS
from anything_plays.zone_rendering import render_zone_overlay
from fetch_mgba_core import CORE_NAMES, OPTIONAL_V21_CORES, core_names_for_build


class UnifiedV21Tests(unittest.TestCase):
    def test_eight_console_libraries_and_external_modes(self):
        self.assertEqual(len(SYSTEMS), 8)
        self.assertEqual([SYSTEMS[s].backend for s in ('nes', 'genesis')],
                         ['libretro', 'libretro'])
        self.assertEqual([SYSTEMS[s].backend for s in ('n64', 'gamecube')],
                         ['retroarch', 'dolphin'])
        for system in SYSTEMS:
            self.assertEqual(len(default_for(system, {'zones': {}, 'mapping': {}})['mapping']),
                             len(BUTTONS_BY_SYSTEM[system]))

    def test_default_and_custom_key_bindings(self):
        keys = normalize_bindings('snes')
        self.assertEqual(button_for_key('snes', keys, 'z'), 'A')
        new = rebind('snes', keys, 'A', 'v')
        self.assertEqual(button_for_key('snes', new, 'v'), 'A')
        self.assertIsNone(button_for_key('snes', new, 'z'))
        self.assertEqual(button_for_key('snes', keys, 'z'), 'A')
        with self.assertRaisesRegex(ValueError, 'already assigned'):
            rebind('snes', new, 'B', 'v')
        for forbidden in RESERVED_KEYS:
            with self.assertRaisesRegex(ValueError, 'reserved'):
                rebind('snes', new, 'B', forbidden)
        self.assertEqual(normalize_bindings('snes', {'A': 'Escape'})['A'],
                         DEFAULT_KEYS['A'])

    def test_genesis_six_button_c_and_mode_are_independent(self):
        expected = {'A': IDS['Y'], 'B': IDS['B'], 'C': IDS['A'],
                    'X': IDS['L'], 'Y': IDS['X'], 'Z': IDS['R'],
                    'Mode': IDS['Select']}
        for key, joypad in expected.items():
            self.assertEqual(GENESIS_IDS[key], joypad)
        input_buffer = InputBuffer()
        input_buffer.system = 'genesis'
        input_buffer.queue_press('C', 2)
        input_buffer.set_manual('Z', True)
        input_buffer.before_frame(armed=True)
        self.assertEqual(input_buffer.state(0, 1, 0, GENESIS_IDS['C']), 1)
        self.assertEqual(input_buffer.state(0, 1, 0, GENESIS_IDS['Z']), 1)
        input_buffer.after_frame()
        input_buffer.release_manual()
        input_buffer.before_frame(armed=False)
        self.assertEqual(input_buffer.state(0, 1, 0, GENESIS_IDS['Z']), 0)
        input_buffer.system = 'gba'
        self.assertEqual(input_buffer.id_for('A'), IDS['A'])

    def test_external_launcher_no_shell_or_implicit_download(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            retro = root / 'retroarch'
            dolphin = root / 'dolphin'
            native = root / 'mupen64plus_next_libretro.so'
            n64 = root / 'A game.z64'
            gamecube = root / 'Another game.rvz'
            for path in (retro, dolphin, native, n64, gamecube):
                path.write_bytes(b'synthetic test file')
            n64_command = command_for('n64', n64, executable=retro,
                                       n64_core=native, fullscreen=True)
            self.assertEqual(n64_command[0], str(retro))
            self.assertIn('-L', n64_command)
            self.assertIn('--fullscreen', n64_command)
            self.assertEqual(n64_command[-1], str(n64))
            gc = command_for('gamecube', gamecube, executable=dolphin)
            self.assertEqual(gc, [str(dolphin), '--batch', '--exec=' + str(gamecube)])
            gc_full = command_for('gamecube', gamecube, executable=dolphin,
                                  fullscreen=True)
            self.assertIn('--config=Dolphin.Display.Fullscreen=True', gc_full)
            gc_borderless = command_for('gamecube', gamecube, executable=dolphin,
                                        borderless=True)
            self.assertIn('--config=Graphics.Settings.BorderlessFullscreen=True',
                          gc_borderless)
            self.assertNotIn('--config=Graphics.Settings.BorderlessFullscreen=True',
                             gc_full)
            with patch('anything_plays.external_emulators.subprocess.Popen') as popen:
                launch('n64', n64, executable=retro, n64_core=native)
                self.assertEqual(popen.call_args.kwargs['shell'], False)
            with self.assertRaisesRegex(ExternalLaunchError, 'compatible'):
                command_for('gamecube', n64, executable=dolphin)
            with self.assertRaisesRegex(ExternalLaunchError, 'Mupen64Plus'):
                command_for('n64', n64, executable=retro, n64_core=root/'missing.so')

    def test_extra_cores_only_allowed_for_private_test(self):
        self.assertEqual(CORE_NAMES, ('mgba', 'snes9x'))
        with patch.dict(os.environ, {'AP_V21_TEST_CORES': '1', 'AP_RELEASE_BUILD': '0'}):
            self.assertEqual(core_names_for_build(), (*CORE_NAMES, *OPTIONAL_V21_CORES))
        with patch.dict(os.environ, {'AP_V21_TEST_CORES': '1', 'AP_RELEASE_BUILD': '1'}):
            with self.assertRaisesRegex(ValueError, 'Unapproved 2.1'):
                core_names_for_build()

    def test_bolder_centered_overlay_does_not_affect_camera_pixels(self):
        frame = np.zeros((160, 240, 3), dtype=np.uint8)
        frame[:] = (30, 38, 44)
        original = frame.copy()
        result = render_zone_overlay(
            frame, {'A': [0.1, 0.15, 0.85, 0.9]},
            {'A': 'A'}, 'A', opacity=93, size=32, style='Bold',
            label_position='Center', border_width=10,
        )
        self.assertTrue(np.array_equal(frame, original))
        self.assertEqual(result.shape, frame.shape)
        self.assertFalse(np.array_equal(result, frame))
        self.assertTrue((result[:, :, 1] > 180).any())


if __name__ == '__main__':
    unittest.main()
