"""Exact source-stage package contracts for QA and stable 3.1.1 channels.

Use synthetic installers, mock native package metadata, and real embedded
identity JSON. Never publish or touch a user's installed preferences.
"""
from __future__ import annotations

import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

from anything_plays.build_identity import make_identity
from tools.verify_v311_source_stage import (
    INSTALLERS as PRIVATE_INSTALLERS, verify as verify_private,
)
from tools.verify_v311_stable_source_stage import (
    INSTALLERS as STABLE_INSTALLERS, verify as verify_stable,
)

SHA = "a" * 40
WHEEL = {"native_wheel_sha256": "b" * 64}


def create_app(root, *, target, stable):
    channel = "v311_stable_candidate" if stable else "v311_candidate"
    mac = target.startswith("macos")
    app_name = ("AnythingPlays31.app" if stable else "AnythingPlays311QA.app") if mac else "Frozen311"
    app = root / app_name
    if mac:
        cores = app / "Contents" / "Resources" / "cores"
        markers = app / "Contents" / "Resources" / "assets"
        plist = {
            "CFBundleIdentifier": ("com.anythingplays.release31" if stable
                                   else "com.anythingplays.private311qa"),
            "CFBundleShortVersionString": "3.1.1",
            "CFBundleVersion": "3.1.1",
        }
        (app / "Contents").mkdir(parents=True)
        with (app / "Contents" / "Info.plist").open("wb") as f:
            plistlib.dump(plist, f)
        extension = ".dylib"
    else:
        cores, markers = app / "cores", app / "assets"
        extension = ".dll" if target == "windows-x64" else ".so"
    cores.mkdir(parents=True)
    markers.mkdir(parents=True)
    (cores / ("mgba_libretro" + extension)).write_bytes(b"\0" * 2048)
    (markers / "v31_build_identity.json").write_text(
        json.dumps(make_identity(channel)), "utf-8",
    )
    return app


class Native311SourceContracts(unittest.TestCase):
    def _fixture(self, target, *, stable=False):
        temp = tempfile.TemporaryDirectory(prefix="ap311-contract-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        filename = (STABLE_INSTALLERS if stable else PRIVATE_INSTALLERS)[target]
        installer = root / filename
        installer.write_bytes(b"MZ" + b"\0" * (1024 * 1024 + 1))
        app = create_app(root, target=target, stable=stable)
        return installer, app

    @staticmethod
    def dpkg_field_only(args, **kw):
        # The original bug incorrectly read -f Package Version together;
        # dpkg labels both fields in that format. Require single-field API.
        assert args[:3] == ["dpkg-deb", "-f", args[2]]
        assert len(args) == 4, args
        if args[3] == "Package":
            return "anything-plays-31\n" if "stable" in kw.get("mode", "") else "anything-plays-311-candidate\n"
        if args[3] == "Version":
            return "3.1.1\n" if "stable" in kw.get("mode", "") else "3.1.1~qa1\n"
        raise AssertionError(args)

    def test_private_linux_uses_two_independent_raw_control_fields(self):
        installer, app = self._fixture("linux-x64")
        calls = []
        def check(args, **kw):
            calls.append(args[-1])
            assert len(args) == 4
            return {"Package": "anything-plays-311-candidate\n",
                    "Version": "3.1.1~qa1\n"}[args[-1]]
        with patch("tools.verify_v311_source_stage.subprocess.check_output",
                   side_effect=check):
            report = verify_private("linux-x64", installer, app, SHA, checkout=SHA)
        self.assertEqual(calls, ["Package", "Version"])
        self.assertEqual(report["native_core_count"], 1)
        self.assertFalse(report["full_18_console_installer"])

    def test_stable_linux_uses_same_stable_3_1_package_with_new_version(self):
        installer, app = self._fixture("linux-x64", stable=True)
        calls = []
        def check(args, **kw):
            calls.append(args[-1])
            assert len(args) == 4
            return {"Package": "anything-plays-31\n",
                    "Version": "3.1.1\n"}[args[-1]]
        with (patch("tools.verify_v311_stable_source_stage.subprocess.check_output",
                    side_effect=check),
              patch("tools.verify_v311_stable_source_stage.require_pinned_native_camera_wheel",
                    return_value=WHEEL)):
            report = verify_stable(
                "linux-x64", installer, app, "/synthetic/wheel.json", SHA,
                checkout_sha=SHA,
            )
        self.assertEqual(calls, ["Package", "Version"])
        self.assertEqual(report["settings_namespace"], "anything-plays-31")
        self.assertFalse(report["public_release_approved"])

    def test_mac_arm_and_intel_require_real_311_bundle_version(self):
        for target in ("macos-arm64", "macos-x64"):
            with self.subTest(target=target):
                installer, app = self._fixture(target)
                report = verify_private(target, installer, app, SHA, checkout=SHA)
                self.assertEqual(report["identity_channel"], "v311_candidate")
                path = app / "Contents" / "Info.plist"
                with path.open("rb") as handle:
                    plist = plistlib.load(handle)
                plist["CFBundleVersion"] = "3.1.1.1"
                with path.open("wb") as handle:
                    plistlib.dump(plist, handle)
                with self.assertRaisesRegex(ValueError, "bundle identifier/version"):
                    verify_private(target, installer, app, SHA, checkout=SHA)

    def test_stable_mac_reuses_public_3_1_bundle_id(self):
        for target in ("macos-arm64", "macos-x64"):
            with self.subTest(target=target):
                installer, app = self._fixture(target, stable=True)
                with patch("tools.verify_v311_stable_source_stage.require_pinned_native_camera_wheel",
                           return_value=WHEEL):
                    result = verify_stable(
                        target, installer, app, "/synthetic/wheel.json", SHA,
                        checkout_sha=SHA,
                    )
                self.assertEqual(result["identity_channel"], "v311_stable_candidate")
                self.assertEqual(result["version"], "3.1.1")
                self.assertEqual(result["settings_namespace"], "anything-plays-31")

    def test_unapproved_windows_source_does_not_claim_full_release(self):
        installer, app = self._fixture("windows-x64")
        result = verify_private("windows-x64", installer, app, SHA, checkout=SHA)
        self.assertFalse(result["public_release_approved"])
        self.assertFalse(result["full_18_console_installer"])
        self.assertEqual(result["native_core_count"], 1)

    def test_stable_windows_requires_real_pe_header(self):
        installer, app = self._fixture("windows-x64", stable=True)
        installer.write_bytes(b"!!" + b"\0" * (1024 * 1024 + 1))
        with patch("tools.verify_v311_stable_source_stage.require_pinned_native_camera_wheel",
                   return_value=WHEEL):
            with self.assertRaisesRegex(ValueError, "Windows PE"):
                verify_stable("windows-x64", installer, app,
                              "/synthetic/wheel.json", SHA, checkout_sha=SHA)


if __name__ == "__main__":
    unittest.main()
