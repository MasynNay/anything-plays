"""Adversarial exact clean final pygame changed-source replacement tests."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_STORED

from tools.build_v31_modified_pygame_probe import PYGAME_COMMIT, PROBE_VALUE
from tools import verify_v31_final_linux_pygame_modified_source as qa

def sha(data):
    return hashlib.sha256(data).hexdigest()

class ExactFinalModifiedPygameTests(unittest.TestCase):
    def fixture(self, root):
        root=Path(root)
        bundle=root/"original"
        native=bundle/qa.RELATIVE
        native.parent.mkdir(parents=True)
        original=os.urandom(125_000)
        native.write_bytes(original)
        installer=root/qa.INSTALLER_NAME
        installer.write_bytes(os.urandom(1_100_000))
        compiled=root/"independent"/qa.BASENAME
        compiled.parent.mkdir()
        compiled.write_bytes(os.urandom(125_000))
        wheel=root/qa.WHEEL_NAME
        with ZipFile(wheel,"w",ZIP_STORED) as archive:
            archive.writestr("pygame/"+qa.BASENAME,original)
            archive.writestr("pygame/safe-test-padding.bin",os.urandom(1_050_000))
        receipt={
            "target":"linux-x64",
            "installer":qa.INSTALLER_NAME,
            "sha256":qa.digest(installer),
            "source_preview_revision":qa.SOURCE_SHA,
            "identity_channel":"final_candidate",
            "settings_namespace":"anything-plays-31",
            "native_core_count":11,
            "console_profiles":18,
            "status":"PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA",
            "public_release_approved":False,
            "final_release_approved":False,
        }
        change={
            "original_source_revision":PYGAME_COMMIT,
            "expected_modified_native_method":"_ap31_relink_probe",
            "expected_modified_native_result":PROBE_VALUE,
            "not_official_unmodified_pygame_wheel":True,
            "full_lgpl_compliance_approved":False,
            "stable_3_1_release_approved":False,
            "original_base_c_sha256":sha(b"original"),
            "patched_base_c_sha256":sha(b"changed"),
        }
        return bundle,installer,receipt,wheel,change,compiled,root/"copied"

    def test_modified_native_is_really_replaced_in_copy_only(self):
        with TemporaryDirectory() as temp:
            bundle,installer,receipt,wheel,change,compiled,destination=self.fixture(temp)
            original=qa.digest(bundle/qa.RELATIVE)
            with patch.object(qa,"WHEEL_SHA256",qa.digest(wheel)):
                result=qa.stage(bundle=bundle,installer=installer,receipt=receipt,
                                wheel=wheel,source_change=change,compiled=compiled,
                                destination=destination)
            self.assertEqual(result["status"],
                "CLEAN_FINAL_3_1_LINUX_CHANGED_SOURCE_PYGAME_BASE_STAGED_NOT_LEGAL_APPROVAL")
            self.assertEqual(qa.digest(bundle/qa.RELATIVE),original)
            self.assertEqual(qa.digest(destination/qa.RELATIVE),qa.digest(compiled))
            self.assertFalse(result["lgpl_relinking_approved"])
            self.assertFalse(result["public_release_approved"])
            self.assertEqual(result["source_app_revision"],qa.SOURCE_SHA)

    def test_unsafe_or_forged_inputs_rejected(self):
        with TemporaryDirectory() as temp:
            bundle,installer,receipt,wheel,change,compiled,destination=self.fixture(temp)
            def attempt(**updates):
                args=dict(bundle=bundle,installer=installer,receipt=receipt,
                          wheel=wheel,source_change=change,compiled=compiled,
                          destination=destination)
                args.update(updates)
                with patch.object(qa,"WHEEL_SHA256",qa.digest(wheel)):
                    with self.assertRaises(ValueError):
                        qa.stage(**args)
            for key,value in (("source_preview_revision","0"*40),
                              ("native_core_count",1),
                              ("public_release_approved",True),
                              ("final_release_approved",True),
                              ("console_profiles",16)):
                with self.subTest(field=key):
                    attempt(receipt={**receipt,key:value})
            for key,value in (("original_source_revision","1"*40),
                              ("full_lgpl_compliance_approved",True),
                              ("original_base_c_sha256",change["patched_base_c_sha256"])):
                with self.subTest(field=key):
                    attempt(source_change={**change,key:value})
            attempt(destination=bundle/"nested")
            attempt(compiled=bundle/qa.RELATIVE)
            compiled.write_bytes((bundle/qa.RELATIVE).read_bytes())
            attempt()

    def test_official_wheel_hash_and_byte_correspondence_are_required(self):
        with TemporaryDirectory() as temp:
            bundle,installer,receipt,wheel,change,compiled,destination=self.fixture(temp)
            with self.assertRaises(ValueError):
                qa.stage(bundle=bundle,installer=installer,receipt=receipt,
                         wheel=wheel,source_change=change,compiled=compiled,
                         destination=destination)
            with ZipFile(wheel,"w",ZIP_STORED) as archive:
                archive.writestr("pygame/"+qa.BASENAME,os.urandom(125_000))
                archive.writestr("pygame/filler.bin",os.urandom(1_050_000))
            with patch.object(qa,"WHEEL_SHA256",qa.digest(wheel)):
                with self.assertRaises(ValueError):
                    qa.stage(bundle=bundle,installer=installer,receipt=receipt,
                             wheel=wheel,source_change=change,compiled=compiled,
                             destination=destination)

if __name__=="__main__":
    unittest.main()
