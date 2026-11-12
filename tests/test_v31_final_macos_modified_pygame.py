"""Fail-closed source-modified pygame C replacement tests for clean final Macs."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import unittest
import zipfile

from tools import verify_v31_final_macos_modified_pygame as check
from tools.build_v31_modified_pygame_probe import PYGAME_COMMIT, PROBE_VALUE


class MacCleanFinalPygameTests(unittest.TestCase):
    def fixture(self, root, target="macos-arm64"):
        root=Path(root)
        app=root/"AnythingPlays31.app"
        frozen=app/check.FROZEN_PATH
        frozen.parent.mkdir(parents=True)
        frozen.write_bytes(b"original signed pygame native")
        original=root/check.EXPECTED[target]
        original.write_bytes(os.urandom(1_050_000))
        modified=root/"compiled"/"base.cpython-313-darwin.so"
        modified.parent.mkdir()
        modified.write_bytes(os.urandom(10_000))
        wheel=root/check.WHEEL_NAME
        with zipfile.ZipFile(wheel,"w",zipfile.ZIP_STORED) as archive:
            archive.writestr("pygame/base.cpython-313-darwin.so",b"official MachO wheel")
            archive.writestr("pygame/extra.bin",os.urandom(1_100_000))
        receipt={
            "target":target,"installer":original.name,"sha256":check.sha(original),
            "source_preview_revision":check.APP_SOURCE_SHA,
            "identity_channel":"final_candidate","settings_namespace":"anything-plays-31",
            "native_core_count":11,"console_profiles":18,
            "status":"PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA",
            "public_release_approved":False,"final_release_approved":False,
        }
        audit={"target":target,"source_revision":check.APP_SOURCE_SHA,
               "native_files":[{"path":check.FROZEN_PATH,"sha256":check.sha(frozen)}]}
        source={
            "original_source_revision":PYGAME_COMMIT,
            "expected_modified_native_method":"_ap31_relink_probe",
            "expected_modified_native_result":PROBE_VALUE,
            "full_lgpl_compliance_approved":False,
            "stable_3_1_release_approved":False,
            "original_base_c_sha256":"a"*64,
            "patched_base_c_sha256":"b"*64,
            "not_official_unmodified_pygame_wheel":True,
        }
        return app,original,receipt,audit,wheel,modified,source,root/"copied.app"

    def test_exact_final_receipt_and_native_sha_required(self):
        with TemporaryDirectory() as temp:
            app,original,receipt,audit,wheel,modified,source,out=self.fixture(temp)
            with patch.object(check,"WHEEL_SHA256",check.sha(wheel)),\
                 patch.object(check,"thin_slice",return_value=b"official slice"),\
                 patch.object(check,"executable_text_fingerprint",return_value={"sha256":"abc"}):
                x=check.validate_inputs(app,original,receipt,audit,wheel,"macos-arm64")
                self.assertEqual(x[0],app/check.FROZEN_PATH)
                self.assertEqual(x[2]["sha256"],"abc")
                for key,val in [
                    ("source_preview_revision","0"*40),
                    ("native_core_count",1),("console_profiles",17),
                    ("status","APPROVED"),("public_release_approved",True),
                    ("final_release_approved",True)]:
                    with self.subTest(field=key),self.assertRaises(ValueError):
                        check.validate_inputs(app,original,{**receipt,key:val},
                                              audit,wheel,"macos-arm64")
                with self.assertRaises(ValueError):
                    check.validate_inputs(app,original,receipt,
                        {**audit,"source_revision":"f"*40},wheel,"macos-arm64")
                with self.assertRaises(ValueError):
                    check.validate_inputs(app,original,receipt,
                        {**audit,"native_files":[]},wheel,"macos-arm64")

    def test_genuine_modified_native_only_in_fresh_app_copy(self):
        with TemporaryDirectory() as temp:
            app,installer,receipt,audit,wheel,compiled,source,dest=self.fixture(temp)
            original_sha=check.sha(app/check.FROZEN_PATH)
            original_slice=b"original official slice"
            def fingerprint(data,arch):
                if data==compiled.read_bytes():
                    return {"sha256":"changed"}
                return {"sha256":"original"}
            with patch.object(check,"validate_inputs",return_value=(
                app/check.FROZEN_PATH,original_slice,{"sha256":"original"})),\
                patch.object(check,"executable_text_fingerprint",side_effect=fingerprint):
                result=check.stage(app,installer,receipt,audit,wheel,
                                   compiled,source,"macos-arm64",dest)
            self.assertEqual(check.sha(app/check.FROZEN_PATH),original_sha)
            self.assertEqual(check.sha(dest/check.FROZEN_PATH),check.sha(compiled))
            self.assertEqual(result["original_app_source_commit"],check.APP_SOURCE_SHA)
            self.assertFalse(result["stable_3_1_release_approved"])
            self.assertFalse(result["complete_lgpl_section_6_source_and_relinking_approved"])

    def test_forbid_forged_source_and_destinations(self):
        with TemporaryDirectory() as temp:
            app,installer,receipt,audit,wheel,compiled,source,dest=self.fixture(temp)
            with patch.object(check,"validate_inputs",return_value=(
                app/check.FROZEN_PATH,b"official",{"sha256":"original"})),\
                patch.object(check,"executable_text_fingerprint",
                    side_effect=lambda data,arch:{"sha256":"changed"}
                    if data==compiled.read_bytes() else {"sha256":"original"}):
                for key,value in [
                    ("original_source_revision","0"*40),
                    ("full_lgpl_compliance_approved",True),
                    ("stable_3_1_release_approved",True),
                    ("patched_base_c_sha256",source["original_base_c_sha256"])]:
                    with self.subTest(field=key),self.assertRaises(ValueError):
                        check.stage(app,installer,receipt,audit,wheel,
                                    compiled,{**source,key:value},
                                    "macos-arm64",dest)
                with self.assertRaises(ValueError):
                    check.stage(app,installer,receipt,audit,wheel,
                                compiled,source,"macos-arm64",app/"bad.app")


if __name__=="__main__":
    unittest.main()
