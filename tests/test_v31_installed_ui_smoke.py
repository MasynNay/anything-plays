"""Strict 3.1 full-RC frozen desktop smoke validation."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from anything_plays.build_identity import make_identity
from tools.verify_v31_installed_ui_smoke import (
    TARGETS, SOURCE_COMMIT, verify_installed_smoke, sha256,
)


def good_smoke():
    return {
        "status": "UNAPPROVED-3.0-INSTALLED-DESKTOP-STARTUP-CHECK",
        "passed": True,
        "actual_tk_window_started": True,
        "actual_app_initialized": True,
        "actual_tk_mainloop_ran": True,
        "frozen_binary": True,
        "console_profile_count": 18,
        "top_level_widgets": 25,
        "initialized_system": "gba",
        "error": None,
        "camera_hardware_tested": False,
        "gameplay_hardware_tested": False,
        "physical_qa_approved": False,
        "public_distribution_approved": False,
    }


def test_files(root, target):
    root = Path(root)
    state, filename = TARGETS[target]
    installer = root / filename
    installer.write_bytes(b"fake-installer-content")
    app = root / "rc1"
    marker = app / "_internal/assets/v31_build_identity.json"
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps(make_identity("rc1")), "utf-8")
    receipt = {
        "target": target,
        "status": state,
        "installer": filename,
        "source_preview_revision": SOURCE_COMMIT,
        "sha256": sha256(installer),
        "native_core_count": 11,
        "console_profiles": 18,
        "public_release_approved": False,
        "final_release_approved": False,
    }
    return installer, app, receipt


class InstalledFrozeGUIContracts(unittest.TestCase):
    def test_four_native_os_targets_require_real_frozen_rc1_identity(self):
        for target in TARGETS:
            with self.subTest(target=target), TemporaryDirectory() as d:
                installer, app, receipt = test_files(d, target)
                result = verify_installed_smoke(
                    target, installer, app, receipt, good_smoke()
                )
                self.assertEqual(result["console_profiles"], 18)
                self.assertEqual(result["native_core_count"], 11)
                self.assertTrue(result["actual_mainloop_ran"])
                self.assertFalse(result["public_release_approved"])
                self.assertFalse(result["physical_controller_verified"])
                self.assertFalse(result["camera_hardware_verified"])
                self.assertFalse(result["gameplay_verified"])

    def test_previews_and_fake_no_window_reports_rejected(self):
        with TemporaryDirectory() as d:
            installer, app, receipt = test_files(d, "linux-x64")
            marker = app / "_internal/assets/v31_build_identity.json"
            marker.write_text(json.dumps(make_identity("preview1")), "utf-8")
            with self.assertRaises(ValueError):
                verify_installed_smoke("linux-x64", installer, app,
                                       receipt, good_smoke())
            marker.write_text(json.dumps(make_identity("rc1")), "utf-8")
            for key, bad in (
                ("passed", False),
                ("actual_tk_window_started", False),
                ("actual_app_initialized", False),
                ("actual_tk_mainloop_ran", False),
                ("frozen_binary", False),
                ("console_profile_count", 3),
                ("top_level_widgets", 0),
                ("error", "Traceback"),
                ("physical_qa_approved", True),
                ("camera_hardware_tested", True),
                ("public_distribution_approved", True),
            ):
                with self.subTest(key=key):
                    smoke = dict(good_smoke(), **{key: bad})
                    with self.assertRaises(ValueError):
                        verify_installed_smoke("linux-x64", installer, app,
                                               receipt, smoke)

    def test_receipts_and_binaries_need_exact_correspondence(self):
        with TemporaryDirectory() as d:
            installer, app, receipt = test_files(d, "windows-x64")
            for key, bad in (
                ("source_preview_revision", "0" * 40),
                ("native_core_count", 1),
                ("console_profiles", 3),
                ("public_release_approved", True),
                ("final_release_approved", True),
                ("sha256", "a" * 64),
            ):
                with self.subTest(key=key):
                    r = dict(receipt, **{key: bad})
                    with self.assertRaises(ValueError):
                        verify_installed_smoke("windows-x64", installer, app,
                                               r, good_smoke())

    def test_ci_uses_existing_frozen_app_smoke_no_release(self):
        text = (
            Path(__file__).resolve().parents[1]
            / ".github/workflows/v31-rc1-installed-gui-smoke.yml"
        ).read_text("utf-8")
        self.assertIn("42886791394", text)
        self.assertIn("--ap-v30-ui-smoke", text)
        self.assertIn("AP_V30_UI_SMOKE_CHECK", text)
        self.assertIn("actions/upload-artifact@v4", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("gh release create", text)


if __name__ == "__main__":
    unittest.main()
