"""Synthetic N64 source-to-native + eleven-license staging regressions.

This test never executes synthetic emulator bytes or grants redistribution.
Real full offline 18-console compiled app runs in separate four-platform CI.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.capture_v30_n64_original_source_build import (
    SOURCE_REVISION, SOURCE_REPOSITORY, STATUS as SOURCE_STATUS,
)
from tools.stage_v30_ten_source_inputs import (
    N64_SOURCE_RUN_ID, SOURCE_MARKER, SOURCE_PROBE, NOTICE_NAMES,
    check_original_n64_artifact, stage_ten,
)
from tools.stage_v30_gpl_trial_inputs import TARGET_EXT


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def original_fixture(folder, target="linux-x64"):
    folder=Path(folder)
    folder.mkdir()
    ext=TARGET_EXT[target]
    native_name=f"parallel_n64_libretro{ext}"
    header={".dll":b"MZ",".so":b"\x7fELF",
            ".dylib":b"\xcf\xfa\xed\xfe"}[ext]
    native=header+b"not executable synthetic original N64"*11000
    (folder/native_name).write_bytes(native)
    notes={}
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode="w") as t:
        for i in range(11):
            path=f"upstream/component{i}/COPYING"
            # The immutable original Git blob uses LF. On Windows Git's
            # source export may present that same content as CRLF.
            contents=(f"ORIGINAL SOURCE LICENSE #{i} NOT ACTUAL GPL ".encode()+b"\n")*100
            exported=(contents.replace(b"\n",b"\r\n") if target=="windows-x64" else contents)
            info=tarfile.TarInfo(path)
            info.size=len(exported)
            t.addfile(info,io.BytesIO(exported))
            notes[path]={"sha256":sha(contents),"size_bytes":len(contents)}
    archive=stream.getvalue()
    archive_name=f"parallel-n64-{SOURCE_REVISION}-ORIGINAL-SOURCE.tar"
    (folder/archive_name).write_bytes(archive)
    (folder/SOURCE_PROBE).write_text(json.dumps({
        "probe_passed":True,"child_returncode":0,
        "details":{"playback_probe_passed":True,"nonblank_samples":10},
    }))
    identity={
        "schema_version":1, "status":SOURCE_STATUS,
        "core":"parallel_n64","target":target,
        "exact_upstream_source_revision":SOURCE_REVISION,
        "original_upstream_source_repository":SOURCE_REPOSITORY,
        "original_git_source_archive":archive_name,
        "original_git_source_archive_sha256":sha(archive),
        "original_git_source_archive_bytes":len(archive),
        "actual_source_compiled_native_filename":native_name,
        "actual_source_compiled_native_sha256":sha(native),
        "actual_source_compiled_native_bytes":len(native),
        "source_tree_gitlinks":0,"original_licenses":notes,
        "original_license_notice_count":11,
        "original_tracked_source_unchanged":True,
        "reported_old_buildbot_source_equivalent":False,
        "native_source_build_and_playback_independently_reviewed":False,
        "mixed_gpl_combined_program_license_approved":False,
        "source_dependency_and_compiler_rights_reviewed":False,
        "corresponding_source_review_approved":False,
        "physical_game_audio_save_long_run_reviewed":False,
        "public_binary_redistribution_approved":False,
    }
    (folder/SOURCE_MARKER).write_text(json.dumps(identity),"utf-8")
    return identity


class TenOriginalNativeStaging(unittest.TestCase):
    def test_all_four_original_native_and_real_source_notices(self):
        with TemporaryDirectory() as temp:
            for target in TARGET_EXT:
                folder=Path(temp)/target
                original=original_fixture(folder,target)
                native,copied,metadata=check_original_n64_artifact(folder,target)
                self.assertEqual(sha(native),original["actual_source_compiled_native_sha256"])
                self.assertEqual(set(copied),set(NOTICE_NAMES))
                self.assertEqual(set(metadata["original_notice_sha256"]),set(NOTICE_NAMES))
                self.assertEqual(metadata["source_build_run_id"],N64_SOURCE_RUN_ID)
                self.assertTrue(metadata["old_unverified_buildbot_replaced"])

    def test_original_binary_source_notice_probe_and_false_rights_are_immutable(self):
        for tamper in ("native","source","notice","probe","rights","revision","missing"):
            with TemporaryDirectory() as temp, self.subTest(tamper=tamper):
                folder=Path(temp)/"n64"
                m=original_fixture(folder)
                if tamper=="native":
                    (folder/"parallel_n64_libretro.so").write_bytes(b"tampered")
                elif tamper=="source":
                    (folder/m["original_git_source_archive"]).write_bytes(b"not a genuine source tar")
                elif tamper=="notice":
                    path=next(iter(m["original_licenses"]))
                    m["original_licenses"][path]["sha256"]="f"*64
                elif tamper=="probe":
                    (folder/SOURCE_PROBE).write_text(json.dumps({"probe_passed":False}))
                elif tamper=="rights":
                    m["public_binary_redistribution_approved"]=True
                elif tamper=="revision":
                    m["exact_upstream_source_revision"]="0"*40
                else:
                    (folder/SOURCE_PROBE).unlink()
                if tamper in ("notice","rights","revision"):
                    (folder/SOURCE_MARKER).write_text(json.dumps(m))
                with self.assertRaises((ValueError,FileNotFoundError,KeyError)):
                    check_original_n64_artifact(folder,"linux-x64")

    def test_no_release_build_without_true_approval_and_original_inputs(self):
        with TemporaryDirectory() as temp:
            folder=Path(temp)
            original_fixture(folder/"n64")
            kwargs={
                "original_dir":folder/"original","snes_dir":folder/"snes",
                "sega_dir":folder/"sega","pce_artifact":folder/"pce.zip",
                "five_dirs":{},"mgba_dir":folder/"mgba",
                "n64_dir":folder/"n64","target":"linux-x64",
                "output":folder/"out","evidence":folder/"proof.json",
            }
            for rights in (
                {"AP_V30_PINNED_N64":"0","AP_RELEASE_BUILD":"0"},
                {"AP_V30_PINNED_N64":"1","AP_RELEASE_BUILD":"1"},
            ):
                env={"AP_V30_GPL_TRIAL":"1","AP_V30_PINNED_PCE":"1",
                     "AP_V30_PINNED_FIVE":"1","AP_V30_PINNED_MGBA":"1",
                     "AP_V30_APPROVED_RELEASE":"0",**rights}
                with patch.dict(os.environ,env,clear=True):
                    with self.assertRaises(ValueError):
                        stage_ten(**kwargs)
            self.assertFalse((folder/"out").exists())

    def test_four_platform_real_offline_app_never_uploads_unapproved_n64(self):
        path=Path(__file__).resolve().parents[1]/"docs/history/workflows/v30-ten-source-offline-integration.yml"
        yml=path.read_text("utf-8")
        for target in ("windows-x64","linux-x64","macos-arm64","macos-x64"):
            self.assertIn("target: "+target,yml)
        self.assertIn("42534736496",yml)
        self.assertIn("AP_V30_PINNED_N64: '1'",yml)
        self.assertIn("--n64-dir source-built-n64",yml)
        self.assertIn("ACTUAL_INSTALLED_N64_ORIGINAL_SOURCE_HOME_BREW_UNAPPROVED.json",yml)
        self.assertNotIn("gh release create",yml)
        self.assertNotIn("dist/**",yml)


if __name__=="__main__":
    unittest.main()
