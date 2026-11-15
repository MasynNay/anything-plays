"""Strict 3.2 stable-upgrade source QA; fake packages in temporary folders."""
import json
from pathlib import Path
import plistlib
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.build_identity import make_identity
from tools.verify_v32_stable_upgrade_source import verify, NAMES, STATUS

SHA = "b" * 40


def fixture(root, target):
    root = Path(root)
    name = "AnythingPlays31.app" if target.startswith("macos") else "AnythingPlays"
    bundle = root / name
    bundle.mkdir()
    marker = bundle / "assets" / "v31_build_identity.json"
    marker.parent.mkdir()
    marker.write_text(json.dumps(make_identity("v32_stable_candidate")), "utf-8")
    if target.startswith("macos"):
        cores = bundle / "Contents" / "Resources" / "cores"
        cores.mkdir(parents=True)
        with (bundle / "Contents" / "Info.plist").open("wb") as out:
            plistlib.dump({
                "CFBundleIdentifier": "com.anythingplays.release31",
                "CFBundleShortVersionString": "3.2.0",
                "CFBundleVersion": "3.2.0",
            }, out)
        suffix = ".dylib"
    else:
        cores = bundle / "cores"
        cores.mkdir()
        suffix = ".dll" if target == "windows-x64" else ".so"
    (cores / ("mgba_libretro" + suffix)).write_bytes(b"native" * 500)
    installer = root / NAMES[target]
    installer.write_bytes(b"MZ" + b"x" * (1024 * 1024 + 8))
    return installer, bundle, cores, suffix


class PrivateUpgradeTests(unittest.TestCase):
    def test_actual_windows_identity_is_one_core_not_public(self):
        with TemporaryDirectory() as tmp:
            installer, bundle, _, _ = fixture(tmp, "windows-x64")
            data = verify("windows-x64", installer, bundle, SHA, checkout_sha=SHA)
            self.assertEqual(data["status"], STATUS)
            self.assertEqual(data["native_core_count"], 1)
            self.assertEqual(data["stable_settings_namespace"], "anything-plays-31")
            self.assertFalse(data["public_release_approved"])
            self.assertFalse(data["real_user_settings_migration_tested"])

    def test_mac_stable_bundle_identity_cannot_be_changed(self):
        with TemporaryDirectory() as tmp:
            installer, bundle, cores, ext = fixture(tmp, "macos-arm64")
            self.assertTrue(verify(
                "macos-arm64", installer, bundle, SHA, checkout_sha=SHA,
            )["stable_package_identity_matches_311"])
            with (bundle / "Contents" / "Info.plist").open("wb") as out:
                plistlib.dump({
                    "CFBundleIdentifier": "com.anythingplays.privatepreview32",
                    "CFBundleShortVersionString": "3.2.0",
                    "CFBundleVersion": "3.2.0",
                }, out)
            with self.assertRaises(ValueError):
                verify("macos-arm64", installer, bundle, SHA, checkout_sha=SHA)

    def test_additional_native_core_fails_closed(self):
        with TemporaryDirectory() as tmp:
            installer, bundle, cores, ext = fixture(tmp, "windows-x64")
            (cores / ("dolphin_libretro" + ext)).write_bytes(b"extra" * 600)
            with self.assertRaises(ValueError):
                verify("windows-x64", installer, bundle, SHA, checkout_sha=SHA)

    def test_forged_upgrade_marker_and_source_rejected(self):
        with TemporaryDirectory() as tmp:
            installer, bundle, _, _ = fixture(tmp, "windows-x64")
            with self.assertRaises(ValueError):
                verify("windows-x64", installer, bundle, SHA, checkout_sha="a" * 40)
            marker = bundle / "assets" / "v31_build_identity.json"
            marker.write_text(json.dumps(make_identity("v32_preview")), "utf-8")
            with self.assertRaises(ValueError):
                verify("windows-x64", installer, bundle, SHA, checkout_sha=SHA)

    def test_symlinked_core_and_short_installer_rejected(self):
        with TemporaryDirectory() as tmp:
            installer, bundle, cores, ext = fixture(tmp, "windows-x64")
            installer.write_bytes(b"MZ")
            with self.assertRaises(ValueError):
                verify("windows-x64", installer, bundle, SHA, checkout_sha=SHA)
            installer.write_bytes(b"MZ" + b"x" * (1024 * 1024 + 8))
            core = cores / ("mgba_libretro" + ext)
            core.unlink()
            backup = cores / "backup.so"
            backup.write_bytes(b"x" * 2048)
            try:
                core.symlink_to(backup)
            except (OSError, NotImplementedError):
                self.skipTest("Host cannot make symlinks")
            with self.assertRaises(ValueError):
                verify("windows-x64", installer, bundle, SHA, checkout_sha=SHA)


if __name__ == "__main__":
    unittest.main()
