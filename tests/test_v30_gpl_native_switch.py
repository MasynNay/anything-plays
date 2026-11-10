"""Fail-closed contracts for genuine GPL-only 3.0 SNES/Sega switch research."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools import probe_v30_gpl_core_switch as mod


def fixture(root, system, target):
    root.mkdir()
    native_name = ("mednafen_supafaust_libretro" if system == "snes"
                   else "blastem_libretro") + mod.PLAT_SUFFIX
    native = root / native_name
    native.write_bytes(b"synthetic dummy native bytes - never executed")
    digest = hashlib.sha256(native.read_bytes()).hexdigest()
    manifest_name = ("SUPAFAUST_SOURCE_BUILD_UNAPPROVED.json" if system == "snes"
                     else "PINNED_GPL_ALTERNATIVE_SOURCE_BUILD_UNAPPROVED.json")
    obj = {"target": target, "source_commit": mod.PINS[system],
           "native_sha256": digest}
    if system == "snes":
        obj.update(native_name=native_name,
                   compiled_from_exact_upstream_checkout=True,
                   replaces_current_snes9x_in_app=False,
                   public_binary_redistribution_approved=False)
    else:
        obj.update(native_filename=native_name, candidate="blastem",
                   compiled_from_exact_pinned_source_checkout=True,
                   matches_current_3_0_shipped_libretro_library=False,
                   public_binary_distribution_approved=False)
    manifest = root / manifest_name
    manifest.write_text(json.dumps(obj), "utf-8")
    # Original source-build artifact contract has >=4 integrity-protected
    # members. These extra two are fake test files, not distributed artifacts.
    for index in range(2):
        (root / f"synthetic-source-{index}.txt").write_text(f"source test {index}", "utf-8")
    (root / "SHA256SUMS.txt").write_text(
        "".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
                for p in sorted(root.iterdir()) if p.name != "SHA256SUMS.txt"), "ascii")
    return native, manifest


class GPLSwitchEvidenceContracts(unittest.TestCase):
    def test_exact_7_cycle_scope_preserves_both_core_reentries(self):
        self.assertEqual(mod.CYCLES, (
            "snes", "mastersystem", "gamegear", "sg1000",
            "genesis", "snes", "mastersystem",
        ))
        self.assertEqual(len(mod.PINS), 2)

    def test_verbatim_checksum_and_repository_commit_required(self):
        target = ("windows-x64" if __import__("sys").platform == "win32"
                  else "macos-arm64" if __import__("sys").platform == "darwin"
                  else "linux-x64")
        with tempfile.TemporaryDirectory() as tmp:
            for system in ("snes", "sega"):
                root = Path(tmp) / system
                native, manifest = fixture(root, system, target)
                validated, digest = mod.validate_original_source_artifact(root, system, target)
                self.assertEqual(validated, native.resolve())
                self.assertEqual(digest, hashlib.sha256(native.read_bytes()).hexdigest())
                with self.assertRaises(ValueError):
                    mod.validate_original_source_artifact(root, system, "bogus-platform")
                native.write_bytes(b"tampered native")
                with self.assertRaises(ValueError):
                    mod.validate_original_source_artifact(root, system, target)
                native.write_bytes(b"synthetic dummy native bytes - never executed")
                obj = json.loads(manifest.read_text("utf-8"))
                obj["source_commit"] = "0" * 40
                manifest.write_text(json.dumps(obj), "utf-8")
                with self.assertRaises(ValueError):
                    mod.validate_original_source_artifact(root, system, target)

    def test_original_post_source_a_v_reports_are_accepted_but_not_used_as_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "src"
            fixture(root, "sega", "linux-x64")
            (root / "GENESIS_AV_UNAPPROVED.json").write_text('{"passed": true}', "utf-8")
            (root / "ISOLATED_SEGA_PROCESS_UNAPPROVED.json").write_text('{"passed": true}', "utf-8")
            (root / "mastersystem-test-frame.png").write_bytes(b"untrusted diagnostic image")
            native, digest = mod.validate_original_source_artifact(root, "sega", "linux-x64")
            self.assertEqual(hashlib.sha256(native.read_bytes()).hexdigest(), digest)
            (root / "unrecognized-emulator-native.so").write_bytes(b"unexpected")
            with self.assertRaises(ValueError):
                mod.validate_original_source_artifact(root, "sega", "linux-x64")

    def test_extra_symlink_and_mutated_license_approval_rejected(self):
        target = "linux-x64"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "src"
            native, manifest = fixture(root, "snes", target)
            extra = root / "unexpected.txt"
            extra.write_text("bad", "utf-8")
            with self.assertRaises(ValueError):
                mod.validate_original_source_artifact(root, "snes", target)
            extra.unlink()
            obj = json.loads(manifest.read_text("utf-8"))
            obj["public_binary_redistribution_approved"] = True
            manifest.write_text(json.dumps(obj), "utf-8")
            # The changed manifest also breaks the independent checksum, but
            # even after recomputing checksum the forbidden approval fails.
            checksums = root / "SHA256SUMS.txt"
            checksums.write_text(
                "".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
                        for p in sorted(root.iterdir()) if p.name != "SHA256SUMS.txt"), "ascii")
            with self.assertRaises(ValueError):
                mod.validate_original_source_artifact(root, "snes", target)

    def test_same_process_switch_alternatives_are_not_app_default(self):
        repo = Path(__file__).resolve().parents[1]
        data = (repo / "anything_plays/systems.py").read_text("utf-8")
        self.assertIn('"snes9x"', data)
        self.assertIn('"genesis_plus_gx"', data)
        self.assertNotIn('System("snes", "Super Nintendo", "mednafen_supafaust"', data)
        self.assertNotIn('System("genesis", "Sega Genesis / Mega Drive", "blastem"', data)
        workflow = (repo / "docs/history/workflows/v30-gpl-native-switch.yml").read_text("utf-8")
        self.assertIn("gh run download", workflow)
        self.assertIn("sha256sum -c", workflow)
        self.assertIn("AP_RELEASE_BUILD: '0'", workflow)
        self.assertIn("AP_V30_APPROVED_RELEASE: '0'", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("continue-on-error: true", workflow)
        for target in ("linux-x64", "windows-x64", "macos-x64", "macos-arm64"):
            self.assertIn("target: " + target, workflow)

    def test_probe_rejects_anything_not_original_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                mod.probe(root / "missing1", root / "missing2", "linux-x64",
                          5, root / "report.json")
            with self.assertRaises(ValueError):
                mod.probe(root / "missing1", root / "missing2", "linux-x64",
                          1, root / "report.json")
            with self.assertRaises(ValueError):
                mod.probe(root / "missing1", root / "missing2", "fake-platform",
                          5, root / "report.json")


if __name__ == "__main__":
    unittest.main()
