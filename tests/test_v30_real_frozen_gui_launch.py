"""Actual frozen GUI startup contract, without launching a GUI in unit tests.

CI separately runs this against four REAL PyInstaller desktop executables.
No unit fixture here is an executable or qualifies for public distribution.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.probe_v30_frozen_gui_launch import BINARIES, prove_frozen_window, STATUS


def original_child():
    return {
        "schema_version":1,
        "status":"UNAPPROVED-3.0-INSTALLED-DESKTOP-STARTUP-CHECK",
        "passed":True,
        "actual_tk_window_started":True,
        "actual_app_initialized":True,
        "actual_tk_mainloop_ran":True,
        "frozen_binary":True,
        "initialized_system":"gba",
        "console_profile_count":18,
        "top_level_widgets":4,
        "camera_hardware_tested":False,
        "gameplay_hardware_tested":False,
        "physical_qa_approved":False,
        "public_distribution_approved":False,
        "error":None,
    }


class RealFrozenAppLaunchContracts(unittest.TestCase):
    def test_four_platform_original_frozen_executable_paths(self):
        self.assertEqual(set(BINARIES),{"windows-x64","linux-x64","macos-arm64","macos-x64"})
        self.assertEqual(BINARIES["windows-x64"].suffix,".exe")
        self.assertEqual(BINARIES["linux-x64"].name,"AnythingPlays")
        self.assertTrue(str(BINARIES["macos-x64"]).endswith(".app/Contents/MacOS/AnythingPlays"))

    def test_report_requires_actual_native_process_and_real_tk_eventloop(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            exe=root/"FAKE_UNRUNNABLE_NOT_A_REAL_EXE.exe"
            exe.write_bytes(b"MZ"+b"unit fixture never executed"*12000)
            def fake_run(args,env,**kwargs):
                self.assertEqual(args[1],"--ap-v30-ui-smoke")
                self.assertEqual(env["AP_V30_UI_SMOKE_CHECK"],"1")
                Path(env["AP_V30_UI_SMOKE_REPORT"]).write_text(
                    json.dumps(original_child()),encoding="utf-8")
                return SimpleNamespace(returncode=0,stdout="",stderr="")
            with patch.dict(BINARIES,{"windows-x64":exe}), \
                 patch("tools.probe_v30_frozen_gui_launch.subprocess.run",
                       side_effect=fake_run):
                out=prove_frozen_window("windows-x64",root/"valid.json")
            self.assertEqual(out["status"],STATUS)
            self.assertTrue(out["passed"])
            self.assertTrue(out["frozen_ui_initialized"])
            self.assertEqual(out["original_console_profiles"],18)
            for flag in ("camera_hardware_tested","physical_qa_approved",
                         "license_review_approved","public_binary_distribution_approved"):
                self.assertIs(out[flag],False)

    def test_no_native_tk_report_or_wrong_exit_code_rejected(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            exe=root/"FAKE_UNRUNNABLE_NOT_A_REAL_EXE.exe"
            exe.write_bytes(b"MZ"+b"unit fixture never executed"*12000)
            with patch.dict(BINARIES,{"windows-x64":exe}), \
                 patch("tools.probe_v30_frozen_gui_launch.subprocess.run",
                       return_value=SimpleNamespace(returncode=0,stdout="",stderr="")):
                missing=prove_frozen_window("windows-x64",root/"missing.json")
            self.assertFalse(missing["passed"])
            def failure(args,env,**kwargs):
                Path(env["AP_V30_UI_SMOKE_REPORT"]).write_text(json.dumps(original_child()))
                return SimpleNamespace(returncode=2,stdout="",stderr="GUI failed")
            with patch.dict(BINARIES,{"windows-x64":exe}), \
                 patch("tools.probe_v30_frozen_gui_launch.subprocess.run",
                       side_effect=failure):
                bad=prove_frozen_window("windows-x64",root/"wrong-exit.json")
            self.assertFalse(bad["passed"])

    def test_false_hardware_rights_or_nonfrozen_child_are_not_accepted(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);exe=root/"FAKE_NONEXECUTABLE.bin"
            exe.write_bytes(b"fake source unit never executed"*12000)
            for i,(attr,value) in enumerate((
                    ("physical_qa_approved",True),
                    ("public_distribution_approved",True),
                    ("frozen_binary",False),
                    ("actual_tk_mainloop_ran",False),
                    ("console_profile_count",11),
            )):
                def fake_run(args,env,**kwargs):
                    record=original_child();record[attr]=value
                    Path(env["AP_V30_UI_SMOKE_REPORT"]).write_text(json.dumps(record))
                    return SimpleNamespace(returncode=0,stdout="",stderr="")
                with patch.dict(BINARIES,{"linux-x64":exe}), \
                     patch("tools.probe_v30_frozen_gui_launch.subprocess.run",
                           side_effect=fake_run):
                    output=prove_frozen_window("linux-x64",root/f"wrong-{i}.json")
                self.assertFalse(output["passed"])

    def test_four_real_installer_jobs_required_not_just_libretro_native_probes(self):
        base=Path(__file__).resolve().parents[1]
        text=(base/".github/workflows/v30-eight-source-offline-integration.yml").read_text("utf-8")
        self.assertIn("tools/probe_v30_frozen_gui_launch.py",text)
        self.assertIn("ACTUAL_FROZEN_GUI_STARTUP_UNAPPROVED.json",text)
        self.assertIn("xvfb-run",text)
        for name in ("windows-x64","linux-x64","macos-arm64","macos-x64"):
            self.assertIn("target: "+name,text)
        code=(base/"app.py").read_text("utf-8")
        self.assertIn("--ap-v30-ui-smoke",code)
        self.assertIn("root.mainloop()",code)
        self.assertIn("App(root)",code)
        self.assertIn('"frozen_binary"',code)
        self.assertIn("AP_V30_UI_SMOKE_CHECK",code)


if __name__ == "__main__":
    unittest.main()
