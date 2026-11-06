"""Check real mGBA Libretro extension support without distributing game ROMs.

Run explicitly with AP_TEST_NATIVE_CORE=1 after downloading an mGBA core.
Ordinary unit tests skip this external-binary check.
"""

import ctypes as C
import os
from pathlib import Path
import unittest

from anything_plays.core_locator import find_core
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


if __name__ == "__main__":
    unittest.main()
