"""Fail-closed future production SNES/Sega/PCE native mapping contracts.

Only SYNTHETIC records. The tracked release rights/QA lock still fails and
NO actual reviewed production package can be created by this test.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays import core_locator
from anything_plays.v30_approved_core_map import (
    MARKER, EXPECTED, REPOSITORIES, TEN_EXPECTED, TEN_REPOSITORIES, WINDOWS_RUNTIME,
    find_approved_core, validate_installed_map,
)
from tools.stage_v30_approved_native_mapping import (
    approved_core_map_from_lock, stage_approved_map, stage_from_approved_lock,
)
from tools.v30_release_lock import ALTERNATIVE_CORE_ORDER


def sha(data):
    return hashlib.sha256(data).hexdigest()


NOTICE = {
    "mednafen_supafaust": "fixture GPL2 source original notice, NOT for release".encode(),
    "blastem": "fixture GPL3 source original notice, NOT for release".encode(),
    "mednafen_pce_fast": "fixture GPL2 PCE original notice, NOT for release".encode(),
}


def synthetic_reviewed_lock(target):
    ext = ".dll" if target == "windows-x86_64" else ".so" if target == "linux-x86_64" else ".dylib"
    cores = {}
    for name in ALTERNATIVE_CORE_ORDER:
        repository = REPOSITORIES.get(name, f"https://github.com/libretro/{name}")
        entry = {
            "file": f"{name}_libretro{ext}",
            "source_commit_sha": EXPECTED.get(name, "a" * 40),
            "upstream_source_repository": repository,
            "native_sha256": sha(("synthetic " + name).encode() * 1600),
            "corresponding_source_verified": True,
            "redistribution_approved": True,
        }
        if name in NOTICE:
            entry["original_license_notice_sha256"] = sha(NOTICE[name])
        cores[name] = entry
    lock = {
        "schema_version": 1, "core_set_id": "gpl-source-built-alternative",
        "legacy_noncommercial_native_binaries_excluded": True,
        "source_built_alternative_binary_rights_reviewed": True,
        "approved_for_binary_distribution": True,
        "license_compatibility_reviewed": True,
        "corresponding_source_inventory_verified": True,
        "native_core_count": 11, "system_profile_count": 18,
        "targets": {},
    }
    row = {"approved_for_distribution": True, "cores": cores}
    if target == "windows-x86_64":
        runtime = b"MZ" + b"synthetic non-executable winpthread fixture" * 600
        row.update(runtime_dependency_source_reviewed=True,
                   runtime_dependencies={WINDOWS_RUNTIME: sha(runtime)})
    else:
        runtime = None
        row["runtime_dependencies"] = {}
    lock["targets"][target] = row
    return lock, runtime, ext


def supply_synthetic_installed_cores(folder, info, ext):
    for name in EXPECTED:
        payload = ("synthetic " + name).encode() * 1600
        (folder / f"{name}_libretro{ext}").write_bytes(payload)


class ApprovedNativeMapContracts(unittest.TestCase):

    def test_ten_source_core_map_preserves_direct_mgba_and_n64_routing(self):
        for target in ("linux-x86_64", "windows-x86_64", "macos-arm64", "macos-x86_64"):
            with self.subTest(target=target), TemporaryDirectory() as temp:
                root = Path(temp)
                cores, archives = root / "cores", root / "archives"
                cores.mkdir(); archives.mkdir()
                lock, runtime, ext = synthetic_reviewed_lock(target)
                lock["core_set_id"] = "gpl-source-built-ten"
                lock["ten_source_built_families_reviewed"] = True
                lock["one_unchanged_dolphin_family_reviewed"] = True
                for name in TEN_EXPECTED:
                    row = lock["targets"][target]["cores"][name]
                    row["source_commit_sha"] = TEN_EXPECTED[name]
                    row["upstream_source_repository"] = TEN_REPOSITORIES[name]
                    row["original_license_notice_sha256"] = sha(
                        f"TEST ONLY {name} upstream source notice".encode())
                if runtime:
                    (archives / WINDOWS_RUNTIME).write_bytes(runtime)
                staged = stage_approved_map(lock, target, cores, archives)
                self.assertEqual(staged["core_set_id"], "gpl-source-built-ten")
                self.assertEqual(set(staged["cores"]), set(TEN_EXPECTED))
                self.assertTrue(staged["ten_source_built_families_reviewed"])
                self.assertTrue(staged["one_unchanged_dolphin_family_reviewed"])
                for name in TEN_EXPECTED:
                    payload = ("synthetic " + name).encode() * 1600
                    (cores / f"{name}_libretro{ext}").write_bytes(payload)
                self.assertTrue(validate_installed_map(cores, ext))
                for system, name in (
                    ("gb", "mgba"), ("gbc", "mgba"), ("gba", "mgba"),
                    ("n64", "parallel_n64"), ("nes", "fceumm"),
                    ("snes", "mednafen_supafaust")):
                    found, native = find_approved_core([cores], system, ext)
                    self.assertTrue(found, system)
                    self.assertEqual(Path(native).name, f"{name}_libretro{ext}")
                (cores / f"parallel_n64_libretro{ext}").write_bytes(b"tampered")
                with self.assertRaises(ValueError):
                    find_approved_core([cores], "n64", ext)
                (cores / f"parallel_n64_libretro{ext}").write_bytes(
                    ("synthetic parallel_n64").encode() * 1600)
                marker = cores / MARKER
                forged = json.loads(marker.read_text("utf-8"))
                forged["one_unchanged_dolphin_family_reviewed"] = False
                marker.write_text(json.dumps(forged), "utf-8")
                with self.assertRaises(ValueError):
                    validate_installed_map(cores, ext)

    def test_existing_real_repository_rights_do_not_allow_prod_staging(self):
        with TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                stage_from_approved_lock(Path(root), Path(root), "linux-x86_64")

    def test_reviewed_source_built_core_identity_on_all_four_targets(self):
        for target in ("windows-x86_64", "linux-x86_64", "macos-arm64", "macos-x86_64"):
            with self.subTest(target=target), TemporaryDirectory() as temp:
                root = Path(temp)
                cores, archive = root / "cores", root / "source"
                cores.mkdir()
                archive.mkdir()
                lock, runtime, ext = synthetic_reviewed_lock(target)
                if runtime:
                    (archive / WINDOWS_RUNTIME).write_bytes(runtime)
                staged = stage_approved_map(lock, target, cores, archive)
                self.assertEqual(staged["status"], "SOURCE-REVIEWED-18-PROFILE-11-CORE-ALTERNATIVE-PAYLOAD")
                self.assertEqual(staged["native_core_count"], 11)
                self.assertEqual(staged["all_console_profiles"], 18)
                self.assertEqual(set(staged["cores"]), set(EXPECTED))
                self.assertFalse((cores / f"snes9x_libretro{ext}").exists())
                self.assertFalse((cores / f"genesis_plus_gx_libretro{ext}").exists())
                supply_synthetic_installed_cores(cores, staged, ext)
                verified = validate_installed_map(cores, ext)
                self.assertEqual(verified["cores"], staged["cores"])
                for system, name in (("snes", "mednafen_supafaust"), ("genesis", "blastem"),
                                     ("mastersystem", "blastem"), ("gamegear", "blastem"),
                                     ("sg1000", "blastem"), ("pce", "mednafen_pce_fast")):
                    present, path = find_approved_core([cores], system, ext)
                    self.assertTrue(present)
                    self.assertEqual(Path(path).name, f"{name}_libretro{ext}")
                self.assertEqual(find_approved_core([cores], "gamecube", ext), (False, None))
                self.assertEqual(find_approved_core([cores], "n64", ext), (False, None))
                self.assertEqual(find_approved_core([cores], "gba", ext), (False, None))
                with patch.object(core_locator, "_search_directories", return_value=[cores]), \
                     patch.object(core_locator, "_library_extension", return_value=ext):
                    self.assertEqual(Path(core_locator.find_core("snes")).name,
                                     f"mednafen_supafaust_libretro{ext}")
                    self.assertEqual(Path(core_locator.find_core("pce")).name,
                                     f"mednafen_pce_fast_libretro{ext}")

    def test_altered_or_old_noncommercial_native_is_never_loaded(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            cores, archive = root / "cores", root / "archives"
            cores.mkdir(); archive.mkdir()
            lock, _, ext = synthetic_reviewed_lock("linux-x86_64")
            stage_approved_map(lock, "linux-x86_64", cores, archive)
            supply_synthetic_installed_cores(cores, None, ext)
            marker = cores / MARKER
            self.assertTrue(validate_installed_map(cores, ext))
            native = cores / f"blastem_libretro{ext}"
            native.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                find_approved_core([cores], "genesis", ext)
            with patch.object(core_locator, "_search_directories", return_value=[cores]), \
                 patch.object(core_locator, "_library_extension", return_value=ext):
                self.assertIsNone(core_locator.find_core("genesis"))
            supply_synthetic_installed_cores(cores, None, ext)
            (cores / f"snes9x_libretro{ext}").write_bytes(b"unreviewed NC library")
            with self.assertRaises(ValueError):
                validate_installed_map(cores, ext)
            (cores / f"snes9x_libretro{ext}").unlink()
            meta = json.loads(marker.read_text())
            meta["cores"]["blastem"]["source_commit"] = "0" * 40
            marker.write_text(json.dumps(meta))
            with self.assertRaises(ValueError):
                validate_installed_map(cores, ext)

    def test_wrong_source_notice_or_windows_runtime_fails_before_writes(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            cores, archive = root / "cores", root / "archive"
            cores.mkdir(); archive.mkdir()
            lock, runtime, ext = synthetic_reviewed_lock("windows-x86_64")
            with self.assertRaises(ValueError):
                stage_approved_map(lock, "windows-x86_64", cores, archive)
            self.assertFalse((cores / MARKER).exists())
            (archive / WINDOWS_RUNTIME).write_bytes(runtime)
            lock["targets"]["windows-x86_64"]["cores"]["blastem"]["original_license_notice_sha256"] = None
            with self.assertRaises(ValueError):
                stage_approved_map(lock, "windows-x86_64", cores, archive)
            self.assertFalse((cores / MARKER).exists())
            lock["targets"]["windows-x86_64"]["cores"]["blastem"]["original_license_notice_sha256"] = sha(NOTICE["blastem"])
            stage_approved_map(lock, "windows-x86_64", cores, archive)
            supply_synthetic_installed_cores(cores, None, ext)
            self.assertTrue(validate_installed_map(cores, ext))
            dep = cores / WINDOWS_RUNTIME
            dep.write_bytes(b"modified")
            with self.assertRaises(ValueError):
                validate_installed_map(cores, ext)

    def test_production_packagers_use_exact_native_marker_only_when_approved(self):
        repo = Path(__file__).resolve().parents[1]
        for filename in ("packaging/build_windows.bat", "packaging/build_linux_deb.sh",
                         "packaging/build_macos_dmg.sh"):
            text = (repo / filename).read_text("utf-8")
            self.assertIn(MARKER, text, filename)
            self.assertIn("AP_V30_APPROVED_RELEASE", text, filename)
            for original in ("Supafaust-COPYING.txt", "BlastEm-COPYING.txt", "PCE-COPYING.txt"):
                self.assertIn(original, text, filename)
        fetcher = (repo / "fetch_mgba_core.py").read_text("utf-8")
        self.assertIn("stage_approved_map(", fetcher)
        self.assertIn("enable_windows_offline_runtime", fetcher)
        verifier = (repo / "verify_bundle.py").read_text("utf-8")
        self.assertIn("validate_installed_map(", verifier)


if __name__ == "__main__":
    unittest.main()
