"""Experimental in-panel N64 contracts, tested without copyrighted games.

A unit test can verify dispatch and native ABI response shape; only actual
supported hardware and user-owned ROMs can validate rendering/performance.
"""
import ctypes as C
from pathlib import Path
from unittest.mock import patch
import unittest

from app import App
from anything_plays.gba_emulator import Emulator
from anything_plays.libretro_input import InputBuffer
from anything_plays.n64_software import RetroVariable, SoftwareN64Options


class _Toggle:
    def __init__(self, enabled):
        self.enabled = enabled

    def get(self):
        return self.enabled


class _CurrentSystem:
    def __init__(self, key):
        self.key = key

    def get(self):
        return self.key


class EmbeddedN64Contracts(unittest.TestCase):
    def test_only_n64_is_switchable_from_embedded_to_external(self):
        app = object.__new__(App)
        app.system_key = _CurrentSystem("n64")
        app.n64_embedded = _Toggle(True)
        self.assertTrue(app.uses_embedded_emulator())
        self.assertTrue(app.uses_embedded_emulator("gba"))
        self.assertFalse(app.uses_embedded_emulator("gamecube"))
        app.n64_embedded.enabled = False
        self.assertFalse(app.uses_embedded_emulator("n64"))
        self.assertTrue(app.uses_embedded_emulator("genesis"))

    def test_embedded_n64_selects_parallel_software_core_not_mupen(self):
        emulator = Emulator()
        emulator.system = "n64"
        with patch("anything_plays.gba_emulator.find_parallel_n64_core",
                   return_value="/test/cores/parallel_n64_libretro.dylib"):
            self.assertEqual(
                emulator.find_system_core(),
                "/test/cores/parallel_n64_libretro.dylib",
            )

    def test_software_renderer_refuses_gpu_context_and_exposes_option(self):
        options = SoftwareN64Options()
        self.assertFalse(options.environment(14, None))
        request = RetroVariable()
        request.key = b"parallel-n64-gfxplugin"
        self.assertTrue(options.environment(15, C.addressof(request)))
        self.assertEqual(request.value, b"angrylion")

    def test_apple_silicon_uses_portable_n64_interpreter(self):
        # The N64 alpha must not assume the x86 Ari64 dynarec exists on ARM.
        with patch("anything_plays.n64_software.platform.machine",
                   return_value="arm64"):
            arm = SoftwareN64Options()
        self.assertEqual(
            arm.values[b"parallel-n64-cpucore"], b"Cached Interpreter"
        )
        with patch("anything_plays.n64_software.platform.machine",
                   return_value="x86_64"):
            desktop = SoftwareN64Options()
        self.assertEqual(
            desktop.values[b"parallel-n64-cpucore"],
            b"Dynamic Recompiler (Ari64)",
        )

    def test_n64_analog_stick_is_supported_without_os_keyboard_injection(self):
        inputs = InputBuffer()
        inputs.system = "n64"
        inputs.set_manual("Left", True)
        inputs.set_manual("C Up", True)
        inputs.before_frame(armed=False)
        self.assertLess(inputs.state(0, 5, 0, 0), 0)
        self.assertLess(inputs.state(0, 5, 1, 1), 0)
        inputs.release_manual()
        inputs.before_frame(armed=False)
        self.assertEqual(inputs.state(0, 5, 0, 0), 0)


if __name__ == "__main__":
    unittest.main()
