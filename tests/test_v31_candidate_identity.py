"""Fail-closed 3.1 release-candidate identity and isolation contracts."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.build_identity import (
    app_title, current_identity, make_identity, validate_identity,
)
from anything_plays.test_preferences import (
    CANDIDATE_DIR, LEGACY_DIR, PREVIOUS_PREVIEW_DIR, TEST_DIR,
    prepare_test_preferences,
)
from tools.write_v31_identity import choose_channel, write_identity
from tools.verify_v31_rc import INSTALLERS, STATUS, validate_staged_identity

ROOT = Path(__file__).resolve().parents[1]


def env(**changes):
    defaults = {
        "AP_V31_RC": "1", "AP_V31_PREVIEW": "0",
        "AP_V30_MINIMAL_CORE_BUILD": "1",
        "AP_RELEASE_BUILD": "0", "AP_V30_APPROVED_RELEASE": "0",
        "AP_V30_STABLE_CANDIDATE": "0",
        "AP_V30_TEST_CORES": "0", "AP_V30_GPL_TRIAL": "0",
        "AP_V30_TIA_TRIAL": "0",
    }
    defaults.update(changes)
    return defaults


class RCIdentityContracts(unittest.TestCase):
    def test_unreleased_rc_has_reviewed_schema_and_separate_settings(self):
        preview, rc = make_identity("preview1"), make_identity("rc1")
        self.assertNotEqual(preview["settings_namespace"],
                            rc["settings_namespace"])
        self.assertEqual(rc["version"], "3.1.0")
        self.assertIn("Release Candidate", rc["title"])
        self.assertFalse(rc["public_release_approved"])
        self.assertEqual(CANDIDATE_DIR, Path(".config/anything-plays-31-rc1"))

    def test_writer_requires_only_safe_mutually_exclusive_flags(self):
        self.assertEqual(choose_channel(env()), "rc1")
        self.assertEqual(
            choose_channel(env(AP_V31_RC="0", AP_V31_PREVIEW="1")),
            "preview1",
        )
        for invalid in (
            {"AP_V31_RC": "1", "AP_V31_PREVIEW": "1"},
            {"AP_V31_RC": "0", "AP_V31_PREVIEW": "0"},
            {"AP_V30_MINIMAL_CORE_BUILD": "0"},
            {"AP_RELEASE_BUILD": "1"},
            {"AP_V30_APPROVED_RELEASE": "1"},
            {"AP_V30_STABLE_CANDIDATE": "1"},
            {"AP_V30_TEST_CORES": "1"},
            {"AP_V30_GPL_TRIAL": "1"},
            {"AP_V30_TIA_TRIAL": "1"},
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    choose_channel(env(**invalid))

    def test_frozen_identity_round_trip_and_tampering_rejected(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            marker = root / "_internal/assets/v31_build_identity.json"
            data = write_identity(marker, env())
            self.assertEqual(validate_staged_identity(root),
                             "_internal/assets/v31_build_identity.json")
            self.assertEqual(current_identity(marker), data)
            for change in (
                {"channel": "preview1"},
                {"settings_namespace": "anything-plays"},
                {"public_release_approved": True},
                {"title": "Anything Plays 3.0"},
            ):
                with self.subTest(change=change):
                    altered = dict(data, **change)
                    marker.write_text(json.dumps(altered), "utf-8")
                    with self.assertRaises(ValueError):
                        validate_staged_identity(root)
            marker.write_text(json.dumps(data), "utf-8")
            marker.unlink()
            self.assertEqual(current_identity(marker)["channel"], "preview1")
            with self.assertRaises(ValueError):
                validate_staged_identity(root)

    def test_rc_settings_copy_preview_without_changing_any_other_directory(self):
        with TemporaryDirectory() as d:
            home = Path(d)
            prev = home / TEST_DIR
            prev.mkdir(parents=True)
            (prev / "preferences.json").write_text('{"theme":"Light"}', "utf-8")
            old = home / LEGACY_DIR
            old.mkdir(parents=True)
            (old / "preferences.json").write_text('{"theme":"Plum Dark"}', "utf-8")
            new = prepare_test_preferences(home, channel="rc1")
            self.assertEqual(new, home / CANDIDATE_DIR / "preferences.json")
            self.assertEqual(new.read_text("utf-8"), '{"theme":"Light"}')
            new.write_text('{"theme":"Ocean Dark"}', "utf-8")
            self.assertEqual((prev / "preferences.json").read_text("utf-8"),
                             '{"theme":"Light"}')
            self.assertEqual((old / "preferences.json").read_text("utf-8"),
                             '{"theme":"Plum Dark"}')
            self.assertEqual(prepare_test_preferences(home, channel="rc1"),
                             new)
            self.assertEqual(new.read_text("utf-8"), '{"theme":"Ocean Dark"}')
            with self.assertRaises(ValueError):
                prepare_test_preferences(home, channel="release30")

    def test_rc_installer_identities_are_never_public_stable_or_preview(self):
        self.assertEqual(set(INSTALLERS), {
            "linux-x64", "windows-x64", "macos-arm64", "macos-x64"
        })
        self.assertEqual(STATUS, "UNRELEASED_3_1_RC1_APP_STAGE_ONLY")
        linux = (ROOT / "packaging/build_linux_deb.sh").read_text("utf-8")
        win = (ROOT / "packaging/build_windows.bat").read_text("utf-8")
        iss = (ROOT / "packaging/installer.iss").read_text("utf-8")
        mac = (ROOT / "packaging/build_macos_dmg.sh").read_text("utf-8")
        self.assertIn('PACKAGE_NAME="anything-plays-31-rc1"', linux)
        self.assertIn('INSTALL_ID="anything-plays-31-rc1"', linux)
        self.assertIn('/DV31RCBuild=1', win)
        self.assertIn("A3C2BEE4-4F7E-476F-A514-940FB1E1E071", iss)
        self.assertIn("com.anythingplays.rc31", mac)
        self.assertIn('BUNDLE_FILE="AnythingPlays31RC.app"', mac)
        self.assertIn("write_v31_identity", linux)
        self.assertIn("write_v31_identity", win)
        self.assertIn("write_v31_identity", mac)

    def test_candidate_ci_does_not_publish_or_claim_full_emulators(self):
        workflow = (
            ROOT / ".github/workflows/v31-rc1-source-app.yml"
        ).read_text("utf-8")
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("AP_V31_RC: '1'", workflow)
        self.assertIn("AP_V30_MINIMAL_CORE_BUILD: '1'", workflow)
        self.assertIn("retention-days: 7", workflow)
        self.assertIn("not full", workflow.lower())
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("AP_V30_APPROVED_RELEASE: '1'", workflow)


if __name__ == "__main__":
    unittest.main()
