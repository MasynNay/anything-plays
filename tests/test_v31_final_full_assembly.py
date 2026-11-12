"""Fail-closed final 3.1.0 source/core receipt and identity contracts."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch
import unittest

from tools.v31_final_source import (
    checked_final_source_revision, require_final_receipt,
    STAGE_STATUS, FULL_STATUS,
)
from tools.assemble_v31_full_linux import FINAL_PREVIEW as LINUX, FINAL_FULL as LINUX_FULL
from tools.assemble_v31_full_windows import (
    FINAL_PREVIEW as WINDOWS, FINAL_FULL as WINDOWS_FULL, full_installer_filename,
)
from tools.assemble_v31_full_macos import verify_inputs as verify_macos_inputs

SHA = "a" * 40
DIGEST = "b" * 64
ENV = {
    "AP_V31_FINAL_CANDIDATE": "1",
    "AP_V31_FULL_TEST_CORES": "1",
    "AP_V31_QA_CHECKOUT_SHA": SHA,
    "AP_V31_PREVIEW": "0", "AP_V31_RC": "0", "AP_V31_RC2": "0",
    "AP_RELEASE_BUILD": "0", "AP_V30_APPROVED_RELEASE": "0",
    "AP_V30_STABLE_CANDIDATE": "0",
    "AP_V30_TEST_CORES": "0", "AP_V30_GPL_TRIAL": "0", "AP_V30_TIA_TRIAL": "0",
}

class FinalFullContracts(unittest.TestCase):
    def test_final_core_reuse_is_source_pinned_and_never_release_approved(self):
        from fetch_mgba_core import core_names_for_build
        isolated = {**ENV, "AP_V31_NEXT_QA": "1"}
        with patch.dict("os.environ", isolated, clear=True):
            names = core_names_for_build()
            self.assertEqual(len(names), 11)
            self.assertEqual(len(set(names)), 11)
            self.assertIn("mgba", names)
            self.assertIn("dolphin", names)
        # The new final identity must never permit production flags,
        # mixing historical RC channels, or unpinned source artifacts.
        for flag, invalid in (
            ("AP_V31_FINAL_CANDIDATE", "0"),
            ("AP_V31_RC2", "1"),
            ("AP_V31_RC", "1"),
            ("AP_V31_PREVIEW", "1"),
            ("AP_V31_NEXT_QA", "0"),
            ("AP_V31_QA_CHECKOUT_SHA", ""),
            ("AP_V31_QA_CHECKOUT_SHA", "invalid"),
            ("AP_RELEASE_BUILD", "1"),
            ("AP_V30_APPROVED_RELEASE", "1"),
            ("AP_V30_STABLE_CANDIDATE", "1"),
        ):
            with self.subTest(flag=flag, value=invalid), patch.dict(
                "os.environ", {**isolated, flag: invalid}, clear=True
            ), self.assertRaises(ValueError):
                core_names_for_build()

    def test_valid_exact_checkout_and_reject_mixed_approvals(self):
        self.assertEqual(checked_final_source_revision(SHA, environ=ENV, checkout=SHA), SHA)
        for key, value in (("AP_V31_FINAL_CANDIDATE", "0"),
                           ("AP_V31_FULL_TEST_CORES", "0"),
                           ("AP_V31_QA_CHECKOUT_SHA", "c" * 40),
                           ("AP_V31_RC2", "1"), ("AP_V31_RC", "1"),
                           ("AP_V31_PREVIEW", "1"), ("AP_RELEASE_BUILD", "1"),
                           ("AP_V30_APPROVED_RELEASE", "1"),
                           ("AP_V30_STABLE_CANDIDATE", "1"),
                           ("AP_V30_TEST_CORES", "1"),
                           ("AP_V30_GPL_TRIAL", "1"),
                           ("AP_V30_TIA_TRIAL", "1")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                checked_final_source_revision(SHA, environ={**ENV,key:value}, checkout=SHA)
        with self.assertRaises(ValueError):
            checked_final_source_revision(SHA, environ=ENV, checkout="c"*40)
        with self.assertRaises(ValueError):
            checked_final_source_revision("invalid", environ=ENV, checkout=SHA)

    def test_source_receipt_requires_same_3_1_identity_and_complete_integrity(self):
        receipt={
            "schema_version":1,
            "status":STAGE_STATUS,
            "target":"linux-x64",
            "source_revision":SHA,
            "installer":LINUX,
            "sha256":DIGEST,
            "size_bytes":4000000,
            "version":"3.1.0",
            "identity_channel":"final_candidate",
            "settings_namespace":"anything-plays-31",
            "public_release_approved":False,
            "only_mgba_source_stage":True,
            "native_core_count":1,
            "full_18_console_release_ready":False,
            "relinking_approved":False,
        }
        args=dict(source=SHA,target="linux-x64",installer=LINUX,digest=DIGEST,size=4000000)
        self.assertTrue(require_final_receipt(receipt,**args))
        for key, bad in (
            ("source_revision", "c"*40), ("installer", "anything-plays-31-rc2.deb"),
            ("sha256", "d"*64), ("size_bytes", 4000001),
            ("status", "PUBLISHED"), ("schema_version", 0),
            ("version", "3.1.0~rc2"), ("native_core_count", 11),
            ("only_mgba_source_stage", False),
            ("identity_channel", "rc2"), ("settings_namespace", "anything-plays-31-rc2"),
            ("relinking_approved", True), ("public_release_approved", True),
            ("full_18_console_release_ready", True),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                require_final_receipt({**receipt,key:bad},**args)
        with self.assertRaises(ValueError):
            require_final_receipt(receipt,**{**args,"size":0})

    def test_full_names_really_are_stable_version_not_rc2_and_no_collisions(self):
        self.assertEqual(LINUX, "anything-plays-31_3.1.0_amd64.deb")
        self.assertEqual(LINUX_FULL, LINUX)
        self.assertEqual(WINDOWS, "AnythingPlaysSetup-3.1.0.exe")
        self.assertEqual(WINDOWS_FULL, WINDOWS)
        self.assertEqual(full_installer_filename(final=True), WINDOWS)
        self.assertNotEqual(full_installer_filename(rc2=True), WINDOWS)
        for args in (dict(rc1=True,final=True),dict(rc2=True,final=True),
                     dict(rc1=True,rc2=True,final=True)):
            with self.assertRaises(ValueError):
                full_installer_filename(**args)


if __name__ == "__main__":
    unittest.main()
