"""Stable 3.0 app identity must be gated and never replace preview branding."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class V30ProductionIdentityTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def test_windows_production_has_own_identity_and_immutable_preflight(self):
        bat = self.read("packaging/build_windows.bat")
        iss = self.read("packaging/installer.iss")
        self.assertIn('if "%AP_V30_APPROVED_RELEASE%"=="1" (', bat)
        self.assertIn('python tools\\check_v30_release.py', bat)
        self.assertIn("load_approved_lock()", bat)
        self.assertIn('set "VERSION=3.0.0"', bat)
        self.assertIn("/DProductionBuild=1", bat)
        # Both preprocessor forms guard the real 3.0 production block.
        # Inno Setup successfully compiled the 3.1 preview using #elif.
        self.assertTrue(
            "#ifdef ProductionBuild" in iss or "#elif defined(ProductionBuild)" in iss
        )
        self.assertIn('#define AppName "Anything Plays"', iss)
        self.assertIn('#define AppName "Anything Plays 3.0 Preview"', iss)
        self.assertIn("DefaultDirName={autopf}\\Anything Plays", iss)
        self.assertIn("DefaultDirName={autopf}\\Anything Plays 3.0 Preview", iss)
        self.assertIn("AADD80D2-54CD-4FD9-BB42-A669D15C8B45", iss)
        self.assertIn("A10F0E4B-E548-4C9A-B93F-5B05493AA844", iss)
        self.assertNotIn("D5C81347-28B4-4F0D-BA82-1D441A83C0F5", iss)

    def test_macos_production_names_match_release_asset_contract(self):
        mac = self.read("packaging/build_macos_dmg.sh")
        self.assertIn('BUNDLE_FILE="AnythingPlays30Preview.app"', mac)
        self.assertIn('BUNDLE_FILE="AnythingPlays.app"', mac)
        self.assertIn("com.anythingplays.preview30", mac)
        self.assertIn("com.anythingplays.release30", mac)
        self.assertIn('DMG_NAME="AnythingPlays-3.0.0-macos-arm64.dmg"', mac)
        self.assertIn('DMG_NAME="AnythingPlays-3.0.0-macos-x64.dmg"', mac)
        self.assertIn('DMG_NAME="AnythingPlays-3.0.0-alpha.1.dmg"', mac)
        self.assertIn("python3 tools/check_v30_release.py", mac)
        self.assertIn("load_approved_lock()", mac)
        self.assertIn('APP_BUNDLE="dist/$BUNDLE_FILE"', mac)
        self.assertIn('"$MOUNT_DIR/${BUNDLE_FILE}"', mac)

    def test_linux_stable_package_includes_new_desktop_launcher_and_verified_path(self):
        linux = self.read("packaging/build_linux_deb.sh")
        self.assertIn('PACKAGE_NAME="anything-plays-preview"', linux)
        self.assertIn('PACKAGE_NAME="anything-plays"', linux)
        self.assertIn('INSTALL_ID="anything-plays-30-preview"', linux)
        self.assertIn('INSTALL_ID="anything-plays"', linux)
        self.assertIn('VERSION="3.0.0"', linux)
        self.assertIn('OUTPUT_DEB="release/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"', linux)
        self.assertIn("python3 tools/check_v30_release.py", linux)
        self.assertIn("load_approved_lock()", linux)
        self.assertIn("Package: anything-plays-preview", linux)
        self.assertIn("Package: anything-plays", linux)
        self.assertIn("Exec=anything-plays-30-preview", linux)
        self.assertIn("Exec=anything-plays", linux)
        self.assertIn("mv \"$PKG/opt/anything-plays-30-preview\" \"$PKG/opt/anything-plays\"", linux)
        self.assertIn('"$AUDIT_DIR/opt/$INSTALL_ID"', linux)
        self.assertIn('"$OUTPUT_DEB"', linux)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Needs Linux bash and dpkg")
    def test_production_fails_before_package_build_without_independent_rights_qa(self):
        env = os.environ.copy()
        env.update({
            "AP_V30_APPROVED_RELEASE": "1",
            "AP_RELEASE_BUILD": "1",
            "AP_CORE_ARCHIVE_DIR": str(ROOT / "not-an-approved-native-input-dir"),
        })
        proc = subprocess.run(
            ["bash", "packaging/build_linux_deb.sh"],
            cwd=ROOT, env=env, text=True, capture_output=True, timeout=20,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("3.0 RELEASE BLOCKED", proc.stdout + proc.stderr)
        self.assertNotIn("Created release/", proc.stdout + proc.stderr)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Needs Linux bash and dpkg")
    def test_production_rejects_missing_approval_mode_before_download(self):
        env = os.environ.copy()
        env.update({
            "AP_V30_APPROVED_RELEASE": "1",
            "AP_RELEASE_BUILD": "0",
            "AP_CORE_ARCHIVE_DIR": "/nonexistent",
        })
        proc = subprocess.run(
            ["bash", "packaging/build_linux_deb.sh"],
            cwd=ROOT, env=env, text=True, capture_output=True, timeout=20,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("requires AP_RELEASE_BUILD=1", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
