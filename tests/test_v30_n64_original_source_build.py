"""Synthetic contracts for pinned original N64 source/native capture.

These tests intentionally do not execute a real emulator or grant GPL rights.
The four-OS GitHub Actions workflow independently builds the actual core.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import capture_v30_n64_original_source_build as mod


def sha(data):
    return hashlib.sha256(data).hexdigest()


class PinnedOriginalN64Contracts(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)

    def mock_original(self, target="linux-x64"):
        source=self.root/"original"
        source.mkdir()
        (source/".gitmodules").write_bytes(b"")
        notes=[]
        for i in range(11):
            name=f"component-{i}/COPYING"
            file=source/name
            file.parent.mkdir(parents=True,exist_ok=True)
            raw=(f"ORIGINAL-SYNTHETIC-N64-NOTICE-{i}".encode()*200)
            file.write_bytes(raw)
            notes.append({"path":name,"git_blob_sha1":mod.gitblob(raw),
                          "size_bytes":len(raw),"notice_reviewed":False})
        index={
            "reported_source_commit":mod.SOURCE_REVISION,
            "source_repository":mod.SOURCE_REPOSITORY,
            "gitlink_count":0,
            "license_notice_file_count":11,
            "source_tree_entry_count":1970,
            "source_to_native_binary_independently_verified":False,
            "public_binary_redistribution_approved":False,
            "notices":notes,
        }
        idx=self.root/"index.json"
        idx.write_text(json.dumps(index),"utf-8")
        ext=mod.EXTENSIONS[target]
        header={".dll":b"MZ",".so":b"\\x7fELF",
                ".dylib":b"\\xcf\\xfa\\xed\\xfe"}[ext]
        native=self.root/f"parallel_n64_libretro{ext}"
        native.write_bytes(header+b"synthetic not executable native"*7000)
        def git_output(*args):
            name=args[0] if args else ""
            if name=="rev-parse":return (mod.SOURCE_REVISION+"\\n").encode()
            if name=="status":return b""
            if name=="ls-tree":
                return b"".join(f"100644 blob {'a'*40} source/{n}\\n".encode() for n in range(1970))
            if name=="archive":return b"SYNTHETIC ORIGINAL SOURCE TAR "*45000
            raise AssertionError("Unexpected Git command")
        return source,native,idx,index,git_output

    def test_platform_native_magic_and_original_notice_sha(self):
        for target in mod.EXTENSIONS:
            with self.subTest(target=target):
                src,native,idx,row,git_output=self.mock_original(target) if target=="linux-x64" else (
                    self._new_fixture(target))
                mod.validate_native(native.name,native.read_bytes(),target)
                with patch.object(mod,"_git",side_effect=lambda source,*a:git_output(*a)):
                    parsed=mod.validate_source_and_notices(src,row)
                self.assertEqual(len(parsed),11)
                self.assertTrue(all(len(v["sha256"])==64 for v in parsed.values()))

    def _new_fixture(self,target):
        # Each subtest gets a distinct fixture directory; no native is executed.
        with TemporaryDirectory() as temp:
            pass
        suffix=target.replace("-","_")
        old=self.root
        try:
            self.root=old/suffix
            self.root.mkdir()
            return self.mock_original(target)
        finally:
            self.root=old

    def test_original_n64_manifest_is_never_approved_for_public_distribution(self):
        src,native,idx,_,git_output=self.mock_original()
        with patch.object(mod,"INDEX",idx),patch.object(mod,"_git",side_effect=lambda source,*a:git_output(*a)), \
             patch.dict(os.environ,{"AP_RELEASE_BUILD":"0","AP_V30_APPROVED_RELEASE":"0"},clear=False):
            output=self.root/"record"
            row=mod.capture(src,native,"linux-x64",output)
        self.assertEqual(row["original_license_notice_count"],11)
        self.assertEqual(row["exact_upstream_source_revision"],mod.SOURCE_REVISION)
        self.assertEqual(row["actual_source_compiled_native_sha256"],sha(native.read_bytes()))
        self.assertEqual(row["original_git_source_archive_sha256"],
                         sha((output/row["original_git_source_archive"]).read_bytes()))
        for field in ("public_binary_redistribution_approved",
                      "mixed_gpl_combined_program_license_approved",
                      "corresponding_source_review_approved",
                      "native_source_build_and_playback_independently_reviewed",
                      "physical_game_audio_save_long_run_reviewed"):
            self.assertIs(row[field],False)

    def test_changed_original_notice_and_gitlink_are_blocked(self):
        src,native,idx,row,git_output=self.mock_original()
        note=src/row["notices"][0]["path"]
        note.write_bytes(b"tampered")
        with patch.object(mod,"_git",side_effect=lambda source,*a:git_output(*a)):
            with self.assertRaises(ValueError):
                mod.validate_source_and_notices(src,row)
        note.write_bytes(b"ORIGINAL-SYNTHETIC-N64-NOTICE-0"*200)
        def git_with_link(*args):
            if args and args[0]=="ls-tree":
                return b"160000 commit "+b"0"*40+b" a/submodule\\n"+b"".join(
                    b"100644 blob "+b"a"*40+b" other\\n" for _ in range(1969))
            return git_output(*args)
        with patch.object(mod,"_git",side_effect=lambda source,*a:git_with_link(*a)):
            with self.assertRaises(ValueError):
                mod.validate_source_and_notices(src,row)

    def test_unreviewed_or_release_mode_never_produces_artifact(self):
        src,native,idx,_,git_output=self.mock_original()
        output=self.root/"bad"
        with patch.object(mod,"INDEX",idx),patch.object(mod,"_git",side_effect=lambda source,*a:git_output(*a)):
            with patch.dict(os.environ,{"AP_RELEASE_BUILD":"1","AP_V30_APPROVED_RELEASE":"0"},clear=False):
                with self.assertRaises(ValueError):
                    mod.capture(src,native,"linux-x64",output)
        self.assertFalse(output.exists())

    def test_native_tampering_or_wrong_platform_refused(self):
        for target in mod.EXTENSIONS:
            with self.subTest(target=target):
                original=b"MZ"+b"synthetic n64"*12000
                if target=="windows-x64":
                    mod.validate_native("parallel_n64_libretro.dll",original,target)
                else:
                    with self.assertRaises(ValueError):
                        mod.validate_native("parallel_n64_libretro"+mod.EXTENSIONS[target],original,target)
        with self.assertRaises(ValueError):
            mod.validate_native("parallel_n64_libretro.so",b"\\x7fELF", "linux-x64")


if __name__=="__main__":
    unittest.main()
