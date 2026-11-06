"""Check real mGBA Libretro extension support without distributing game ROMs.

Run explicitly with AP_TEST_NATIVE_CORE=1 after downloading an mGBA core.
Ordinary unit tests skip this external-binary check.
"""

import ctypes as C
import os
from pathlib import Path
import tempfile
import time
import unittest

from anything_plays.core_locator import find_core
from anything_plays.gba_emulator import Emulator
from anything_plays.libretro_abi import CoreInfo


@unittest.skipUnless(os.environ.get("AP_TEST_NATIVE_CORE") == "1",
                     "Requires a separately downloaded Libretro mGBA core")
class RealMGBASupport(unittest.TestCase):
    def test_game_boy_color_and_advance_extensions(self):
        paths = {name: find_core(name) for name in ("gb", "gbc", "gba")}
        self.assertTrue(all(paths.values()), "mGBA binary not found")
        self.assertEqual(len(set(paths.values())), 1,
                         "GB, GBC and GBA should use the same mGBA binary")
        path = Path(paths["gba"])
        self.assertIn("mgba", path.name.lower())

        library = C.CDLL(str(path))
        describe = library.retro_get_system_info
        describe.argtypes = [C.POINTER(CoreInfo)]
        describe.restype = None
        info = CoreInfo()
        describe(C.byref(info))
        reported = (info.valid_extensions or b"").decode("utf-8", "replace")
        extensions = {ext.strip(". ").lower() for ext in reported.replace(";", "|").split("|")}
        self.assertTrue({"gb", "gbc", "gba"} <= extensions,
                        f"mGBA core did not advertise GB/GBC/GBA: {reported}")


    def test_game_boy_and_color_render_with_minimal_homebrew_rom(self):
        """Exercise core load and live video without including copyrighted ROMs."""
        with tempfile.TemporaryDirectory(prefix="anything-plays-mgba-") as directory:
            for system in ("gb", "gbc"):
                with self.subTest(system=system):
                    rom = Path(directory) / f"minimal.{system}"
                    payload = bytearray(32768)
                    # A 32 KiB ROM-only image with a valid cartridge header.
                    # Entry at 0100h jumps to a two-byte idle loop at 0150h.
                    payload[0x100:0x104] = b"\x00\xc3\x50\x01"
                    payload[0x134:0x141] = b"ANYTHINGPLAYS"
                    payload[0x143] = 0x80 if system == "gbc" else 0x00
                    payload[0x147] = 0x00  # ROM-only
                    payload[0x148] = 0x00  # 32 KiB
                    payload[0x149] = 0x00  # No cartridge RAM
                    header_check = 0
                    for address in range(0x134, 0x14D):
                        header_check = (header_check - payload[address] - 1) & 0xFF
                    payload[0x14D] = header_check
                    payload[0x150:0x152] = b"\x18\xfe"  # JR -2
                    rom.write_bytes(payload)

                    emulator = Emulator()
                    emulator.system = system
                    emulator.core_path = find_core(system)
                    emulator.start(rom)
                    frame = None
                    try:
                        deadline = time.monotonic() + 5.0
                        while time.monotonic() < deadline:
                            if emulator.error:
                                self.fail(emulator.error)
                            with emulator.lock:
                                frame = emulator.frame
                            if emulator.running and frame is not None:
                                break
                            time.sleep(0.05)
                        self.assertTrue(emulator.running, emulator.error)
                        self.assertIsNotNone(frame, "No video frame received")
                        self.assertEqual(frame.shape[-1], 3)
                    finally:
                        emulator.stop()
                    self.assertIsNone(emulator.error)


if __name__ == "__main__":
    unittest.main()
