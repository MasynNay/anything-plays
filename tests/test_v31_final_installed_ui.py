"""Fail closed on tampered final 3.1.0 frozen GUI and settings evidence."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from anything_plays.build_identity import make_identity
from tools.qa_v31_final_installed_preferences import seed, verify
from tools.verify_v31_final_installed_ui import (
    FILENAMES, SMOKE_STATUS, hash_file, verify_installed_final,
)
from tools.v31_final_source import FULL_STATUS

SOURCE="a"*40
SMOKE={
    "status":SMOKE_STATUS,"passed":True,
    "actual_tk_window_started":True,"actual_app_initialized":True,
    "actual_tk_mainloop_ran":True,"frozen_binary":True,
    "console_profile_count":18,"stream_output_window_opened":True,
    "stream_settings_separate":True,"stream_appearance_configured":True,
    "stream_camera_reference_rendered":True,"stream_closed_cleanly":True,
    "top_level_widgets":1,"initialized_system":"gba","error":None,
    "camera_hardware_tested":False,"gameplay_hardware_tested":False,
    "physical_qa_approved":False,"public_distribution_approved":False,
}

class FinalInstalledTests(unittest.TestCase):
    def sample(self, root, target="linux-x64"):
        root=Path(root)
        binary=root/FILENAMES[target]
        binary.write_bytes(b"fake source-matched package" * 50000)
        bundle=root/"app"
        marker=bundle/"assets/v31_build_identity.json"
        marker.parent.mkdir(parents=True)
        marker.write_text(json.dumps(make_identity("final_candidate")),"utf-8")
        receipt={
            "status":FULL_STATUS,
            "target":target,
            "installer":binary.name,
            "sha256":hash_file(binary),
            "source_preview_revision":SOURCE,
            "identity_channel":"final_candidate",
            "settings_namespace":"anything-plays-31",
            "native_core_count":11,
            "console_profiles":18,
            "public_release_approved":False,
            "final_release_approved":False,
        }
        return binary,bundle,receipt

    def test_four_real_version_names_and_no_old_candidate_labels(self):
        self.assertEqual(set(FILENAMES),{"linux-x64","windows-x64","macos-arm64","macos-x64"})
        self.assertTrue(all("3.1.0" in name for name in FILENAMES.values()))
        self.assertTrue(all("rc2" not in name and "preview" not in name for name in FILENAMES.values()))

    def test_full_installed_smoke_and_source_sha_checks(self):
        with TemporaryDirectory() as tmp:
            binary,bundle,receipt=self.sample(tmp)
            report=verify_installed_final("linux-x64",binary,bundle,receipt,SMOKE,SOURCE)
            self.assertEqual(report["console_profiles"],18)
            self.assertFalse(report["public_release_approved"])
            for name,invalid in (("identity_channel","rc2"),
                                 ("settings_namespace","anything-plays-31-rc2"),
                                 ("source_preview_revision","b"*40),
                                 ("status","READY_FOR_PUBLICATION"),
                                 ("native_core_count",1),
                                 ("console_profiles",3),
                                 ("public_release_approved",True),
                                 ("final_release_approved",True),
                                 ("sha256","c"*64)):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    verify_installed_final("linux-x64",binary,bundle,
                                           {**receipt,name:invalid},SMOKE,SOURCE)
            for name,invalid in (("passed",False),("stream_output_window_opened",False),
                                 ("stream_settings_separate",False),
                                 ("stream_appearance_configured",False),
                                 ("stream_camera_reference_rendered",False),
                                 ("stream_closed_cleanly",False),
                                 ("physical_qa_approved",True),
                                 ("public_distribution_approved",True),
                                 ("actual_tk_mainloop_ran",False),("top_level_widgets",0)):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    verify_installed_final("linux-x64",binary,bundle,receipt,
                                           {**SMOKE,name:invalid},SOURCE)
            marker=bundle/"assets/v31_build_identity.json"
            marker.write_text(json.dumps(make_identity("rc2")),"utf-8")
            with self.assertRaises(ValueError):
                verify_installed_final("linux-x64",binary,bundle,receipt,SMOKE,SOURCE)
            marker.write_text(json.dumps(make_identity("final_candidate")),"utf-8")
            binary.write_bytes(binary.read_bytes()+b"tampered")
            with self.assertRaises(ValueError):
                verify_installed_final("linux-x64",binary,bundle,receipt,SMOKE,SOURCE)

    def test_final_copies_rc2_and_preserves_three_previous_settings_namespaces(self):
        from anything_plays.test_preferences import prepare_test_preferences, RC2_DIR, FINAL_DIR
        with TemporaryDirectory() as tmp:
            base=Path(tmp)
            home=base/"synthetic"
            home.mkdir()
            manifest=base/"fixture.json"
            seed(home,manifest=manifest)
            target=prepare_test_preferences(home,channel="final_candidate")
            self.assertEqual(target,home/FINAL_DIR/"preferences.json")
            (home/FINAL_DIR/"system_profiles.json").write_text('{"gba":{"zones":{}}}',"utf-8")
            report=verify(home,manifest=manifest)
            self.assertEqual(report["final_theme"],"Ocean Dark")
            self.assertTrue(report["rc2_preferences_and_profiles_unchanged"])
            self.assertTrue(report["rc1_preferences_and_profiles_unchanged"])
            self.assertTrue(report["stable_preferences_and_profiles_unchanged"])
            with self.assertRaises(ValueError):
                seed(home,manifest=manifest)
            (home/RC2_DIR/"preferences.json").write_text('{"theme":"tampered"}',"utf-8")
            with self.assertRaises(ValueError):
                verify(home,manifest=manifest)

    def test_symlinked_final_preferences_refused(self):
        from anything_plays.test_preferences import FINAL_DIR, RC2_DIR
        with TemporaryDirectory() as tmp:
            base=Path(tmp)
            home=base/"synthetic"
            home.mkdir()
            manifest=base/"fixture.json"
            seed(home,manifest=manifest)
            target=home/FINAL_DIR
            target.mkdir()
            try:
                (target/"preferences.json").symlink_to(home/RC2_DIR/"preferences.json")
            except (OSError, NotImplementedError):
                self.skipTest("No symlink support")
            with self.assertRaises(ValueError):
                verify(home,manifest=manifest)

if __name__=="__main__":
    unittest.main()
