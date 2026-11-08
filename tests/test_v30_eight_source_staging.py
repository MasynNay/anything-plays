"""Fail-closed tests for 8-source-core complete 18-profile 3.0 test installer.

Synthetic source/native bytes; NEVER a license grant or a release acceptance.
Actual installed native playbacks happen separately on all four CI runners.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.stage_v30_eight_source_inputs import (
    ORIGINAL_RUN, FAMILIES, LEFT_UNCHANGED,
    check_original_five_artifact, stage_eight,
)
from tools.capture_v30_2d_five_source_build import (
    CANDIDATES, PINNED_COMMITS,
)
from anything_plays.v30_gpl_trial import FIVE_ORIGINAL_SOURCE_COMMITS


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(folder, name, target="linux-x64", extension=".so"):
    folder=Path(folder)
    folder.mkdir()
    filename=f"{name}_libretro{extension}"
    source_name=f"{name}-{PINNED_COMMITS[name]}-SOURCE.tar"
    native=(b"\x7fELF"+f"unit-source-built {name}".encode()*5000)
    tracked=(f"project untouched pinned source for {name}".encode()*3500)
    (folder/filename).write_bytes(native)
    (folder/source_name).write_bytes(tracked)
    _, notice_path=CANDIDATES[name]
    notice=(b"GNU GENERAL PUBLIC LICENSE Version 2; SYNTHETIC NOT ORIGINAL")
    if notice_path is not None:
        (folder/"ORIGINAL_UPSTREAM_GPL_NOTICE.txt").write_bytes(notice)
    rows={
        "fceumm":("ORIGINAL_NES_NATIVE_AV.json",),
        "stella2014":("ORIGINAL_ATARI2600_NATIVE_AV.json",),
        "prosystem":("ORIGINAL_ATARI7800_NATIVE_AV.json",),
        "mednafen_ngp":("ORIGINAL_NGPC_NATIVE_AV.json",),
        "mednafen_wswan":("ORIGINAL_WSWAN_NATIVE_AV.json","ORIGINAL_WS_COLOR_NATIVE_AV.json"),
    }[name]
    for report in rows:
        child={"passed":True} if name!="fceumm" else {"playback_probe_passed":True}
        (folder/report).write_text(json.dumps({"passed":True,"native_exit_code":0,
                                                 "details":child}))
    data={
        "schema_version":1,
        "status":"UNAPPROVED-ORIGINAL-5-CORE-SOURCE-NATIVE-RESEARCH",
        "candidate":name,"target":target,
        "original_source_repository":"https://github.com/"+CANDIDATES[name][0],
        "exact_source_revision":PINNED_COMMITS[name],
        "real_checkout_head_verified":True,
        "original_source_archive":source_name,
        "source_archive_sha256":sha(tracked),
        "source_archive_size_bytes":len(tracked),
        "native_filename":filename,
        "native_sha256":sha(native),
        "native_size_bytes":len(native),
        "original_license_source_file":notice_path,
        "original_license_notice_sha256":sha(notice) if notice_path else None,
        "original_license_notice_copied":bool(notice_path),
        "binary_redistribution_approved":False,
        "combined_gpl_version_license_review_approved":False,
        "physical_gameplay_and_webcam_qa_approved":False,
        "production_source_to_binary_approved":False,
        "source_submodules_and_deps_independently_reviewed":False,
    }
    (folder/"PINNED_ORIGINAL_SOURCE_RESEARCH_UNAPPROVED.json").write_text(json.dumps(data))
    return data


class EightOriginalCoreOfflineContracts(unittest.TestCase):
    def test_original_source_commit_map_matches_pinned_original_ci_build(self):
        self.assertEqual(FIVE_ORIGINAL_SOURCE_COMMITS,PINNED_COMMITS)
        self.assertEqual(len(FAMILIES),5)
        self.assertEqual(len(LEFT_UNCHANGED),3)
        self.assertEqual(ORIGINAL_RUN,42513615955)

    def test_five_original_sources_and_native_true_identity(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            for name in sorted(FAMILIES):
                folder=root/name
                original=fixture(folder,name)
                native,notice,record=check_original_five_artifact(folder,name,"linux-x64",".so")
                self.assertEqual(sha(native),original["native_sha256"])
                self.assertEqual(record["exact_source_revision"],PINNED_COMMITS[name])
                self.assertEqual(notice is not None,name!="stella2014")
                self.assertFalse(record["binary_redistribution_approved"])

    def test_tampered_native_source_or_false_approval_is_refused(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            original=fixture(root/"candidate","fceumm")
            folder=root/"candidate"
            native=folder/"fceumm_libretro.so"
            native.write_bytes(b"native tampered")
            with self.assertRaises(ValueError):
                check_original_five_artifact(folder,"fceumm","linux-x64",".so")
            native.write_bytes(b"\x7fELF"+b"unit-source-built fceumm"*5000)
            original["binary_redistribution_approved"]=True
            (folder/"PINNED_ORIGINAL_SOURCE_RESEARCH_UNAPPROVED.json").write_text(json.dumps(original))
            with self.assertRaises(ValueError):
                check_original_five_artifact(folder,"fceumm","linux-x64",".so")

    def test_original_monochrome_ngp_not_claimed(self):
        with TemporaryDirectory() as temp:
            folder=Path(temp)/"ngp"
            fixture(folder,"mednafen_ngp")
            self.assertEqual(
                [p.name for p in folder.glob("ORIGINAL_*_NATIVE_AV.json")],
                ["ORIGINAL_NGPC_NATIVE_AV.json"],
            )

    def test_public_release_mode_never_assembles_unapproved_natives(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            kwargs={
                "original_dir":root/"original","snes_dir":root/"snes",
                "sega_dir":root/"sega","pce_artifact":root/"pce.zip",
                "five_dirs":{name:root/name for name in FAMILIES},
                "output":root/"out","evidence":root/"proof.json",
                "target":"linux-x64",
            }
            for env in (
                    {"AP_V30_GPL_TRIAL":"0","AP_V30_PINNED_PCE":"1",
                     "AP_V30_PINNED_FIVE":"1","AP_RELEASE_BUILD":"0",
                     "AP_V30_APPROVED_RELEASE":"0"},
                    {"AP_V30_GPL_TRIAL":"1","AP_V30_PINNED_PCE":"1",
                     "AP_V30_PINNED_FIVE":"1","AP_RELEASE_BUILD":"1",
                     "AP_V30_APPROVED_RELEASE":"1"},
            ):
                with patch.dict(os.environ,env,clear=True):
                    with self.assertRaises(ValueError):
                        stage_eight(**kwargs)
            self.assertFalse((root/"out").exists())
            self.assertFalse((root/"proof.json").exists())

    def test_actual_four_platform_complete_offline_workflow_never_uploads_unapproved_core(self):
        path=Path(__file__).resolve().parents[1]/".github/workflows/v30-eight-source-offline-integration.yml"
        yml=path.read_text("utf-8")
        for target in ("windows-x64","linux-x64","macos-arm64","macos-x64"):
            self.assertIn("target: "+target,yml)
        for name in FAMILIES:
            self.assertIn("AnythingPlays-3.0-PINNED-REMAINING-$name-$TARGET-UNAPPROVED",yml)
            self.assertIn("--"+name.replace("_","-")+"-dir",yml)
        self.assertIn("42513615955",yml)
        self.assertIn("AP_V30_PINNED_FIVE: '1'",yml)
        self.assertIn("original_unchanged_core_archives",yml)
        self.assertIn("ACTUAL_INSTALLED_7_CYCLE_SWITCH_UNAPPROVED.json",yml)
        self.assertNotIn("gh release create",yml)
        self.assertNotIn("dist/**",yml)


if __name__=="__main__":
    unittest.main()
