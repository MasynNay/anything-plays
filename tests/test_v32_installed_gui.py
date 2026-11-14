"""Contract for the real frozen 3.2 UI acceptance on every native runner.

Synthetic JSON and disposable directories only. Never launches a GUI, reads
the current user's settings or reports a passing physical-device test.
"""

from pathlib import Path
import json
import tempfile
import unittest

from tools.verify_v32_installed_gui import (
    REQUIRED_FALSE, REQUIRED_TRUE, STABLE_FILES, seed, verify,
)


def passing_report():
    return {
        **{name: True for name in REQUIRED_TRUE},
        **{name: False for name in REQUIRED_FALSE},
        "error": None,
        "v32_settings_namespace": "anything-plays-32-preview",
        "console_profile_count": 18,
        "v32_setup_dialog_count": 40,
        "v32_setup_repeat_cycles": 8,
        "initialized_system": "gba",
    }


class V32InstalledGuiAcceptanceTests(unittest.TestCase):
    def fixture(self, base):
        home = base / "home"
        seed(home)
        private = home / ".config" / "anything-plays-32-preview"
        private.mkdir()
        (private / "system_profiles.json").write_text(
            json.dumps({"gba": {"mapping": {}}}) + "\n",
            encoding="utf-8",
        )
        report = base / "frozen-gui-report.json"
        report.write_text(json.dumps(passing_report()), encoding="utf-8")
        return home, report

    def test_passes_a_real_frozen_report_shape_and_unchanged_stable_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, report = self.fixture(Path(tmp))
            result = verify(report, home)
            self.assertTrue(result["installed_frozen_preview"])
            self.assertTrue(result["stable_settings_unchanged"])
            self.assertTrue(result["five_native_setup_windows_verified"])
            self.assertEqual(result["native_dialog_roundtrips_verified"], 40)
            self.assertEqual(result["repeated_native_setup_cycles_verified"], 8)
            self.assertFalse(result["camera_hardware_tested"])
            self.assertFalse(result["public_release_approved"])

    def test_seed_refuses_ever_to_overwrite_existing_home_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            seed(home)
            file = home / ".config" / "anything-plays-31" / "preferences.json"
            file.write_bytes(b"existing user data")
            with self.assertRaisesRegex(ValueError, "already exist"):
                seed(home)
            self.assertEqual(file.read_bytes(), b"existing user data")

    def test_public_settings_canary_change_fails_the_installed_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, report = self.fixture(Path(tmp))
            for file in STABLE_FILES:
                with self.subTest(file=file):
                    path = home / ".config" / "anything-plays-31" / file
                    original = path.read_bytes()
                    path.write_bytes(b"changed by candidate")
                    with self.assertRaisesRegex(ValueError, "changed public"):
                        verify(report, home)
                    path.write_bytes(original)

    def test_false_frozen_approval_or_missing_tk_event_loop_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, report = self.fixture(Path(tmp))
            baseline = passing_report()
            for key, value in (
                ("passed", False),
                ("actual_tk_mainloop_ran", False),
                ("frozen_binary", False),
                ("v32_frozen_isolation_verified", False),
                ("camera_hardware_tested", True),
                ("public_distribution_approved", True),
                ("v32_settings_namespace", "anything-plays-31"),
                ("console_profile_count", 1),
                ("v32_setup_dialog_count", 39),
                ("v32_setup_repeat_cycles", 7),
                ("v32_setup_no_orphan_windows", False),
                ("v32_setup_theme_traces_stable", False),
                ("v32_setup_camera_untouched", False),
                ("v32_setup_gamepad_untouched", False),
                ("v32_setup_still_disarmed", False),
                ("initialized_system", "snes"),
                ("error", "frozen app startup failed"),
            ):
                with self.subTest(key=key):
                    modified = dict(baseline, **{key: value})
                    report.write_text(json.dumps(modified), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        verify(report, home)

    def test_missing_private_profiles_cannot_be_mistaken_for_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, report = self.fixture(Path(tmp))
            profiles = (home / ".config" / "anything-plays-32-preview"
                        / "system_profiles.json")
            profiles.unlink()
            with self.assertRaisesRegex(ValueError, "its own safe"):
                verify(report, home)

    def test_symlinked_frozen_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home, report = self.fixture(base)
            linked = base / "linked.json"
            try:
                linked.symlink_to(report)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable on this runner")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                verify(linked, home)


if __name__ == "__main__":
    unittest.main()
