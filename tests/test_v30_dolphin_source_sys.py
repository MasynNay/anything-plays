"""Synthetic source-backed Dolphin Sys provenance, tamper and installer tests."""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest
import zipfile
from unittest.mock import patch

from tools.fetch_dolphin_sys import extract_dolphin_sys
from tools.prepare_v30_dolphin_source_sys import (
    DOLPHIN_REV, PINNED_SYS_TREE_SHA1, ZIP_PREFIX,
    _git_tree_sha, create_pinned_sys,
)

FIXTURE = {
    "codehandler.bin": b"test only original codehandler",
    "GC/dsp_rom.bin": b"test only original DSP\n",
    "GC/font_western.bin": b"test only original font\n",
    "GameSettings/A.ini": b"[Core]\nEnableCheats = False\n",
    "Readme.txt": b"synthetic Dolphin source fixture\n",
}


def source_tar(path, *, files=FIXTURE, unsafe=None):
    """Build test source with realistic path/modes; never ship game firmware."""
    root=f"dolphin-{DOLPHIN_REV}"
    with tarfile.open(path, "w:gz") as tar:
        for name, content in sorted(files.items()):
            info=tarfile.TarInfo(f"{root}/Data/Sys/{name}")
            info.mode=0o644
            info.size=len(content)
            tar.addfile(info, io.BytesIO(content))
        if unsafe is not None:
            name, type_ = unsafe
            info=tarfile.TarInfo(f"{root}/Data/Sys/{name}")
            info.type=type_
            info.linkname="../untrusted"
            info.size=0
            tar.addfile(info)
        # The real original parent source TAR also contains CMake files and
        # C++ source, and is far larger than a five-file minimal synthetic.
        filler=os.urandom(145_000)
        info=tarfile.TarInfo(f"{root}/CMakeLists.txt")
        info.size=len(filler)
        tar.addfile(info, io.BytesIO(filler))


