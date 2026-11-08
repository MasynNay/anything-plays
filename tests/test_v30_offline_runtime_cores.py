"""Regression contracts for complete offline native-core resolution from a real bundle layout."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from anything_plays import core_locator, core_packs
from anything_plays.systems import SYSTEMS
from tools.probe_v30_installed_offline_cores import (
    STATUS, TARGETS, check_offline_bundle, _blocked_network,
)
from tools.v30_release_lock import CORE_NAMES


def fake_bundle(root):
    target, ext = core_packs.target_identity()
    assert target in TARGETS
    assert len(SYSTEMS) == 18
    cores = root / "cores"
    cores.mkdir()
    records = []
    for name in sorted(CORE_NAMES):
        filename = f"{name}_libretro{ext}"
        data = (f"FAKE-INERT-NATIVE-TEST-DATA/{name}/{target}/").encode() * 4
        (cores / filename).write_bytes(data)
        records.append({
            "name": name,
            "file": filename,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
        })
    handler = cores / "dolphin-emu" / "Sys" / "codehandler.bin"
    handler.parent.mkdir(parents=True)
    handler.write_bytes(b"TEST-ONLY-DOLPHIN-SYS")
    (cores / "CORE_PROVENANCE.json").write_text(json.dumps({"cores": records}))
    return cores, target


class OfflineResolverAcceptanceTests(unittest.TestCase):
    def test_all_18_profiles_resolve_complete_hash_matched_payload_without_network(self):
        with TemporaryDirectory() as tmp:
            core_dir, target = fake_bundle(Path(tmp))
            report = check_offline_bundle(core_dir, target)
            self.assertEqual(report["status"], STATUS)
            self.assertEqual(report["systems_resolved_without_network"], 18)
            self.assertEqual(report["native_cores_hash_verified"], 11)
            self.assertEqual(set(report["system_to_core"]), set(SYSTEMS))
            self.assertEqual(set(report["native_payload_checksums"]), set(CORE_NAMES))
            self.assertTrue(report["no_external_emulator_setup_required_in_staged_bundle"])
            self.assertTrue(report["no_runtime_core_download_required_for_fresh_bundled_lookup"])
            for flag in ("physical_installer_launch_verified",
                         "real_gameplay_video_audio_input_verified",
                         "all_supported_games_verified",
                         "legal_distribution_review_complete",
                         "approved_for_public_release"):
                self.assertIs(report[flag], False)

    def test_tampering_missing_dolphin_sys_or_core_fails_closed(self):
        with TemporaryDirectory() as tmp:
            core_dir, target = fake_bundle(Path(tmp))
            filename = f"mgba_libretro{TARGETS[target]}"
            (core_dir / filename).write_bytes(b"WRONG NATIVE BYTES")
            with self.assertRaisesRegex(ValueError, "size mismatch|SHA-256 mismatch"):
                check_offline_bundle(core_dir, target)
        with TemporaryDirectory() as tmp:
            core_dir, target = fake_bundle(Path(tmp))
            (core_dir / "dolphin-emu/Sys/codehandler.bin").unlink()
            with self.assertRaisesRegex(ValueError, "Dolphin required Sys"):
                check_offline_bundle(core_dir, target)
        with TemporaryDirectory() as tmp:
            core_dir, target = fake_bundle(Path(tmp))
            (core_dir / f"snes9x_libretro{TARGETS[target]}").unlink()
            with self.assertRaisesRegex(ValueError, "core missing"):
                check_offline_bundle(core_dir, target)

    def test_duplicate_core_metadata_and_unsafe_symlinks_rejected(self):
        with TemporaryDirectory() as tmp:
            core_dir, target = fake_bundle(Path(tmp))
            p = core_dir / "CORE_PROVENANCE.json"
            data = json.loads(p.read_text())
            data["cores"][0]["name"] = data["cores"][1]["name"]
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "repeated native"):
                check_offline_bundle(core_dir, target)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            core_dir, target = fake_bundle(root)
            path = core_dir / "CORE_PROVENANCE.json"
            saved = path.read_bytes()
            path.unlink()
            path.symlink_to(root / "external.json")
            (root / "external.json").write_bytes(saved)
            with self.assertRaisesRegex(ValueError, "genuine native core provenance"):
                check_offline_bundle(core_dir, target)

    def test_reject_external_resolution_and_fake_success_through_network(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            core_dir, target = fake_bundle(root)
            external = root / "external"
            external.mkdir()
            (external / f"mgba_libretro{TARGETS[target]}").write_bytes(b"NOT-IN-INSTALLER")
            with self.assertRaisesRegex(ValueError, "external emulator"):
                check_offline_bundle(
                    core_dir, target,
                    lookup=lambda system: str(external / f"mgba_libretro{TARGETS[target]}"),
                )
            with self.assertRaisesRegex(AssertionError, "network"):
                check_offline_bundle(
                    core_dir, target,
                    lookup=lambda system: _blocked_network(),
                )

    def test_missing_target_and_developer_external_mode_disallowed(self):
        with TemporaryDirectory() as tmp:
            core_dir, target = fake_bundle(Path(tmp))
            with self.assertRaisesRegex(ValueError, "Unknown 3.0"):
                check_offline_bundle(core_dir, "macos-pc")
            other = next(k for k in TARGETS if k != target)
            with self.assertRaisesRegex(ValueError, "does not match"):
                check_offline_bundle(core_dir, other)
            with mock.patch.dict("os.environ", {"AP_V21_DEVELOPER_EXTERNAL": "1"}):
                with self.assertRaisesRegex(ValueError, "fallback"):
                    check_offline_bundle(core_dir, target)

    def test_actual_core_finder_developer_only_external_paths_are_opt_in(self):
        with mock.patch.dict("os.environ", {"AP_V21_DEVELOPER_EXTERNAL": "0"}):
            folders = [str(x).casefold() for x in core_locator._search_directories()]
        self.assertFalse(any("retroarch" in x for x in folders))
        self.assertFalse(any("/usr/lib/libretro" in x for x in folders))

    def test_ci_executes_real_installed_core_probe_with_true_payloads(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/v30-full-bundle.yml").read_text("utf-8")
        self.assertIn("tools/probe_v30_installed_offline_cores.py", workflow)
        self.assertIn("--core-dir", workflow)
        self.assertIn("test-evidence/offline-runtime-", workflow)
        self.assertIn("anything-plays-v30-fresh-core-store-", (root / "tools/probe_v30_installed_offline_cores.py").read_text())
        self.assertNotIn("gh release create", workflow)


if __name__ == "__main__":
    unittest.main()
