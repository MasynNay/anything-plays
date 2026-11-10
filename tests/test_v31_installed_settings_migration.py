"""Real 3.1 settings migration fixture stays disposable and fail-closed."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import unittest

from anything_plays.test_preferences import CANDIDATE_DIR, LEGACY_DIR, prepare_test_preferences
from tools.qa_v31_installed_settings_migration import (
    EXPECTED_THEME, FIXTURE_PREFS, FIXTURE_PROFILES,
    seed_fixture, verify_fixture, STATUS,
)


class FrozenCandidateSettingsSafetyTests(unittest.TestCase):
    def setUp(self):
        self.workspace = TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.home = self.root / "fresh-home"
        self.home.mkdir()
        self.manifest = self.root / "source-snapshot.json"

    def test_full_seed_copy_and_stable_hash_receipt(self):
        seed = seed_fixture(self.home, manifest=self.manifest)
        self.assertEqual(seed["status"], STATUS)
        self.assertFalse(seed["public_release_approved"])
        self.assertEqual((self.home / LEGACY_DIR / "preferences.json").read_bytes(),
                         FIXTURE_PREFS)
        with self.assertRaises(ValueError):
            verify_fixture(self.home, manifest=self.manifest)

        candidate = prepare_test_preferences(self.home, channel="rc1")
        result = verify_fixture(self.home, manifest=self.manifest)
        self.assertEqual(candidate, self.home / CANDIDATE_DIR / "preferences.json")
        self.assertEqual(result["migrated_theme"], EXPECTED_THEME)
        self.assertTrue(result["stable_preferences_unchanged"])
        self.assertTrue(result["stable_profiles_unchanged"])
        self.assertTrue(result["rc_pref_namespace_created"])
        self.assertTrue(result["rc_profile_namespace_created"])
        self.assertFalse(result["public_release_approved"])
        self.assertFalse(result["physical_controller_verified"])
        self.assertEqual((self.home / LEGACY_DIR / "system_profiles.json").read_bytes(),
                         FIXTURE_PROFILES)

    def test_stable_mutation_or_missing_candidate_profile_fails(self):
        seed_fixture(self.home, manifest=self.manifest)
        prepare_test_preferences(self.home, channel="rc1")
        stable = self.home / LEGACY_DIR / "preferences.json"
        stable.write_bytes(b'{"theme":"Changed"}')
        with self.assertRaisesRegex(ValueError, "Stable version"):
            verify_fixture(self.home, manifest=self.manifest)
        stable.write_bytes(FIXTURE_PREFS)
        profile = self.home / CANDIDATE_DIR / "system_profiles.json"
        profile.unlink()
        with self.assertRaises(ValueError):
            verify_fixture(self.home, manifest=self.manifest)

    def test_wrong_candidate_theme_and_forged_manifest_fail(self):
        seed_fixture(self.home, manifest=self.manifest)
        prepare_test_preferences(self.home, channel="rc1")
        candidate = self.home / CANDIDATE_DIR / "preferences.json"
        candidate.write_text('{"theme":"Dark"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "theme"):
            verify_fixture(self.home, manifest=self.manifest)
        candidate.write_bytes(FIXTURE_PREFS)
        forged = json.loads(self.manifest.read_text("utf-8"))
        forged["public_release_approved"] = True
        self.manifest.write_text(json.dumps(forged), "utf-8")
        with self.assertRaisesRegex(ValueError, "fixture"):
            verify_fixture(self.home, manifest=self.manifest)

    def test_seed_refuses_nonempty_or_real_home(self):
        (self.home / "user-data").write_text("Do not modify", "utf-8")
        with self.assertRaises(ValueError):
            seed_fixture(self.home, manifest=self.manifest)
        self.assertFalse(self.manifest.exists())
        with self.assertRaises(ValueError):
            seed_fixture(Path.home(), manifest=self.manifest)

    def test_relative_and_linked_fixture_paths_fail_closed(self):
        with self.assertRaises(ValueError):
            seed_fixture(Path("relative-home"), manifest=self.manifest)
        if os.name == "nt":
            self.skipTest("Windows runner may prohibit creating symlinks")
        symlink = self.root / "linked-home"
        symlink.symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(ValueError):
            seed_fixture(symlink, manifest=self.manifest)

    def test_symlinked_candidate_preferences_not_accepted(self):
        if os.name == "nt":
            self.skipTest("Windows runner may prohibit creating symlinks")
        seed_fixture(self.home, manifest=self.manifest)
        prepare_test_preferences(self.home, channel="rc1")
        candidate = self.home / CANDIDATE_DIR / "preferences.json"
        candidate.unlink()
        candidate.symlink_to(self.home / LEGACY_DIR / "preferences.json")
        with self.assertRaisesRegex(ValueError, "redirected"):
            verify_fixture(self.home, manifest=self.manifest)

    def test_acceptance_proof_requires_running_installed_application(self):
        """Merely staging a fixture cannot be confused with actual app boot."""
        report = seed_fixture(self.home, manifest=self.manifest)
        self.assertEqual(report["stable_data_was_modified"], False)
        self.assertNotIn("installed_application_booted", report)
        self.assertNotIn("stable_preferences_unchanged", report)
        self.assertFalse(report["public_release_approved"])


if __name__ == "__main__":
    unittest.main()
