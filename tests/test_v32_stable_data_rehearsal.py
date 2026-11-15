"""Stable 3.1.1 -> 3.2 synthetic preservation contract, no Tk or hardware."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.v32_stable_data_rehearsal import (
    NAMESPACE, PREFERENCES, SAVE_CANARY, seed, verify,
)


class StableDataTests(unittest.TestCase):
    def report(self, home):
        path = Path(home) / "smoke.json"
        path.write_text(json.dumps({
            "passed": True, "actual_tk_window_started": True,
            "actual_app_initialized": True, "actual_tk_mainloop_ran": True,
            "frozen_binary": True,
            "public_distribution_approved": False,
            "physical_qa_approved": False,
            "camera_hardware_tested": False,
            "gameplay_hardware_tested": False,
            "initialized_system": "gba", "console_profile_count": 18,
            "error": None,
        }), "utf-8")
        return path

    def test_existing_stable_settings_and_save_pass_unchanged(self):
        with TemporaryDirectory() as td:
            root = seed(td)
            report = self.report(td)
            status = verify(td, report)
            self.assertTrue(status["old_save_canary_byte_identical"])
            self.assertFalse(status["stable_upgrade_release_approved"])
            self.assertEqual(
                json.loads((root / "preferences.json").read_text("utf-8")),
                PREFERENCES,
            )

    def test_seed_never_overwrites_existing_stable_profile(self):
        with TemporaryDirectory() as td:
            root = seed(td)
            source = (root / "preferences.json").read_bytes()
            with self.assertRaises(ValueError):
                seed(td)
            self.assertEqual((root / "preferences.json").read_bytes(), source)

    def test_missing_or_replaced_settings_fail(self):
        with TemporaryDirectory() as td:
            root = seed(td)
            report = self.report(td)
            original = json.loads((root / "preferences.json").read_text("utf-8"))
            original["rom_directories"]["gba"] = ""
            (root / "preferences.json").write_text(json.dumps(original), "utf-8")
            with self.assertRaisesRegex(ValueError, "rom_directories"):
                verify(td, report)

    def test_changed_profile_or_save_cannot_pass(self):
        with TemporaryDirectory() as td:
            root = seed(td)
            report = self.report(td)
            profiles = json.loads((root / "system_profiles.json").read_text("utf-8"))
            profiles["gba"]["tolerance"] = 10
            (root / "system_profiles.json").write_text(json.dumps(profiles), "utf-8")
            with self.assertRaisesRegex(ValueError, "GBA control profile"):
                verify(td, report)
            profiles["gba"]["tolerance"] = 61
            (root / "system_profiles.json").write_text(json.dumps(profiles), "utf-8")
            (root / "synthetic-existing.sav").write_bytes(b"changed" + SAVE_CANARY)
            with self.assertRaisesRegex(ValueError, "saved-game canary"):
                verify(td, report)

    def test_preview_namespace_and_forged_success_are_rejected(self):
        with TemporaryDirectory() as td:
            seed(td)
            report = self.report(td)
            (Path(td) / ".config" / "anything-plays-32-preview").mkdir()
            with self.assertRaisesRegex(ValueError, "preview settings"):
                verify(td, report)
            (Path(td) / ".config" / "anything-plays-32-preview").rmdir()
            raw = json.loads(report.read_text("utf-8"))
            raw["physical_qa_approved"] = True
            report.write_text(json.dumps(raw), "utf-8")
            with self.assertRaisesRegex(ValueError, "hardware"):
                verify(td, report)


if __name__ == "__main__":
    unittest.main()
