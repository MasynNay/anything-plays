"""True, fail-closed 3.1.1 identity and non-public packaging contracts.

All checks are static/local or source marker checks. They do not pretend
to create the complete 18-console installers nor grant release approval.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from anything_plays.build_identity import make_identity, validate_identity
from tools.write_v31_identity import choose_channel, write_identity

ROOT = Path(__file__).resolve().parents[1]
QA_FLAG = "AP_V311_CANDIDATE"
SLOTS = ("AP_V31_PREVIEW", "AP_V31_RC", "AP_V31_RC2",
         "AP_V31_FINAL_CANDIDATE")


class Version311PrivateCandidateTests(unittest.TestCase):
    def test_exact_version_and_isolated_nonpublic_identity(self):
        identity = make_identity("v311_candidate")
        self.assertEqual(identity["version"], "3.1.1")
        self.assertEqual(identity["channel"], "v311_candidate")
        self.assertEqual(identity["settings_namespace"],
                         "anything-plays-311-candidate")
        self.assertFalse(identity["public_release_approved"])
        self.assertNotEqual(identity["settings_namespace"],
                            make_identity("final_candidate")["settings_namespace"])
        self.assertNotEqual(identity["title"],
                            make_identity("final_candidate")["title"])
        self.assertEqual(validate_identity(identity), identity)

    def test_mixed_candidate_or_stable_release_flags_are_rejected(self):
        allowed = {QA_FLAG: "1", "AP_V30_MINIMAL_CORE_BUILD": "1"}
        self.assertEqual(choose_channel(allowed), "v311_candidate")
        for flag in SLOTS + ("AP_RELEASE_BUILD", "AP_V30_APPROVED_RELEASE",
                             "AP_V30_STABLE_CANDIDATE", "AP_V30_TEST_CORES",
                             "AP_V30_GPL_TRIAL", "AP_V30_TIA_TRIAL"):
            with self.subTest(flag=flag):
                with self.assertRaises(ValueError):
                    choose_channel({**allowed, flag: "1"})
        with self.assertRaises(ValueError):
            choose_channel({QA_FLAG: "1"})
        with self.assertRaises(ValueError):
            choose_channel({**allowed, QA_FLAG: "0"})
        self.assertEqual(choose_channel(
            {"AP_V31_FINAL_CANDIDATE": "1",
             "AP_V30_MINIMAL_CORE_BUILD": "1"}), "final_candidate")

    def test_marker_writer_is_deterministic_and_validated(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / "assets" / "v31_build_identity.json"
            flags = {QA_FLAG: "1", "AP_V30_MINIMAL_CORE_BUILD": "1"}
            one = write_identity(marker, environ=flags)
            two = write_identity(marker, environ=flags)
            self.assertEqual(one, two)
            self.assertEqual(marker.read_text("utf-8").count("3.1.1"), 2)
            self.assertEqual(validate_identity(__import__("json").loads(
                marker.read_text("utf-8"))), make_identity("v311_candidate"))

    def test_three_platform_builders_use_the_actual_311_flag_and_new_identity(self):
        expected = {
            "packaging/build_linux_deb.sh": (
                'VERSION="3.1.1~qa1"',
                'PACKAGE_NAME="anything-plays-311-candidate"',
                'INSTALL_ID="anything-plays-311-candidate"',
                'AP_V30_MINIMAL_CORE_BUILD',
                "tools.write_v31_identity",
            ),
            "packaging/build_windows.bat": (
                'VERSION=3.1.1-qa1',
                '/DV311QABuild=1',
                'AP_V30_MINIMAL_CORE_BUILD',
                'V31_IDENTITY_ARG',
                'tools.write_v31_identity',
            ),
            "packaging/build_macos_dmg.sh": (
                'BUNDLE_FILE="AnythingPlays311QA.app"',
                'DMG_NAME="AnythingPlays-3.1.1-qa1-macos-arm64.dmg"',
                'DMG_NAME="AnythingPlays-3.1.1-qa1-macos-x64.dmg"',
                'com.anythingplays.private311qa',
                "tools.write_v31_identity",
            ),
        }
        for path, fragments in expected.items():
            with self.subTest(script=path):
                source = (ROOT / path).read_text("utf-8")
                self.assertIn(QA_FLAG, source)
                for fragment in fragments:
                    self.assertIn(fragment, source)

    def test_windows_qa_installer_does_not_reuse_public_app_guid(self):
        source = (ROOT / "packaging/installer.iss").read_text("utf-8")
        self.assertIn("V311QABuild", source)
        self.assertIn("D2946CA0-E7F8-4667-B1C5-A7733F570311", source)
        self.assertIn("753B9C90-2D6A-43E4-90E4-49393B3AE025", source)
        self.assertIn("Anything Plays 3.1.1 Private QA", source)
        self.assertIn('DefaultDirName={autopf}\\Anything Plays 3.1.1', source)

    def test_unknown_or_mutated_version_is_rejected(self):
        one = make_identity("v311_candidate")
        one["public_release_approved"] = True
        with self.assertRaises(ValueError):
            validate_identity(one)
        one = make_identity("v311_candidate")
        one["settings_namespace"] = "anything-plays-31"
        with self.assertRaises(ValueError):
            validate_identity(one)
        with self.assertRaises(ValueError):
            make_identity("3.1.1-stable")


if __name__ == "__main__":
    unittest.main()
