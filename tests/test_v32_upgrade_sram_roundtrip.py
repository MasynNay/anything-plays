"""3.2 frozen stable cartridge SRAM continuity, without a native ROM/core."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.build_identity import make_identity
from anything_plays.v32_sram_fixture import ROM_FOLDER, ROM_NAME, ROM_CANARY, OLD_SRAM, NEW_SRAM
from anything_plays.v32_upgrade_sram_smoke import exercise_installed_stable_sram
from tools.v32_stable_data_rehearsal import seed, verify


class DummyPad:
    api = None


class DummyApp:
    armed = False
    cap = None
    current_rom = None
    _gamepad = DummyPad()


class SaveTransitionTests(unittest.TestCase):
    def exercise(self, home):
        identity = make_identity("v32_stable_candidate")
        with (
            patch.object(Path, "home", return_value=Path(home)),
            patch.object(sys, "frozen", True, create=True),
            patch("anything_plays.v32_upgrade_sram_smoke.current_identity", return_value=identity),
            patch("anything_plays.preview_storage.current_identity", return_value=identity),
        ):
            return exercise_installed_stable_sram(DummyApp())

    def report(self, root, accepted):
        report = Path(root) / "frozen.json"
        report.write_text(json.dumps({
            "passed": True, "actual_tk_window_started": True,
            "actual_app_initialized": True, "actual_tk_mainloop_ran": True,
            "frozen_binary": True, "initialized_system": "gba",
            "console_profile_count": 18, "error": None,
            "public_distribution_approved": False,
            "physical_qa_approved": False, "camera_hardware_tested": False,
            "gameplay_hardware_tested": False,
            "v32_upgrade_sram_roundtrip_verified": accepted,
        }), "utf-8")
        return report

    def test_actual_sram_reads_311_bytes_writes_320_and_cold_restores(self):
        with TemporaryDirectory() as tmp:
            seed(tmp)
            rom = Path(tmp) / ROM_FOLDER / ROM_NAME
            self.assertEqual(rom.with_suffix(".sav").read_bytes(), OLD_SRAM)
            self.assertTrue(self.exercise(tmp))
            self.assertEqual(rom.read_bytes(), ROM_CANARY)
            self.assertEqual(rom.with_suffix(".sav").read_bytes(), NEW_SRAM)
            result = verify(tmp, self.report(tmp, True), require_sram=True)
            self.assertTrue(result["legacy_cartridge_sram_roundtrip_verified"])
            self.assertFalse(result["native_game_core_executed"])
            self.assertFalse(result["stable_upgrade_release_approved"])

    def test_missing_fixture_or_existing_preview_scope_is_rejected(self):
        with TemporaryDirectory() as tmp:
            seed(tmp)
            save = Path(tmp) / ROM_FOLDER / ROM_NAME
            save.with_suffix(".sav").unlink()
            with self.assertRaisesRegex(RuntimeError, "fixture"):
                self.exercise(tmp)

    def test_missing_frozen_sram_marker_is_not_accepted(self):
        with TemporaryDirectory() as tmp:
            seed(tmp)
            with self.assertRaisesRegex(ValueError, "not verified"):
                verify(tmp, self.report(tmp, False), require_sram=True)
            with self.assertRaisesRegex(ValueError, "not verified"):
                verify(tmp, self.report(tmp, None), require_sram=True)

    def test_false_identity_never_touches_old_sram(self):
        with TemporaryDirectory() as tmp:
            seed(tmp)
            identity = make_identity("v32_preview")
            with (
                patch.object(Path, "home", return_value=Path(tmp)),
                patch.object(sys, "frozen", True, create=True),
                patch("anything_plays.v32_upgrade_sram_smoke.current_identity", return_value=identity),
            ):
                with self.assertRaisesRegex(RuntimeError, "frozen private stable"):
                    exercise_installed_stable_sram(DummyApp())
            old = Path(tmp) / ROM_FOLDER / ROM_NAME
            self.assertEqual(old.with_suffix(".sav").read_bytes(), OLD_SRAM)

    def test_no_real_hardware_or_game_can_be_running(self):
        with TemporaryDirectory() as tmp:
            seed(tmp)
            active = DummyApp()
            active.armed = True
            identity = make_identity("v32_stable_candidate")
            with (
                patch.object(sys, "frozen", True, create=True),
                patch("anything_plays.v32_upgrade_sram_smoke.current_identity", return_value=identity),
            ):
                with self.assertRaisesRegex(RuntimeError, "devices or a game"):
                    exercise_installed_stable_sram(active)


if __name__ == "__main__":
    unittest.main()