class PinnedOriginalDolphinSysTests(unittest.TestCase):
    def test_immutable_original_root_commit_and_tree_are_exact(self):
        self.assertEqual(DOLPHIN_REV, "32c61f9d0e933331bb7087ba57e96883241b4960")
        self.assertEqual(PINNED_SYS_TREE_SHA1, "6abd87498928d5362d83f698a562e956072b8700")
        self.assertEqual(len(PINNED_SYS_TREE_SHA1), 40)

    def test_deterministic_zip_matches_existing_offline_dolphin_sys_extractor(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            source=root/"source.tar.gz"
            source_tar(source)
            tree=_git_tree_sha({name:(body,False) for name,body in FIXTURE.items()})
            out1, manifest1=root/"one"/"Dolphin.zip",root/"one"/"review.json"
            out2, manifest2=root/"two"/"Dolphin.zip",root/"two"/"review.json"
            one=create_pinned_sys(source,out1,manifest1,expected_tree=tree)
            two=create_pinned_sys(source,out2,manifest2,expected_tree=tree)
            self.assertEqual(out1.read_bytes(),out2.read_bytes())
            self.assertEqual(one,two)
            self.assertTrue(one["matches_original_source_bytes"])
            self.assertEqual(one["dolphin_sys_file_count"],len(FIXTURE))
            self.assertEqual(one["pinned_git_data_sys_tree_sha1"],tree)
            for field in ("binary_to_source_compilation_verified",
                          "all_third_party_fonts_and_asset_rights_independently_reviewed",
                          "public_binary_distribution_approved"):
                self.assertIs(one[field],False)
            with zipfile.ZipFile(out1) as archive:
                self.assertEqual(sorted(archive.namelist()),
                                 sorted(ZIP_PREFIX+k for k in FIXTURE))
            dest=root/"installed"
            info=extract_dolphin_sys(out1.read_bytes(), dest)
            self.assertEqual(info["file_count"],len(FIXTURE))
            for name,data in FIXTURE.items():
                self.assertEqual((dest/"dolphin-emu"/"Sys"/name).read_bytes(),data)
            with self.assertRaisesRegex(ValueError,"overwrite"):
                create_pinned_sys(source,out1,manifest1,expected_tree=tree)

    def test_rejects_changed_original_source_vs_git_tree(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            original=_git_tree_sha({name:(body,False) for name,body in FIXTURE.items()})
            changed=dict(FIXTURE)
            changed["GC/dsp_rom.bin"]=b"replaced! not from exact pinned source"
            source=root/"altered.tar.gz"
            source_tar(source,files=changed)
            out,meta=root/"output.zip",root/"report.json"
            with self.assertRaisesRegex(ValueError,"tree does not match"):
                create_pinned_sys(source,out,meta,expected_tree=original)
            self.assertFalse(out.exists())
            self.assertFalse(meta.exists())

    def test_rejects_unsafe_tar_links_and_source_path_traversal(self):
        for unsafe in (
            ("../escape.txt",tarfile.SYMTYPE),
            ("GC/fake_symlink.bin",tarfile.SYMTYPE),
            ("GC/fake_hardlink.bin",tarfile.LNKTYPE),
        ):
            with self.subTest(unsafe=unsafe),TemporaryDirectory() as temp:
                root=Path(temp)
                source=root/"source.tar.gz"
                source_tar(source,unsafe=unsafe)
                out,meta=root/"output.zip",root/"report.json"
                with self.assertRaises(ValueError):
                    create_pinned_sys(source,out,meta)
                self.assertFalse(out.exists())
                self.assertFalse(meta.exists())

    def test_rejects_partial_zip_when_postwrite_source_verification_fails(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.tar.gz"
            source_tar(source)
            tree = _git_tree_sha({name: (body, False) for name, body in FIXTURE.items()})
            out, manifest = root / "Dolphin.zip", root / "review.json"
            original = zipfile.ZipFile
            calls = [0]

            def broken_verifier(*args, **kwargs):
                calls[0] += 1
                if calls[0] == 2:
                    raise zipfile.BadZipFile("simulated corrupt postwrite ZIP")
                return original(*args, **kwargs)

            with patch("tools.prepare_v30_dolphin_source_sys.zipfile.ZipFile",
                       side_effect=broken_verifier):
                with self.assertRaises(zipfile.BadZipFile):
                    create_pinned_sys(source, out, manifest, expected_tree=tree)
            self.assertEqual(calls[0], 2)
            self.assertFalse(out.exists(), "corrupt output must be removed")
            self.assertFalse(manifest.exists(), "no false source proof on failure")
            # Recovery must work with the same paths, without manual cleanup.
            create_pinned_sys(source, out, manifest, expected_tree=tree)
            self.assertTrue(out.is_file())
            self.assertTrue(manifest.is_file())

    def test_rejects_partial_zip_when_manifest_write_fails(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.tar.gz"
            source_tar(source)
            tree = _git_tree_sha({name: (body, False) for name, body in FIXTURE.items()})
            out, manifest = root / "Dolphin.zip", root / "review.json"
            original_write = Path.write_text

            def failed_manifest_write(path, content, *args, **kwargs):
                if path == manifest:
                    original_write(path, "partial unapproved evidence", *args, **kwargs)
                    raise OSError("simulated disk failure writing provenance")
                return original_write(path, content, *args, **kwargs)

            with patch.object(Path, "write_text", failed_manifest_write):
                with self.assertRaisesRegex(OSError, "disk failure"):
                    create_pinned_sys(source, out, manifest, expected_tree=tree)
            self.assertFalse(out.exists(), "no ZIP without verified provenance")
            self.assertFalse(manifest.exists(), "no partial provenance JSON")
            create_pinned_sys(source, out, manifest, expected_tree=tree)
            self.assertTrue(out.is_file())
            self.assertTrue(manifest.is_file())

    def test_does_not_accept_missing_codehandler_or_existing_output(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            modified={k:v for k,v in FIXTURE.items() if k!="codehandler.bin"}
            source=root/"source.tar.gz"
            source_tar(source,files=modified)
            with self.assertRaisesRegex(ValueError,"required Sys files"):
                create_pinned_sys(source,root/"out.zip",root/"manifest.json")
            source_tar(source,files=FIXTURE)
            (root/"out.zip").write_bytes(b"do not overwrite")
            with self.assertRaisesRegex(ValueError,"overwrite"):
                create_pinned_sys(source,root/"out.zip",root/"manifest.json")


if __name__=="__main__":
    unittest.main()
