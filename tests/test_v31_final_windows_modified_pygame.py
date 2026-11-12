"""Exact clean final Windows source-modified pygame native acceptance guards."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
import unittest
import zipfile
from tools import verify_v31_final_windows_modified_pygame as qa
from tools.build_v31_modified_pygame_probe import PYGAME_COMMIT, PROBE_VALUE
from tools.build_v31_modified_pygame_windows import PINNED_CHANGED_C_SHA256

class FinalWindowsNativeTests(unittest.TestCase):
    def inputs(self,root):
        root=Path(root)
        app=root/"extracted";original=app/qa.RELATIVE_PATH
        original.parent.mkdir(parents=True)
        original.write_bytes(os.urandom(30_000))
        installer=root/qa.INSTALLER_NAME
        installer.write_bytes(os.urandom(1_050_000))
        wheel=root/qa.WHEEL_NAME
        with zipfile.ZipFile(wheel,"w",zipfile.ZIP_STORED) as z:
            z.writestr("pygame/base.cp313-win_amd64.pyd",original.read_bytes())
            z.writestr("pygame/pad.bin",os.urandom(1_100_000))
        audit={"target":"windows-x64","source_revision":qa.SOURCE_SHA,
               "native_files":[{"path":qa.RELATIVE_PATH.as_posix(),"sha256":qa.digest(original)}]}
        receipt={"target":"windows-x64","installer":qa.INSTALLER_NAME,
                 "sha256":qa.digest(installer),"source_preview_revision":qa.SOURCE_SHA,
                 "identity_channel":"final_candidate","settings_namespace":"anything-plays-31",
                 "native_core_count":11,"console_profiles":18,
                 "status":"PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA",
                 "public_release_approved":False,"final_release_approved":False}
        manifest={"original_source_revision":PYGAME_COMMIT,
                  "patched_base_c_sha256":PINNED_CHANGED_C_SHA256,
                  "original_base_c_sha256":"0"*64,
                  "expected_modified_native_method":"_ap31_relink_probe",
                  "expected_modified_native_result":PROBE_VALUE,
                  "not_official_unmodified_pygame_wheel":True,
                  "full_lgpl_compliance_approved":False,
                  "stable_3_1_release_approved":False}
        compiled=root/"compiled"/"base.cp313-win_amd64.pyd"
        compiled.parent.mkdir()
        compiled.write_bytes(os.urandom(40_000))
        return app,installer,receipt,audit,wheel,manifest,compiled,root/"copy"

    def test_frozen_final_native_must_match_pinned_wheel_and_sha_inventory(self):
        with TemporaryDirectory() as tmp:
            app,installer,receipt,audit,wheel,manifest,compiled,dest=self.inputs(tmp)
            with patch.object(qa,"WHEEL_SHA256",qa.digest(wheel)):
                old,slice,member=qa.validate_original(app,installer,receipt,audit,wheel,"windows-x64")
                self.assertEqual(old,app/qa.RELATIVE_PATH)
                self.assertEqual(member,"pygame/base.cp313-win_amd64.pyd")
                for name,bad in [("source_preview_revision","0"*40),
                                 ("native_core_count",1),
                                 ("public_release_approved",True),
                                 ("final_release_approved",True)]:
                    with self.subTest(name=name),self.assertRaises(ValueError):
                        qa.validate_original(app,installer,{**receipt,name:bad},audit,wheel,"windows-x64")
                with self.assertRaises(ValueError):
                    qa.validate_original(app,installer,receipt,{**audit,"native_files":[]},wheel,"windows-x64")
                with self.assertRaises(ValueError):
                    qa.validate_original(app,installer,receipt,{**audit,"source_revision":"0"*40},wheel,"windows-x64")

    def test_modified_source_copy_executes_no_approval_and_original_unchanged(self):
        with TemporaryDirectory() as tmp:
            app,installer,receipt,audit,wheel,manifest,compiled,dest=self.inputs(tmp)
            orig_hash=qa.digest(app/qa.RELATIVE_PATH)
            with patch.object(qa,"WHEEL_SHA256",qa.digest(wheel)),patch.object(qa,"validate_pe_amd64",return_value=40_000):
                result=qa.stage(app,installer,receipt,audit,wheel,manifest,compiled,dest)
            self.assertEqual(qa.digest(app/qa.RELATIVE_PATH),orig_hash)
            self.assertEqual(qa.digest(dest/qa.RELATIVE_PATH),qa.digest(compiled))
            self.assertEqual(result["original_source_commit"],qa.SOURCE_SHA)
            self.assertFalse(result["all_lgpl_relinking_requirements_approved"])
            self.assertFalse(result["stable_3_1_release_approved"])

    def test_forged_approval_or_writable_original_rejected(self):
        with TemporaryDirectory() as tmp:
            app,installer,receipt,audit,wheel,manifest,compiled,dest=self.inputs(tmp)
            with patch.object(qa,"WHEEL_SHA256",qa.digest(wheel)),patch.object(qa,"validate_pe_amd64",return_value=40_000):
                for key,val in [("full_lgpl_compliance_approved",True),
                                ("stable_3_1_release_approved",True),
                                ("original_source_revision","0"*40),
                                ("patched_base_c_sha256","f"*64)]:
                    with self.subTest(key=key),self.assertRaises(ValueError):
                        qa.stage(app,installer,receipt,audit,wheel,{**manifest,key:val},compiled,dest)
                with self.assertRaises(ValueError):
                    qa.stage(app,installer,receipt,audit,wheel,manifest,compiled,app/"bad")
                compiled.write_bytes((app/qa.RELATIVE_PATH).read_bytes())
                with self.assertRaises(ValueError):
                    qa.stage(app,installer,receipt,audit,wheel,manifest,compiled,dest)

if __name__=="__main__":
    unittest.main()
