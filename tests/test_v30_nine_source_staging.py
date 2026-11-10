"""Nine-source 3.0 offline research contracts; synthetic bytes, never release proof."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.capture_v30_mgba_original_source import STATUS as MGBA_STATUS, SOURCE_REVISION, SOURCE_REPOSITORY
from tools.stage_v30_nine_source_inputs import (
    MGBA_SOURCE_RUN, MGBA_REPORTS, MGBA_LICENSE_NAME, inspect_original_mgba,
    stage_nine,
)
from tools.stage_v30_gpl_trial_inputs import TARGET_EXT


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(folder, target="linux-x64"):
    folder.mkdir()
    ext=TARGET_EXT[target]
    native_name=f"mgba_libretro{ext}"
    source_name=f"mgba-{SOURCE_REVISION}-ORIGINAL-SOURCE.tar"
    magic={"windows-x64":b"MZ","linux-x64":b"\x7fELF",
           "macos-arm64":b"\xcf\xfa\xed\xfe",
           "macos-x64":b"\xcf\xfa\xed\xfe"}[target]
    native=magic+b"synthetic source-compiled mGBA bytes (NOT EXECUTABLE)"*1600
    source=b"SYNTHETIC PINNED SOURCE TAR FIXTURE"*10000
    license_bytes=(b"Mozilla Public License Version 2.0\n1. Definitions\n"
                   b"3. Responsibilities\nSYNTHETIC TEST ONLY\n")
    (folder/native_name).write_bytes(native)
    (folder/source_name).write_bytes(source)
    (folder/"ORIGINAL_MPL_2_0_LICENSE.txt").write_bytes(license_bytes)
    for report in MGBA_REPORTS:
        (folder/report).write_text(json.dumps({
            "passed":True,"native_exit_code":0,
            "details":{"passed":True,"synthetic":True},
        }), "utf-8")
    data={
        "schema_version":1, "status":MGBA_STATUS, "core":"mgba",
        "target":target,"original_upstream":SOURCE_REPOSITORY,
        "exact_upstream_revision":SOURCE_REVISION,
        "compiled_libretro_native":native_name,
        "native_sha256":sha(native),"native_size_bytes":len(native),
        "original_source_tar":source_name,"original_source_sha256":sha(source),
        "original_source_bytes":len(source),
        "original_license_path":"LICENSE",
        "original_license_sha256":sha(license_bytes),
        "original_license_bytes":len(license_bytes),
        "license_family":"MPL-2.0",
        "source_checkout_verified":True,
        "original_upstream_source_tar_verified":True,
        "original_native_gb_gbc_gba_test_verified":False,
        "third_party_compiler_and_link_deps_rights_reviewed":False,
        "binary_redistribution_approved":False,
        "combined_gpl_license_review_approved":False,
        "production_source_inventory_approved":False,
        "physical_qa_approved":False,
    }
    (folder/"PINNED_MGBA_SOURCE_NATIVE_UNAPPROVED.json").write_text(json.dumps(data))
    return data


class NineOriginalSourceStaging(unittest.TestCase):
    def test_real_original_mgba_provenance_pin(self):
        self.assertEqual(MGBA_SOURCE_RUN,42527449154)
        self.assertEqual(SOURCE_REVISION,"7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6")
        self.assertEqual(len(MGBA_REPORTS),3)

    def test_source_native_license_av_verified_all_four_formats(self):
        with TemporaryDirectory() as tmp:
            for target in TARGET_EXT:
                folder=Path(tmp)/target
                info=fixture(folder,target)
                native,notice,record=inspect_original_mgba(folder,target)
                self.assertEqual(sha(native),info["native_sha256"])
                self.assertEqual(sha(notice),record["original_license_notice_sha256"])
                self.assertEqual(record["source_build_run_id"],MGBA_SOURCE_RUN)
                self.assertEqual(len(record["original_native_av_report_sha256"]),3)
                self.assertTrue(record["old_unverified_source_buildbot_replaced"])

    def test_tampering_source_native_notice_av_and_false_rights_refused(self):
        for tamper in ("native", "source", "license", "av", "approval", "revision"):
            with self.subTest(tamper=tamper), TemporaryDirectory() as tmp:
                folder=Path(tmp)/"candidate"
                row=fixture(folder)
                if tamper=="native":
                    (folder/"mgba_libretro.so").write_bytes(b"native corrupt")
                elif tamper=="source":
                    (folder/f"mgba-{SOURCE_REVISION}-ORIGINAL-SOURCE.tar").write_bytes(b"changed")
                elif tamper=="license":
                    (folder/"ORIGINAL_MPL_2_0_LICENSE.txt").write_bytes(b"changed")
                elif tamper=="av":
                    (folder/MGBA_REPORTS[0]).write_text(json.dumps({"passed":False,"native_exit_code":1}))
                elif tamper=="approval":
                    row["binary_redistribution_approved"]=True
                else:
                    row["exact_upstream_revision"]="0"*40
                if tamper in ("approval","revision"):
                    (folder/"PINNED_MGBA_SOURCE_NATIVE_UNAPPROVED.json").write_text(json.dumps(row))
                with self.assertRaises(ValueError):
                    inspect_original_mgba(folder,"linux-x64")

    def test_reject_production_or_unapproved_env_without_writing(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root/"mgba")
            args={
                "original_dir":root/"original","snes_dir":root/"snes",
                "sega_dir":root/"sega","pce_artifact":root/"pce.zip",
                "five_dirs":{},"mgba_dir":root/"mgba",
                "target":"linux-x64","output":root/"out","evidence":root/"evidence.json",
            }
            for env in (
                {"AP_V30_GPL_TRIAL":"0","AP_V30_PINNED_PCE":"1",
                 "AP_V30_PINNED_FIVE":"1","AP_V30_PINNED_MGBA":"1"},
                {"AP_V30_GPL_TRIAL":"1","AP_V30_PINNED_PCE":"1",
                 "AP_V30_PINNED_FIVE":"1","AP_V30_PINNED_MGBA":"1",
                 "AP_RELEASE_BUILD":"1","AP_V30_APPROVED_RELEASE":"1"},
            ):
                with patch.dict(os.environ,env,clear=True):
                    with self.assertRaises(ValueError):
                        stage_nine(**args)
            self.assertFalse((root/"out").exists())
            self.assertFalse((root/"evidence.json").exists())

    def test_four_platform_9_of_11_real_gui_workflow_preserves_rights_gate(self):
        workflow=(Path(__file__).resolve().parents[1]/
                  "docs/history/workflows/v30-nine-source-offline-integration.yml").read_text()
        for target in ("windows-x64","linux-x64","macos-arm64","macos-x64"):
            self.assertIn("target: "+target,workflow)
        self.assertIn("42527449154",workflow)
        self.assertIn("AP_V30_PINNED_MGBA: '1'",workflow)
        self.assertIn("--mgba-dir source-built-mgba",workflow)
        self.assertIn("ACTUAL_INSTALLED_gba_SOURCE_MGBA_NATIVE_AV_UNAPPROVED.json",workflow)
        self.assertIn('trials["total_source_built_core_families"]==9',workflow)
        self.assertNotIn("gh release create",workflow)
        self.assertNotIn("dist/**",workflow)
        self.assertEqual(MGBA_LICENSE_NAME,"MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt")


if __name__=="__main__":
    unittest.main()
