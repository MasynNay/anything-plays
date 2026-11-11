"""Nonrelease RC2 installed-Tk acceptance validators and adversarial fixtures."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from anything_plays.build_identity import make_identity
from tools.qa_v31_rc2_installed_preferences import seed, verify
from tools.verify_v31_rc2_installed_ui import (
    FILENAMES, SMOKE_STATUS, hash_file, verify_installed_rc2,
)
from tools.v31_rc2_source import FULL_STATUS

COMMIT = "a" * 40
SMOKE = {
    "status": SMOKE_STATUS,
    "passed": True,
    "actual_tk_window_started": True,
    "actual_app_initialized": True,
    "actual_tk_mainloop_ran": True,
    "frozen_binary": True,
    "console_profile_count": 18,
    "top_level_widgets": 1,
    "initialized_system": "gba",
    "error": None,
    "camera_hardware_tested": False,
    "gameplay_hardware_tested": False,
    "physical_qa_approved": False,
    "public_distribution_approved": False,
}


class InstalledRc2Tests(unittest.TestCase):
    def sample(self, root, target="linux-x64"):
        root = Path(root)
        installer = root / FILENAMES[target]
        installer.write_bytes(b"synthetic-native-installer" * 50000)
        app = root / "app"
        identity = app / "assets/v31_build_identity.json"
        identity.parent.mkdir(parents=True)
        identity.write_text(json.dumps(make_identity("rc2")), "utf-8")
        receipt = {
            "status": FULL_STATUS,
            "target": target,
            "installer": installer.name,
            "sha256": hash_file(installer),
            "source_preview_revision": COMMIT,
            "identity_channel": "rc2",
            "settings_namespace": "anything-plays-31-rc2",
            "native_core_count": 11,
            "console_profiles": 18,
            "public_release_approved": False,
            "final_release_approved": False,
        }
        return installer, app, receipt

    def test_rc2_receipt_and_real_smoke_evidence_are_fail_closed(self):
        with TemporaryDirectory() as tmp:
            installer, app, receipt = self.sample(tmp)
            good = verify_installed_rc2(
                "linux-x64", installer, app, receipt, dict(SMOKE), COMMIT,
            )
            self.assertEqual(good["console_profiles"], 18)
            self.assertEqual(good["native_core_count"], 11)
            self.assertEqual(good["source_revision"], COMMIT)
            self.assertFalse(good["public_release_approved"])
            for field, bad in (
                ("status", "APPROVED"),
                ("source_preview_revision", "b" * 40),
                ("identity_channel", "rc1"),
                ("settings_namespace", "anything-plays-31-rc1"),
                ("native_core_count", 3),
                ("console_profiles", 3),
                ("public_release_approved", True),
                ("final_release_approved", True),
                ("sha256", "b" * 64),
            ):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    verify_installed_rc2(
                        "linux-x64", installer, app,
                        dict(receipt, **{field: bad}), dict(SMOKE), COMMIT,
                    )
            for field, bad in (
                ("passed", False), ("actual_tk_window_started", False),
                ("actual_tk_mainloop_ran", False),
                ("frozen_binary", False), ("console_profile_count", 3),
                ("public_distribution_approved", True),
                ("physical_qa_approved", True),
                ("error", "fake error"), ("top_level_widgets", 0),
            ):
                with self.subTest(smoke=field), self.assertRaises(ValueError):
                    verify_installed_rc2(
                        "linux-x64", installer, app, receipt,
                        dict(SMOKE, **{field: bad}), COMMIT,
                    )
            with self.assertRaises(ValueError):
                verify_installed_rc2("linux-x64", installer, app, receipt, SMOKE, "bad")
            installer.write_bytes(installer.read_bytes() + b"tampered")
            with self.assertRaises(ValueError):
                verify_installed_rc2("linux-x64", installer, app, receipt, SMOKE, COMMIT)

    def test_platform_filenames_and_rc1_identity_are_not_accepted(self):
        self.assertEqual(set(FILENAMES), {
            "linux-x64", "windows-x64", "macos-arm64", "macos-x64",
        })
        self.assertTrue(all("rc2" in name for name in FILENAMES.values()))
        with TemporaryDirectory() as tmp:
            installer, app, receipt = self.sample(tmp)
            marker = app / "assets/v31_build_identity.json"
            marker.write_text(json.dumps(make_identity("rc1")), "utf-8")
            with self.assertRaises(ValueError):
                verify_installed_rc2("linux-x64", installer, app, receipt, SMOKE, COMMIT)
            marker.write_text(json.dumps(make_identity("rc2")), "utf-8")
            with self.assertRaises(ValueError):
                verify_installed_rc2("windows-x64", installer, app, receipt, SMOKE, COMMIT)

    def test_fixture_seeds_rc1_and_stable_and_confirms_atomic_import(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "newhome"
            home.mkdir()
            manifest = root / "fixture.json"
            seed(home, manifest=manifest)
            from anything_plays.test_preferences import prepare_test_preferences
            prepare_test_preferences(home, channel="rc2")
            profile = home / ".config/anything-plays-31-rc2/system_profiles.json"
            profile.write_text(json.dumps({"gba": {"zones": {}}}), "utf-8")
            evidence = verify(home, manifest=manifest)
            self.assertTrue(evidence["stable_preferences_and_profiles_unchanged"])
            self.assertTrue(evidence["rc1_preferences_and_profiles_unchanged"])
            self.assertEqual(evidence["rc2_theme"], "Plum Dark")
            self.assertFalse(evidence["public_release_approved"])
            with self.assertRaises(ValueError):
                seed(home, manifest=manifest)
            stable = home / ".config/fish-plays-pokemon-studio/preferences.json"
            stable.write_text('{"theme":"tampered"}', "utf-8")
            with self.assertRaises(ValueError):
                verify(home, manifest=manifest)

    def test_symlinks_to_rc1_or_stable_are_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "h"
            home.mkdir()
            manifest = root / "evidence.json"
            seed(home, manifest=manifest)
            rc2 = home / ".config/anything-plays-31-rc2"
            rc2.mkdir()
            source = home / ".config/anything-plays-31-rc1/preferences.json"
            try:
                (rc2 / "preferences.json").symlink_to(source)
            except (OSError, NotImplementedError):
                self.skipTest("No symlink support in fixture filesystem")
            with self.assertRaises(ValueError):
                verify(home, manifest=manifest)


if __name__ == "__main__":
    unittest.main()
