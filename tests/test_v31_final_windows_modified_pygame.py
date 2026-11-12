"""Fail-closed actual final Windows pygame C replacement staging tests."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import hashlib
import os
import struct
import unittest
import zipfile

from tools import verify_v31_final_windows_modified_pygame as check
from tools.build_v31_modified_pygame_probe import PYGAME_COMMIT, PROBE_VALUE
from tools.build_v31_modified_pygame_windows import PINNED_CHANGED_C_SHA256


def pe():
    b=bytearray(45_000)
    b[:2]=b"MZ"
    struct.pack_into("<I",b,0x3C,0x80)
    b[0x80:0x84]=b"PE\\0\\0".replace(b"\\0",b"\x00")
    struct.pack_into("<H",b,0x84,0x8664)
    return bytes(b)


class CleanFinalWindowsPygameTests(unittest.TestCase):
    def fixture(self, base):
        base=Path(base)
        app=base/"installed"
        native=app/check.RELATIVE
        native.parent.mkdir(parents=True)
        native.write_bytes(b"authentic-upstream-extension" * 1800)
        installer=base/check.INSTALLER_NAME
        installer.write_bytes(os.urandom(1_060_000))
        wheel=base/check.ORIGINAL_WHEEL
        with zipfile.ZipFile(wheel,"w",compression=zipfile.ZIP_STORED) as z:
            z.writestr("pygame/base.cp313-win_amd64.pyd",native.read_bytes())
            z.writestr("pygame/wheel-fixture.bin",os.urandom(1_040_000))
        compiled=base/"source-compiled"/check.OUTPUT_NAME
        compiled.parent.mkdir()
        compiled.write_bytes(pe())
        receipt={
            "target":"windows-x64","installer":installer.name,
            "sha256":check.digest(installer),
            "source_preview_revision":check.APP_SOURCE_SHA,
            "identity_channel":"final_candidate",
            "settings_namespace":"anything-plays-31",
            "native_core_count":11,"console_profiles":18,
            "status":"PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA",
            "public_release_approved":False,"final_release_approved":False,
        }
        audit={
            "target":"windows-x64","source_revision":check.APP_SOURCE_SHA,
            "status":"UNAPPROVED_EXACT_FINAL_3_1_NATIVE_AND_NOTICE_INVENTORY",
            "public_release_approved":False,
            "native_files":[{"path":check.RELATIVE.as_posix(),
                             "sha256":check.digest(native)}],
        }
        change={
            "original_source_revision":PYGAME_COMMIT,
            "original_base_c_sha256":"0"*64,
            "patched_base_c_sha256":PINNED_CHANGED_C_SHA256,
            "expected_modified_native_method":"_ap31_relink_probe",
            "expected_modified_native_result":PROBE_VALUE,
            "not_official_unmodified_pygame_wheel":True,
            "full_lgpl_compliance_approved":False,
            "stable_3_1_release_approved":False,
        }
        return dict(bundle=app,installer=installer,receipt=receipt,audit=audit,
                    original_wheel=wheel,source_receipt=change,
                    compiled=compiled,destination=base/"separate-copied-app")

    def run_stage(self, args):
        with patch.object(check,"ORIGINAL_WHEEL_SHA",check.digest(args["original_wheel"])):
            return check.stage(**args)

    def test_actual_source_modified_pe_staged_in_isolated_copy(self):
        with TemporaryDirectory() as tmp:
            a=self.fixture(tmp)
            original_sha=check.digest(a["bundle"]/check.RELATIVE)
            r=self.run_stage(a)
            self.assertEqual(r["status"],check.STATUS)
            self.assertEqual(r["source_app_commit"],check.APP_SOURCE_SHA)
            self.assertTrue(r["source_modified_native_distinct_pe_amd64"])
            self.assertEqual(check.digest(a["bundle"]/check.RELATIVE),original_sha)
            self.assertEqual((a["destination"]/check.RELATIVE).read_bytes(),pe())
            self.assertFalse(r["public_release_approved"])
            self.assertFalse(r["all_lgpl_native_relinking_verified"])
            self.assertFalse(r["real_modified_c_method_executed"])

    def test_fail_closed_on_wrong_final_identity_legal_flags_and_wheel(self):
        with TemporaryDirectory() as tmp:
            a=self.fixture(tmp)
            for key,value in (
                ("source_preview_revision","f"*40),
                ("native_core_count",1),
                ("public_release_approved",True),
                ("final_release_approved",True),
            ):
                with self.subTest(key=key):
                    modified=dict(a,receipt={**a["receipt"],key:value})
                    with self.assertRaises(ValueError):self.run_stage(modified)
            for key,value in (
                ("original_source_revision","b"*40),
                ("full_lgpl_compliance_approved",True),
                ("stable_3_1_release_approved",True),
                ("patched_base_c_sha256","0"*64),
            ):
                with self.subTest(key=key):
                    modified=dict(a,source_receipt={**a["source_receipt"],key:value})
                    with self.assertRaises(ValueError):self.run_stage(modified)
            modified=dict(a,audit={**a["audit"],"source_revision":"f"*40})
            with self.assertRaises(ValueError):self.run_stage(modified)
            with self.assertRaises(ValueError):
                self.run_stage({**a,"destination":a["bundle"]})
            with self.assertRaises(ValueError):
                self.run_stage({**a,"compiled":a["bundle"]/check.RELATIVE})
            with patch.object(check,"ORIGINAL_WHEEL_SHA","0"*64):
                with self.assertRaises(ValueError):check.stage(**a)

    def test_reject_non_x64_native_and_tampered_original(self):
        with TemporaryDirectory() as tmp:
            a=self.fixture(tmp)
            compiled=a["compiled"]
            data=bytearray(compiled.read_bytes())
            struct.pack_into("<H",data,0x84,0x14c)
            compiled.write_bytes(data)
            with self.assertRaises(ValueError):self.run_stage(a)
            compiled.write_bytes(pe())
            (a["bundle"]/check.RELATIVE).write_bytes(b"modified-original" * 3000)
            with self.assertRaises(ValueError):self.run_stage(a)


if __name__=="__main__":
    unittest.main()
