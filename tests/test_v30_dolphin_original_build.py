"""Fail-closed original Dolphin source-built Linux candidate contracts."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import verify_v30_dolphin_original_build as candidate


class OriginalDolphinNativeLinuxContracts(unittest.TestCase):
    def test_immutable_parent_and_37_child_gitlink_contract(self):
        self.assertEqual(candidate.REV, "32c61f9d0e933331bb7087ba57e96883241b4960")
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                candidate.verify_original_source(root / "absent")
            with patch.object(candidate, "git", return_value="f" * 40):
                with self.assertRaisesRegex(ValueError, "parent source commit"):
                    candidate.verify_original_source(root)

    def test_submodule_tracked_edit_fails_closed(self):
        with TemporaryDirectory() as temp:
            checkout = Path(temp)
            with patch.object(candidate, "git", return_value=" M Source/Core/Core.cpp") as git_call:
                with self.assertRaisesRegex(ValueError, "tracked source was edited: Externals/example"):
                    candidate.require_clean_tracked_source(checkout, "Externals/example")
                git_call.assert_called_once_with(checkout, "status", "--porcelain", "--untracked-files=no")

    def test_clean_submodule_checkout_is_accepted(self):
        with TemporaryDirectory() as temp:
            checkout = Path(temp)
            with patch.object(candidate, "git", return_value="") as git_call:
                candidate.require_clean_tracked_source(checkout, "Externals/example")
                git_call.assert_called_once()

    def test_verifier_rejects_dirty_direct_submodule_before_native_audit(self):
        """Exercise the complete direct Gitlink loop, not just its helper."""
        with TemporaryDirectory() as temp:
            root = Path(temp)
            sha = "a" * 40
            paths = [f"Externals/submodule_{i}" for i in range(34)]
            for path in paths:
                (root / path).mkdir(parents=True)
            for suffix in ("child_0", "child_1"):
                (root / paths[0] / suffix).mkdir()
            (root / paths[1] / "child_2").mkdir()
            direct = {path: {"sha": sha} for path in paths}
            nested = {"status": candidate.INDEX_STATUS,
                      "dolphin_parent_commit": candidate.REV,
                      "parents": [
                          {"parent_path": paths[0], "parent_gitlink_commit": sha,
                           "nested": [{"path": "child_0", "gitlink_commit": sha},
                                      {"path": "child_1", "gitlink_commit": sha}]},
                          {"parent_path": paths[1], "parent_gitlink_commit": sha,
                           "nested": [{"path": "child_2", "gitlink_commit": sha}]}]}
            direct_file = root / "direct.json"
            nested_file = root / "nested.json"
            direct_file.write_text(json.dumps({"parent_commit": candidate.REV}))
            nested_file.write_text(json.dumps(nested))

            def fake_git(checkout, *args):
                if args == ("rev-parse", "HEAD"):
                    return candidate.REV if checkout == root else sha
                if args[:1] == ("rev-parse",):
                    return sha
                if args == ("status", "--porcelain", "--untracked-files=no"):
                    return " M edited.cpp" if checkout == root / paths[17] else ""
                raise AssertionError((checkout, args))

            with patch.object(candidate, "validate_index", return_value=direct), \
                 patch.object(candidate, "git", side_effect=fake_git):
                with self.assertRaisesRegex(ValueError, "tracked source was edited: " + paths[17]):
                    candidate.verify_original_source(root, direct_index=direct_file,
                                                     nested_index=nested_file)

    def test_refuses_wrong_or_tampered_native(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            native = root / "dolphin_libretro.so"
            native.write_bytes(b"TEST-ONLY not an ELF core" * 20_000)
            with self.assertRaisesRegex(ValueError, "ELF"):
                candidate.verify_original_library(native)
            native.rename(root / "unapproved-build.so")
            with self.assertRaisesRegex(ValueError, "Missing unmodified original"):
                candidate.verify_original_library(root / "unapproved-build.so")

    def test_elf_architecture_and_shared_object_contract(self):
        """Reject ELF-magic impostors before symbol inspection or hashing."""
        with TemporaryDirectory() as temp:
            native = Path(temp) / "dolphin_libretro.so"
            header = bytearray(64)
            header[:4] = b"\x7fELF"
            header[4:7] = b"\x02\x01\x01"
            header[16:18] = (3).to_bytes(2, "little")
            header[18:20] = (62).to_bytes(2, "little")
            header[20:24] = (1).to_bytes(4, "little")
            header[32:40] = (64).to_bytes(8, "little")
            header[52:54] = (64).to_bytes(2, "little")
            header[54:56] = (56).to_bytes(2, "little")
            header[56:58] = (2).to_bytes(2, "little")
            for offset, replacement in (
                (4, b"\x01"),            # ELF32
                (5, b"\x02"),            # big endian
                (6, b"\x00"),            # unsupported ELF version
                (16, (2).to_bytes(2, "little")),  # ET_EXEC
                (18, (183).to_bytes(2, "little")), # AArch64
            ):
                invalid = bytearray(header)
                invalid[offset:offset + len(replacement)] = replacement
                native.write_bytes(bytes(invalid) + b"\0" * 200_000)
                with patch.object(candidate.subprocess, "check_output") as nm:
                    with self.subTest(offset=offset):
                        with self.assertRaisesRegex(ValueError, "ELF64 shared-library architecture"):
                            candidate.verify_original_library(native)
                    nm.assert_not_called()
            for offset, replacement in (
                (20, (0).to_bytes(4, "little")),
                (32, (0).to_bytes(8, "little")),
                (32, (500_000).to_bytes(8, "little")),
                (52, (0).to_bytes(2, "little")),
                (54, (32).to_bytes(2, "little")),
                (56, (0).to_bytes(2, "little")),
            ):
                invalid = bytearray(header)
                invalid[offset:offset + len(replacement)] = replacement
                native.write_bytes(bytes(invalid) + b"\0" * 200_000)
                with patch.object(candidate.subprocess, "check_output") as nm:
                    with self.subTest(structure_offset=offset):
                        with self.assertRaisesRegex(ValueError, "program-header table"):
                            candidate.verify_original_library(native)
                    nm.assert_not_called()
            # Two genuine file-backed segments: PT_LOAD and PT_DYNAMIC.
            segments = bytearray(112)
            for index, kind in enumerate((1, 2)):
                pos = index * 56
                segments[pos:pos + 4] = kind.to_bytes(4, "little")
                segments[pos + 8:pos + 16] = (176).to_bytes(8, "little")
                segments[pos + 32:pos + 40] = (64).to_bytes(8, "little")
                segments[pos + 40:pos + 48] = (64).to_bytes(8, "little")
            for mutation, expected in (
                (lambda p: p.__setitem__(slice(0, 4), (0).to_bytes(4, "little")), "loadable or dynamic"),
                (lambda p: p.__setitem__(slice(56, 60), (0).to_bytes(4, "little")), "loadable or dynamic"),
                (lambda p: p.__setitem__(slice(8, 16), (300_000).to_bytes(8, "little")), "segment file bounds"),
                (lambda p: p.__setitem__(slice(32, 40), (128).to_bytes(8, "little")), "segment file bounds"),
            ):
                bad = bytearray(segments)
                mutation(bad)
                native.write_bytes(bytes(header) + bytes(bad) + b"\0" * 200_000)
                with patch.object(candidate.subprocess, "check_output") as nm:
                    with self.subTest(segment_failure=expected):
                        with self.assertRaisesRegex(ValueError, expected):
                            candidate.verify_original_library(native)
                    nm.assert_not_called()
            native.write_bytes(bytes(header) + bytes(segments) + b"\0" * 200_000)
            symbols = "\n".join("00000000 T " + symbol for symbol in candidate.MANDATORY_LIBRETRO_SYMBOLS)
            with patch.object(candidate.subprocess, "check_output", return_value=symbols):
                proof = candidate.verify_original_library(native)
            self.assertEqual(proof["native_size_bytes"], native.stat().st_size)
            self.assertEqual(len(proof["native_sha256"]), 64)

    def test_audit_never_grants_public_distribution_or_buildbot_equivalence(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "proof.json"
            direct = {"parent_commit": candidate.REV, "direct_gitlinks_verified": 34,
                      "nested_gitlinks_verified": 3}
            compiled = {"filename": "dolphin_libretro.so",
                        "native_sha256": "a" * 64,
                        "native_size_bytes": 10_000_000,
                        "verified_exports": list(candidate.MANDATORY_LIBRETRO_SYMBOLS)}
            with patch.object(candidate, "verify_original_source", return_value=direct), \
                 patch.object(candidate, "verify_original_library", return_value=compiled):
                report = candidate.audit(root, root / "dolphin_libretro.so", output)
                self.assertTrue(report["original_unmodified_dolphin_source_compiled"])
                for field in ("old_buildbot_binary_equivalence_claimed",
                              "physical_gameplay_tested",
                              "complete_corresponding_source_and_runtime_dependencies_reviewed",
                              "combined_gpl_distribution_reviewed",
                              "public_binary_distribution_approved"):
                    self.assertFalse(report[field])
                self.assertEqual(json.loads(output.read_text()), report)
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    candidate.audit(root, root / "dolphin_libretro.so", output)


if __name__ == "__main__":
    unittest.main()
