"""Adversarial private release-staging contracts for versioned 3.1.0."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.stage_v31_final_for_review import (
    FULL_STATUS, INSTALLED_STATUS, TARGETS, sha, stage,
)
SHA="a"*40


class StageV31FinalTests(unittest.TestCase):
    def fixture(self,root):
        root=Path(root)
        full=root/"full"
        installed=root/"installed"
        full.mkdir()
        installed.mkdir()
        for platform,(filename,receipt_file) in TARGETS.items():
            out=full/platform
            gui=installed/platform
            out.mkdir()
            gui.mkdir()
            binary=out/filename
            binary.write_bytes((platform+":").encode()*150000)
            self.assertGreater(binary.stat().st_size,1024*1024)
            digest=sha(binary)
            receipt={
                "status":FULL_STATUS,
                "target":platform,
                "installer":filename,
                "sha256":digest,
                "source_preview_revision":SHA,
                "identity_channel":"final_candidate",
                "settings_namespace":"anything-plays-31",
                "native_core_count":11,
                "console_profiles":18,
                "public_release_approved":False,
                "final_release_approved":False,
            }
            installed_receipt={
                "status":INSTALLED_STATUS,
                "target":platform,
                "installer":filename,
                "installer_sha256":digest,
                "source_revision":SHA,
                "actual_tk_window_started":True,
                "actual_app_initialized":True,
                "actual_tk_mainloop_ran":True,
                "stream_output_window_opened":True,
                "stream_appearance_configured":True,
                "stream_closed_cleanly":True,
                "console_profiles":18,
                "native_core_count":11,
                "camera_hardware_verified":False,
                "physical_controller_verified":False,
                "gameplay_verified":False,
                "relinking_reviewed":False,
                "public_release_approved":False,
            }
            (out/receipt_file).write_text(json.dumps(receipt),"utf-8")
            (gui/"FINAL_INSTALLED_RECEIPT.json").write_text(json.dumps(installed_receipt),"utf-8")
        return full,installed,root/"staged"

    def test_valid_four_platform_stage_is_byte_identical_and_not_a_public_release(self):
        with TemporaryDirectory() as tmp:
            full,installed,out=self.fixture(tmp)
            report=stage(full,installed,out,source_sha=SHA,qa_run_id=123456789)
            self.assertEqual(set(report["installers"]),set(TARGETS))
            self.assertEqual(report["native_core_count"],11)
            self.assertFalse(report["public_release_approved"])
            self.assertFalse(report["stable_3_1_0_published"])
            for platform,(name,_) in TARGETS.items():
                self.assertEqual(sha(full/platform/name),sha(out/name))
            self.assertTrue((out/"FINAL_SOURCE_ACCESS_REVIEW.md").is_file())
            for entry in (out/"SHA256SUMS.txt").read_text("ascii").splitlines():
                digest,name=entry.split("  ",1)
                self.assertEqual(sha(out/name),digest)
            with self.assertRaises(ValueError):
                stage(full,installed,out,source_sha=SHA,qa_run_id=123456789)

    def test_exact_clean_source_built_wheels_appear_in_source_access_notes(self):
        from tools.stage_v31_final_for_review import (
            CLEAN_SOURCE_RECEIPT, OPENCV_ORIGINAL_SOURCE_SHA,
        )
        with TemporaryDirectory() as tmp:
            full,installed,out=self.fixture(tmp)
            for i,target in enumerate(TARGETS):
                data={
                    "target":target,
                    "source_sha256":OPENCV_ORIGINAL_SOURCE_SHA,
                    "source_ci_run_id":43133383864+i,
                    "native_wheel_sha256":format(i+1,"064x"),
                    "native_camera_capture_backend_proven":True,
                    "frozen_installer_tested":False,
                    "redistribution_approved":False,
                    "public_release_approved":False,
                }
                (full/target/CLEAN_SOURCE_RECEIPT).write_text(
                    json.dumps(data),"utf-8"
                )
            report=stage(full,installed,out,source_sha=SHA,qa_run_id=123456789)
            self.assertTrue(report["clean_original_camera_only_wheels_verified_on_four_hosts"])
            self.assertEqual(
                set(report["clean_source_built_opencv_wheel_receipts"]),set(TARGETS),
            )
            notes=(out/"FINAL_SOURCE_ACCESS_REVIEW.md").read_text("utf-8")
            self.assertIn("Four independent native camera-only",notes)
            self.assertIn(OPENCV_ORIGINAL_SOURCE_SHA,notes)
            for target,value in report["clean_source_built_opencv_wheel_receipts"].items():
                self.assertIn(target,notes)
                self.assertIn(value["native_wheel_sha256"],notes)
                self.assertFalse(value["redistribution_approved"])

    def test_reject_partial_or_forged_source_built_wheel_provenance(self):
        from tools.stage_v31_final_for_review import (
            CLEAN_SOURCE_RECEIPT, OPENCV_ORIGINAL_SOURCE_SHA,
        )
        with TemporaryDirectory() as tmp:
            full,installed,out=self.fixture(tmp)
            valid={
                "target":"linux-x64",
                "source_sha256":OPENCV_ORIGINAL_SOURCE_SHA,
                "source_ci_run_id":43133383864,
                "native_wheel_sha256":"f"*64,
                "native_camera_capture_backend_proven":True,
                "frozen_installer_tested":False,
                "redistribution_approved":False,
                "public_release_approved":False,
            }
            evidence=full/"linux-x64"/CLEAN_SOURCE_RECEIPT
            evidence.write_text(json.dumps(valid),"utf-8")
            with self.assertRaises(ValueError):
                stage(full,installed,out,source_sha=SHA,qa_run_id=1)
            self.assertFalse(out.exists())
            for target in TARGETS:
                (full/target/CLEAN_SOURCE_RECEIPT).write_text(
                    json.dumps({**valid,"target":target}),"utf-8"
                )
            for field,bad in (
                ("public_release_approved",True),
                ("redistribution_approved",True),
                ("native_wheel_sha256","invalid"),
                ("source_sha256","0"*64),
                ("native_camera_capture_backend_proven",False),
                ("source_ci_run_id",True),
            ):
                with self.subTest(field=field):
                    evidence.write_text(json.dumps({**valid,field:bad}),"utf-8")
                    with self.assertRaises(ValueError):
                        stage(full,installed,out,source_sha=SHA,qa_run_id=1)
                    self.assertFalse(out.exists())
            evidence.write_text(json.dumps(valid),"utf-8")

    def test_reject_wrong_sha_workflow_and_absent_platform(self):
        with TemporaryDirectory() as tmp:
            full,installed,out=self.fixture(tmp)
            for sha_in,run in (("a"*39,123456789),("b"*40,0),("INVALID",1)):
                with self.assertRaises(ValueError):
                    stage(full,installed,out,source_sha=sha_in,qa_run_id=run)
            (installed/"macos-x64/FINAL_INSTALLED_RECEIPT.json").unlink()
            with self.assertRaises(ValueError):
                stage(full,installed,out,source_sha=SHA,qa_run_id=123456789)
            self.assertFalse(out.exists())

    def test_reject_byte_tampering_without_creating_output(self):
        with TemporaryDirectory() as tmp:
            full,installed,out=self.fixture(tmp)
            binary=full/"windows-x64"/TARGETS["windows-x64"][0]
            binary.write_bytes(binary.read_bytes()+b"evil")
            with self.assertRaises(ValueError):
                stage(full,installed,out,source_sha=SHA,qa_run_id=1)
            self.assertFalse(out.exists())

    def test_reject_any_false_physical_or_licensing_approval_and_wrong_installed_gui(self):
        for field,value in (
            ("native_core_count",1),("console_profiles",3),
            ("identity_channel","rc2"),("settings_namespace","anything-plays-31-rc2"),
            ("final_release_approved",True),("public_release_approved",True),
            ("source_preview_revision","b"*40),("status","PUBLISHED"),
        ):
            with self.subTest(artifact_field=field), TemporaryDirectory() as tmp:
                full,installed,out=self.fixture(tmp)
                path=full/"linux-x64"/TARGETS["linux-x64"][1]
                data=json.loads(path.read_text("utf-8"))
                data[field]=value
                path.write_text(json.dumps(data),"utf-8")
                with self.assertRaises(ValueError):
                    stage(full,installed,out,source_sha=SHA,qa_run_id=1)
                self.assertFalse(out.exists())
        for field,value in (
            ("stream_output_window_opened",False),
            ("stream_appearance_configured",False),("stream_closed_cleanly",False),
            ("actual_tk_window_started",False),
            ("native_core_count",1),
            ("camera_hardware_verified",True),
            ("physical_controller_verified",True),
            ("gameplay_verified",True),
            ("relinking_reviewed",True),
            ("public_release_approved",True),
        ):
            with self.subTest(installed_field=field), TemporaryDirectory() as tmp:
                full,installed,out=self.fixture(tmp)
                path=installed/"macos-arm64/FINAL_INSTALLED_RECEIPT.json"
                data=json.loads(path.read_text("utf-8"))
                data[field]=value
                path.write_text(json.dumps(data),"utf-8")
                with self.assertRaises(ValueError):
                    stage(full,installed,out,source_sha=SHA,qa_run_id=1)
                self.assertFalse(out.exists())

    def test_reject_symlinked_installer(self):
        with TemporaryDirectory() as tmp:
            full,installed,out=self.fixture(tmp)
            p=full/"linux-x64"/TARGETS["linux-x64"][0]
            original=p.with_suffix(".original")
            p.rename(original)
            try:
                p.symlink_to(original)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable")
            with self.assertRaises(ValueError):
                stage(full,installed,out,source_sha=SHA,qa_run_id=1)


if __name__=="__main__":
    unittest.main()
