"""3.0 frozen UI startup verification contracts.

These are SYNTHETIC unit records; ONLY the real four-runner workflow launches
actual PyInstaller executables and Tk App. Neither path grants license rights.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.probe_v30_installed_desktop_window import (
    STATUS, VALID_PLATFORMS, default_binary, run, validate_report,
)


def good():
    return {
        "schema_version": 1,
        "status": STATUS,
        "passed": True,
        "actual_tk_window_started": True,
        "actual_app_initialized": True,
        "actual_tk_mainloop_ran": True,
        "frozen_binary": True,
        "initialized_system": "gba",
        "console_profile_count": 18,
        "top_level_widgets": 9,
        "camera_hardware_tested": False,
        "gameplay_hardware_tested": False,
        "physical_qa_approved": False,
        "public_distribution_approved": False,
        "error": None,
    }


class RealFrozenUIContracts(unittest.TestCase):
    def test_refuses_synthetic_gui_launch_or_fake_hardware_approvals(self):
        for key, invalid in (
            ("passed", False), ("actual_tk_window_started", False),
            ("actual_app_initialized", False), ("actual_tk_mainloop_ran", False),
            ("frozen_binary", False), ("console_profile_count", 17),
            ("top_level_widgets", 0), ("error", "original startup traceback"),
            ("camera_hardware_tested", True),
            ("gameplay_hardware_tested", True),
            ("physical_qa_approved", True),
            ("public_distribution_approved", True),
        ):
            with self.subTest(key=key):
                row=good()
                row[key]=invalid
                with self.assertRaises(ValueError):
                    validate_report(row,"linux-x64")
        for platform in VALID_PLATFORMS:
            self.assertTrue(validate_report(good(),platform))

    def test_four_os_expected_real_pyinstaller_binary_paths(self):
        self.assertEqual(default_binary("windows-x64"),
                         Path("dist/AnythingPlays/AnythingPlays.exe"))
        self.assertEqual(default_binary("linux-x64"),
                         Path("dist/AnythingPlays/AnythingPlays"))
        for mac in ("macos-x64","macos-arm64"):
            self.assertEqual(default_binary(mac),
                             Path("dist/AnythingPlays30Preview.app/Contents/MacOS/AnythingPlays"))

    def test_must_spawn_executable_and_verify_actual_child_written_report(self):
        for platform in VALID_PLATFORMS:
            with self.subTest(platform=platform),TemporaryDirectory() as temp:
                binary=Path(temp)/"installed-real-executable"
                binary.write_bytes(b"synthetic test image never executed")
                report=Path(temp)/"real-gui-evidence.json"
                def fake_run(args,*,cwd,env,timeout,check,stdout,stderr,text,errors):
                    self.assertEqual(args[-1],"--ap-v30-ui-smoke")
                    self.assertEqual(env["AP_V30_UI_SMOKE_CHECK"],"1")
                    self.assertEqual(env["AP_V30_APPROVED_RELEASE"],"0")
                    self.assertEqual(env["AP_RELEASE_BUILD"],"0")
                    self.assertEqual(env["AP_V30_UI_SMOKE_REPORT"],str(report))
                    if platform=="linux-x64":
                        self.assertEqual(args[0],"xvfb-run")
                    else:
                        self.assertEqual(args[0],str(binary))
                    report.write_text(json.dumps(good()),encoding="utf-8")
                    return subprocess.CompletedProcess(args,0,"")
                with patch("tools.probe_v30_installed_desktop_window.subprocess.run",
                           side_effect=fake_run):
                    result=run(platform,binary,report,timeout=20)
                self.assertTrue(result["passed"])
                self.assertFalse(result["public_distribution_approved"])

    def test_missing_actual_child_report_is_failure_not_fake_success(self):
        with TemporaryDirectory() as temp:
            binary=Path(temp)/"fake-executable"
            binary.write_text("synthetic stub",encoding="utf-8")
            report=Path(temp)/"missing.json"
            with patch("tools.probe_v30_installed_desktop_window.subprocess.run",
                       return_value=subprocess.CompletedProcess([],1,"startup failed")):
                with self.assertRaisesRegex(ValueError,"without startup report"):
                    run("linux-x64",binary,report,timeout=20)
            self.assertFalse(report.exists())

    def test_3_0_app_smoke_uses_same_tk_app_and_never_fake_camera(self):
        root=Path(__file__).resolve().parents[1]
        app=(root/"app.py").read_text("utf-8")
        smoke=(root/"anything_plays/frozen_gui_smoke.py").read_text("utf-8")
        self.assertIn("from anything_plays.frozen_gui_smoke import run_smoke_gui",app)
        self.assertIn("return run_smoke_gui(App, SYSTEMS)",app)
        for snippet in ("def run_smoke_gui(app_type, systems):",
                        "root = tk.Tk()", "app = app_type(root)",
                        "root.mainloop()", 'AP_V30_UI_SMOKE_CHECK',
                        "camera_hardware_tested", "physical_qa_approved"):
            self.assertIn(snippet,smoke)
        self.assertIn('if os.environ.get("AP_V30_UI_SMOKE_CHECK") != "1":',app)
        self.assertIn("root.after(100, self.scan_cameras)",app)
        yml=(root/"docs/history/workflows/v30-eight-source-offline-integration.yml").read_text("utf-8")
        self.assertIn("tools.probe_v30_installed_desktop_window",yml)
        self.assertIn("ACTUAL_FROZEN_DESKTOP_UI_LAUNCH_UNAPPROVED.json",yml)
        for platform in VALID_PLATFORMS:
            self.assertIn("target: "+platform,yml)
        self.assertNotIn("gh release create",yml)


if __name__=="__main__":
    unittest.main()
