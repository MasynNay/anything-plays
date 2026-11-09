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
