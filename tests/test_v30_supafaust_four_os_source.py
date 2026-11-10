"""Four original GPLv2-or-later Supafaust source-built platform contracts."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import capture_v30_supafaust_source as source
from tools import patch_v30_supafaust_macos_semaphore as macfix


class SupafaustFourOSContracts(unittest.TestCase):
    def test_all_required_native_platform_names_and_real_headers_are_defined(self):
        self.assertEqual(set(source.NATIVE_BY_TARGET), {
            "linux-x64", "windows-x64", "macos-arm64", "macos-x64",
        })
        self.assertEqual(source.NATIVE_BY_TARGET["linux-x64"], source.BINARY)
        self.assertEqual(source.NATIVE_BY_TARGET["windows-x64"],
                         "mednafen_supafaust_libretro.dll")
        self.assertEqual(source.NATIVE_BY_TARGET["macos-arm64"],
                         source.NATIVE_BY_TARGET["macos-x64"])
        self.assertEqual(set(source.HEADER_BY_TARGET), set(source.NATIVE_BY_TARGET))
        self.assertIn(b"\x7fELF", source.HEADER_BY_TARGET["linux-x64"])
        self.assertIn(b"MZ", source.HEADER_BY_TARGET["windows-x64"])
        self.assertIn(b"\xcf\xfa\xed\xfe", source.HEADER_BY_TARGET["macos-arm64"])
        self.assertEqual(source.COMMIT, "642d1d1b6684aa7e306a02a89885f3f5456a5157")

    def test_each_platform_native_image_is_hashed_with_same_pinned_source(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            original = root/"original-upstream"
            (original/"mednafen/snes_faust").mkdir(parents=True)
            (original/"COPYING").write_text(
                "GNU GENERAL PUBLIC LICENSE\nVersion 2\n", "utf-8")
            (original/"mednafen/snes_faust/snes.cpp").write_text(
                "either version 2 or any later version\n", "utf-8")
            (original/"Makefile").write_text("all: \n\t@echo test\n", "utf-8")
            original_config = macfix.BEFORE + "\n"
            config = original/"mednafen/config.h"
            config.write_text(original_config, "utf-8")
            source_tar = io.BytesIO()
            with tarfile.open(fileobj=source_tar, mode="w") as tar:
                for name in ["COPYING", "mednafen/snes_faust/snes.cpp",
                             "mednafen/config.h", "Makefile"]:
                    data=(original/name).read_bytes()
                    item=tarfile.TarInfo(name)
                    item.size=len(data)
                    tar.addfile(item, io.BytesIO(data))
            current_target = ["linux-x64"]
            def fake_git(root_arg, *args, binary=False):
                if args[:2]==("rev-parse","HEAD"):
                    return source.COMMIT
                if args[:2]==("remote","get-url"):
                    return source.REPOSITORY + ".git"
                if args[:2]==("status","--porcelain"):
                    return "M mednafen/config.h" if current_target[0].startswith("macos-") else ""
                if args[:2]==("show","HEAD:mednafen/config.h"):
                    return original_config.encode("utf-8")
                if args[:2]==("diff","--"):
                    return b"diff --git a/mednafen/config.h b/mednafen/config.h\n" + macfix.AFTER.encode("utf-8")
                if args[:2]==("archive","--format=tar"):
                    return source_tar.getvalue()
                raise ValueError("Unexpected source identity query")
            for target, native_name in source.NATIVE_BY_TARGET.items():
                with self.subTest(target=target), patch.object(source,"git",fake_git):
                    current_target[0]=target
                    config.write_text(
                        original_config.replace(macfix.BEFORE,macfix.AFTER,1)
                        if target.startswith("macos-") else original_config, "utf-8")
                    native=original/native_name
                    blob=source.HEADER_BY_TARGET[target][0] + (target.encode()*7000)
                    native.write_bytes(blob)
                    folder=root/("out-"+target)
                    result=source.capture(
                        source=original,native=native,output=folder,target=target)
                    self.assertEqual(result["target"],target)
                    self.assertEqual(result["native_name"],native_name)
                    self.assertEqual(result["native_sha256"],hashlib.sha256(blob).hexdigest())
                    self.assertEqual(result["source_commit"],source.COMMIT)
                    self.assertFalse(result["public_binary_redistribution_approved"])
                    self.assertFalse(result["replaces_current_snes9x_in_app"])
                    self.assertFalse(result["complete_combined_core_license_reviewed"])
                    is_macos=target.startswith("macos-")
                    self.assertEqual(result["original_source_modified_for_macos"], is_macos)
                    patchfile=folder/"SUPAFAUST_MACOS_SOURCE_PATCH_UNAPPROVED.diff"
                    self.assertEqual(patchfile.is_file(),is_macos)
                    if is_macos:
                        self.assertEqual(
                            result["reproducible_macos_source_patch_sha256"],
                            hashlib.sha256(patchfile.read_bytes()).hexdigest())
                    self.assertEqual((folder/native_name).read_bytes(),blob)
                    self.assertIn("mednafen/snes_faust/snes.cpp",
                                  tarfile.open(folder/result["source_archive"],"r:gz").getnames())
                    raw_checksums=(folder/"SHA256SUMS.txt").read_bytes()
                    self.assertNotIn(b"\r", raw_checksums)
                    self.assertTrue(raw_checksums.endswith(b"\n"))
                    for check in raw_checksums.decode("ascii").splitlines():
                        digest,name=check.split("  ")
                        self.assertEqual(hashlib.sha256((folder/name).read_bytes()).hexdigest(),digest)
                    native.unlink()

    def test_target_architecture_mismatch_is_rejected_with_wrong_pe_macho_elf(self):
        with TemporaryDirectory() as root:
            native = Path(root)/source.NATIVE_BY_TARGET["windows-x64"]
            native.write_bytes(b"\x7fELF" + b"a"*60000)
            with self.assertRaisesRegex(ValueError, "header"):
                source.capture(source=root, native=native, output=Path(root)/"out",
                               target="windows-x64")
            with self.assertRaisesRegex(ValueError, "Unknown Supafaust target"):
                source.capture(source=root, native=native, output=Path(root)/"out",
                               target="unsupported")
            with self.assertRaisesRegex(ValueError, "name or size"):
                source.capture(source=root, native=native, output=Path(root)/"out",
                               target="linux-x64")

    def test_actual_ci_builds_and_executes_all_four_without_public_distribution(self):
        root=Path(__file__).resolve().parents[1]
        workflow=(root/"docs/history/workflows/v30-supafaust-four-os-source.yml").read_text("utf-8")
        self.assertIn("pull_request:",workflow)
        self.assertIn("libretro/supafaust",workflow)
        self.assertIn(source.COMMIT,workflow)
        for target in source.NATIVE_BY_TARGET:
            self.assertIn("target: "+target,workflow)
        for runner in ("ubuntu-24.04","windows-2025","macos-15","macos-15-intel"):
            self.assertIn(runner,workflow)
        for option in ("platform=unix","platform=osx","platform=win"):
            self.assertIn(option,workflow)
        for criterion in ("native_video_frames","native_nonzero_pcm_values","distinct_rgb_frames"):
            self.assertIn(criterion,workflow)
        self.assertIn("capture_v30_supafaust_source",workflow)
        self.assertIn("patch_v30_supafaust_macos_semaphore",workflow)
        self.assertIn("probe_snes_homebrew.py",workflow)
        self.assertNotIn("gh release create",workflow)
        self.assertNotIn("APPROVED-IMMUTABLE-PRODUCTION",workflow)
        self.assertNotIn("continue-on-error: true",workflow)
        from anything_plays.systems import SYSTEMS
        self.assertEqual(SYSTEMS["snes"].core,"snes9x")
        self.assertEqual(len(SYSTEMS),18)


if __name__=="__main__":
    unittest.main()
