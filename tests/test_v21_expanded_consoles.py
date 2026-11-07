"""Expanded 2.1 consoles must use bundled cores, not external emulators."""
import unittest

from anything_plays.systems import SYSTEMS
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM
from anything_plays.libretro_input import InputBuffer
from fetch_mgba_core import OPTIONAL_V21_CORES, SOURCE_REPOSITORIES
from anything_plays.emulator_updates import UPSTREAM_REPOS, DISPLAY_NAMES


class ExpandedConsoleInventory(unittest.TestCase):
    def test_eighteen_libraries_have_valid_core_and_control_entries(self):
        self.assertEqual(len(SYSTEMS), 18)
        for key in ("mastersystem", "gamegear", "sg1000"):
            self.assertEqual(SYSTEMS[key].core, "genesis_plus_gx")
        for key, core in {
            "atari2600": "stella2014", "atari7800": "prosystem",
            "pce": "mednafen_pce_fast", "ngp": "mednafen_ngp",
            "ngpc": "mednafen_ngp", "ws": "mednafen_wswan",
            "wsc": "mednafen_wswan",
        }.items():
            self.assertEqual(SYSTEMS[key].core, core)
            self.assertIn(core, OPTIONAL_V21_CORES)
        for item in SYSTEMS.values():
            # The legacy N64 system metadata intentionally names a
            # developer-only RetroArch fallback, while the installed app's
            # real in-panel core is ParaLLEl-N64.
            core = "parallel_n64" if item.key == "n64" else item.core
            self.assertIn(core, SOURCE_REPOSITORIES)
            self.assertIn(core, UPSTREAM_REPOS)
            self.assertIn(core, DISPLAY_NAMES)
            self.assertIn(item.key, BUTTONS_BY_SYSTEM)
            if item.key not in ("n64", "gamecube"):
                self.assertEqual(item.backend, "libretro")
            self.assertTrue(item.extensions)

    def test_sega_reuses_same_core_without_separate_download(self):
        self.assertEqual(SYSTEMS["mastersystem"].extensions, (".sms", ".bms"))
        self.assertEqual(SYSTEMS["gamegear"].extensions, (".gg",))
        self.assertEqual(SYSTEMS["sg1000"].extensions, (".sg",))
        names = {SYSTEMS[name].core for name in ("genesis", "mastersystem", "gamegear", "sg1000")}
        self.assertEqual(names, {"genesis_plus_gx"})
        for key in ("mastersystem", "gamegear", "sg1000", "atari2600", "pce"):
            controller = InputBuffer()
            controller.system = key
            self.assertIsNotNone(controller.id_for("A"))
            self.assertIsNotNone(controller.id_for("Start"))


if __name__ == "__main__":
    unittest.main()
