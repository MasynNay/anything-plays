"""Exact 37-Gitlink original macOS Dolphin source-build verification contracts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.verify_v30_dolphin_original_macos import (
    MAGIC_MACHO_64, MANDATORY_LIBRETRO_SYMBOLS, TARGET_ARCHES,
    audit, verify_original_macos_native,
)


class OriginalDolphinMacOSTests(unittest.TestCase):
    def make_native(self, root):
        p = Path(root) / "dolphin_libretro.dylib"
        p.write_bytes(MAGIC_MACHO_64 + b"\x00" * 300_000)
        return p

    def checks(self, path, target):
        def command(*args):
            if args[0] == "lipo":
                return TARGET_ARCHES[target]
            if args[0] == "nm":
                return "\n".join(f"0000000100000000 T _{s}"
                                 for s in MANDATORY_LIBRETRO_SYMBOLS)
            if args[0] == "otool":
                return f"{path}:\n\t/usr/lib/libSystem.B.dylib (compatibility version 1.0.0)"
            raise AssertionError(args)
        return command

    def test_original_macho_both_apple_architectures_fail_closed(self):
        for target in TARGET_ARCHES:
            with self.subTest(target=target), TemporaryDirectory() as temp:
                native = self.make_native(temp)
                with patch(
                    "tools.verify_v30_dolphin_original_macos._command",
                    side_effect=self.checks(native, target),
                ):
                    result = verify_original_macos_native(native, target)
                self.assertEqual(result["source_build_target"], target)
                self.assertEqual(result["architecture"], TARGET_ARCHES[target])
                self.assertEqual(result["native_sha256"],
                                 hashlib.sha256(native.read_bytes()).hexdigest())
                self.assertEqual(len(result["verified_exports"]),
                                 len(MANDATORY_LIBRETRO_SYMBOLS))
                self.assertTrue(result["mach_o_runtime_dependency_paths_not_yet_rights_reviewed"])

    def test_missing_symbols_bad_macho_and_wrong_cpu_rejected(self):
        with TemporaryDirectory() as temp:
            native = self.make_native(temp)
            native.write_bytes(b"faux" + b"\x00" * 300_000)
            with self.assertRaisesRegex(ValueError, "Mach-O"):
                verify_original_macos_native(native, "macos-arm64")
            native = self.make_native(temp)
            with patch(
                "tools.verify_v30_dolphin_original_macos._command",
                return_value="x86_64",
            ):
                with self.assertRaisesRegex(ValueError, "architecture"):
                    verify_original_macos_native(native, "macos-arm64")
            with patch(
                "tools.verify_v30_dolphin_original_macos._command",
                side_effect=lambda *args: (
                    "arm64" if args[0] == "lipo" else
                    "00000000 T _retro_init" if args[0] == "nm" else
                    "/usr/lib/libSystem.B.dylib (compatibility version 1.0.0)"
                ),
            ):
                with self.assertRaisesRegex(ValueError, "entrypoints"):
                    verify_original_macos_native(native, "macos-arm64")

    def test_mac_source_build_report_cannot_claim_public_distribution(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            native = self.make_native(root)
            proof = {"parent_commit": "32c61f9d0e933331bb7087ba57e96883241b4960",
                     "direct_gitlinks_verified": 34, "nested_gitlinks_verified": 3}
            source = lambda *_: proof
            for target in TARGET_ARCHES:
                report = root / (target + ".json")
                with patch(
                    "tools.verify_v30_dolphin_original_macos._command",
                    side_effect=self.checks(native, target),
                ):
                    result = audit(root, native, report, target,
                                   verify_source=source)
                self.assertEqual(json.loads(report.read_text("utf-8")), result)
                for f in (
                    "old_buildbot_binary_equivalence_claimed",
                    "physical_gameplay_tested",
                    "complete_corresponding_source_and_runtime_dependencies_reviewed",
                    "combined_gpl_distribution_reviewed",
                    "public_binary_distribution_approved",
                ):
                    self.assertIs(result[f], False)
                with self.assertRaisesRegex(ValueError, "already exist"):
                    audit(root, native, report, target,
                          verify_source=source,
                          verify_library=lambda *_: result)

    def test_forged_submodule_count_never_passes_audit(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            native=self.make_native(root)
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                audit(root, native, root/"proof.json", "macos-arm64",
                      verify_source=lambda *_: {"direct_gitlinks_verified": 33,
                                                "nested_gitlinks_verified": 3},
                      verify_library=lambda *_: {})
            self.assertFalse((root/"proof.json").exists())


if __name__ == "__main__":
    unittest.main()
