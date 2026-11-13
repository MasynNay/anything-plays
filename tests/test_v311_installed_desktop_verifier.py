"""No fake source-only installer or physical acceptance as installed 3.1.1."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.build_identity import make_identity
from tools.verify_v311_installed_smoke import QA_STATUS, verify
from tools.verify_v311_stable_source_stage import INSTALLERS, digest
from tools.probe_v30_installed_desktop_window import STATUS as SMOKE_STATUS

SHA="a"*40
SMOKE={
    "schema_version":1,"status":SMOKE_STATUS,
    "passed":True,"frozen_binary":True,"actual_tk_window_started":True,
    "actual_app_initialized":True,"actual_tk_mainloop_ran":True,
    "console_profile_count":18,"top_level_widgets":1,
    "initialized_system":"gba","error":None,
    "stream_output_window_opened":True,"stream_closed_cleanly":True,
    "stream_appearance_configured":True,
    "camera_hardware_tested":False,"gameplay_hardware_tested":False,
    "physical_qa_approved":False,"public_distribution_approved":False,
}
NATIVE={
    "native_core_count":11,"total_source_built_core_families":11,
    "all_console_profiles":18,
    "source_built_tia":{"sha256":"x"},"source_built_dolphin":{"sha256":"y"},
}


class Version311FrozenInstalledQATests(unittest.TestCase):
    def sample(self,root,target="linux-x64"):
        root=Path(root)
        archive=root/INSTALLERS[target]
        archive.write_bytes(b"0"*(1024*1024+5))
        app=root/"installed"
        marker=app/"assets/v31_build_identity.json"
        marker.parent.mkdir(parents=True)
        marker.write_text(json.dumps(make_identity("v311_stable_candidate")),"utf-8")
        base={
            "status":QA_STATUS[target],"target":target,"installer":archive.name,
            "version":"3.1.1","identity_channel":"v311_stable_candidate",
            "settings_namespace":"anything-plays-31",
            "stable_in_place_update":True,"native_core_count":11,
            "console_profiles":18,"public_release_approved":False,
            "full_four_platform_311_verified":False,
        }
        if target=="linux-x64":
            base.update({"installer_sha256":digest(archive),"app_source_sha":SHA})
        else:
            base.update({"sha256":digest(archive),"new_source_revision":SHA})
        return archive,app,base

    def test_real_installed_verified_evidence_and_tampering(self):
        with TemporaryDirectory() as temp:
            binary,app,receipt=self.sample(temp)
            with patch("tools.verify_v311_installed_smoke.validate_trial_core_directory",
                       return_value=NATIVE):
                good=verify("linux-x64",binary,app,receipt,SMOKE,SHA)
                self.assertEqual(good["console_profiles"],18)
                self.assertFalse(good["public_release_approved"])
                for key,value in [
                    ("native_core_count",1),
                    ("console_profiles",3),
                    ("identity_channel","v311_candidate"),
                    ("settings_namespace","anything-plays-311-candidate"),
                    ("stable_in_place_update",False),
                    ("public_release_approved",True),
                    ("installer_sha256","0"*64),
                    ("app_source_sha","f"*40),
                ]:
                    with self.subTest(key=key),self.assertRaises(ValueError):
                        verify("linux-x64",binary,app,{**receipt,key:value},SMOKE,SHA)
                for key,value in [
                    ("passed",False),
                    ("stream_output_window_opened",False),
                    ("actual_tk_mainloop_ran",False),
                    ("physical_qa_approved",True),
                ]:
                    with self.subTest(key=key),self.assertRaises(ValueError):
                        verify("linux-x64",binary,app,receipt,
                               {**SMOKE,key:value},SHA)

    def test_qa_identity_and_core_count_do_not_count_as_full_stable_install(self):
        with TemporaryDirectory() as temp:
            binary,app,receipt=self.sample(temp)
            marker=app/"assets/v31_build_identity.json"
            marker.write_text(json.dumps(make_identity("v311_candidate")),"utf-8")
            with patch("tools.verify_v311_installed_smoke.validate_trial_core_directory",
                       return_value=NATIVE),self.assertRaises(ValueError):
                verify("linux-x64",binary,app,receipt,SMOKE,SHA)
            marker.write_text(json.dumps(make_identity("v311_stable_candidate")),"utf-8")
            with patch("tools.verify_v311_installed_smoke.validate_trial_core_directory",
                       return_value={**NATIVE,"native_core_count":1}),self.assertRaises(ValueError):
                verify("linux-x64",binary,app,receipt,SMOKE,SHA)

    def test_source_revision_and_file_bytes_are_not_interchangeable(self):
        with TemporaryDirectory() as temp:
            binary,app,receipt=self.sample(temp)
            with patch("tools.verify_v311_installed_smoke.validate_trial_core_directory",
                       return_value=NATIVE):
                with self.assertRaises(ValueError):
                    verify("linux-x64",binary,app,receipt,SMOKE,"badsha")
                binary.write_bytes(binary.read_bytes()+b"tamper")
                with self.assertRaises(ValueError):
                    verify("linux-x64",binary,app,receipt,SMOKE,SHA)


if __name__=="__main__":
    unittest.main()
