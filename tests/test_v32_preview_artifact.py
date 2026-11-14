"""Private 3.2 installer receipt rejects tampering and incorrect identities.

Fake packages are used. These unit tests do not produce real installers or
assert physical hardware or redistribution acceptance.
"""

import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

from anything_plays.build_identity import make_identity
from tools.verify_v32_preview import FILES, verify


REVISION = "1234567890abcdef1234567890abcdef12345678"


def fake_identity(root, *, channel="v32_preview"):
    location = root / "_internal" / "assets" / "v31_build_identity.json"
    location.parent.mkdir(parents=True, exist_ok=True)
    location.write_text(
        json.dumps(make_identity(channel)), encoding="utf-8",
    )
    return location


def fake_file(folder, name, *, windows=False):
    file = folder / name
    data = (b"MZ" if windows else b"q!") + b"*" * (1024 * 1024 + 4)
    file.write_bytes(data)
    return file


class V32ArtifactReceiptTests(unittest.TestCase):
    def test_windows_receipt_checks_exact_embedded_settings_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            bundle = folder / "dist" / "AnythingPlays"
            fake_identity(bundle)
            file = fake_file(folder, FILES["windows-x64"], windows=True)
            report = verify("windows-x64", file, REVISION, bundle=bundle)
            self.assertEqual(report["channel"], "v32_preview")
            self.assertEqual(
                report["settings_namespace"], "anything-plays-32-preview"
            )
            self.assertFalse(report["public_release_approved"])
            self.assertFalse(report["physical_controller_verified"])
            self.assertFalse(report["all_18_consoles_verified"])
            self.assertEqual(len(report["sha256"]), 64)

    def test_refuses_wrong_or_missing_frozen_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            bundle = folder / "bundle"
            marker = fake_identity(bundle, channel="v311_stable_candidate")
            file = fake_file(folder, FILES["windows-x64"], windows=True)
            with self.assertRaisesRegex(ValueError, "wrong build identity"):
                verify("windows-x64", file, REVISION, bundle=bundle)
            marker.unlink()
            with self.assertRaisesRegex(ValueError, "exactly one"):
                verify("windows-x64", file, REVISION, bundle=bundle)

    def test_refuses_wrong_filename_and_source_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            bundle = folder / "bundle"
            fake_identity(bundle)
            file = fake_file(folder, FILES["windows-x64"], windows=True)
            with self.assertRaisesRegex(ValueError, "source revision"):
                verify("windows-x64", file, "not-a-git-sha", bundle=bundle)
            renamed = file.with_name("AnythingPlaysSetup-3.1.1.exe")
            file.rename(renamed)
            with self.assertRaisesRegex(ValueError, "incorrectly named"):
                verify("windows-x64", renamed, REVISION, bundle=bundle)

    def test_linux_deb_metadata_is_checked_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            bundle = folder / "bundle"
            fake_identity(bundle)
            file = fake_file(folder, FILES["linux-x64"])
            with patch("tools.verify_v32_preview.subprocess.check_output",
                       side_effect=["anything-plays-32-preview\n",
                                    "3.2.0~preview1\n"]) as process:
                report = verify("linux-x64", file, REVISION, bundle=bundle)
            self.assertEqual(process.call_count, 2)
            self.assertEqual(report["target"], "linux-x64")

    def test_dmg_needs_separate_32_plist_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            bundle = folder / "AnythingPlays32Preview.app"
            fake_identity(bundle)
            plist = bundle / "Contents" / "Info.plist"
            plist.parent.mkdir(parents=True, exist_ok=True)
            with plist.open("wb") as stream:
                plistlib.dump({
                    "CFBundleIdentifier": "com.anythingplays.privatepreview32",
                    "CFBundleShortVersionString": "3.2.0",
                    "CFBundleVersion": "3.2.0.1",
                }, stream)
            file = fake_file(folder, FILES["macos-arm64"])
            result = verify("macos-arm64", file, REVISION, bundle=bundle)
            self.assertEqual(result["target"], "macos-arm64")
            with plist.open("wb") as stream:
                plistlib.dump({
                    "CFBundleIdentifier": "com.anythingplays.release31",
                    "CFBundleShortVersionString": "3.2.0",
                    "CFBundleVersion": "3.2.0.1",
                }, stream)
            with self.assertRaisesRegex(ValueError, "not isolated"):
                verify("macos-arm64", file, REVISION, bundle=bundle)


if __name__ == "__main__":
    unittest.main()
