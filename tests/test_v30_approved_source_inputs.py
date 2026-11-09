"""Synthetic 44-native source/rights contract for the genuine production stager.

Every test author-created image is fake, not a real emulator or license.
The actual checked-in source/license/physical approval flags remain FALSE.
The production CLI cannot be invoked by these synthetic test fixtures.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fetch_mgba_core import CORE_NAMES, OPTIONAL_V21_CORES
from tools.v30_release_lock import (
    ALTERNATIVE_CORE_ORDER, TARGETS, SOURCE_BUILT_TEN, selected_source_families,
)
from tools.stage_v30_gpl_trial_inputs import package_native_zip
from tools.prepare_v30_dolphin_source_sys import DOLPHIN_REV, PINNED_SYS_TREE_SHA1
from tools import stage_v30_approved_source_inputs as staging
from anything_plays.v30_approved_core_map import (
    EXPECTED, REPOSITORIES, TEN_EXPECTED, TEN_REPOSITORIES, WINDOWS_RUNTIME,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fake_original_bytes(name, ext):
    return package_native_zip(name, ext, (f"TEST-ONLY native {name}{ext}".encode() * 10000))


def fake_source(name, target):
    ext = staging.EXT[target]
    binary = (f"TEST-ONLY compiled original {name}{ext}".encode() * 10000)
    notice = (b"GNU GENERAL PUBLIC LICENSE " +
              f"TEST ONLY {name} exact notice".encode())
    return binary, notice, sha(f"source archive for {name} on {target}".encode())


def synthetic_target(root, target):
    """Prepare 4-target review fields and one exact source-original ZIP set."""
    ext = staging.EXT[target]
    root = Path(root)
    native = root / "original"
    native.mkdir()
    originals = frozenset((*CORE_NAMES, *OPTIONAL_V21_CORES))
    rows, old = [], {}
    for name in sorted(originals):
        archive_name = f"{name}_libretro{ext}.zip"
        data = fake_original_bytes(name, ext)
        old[archive_name] = data
        rows.append({"name": archive_name, "sha256": sha(data), "size_bytes": len(data)})
        (native / archive_name).write_bytes(data)
    dolphin = b"ORIGINAL TEST-ONLY Dolphin Sys archive" * 100
    old["Dolphin.zip"] = dolphin
    (native / "Dolphin.zip").write_bytes(dolphin)
    rows.append({"name": "Dolphin.zip", "sha256": sha(dolphin),
                 "size_bytes": len(dolphin)})
    (native / "PRESERVED_NATIVE_INPUTS.json").write_text(json.dumps({
        "target": {
            "windows-x86_64": "windows-x64", "linux-x86_64": "linux-x64",
            "macos-arm64": "macos-arm64", "macos-x86_64": "macos-x64",
        }[target],
        "status": "UNAPPROVED-TEST-INPUTS",
        "public_distribution_approved": False,
        "original_archive_count": 12, "files": rows,
    }), "utf-8")
    lock_row = {
        "approved_for_distribution": True, "cores": {},
        "runtime_dependencies": {},
        "dolphin_sys": {
            "original_archive_sha256": sha(dolphin),
            "original_archive_size_bytes": len(dolphin),
            "source_correspondence_verified": True, "redistribution_approved": True,
        },
    }
    src_row = {
        "cores": {},
        "dolphin_sys": {
            **lock_row["dolphin_sys"], "source_and_license_reviewed": True,
        },
    }
    source_bytes = {}
    for name in ALTERNATIVE_CORE_ORDER:
        if name in EXPECTED:
            blob, notice, source_sha = fake_source(name, target)
            zipped = package_native_zip(name, ext, blob)
            notice_sha = sha(notice)
            source_commit = EXPECTED[name]
            repository = REPOSITORIES[name]
            source_bytes[name] = (blob, notice, source_sha)
        else:
            zipped = old[f"{name}_libretro{ext}.zip"]
            blob = (f"TEST-ONLY native {name}{ext}".encode() * 10000)
            notice_sha = None
            source_sha = sha(f"original source for {name}{target}".encode())
            source_commit = "a" * 40
            repository = "https://github.com/libretro/" + name
        row = {
            "file": f"{name}_libretro{ext}",
            "native_sha256": sha(blob), "native_size_bytes": len(blob),
            "original_archive_sha256": sha(zipped),
            "original_archive_size_bytes": len(zipped),
            "source_commit_sha": source_commit,
            "upstream_source_repository": repository,
            "redistribution_approved": True, "corresponding_source_verified": True,
        }
        if notice_sha is not None:
            row["original_license_notice_sha256"] = notice_sha
        lock_row["cores"][name] = row
        src_row["cores"][name] = {
            "source_commit_sha": source_commit,
            "native_sha256": sha(blob),
            "original_native_archive_sha256": sha(zipped),
            "source_repository": repository,
            "source_archive_sha256": source_sha,
            "source_archive_size_bytes": 6000,
            "source_build_dependencies_reviewed": True,
            "source_to_binary_verified": True, "redistribution_license_reviewed": True,
        }
    runtime = None
    if target == "windows-x86_64":
        runtime = b"MZ" + b"TEST-ONLY synthetic MinGW runtime " * 2000
        lock_row["runtime_dependencies"] = {WINDOWS_RUNTIME: sha(runtime)}
        lock_row["runtime_dependency_source_reviewed"] = True
        (root / "runtime.dll").write_bytes(runtime)
    return lock_row, src_row, source_bytes, old, runtime


def synthetic_four_platform_review(root):
    root = Path(root)
    lock = {
        "schema_version": 1, "core_set_id": "gpl-source-built-alternative",
        "source_commit": "b" * 40, "approved_for_binary_distribution": True,
        "license_compatibility_reviewed": True,
        "corresponding_source_inventory_verified": True,
        "legacy_noncommercial_native_binaries_excluded": True,
        "source_built_alternative_binary_rights_reviewed": True,
        "native_core_count": 11, "system_profile_count": 18,
        "targets": {},
    }
    source = {
        "schema_version": 1, "source_commit": lock["source_commit"],
        "native_core_count": 11,
        "approved_for_public_binary_distribution": True,
        "corresponding_source_inventory_verified": True,
        "independent_binary_to_source_match_proven": True,
        "targets": {},
    }
    fixtures = {}
    for target in sorted(TARGETS):
        (root / target).mkdir()
        reviewed, src, compiled, originals, runtime = synthetic_target(root / target, target)
        lock["targets"][target] = reviewed
        source["targets"][target] = src
        fixtures[target] = (root / target, compiled, originals, runtime)
    return lock, source, fixtures


def original_stub(compiled):
    def source(location, name, target, ext):
        return compiled[name]
    return source


class CompleteReviewedSourceInputContracts(unittest.TestCase):

    def test_ten_original_source_approved_path_requires_original_git_source_sys(self):
        """Synthetic-only: ten native source family SHA + pinned source Sys, zero real rights."""
        with TemporaryDirectory() as temp:
            lock, source, fixtures = synthetic_four_platform_review(temp)
            lock["core_set_id"] = "gpl-source-built-ten"
            lock["ten_source_built_families_reviewed"] = True
            lock["one_unchanged_dolphin_family_reviewed"] = True
            self.assertEqual(selected_source_families(lock), SOURCE_BUILT_TEN)
            with patch.dict(os.environ, {
                "AP_RELEASE_BUILD": "1", "AP_V30_APPROVED_RELEASE": "1",
                "AP_V30_GPL_TRIAL": "0", "AP_V30_TEST_CORES": "0",
            }, clear=True):
                for target, (folder, original_compiled, originals, runtime) in fixtures.items():
                    with self.subTest(target=target):
                        ext = staging.EXT[target]
                        source_inputs = dict(original_compiled)
                        for name in TEN_EXPECTED:
                            native, notice, archive_sha = fake_source(name, target)
                            source_inputs[name] = (native, notice, archive_sha)
                            row = lock["targets"][target]["cores"][name]
                            row["source_commit_sha"] = TEN_EXPECTED[name]
                            row["upstream_source_repository"] = TEN_REPOSITORIES[name]
                            row["native_sha256"] = sha(native)
                            row["native_size_bytes"] = len(native)
                            archive = package_native_zip(name, ext, native)
                            row["original_archive_sha256"] = sha(archive)
                            row["original_archive_size_bytes"] = len(archive)
                            row["original_license_notice_sha256"] = sha(notice)
                            reviewed = source["targets"][target]["cores"][name]
                            reviewed.update(
                                source_commit_sha=TEN_EXPECTED[name],
                                source_repository=TEN_REPOSITORIES[name],
                                native_sha256=sha(native),
                                original_native_archive_sha256=sha(archive),
                                source_archive_sha256=archive_sha,
                            )
                        mgba_native, _, mgba_source_sha = source_inputs["mgba"]
                        mgba_notice = b"TEST ONLY Mozilla Public License Version 2.0"
                        lock["targets"][target]["cores"]["mgba"]["original_license_notice_sha256"] = sha(mgba_notice)
                        n64_native, _, n64_source_sha = source_inputs["parallel_n64"]
                        n64_notices = {
                            f"GPL-TRIAL-N64-NOTICE-{i:02}.txt": f"TEST ONLY source notice {i}".encode()
                            for i in range(1, 12)
                        }
                        n64_notices_sha = sha(json.dumps(
                            {name: sha(data) for name, data in sorted(n64_notices.items())},
                            sort_keys=True, separators=(",", ":")).encode())
                        lock["targets"][target]["cores"]["parallel_n64"]["original_license_notice_sha256"] = n64_notices_sha
                        snes = folder / "snes"; sega = folder / "sega"
                        snes.mkdir(); sega.mkdir()
                        pce = folder / "pce.zip"; pce.write_bytes(b"synthetic test only")
                        five = {}
                        for name in ("fceumm", "stella2014", "prosystem",
                                     "mednafen_ngp", "mednafen_wswan"):
                            loc = folder / name
                            loc.mkdir()
                            five[name] = loc
                        mgba = folder / "mgba"; mgba.mkdir()
                        n64 = folder / "n64"; n64.mkdir()
                        sys_dir = folder / "source-sys"; sys_dir.mkdir()
                        exact_sys_data = b"TEST ONLY original source Git Dolphin Sys ZIP " * 130
                        exact_sys_receipt = {
                            "original_git_data_sys_tree_sha1": PINNED_SYS_TREE_SHA1,
                            "public_distribution_approved": False,
                            "source_asset_rights_independently_approved": False,
                        }
                        locked_sys = lock["targets"][target]["dolphin_sys"]
                        locked_sys.update(
                            original_archive_sha256=sha(exact_sys_data),
                            original_archive_size_bytes=len(exact_sys_data),
                            original_upstream_source_commit=DOLPHIN_REV,
                            original_git_data_sys_tree_sha1=PINNED_SYS_TREE_SHA1,
                        )
                        source_sys = source["targets"][target]["dolphin_sys"]
                        source_sys.update(
                            original_archive_sha256=sha(exact_sys_data),
                            original_archive_size_bytes=len(exact_sys_data),
                        )
                        def five_stub(location, name, original_target, original_ext):
                            binary, notice, archive_sha = source_inputs[name]
                            return binary, notice, {
                                "source_archive_sha256": archive_sha,
                                "original_license_notice_copied": True,
                            }
                        def mgba_stub(location, original_target):
                            return mgba_native, mgba_notice, {
                                "source_commit": TEN_EXPECTED["mgba"],
                                "source_repository": TEN_REPOSITORIES["mgba"],
                                "source_archive_sha256": mgba_source_sha,
                                "native_sha256": sha(mgba_native),
                                "source_build_run_id": 42527449154,
                            }
                        def n64_stub(location, original_target):
                            return n64_native, n64_notices, {
                                "source_commit": TEN_EXPECTED["parallel_n64"],
                                "source_repository": TEN_REPOSITORIES["parallel_n64"],
                                "original_source_sha256": n64_source_sha,
                                "native_sha256": sha(n64_native),
                                "source_build_run_id": 42534736496,
                            }
                        with patch.object(staging, "_source_original_family",
                                          side_effect=original_stub(source_inputs)), \
                             patch.object(staging, "check_original_five_artifact",
                                          side_effect=five_stub), \
                             patch.object(staging, "inspect_original_mgba",
                                          side_effect=mgba_stub), \
                             patch.object(staging, "check_original_n64_artifact",
                                          side_effect=n64_stub), \
                             patch.object(staging, "exact_original_sys_artifact",
                                          return_value=(exact_sys_data, exact_sys_receipt)):
                            result = staging.assemble_approved_inputs(
                                lock=lock, inventory=source, target=target,
                                original_dir=folder / "original",
                                snes_dir=snes, sega_dir=sega, pce_artifact=pce,
                                output_dir=folder / "output", five_dirs=five,
                                mgba_dir=mgba, n64_dir=n64, dolphin_sys_dir=sys_dir,
                                windows_runtime=folder / "runtime.dll" if runtime else None,
                            )
                        self.assertEqual(result["unchanged_original_core_count"], 1)
                        self.assertEqual(set(result["source_built_families"]), SOURCE_BUILT_TEN)
                        self.assertFalse(result["auto_granted_license_rights"])
                        built = folder / "output"
                        self.assertEqual((built / "Dolphin.zip").read_bytes(), exact_sys_data)
                        self.assertNotEqual((built / "Dolphin.zip").read_bytes(), originals["Dolphin.zip"])
                        self.assertEqual(
                            result["source_exact_dolphin_sys_evidence"],
                            exact_sys_receipt,
                        )
                        for name in TEN_EXPECTED:
                            package = built / f"{name}_libretro{ext}.zip"
                            self.assertTrue(package.is_file())
                            self.assertNotEqual(package.read_bytes(), originals.get(package.name))
                        self.assertEqual(
                            (built / "MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt").read_bytes(), mgba_notice)
                        for notice_name, bytes_ in n64_notices.items():
                            self.assertEqual((built / notice_name).read_bytes(), bytes_)
                        for forbidden in ("snes9x", "genesis_plus_gx"):
                            self.assertFalse((built / f"{forbidden}_libretro{ext}.zip").exists())

    def test_approved_production_cli_uses_namespace_native_and_dolphin_sys_paths(self):
        """Regression: release CLI must not subscript an argparse.Namespace."""
        with TemporaryDirectory() as temp:
            base = Path(temp)
            (base / "docs").mkdir()
            (base / "docs" / "V3_LICENSE_COMPATIBILITY_APPROVED.md").write_text(
                "SYNTHETIC TEST only", "utf-8")
            source = base / "source.json"
            source.write_text("{}", "utf-8")
            lock = {
                "core_set_id": "gpl-source-built-ten",
                "legacy_noncommercial_native_binaries_excluded": True,
                "source_built_alternative_binary_rights_reviewed": True,
                "ten_source_built_families_reviewed": True,
                "one_unchanged_dolphin_family_reviewed": True,
            }
            command = [
                "--target", "linux-x86_64",
                "--original-dir", str(base / "old"),
                "--snes-dir", str(base / "snes"),
                "--sega-dir", str(base / "sega"),
                "--pce-artifact", str(base / "pce.zip"),
                "--output-dir", str(base / "out"),
                "--mgba-dir", str(base / "mgba"),
                "--n64-dir", str(base / "n64"),
                "--dolphin-sys-dir", str(base / "sys"),
            ]
            for name in sorted(staging.SOURCE_BUILT_FIVE):
                command.extend([
                    "--" + name.replace("_", "-") + "-dir",
                    str(base / name),
                ])
            with patch.object(staging, "ROOT", base), \
                 patch.object(staging, "SOURCE_FILE", source), \
                 patch.object(staging, "load_approved_lock", return_value=lock), \
                 patch.object(staging, "assemble_approved_inputs",
                              return_value={"target": "linux-x86_64"}) as staged:
                self.assertEqual(staging.main(command), 0)
            kwargs = staged.call_args.kwargs
            self.assertEqual(kwargs["mgba_dir"], base / "mgba")
            self.assertEqual(kwargs["n64_dir"], base / "n64")
            self.assertEqual(kwargs["dolphin_sys_dir"], base / "sys")
            self.assertEqual(set(kwargs["five_dirs"]), staging.SOURCE_BUILT_FIVE)

    def test_ten_source_staging_never_overwrites_any_evidence_directory(self):
        """All original source proofs must survive invalid output locations."""
        with TemporaryDirectory() as temp:
            lock, source, fixtures = synthetic_four_platform_review(temp)
            lock["core_set_id"] = "gpl-source-built-ten"
            lock["ten_source_built_families_reviewed"] = True
            lock["one_unchanged_dolphin_family_reviewed"] = True
            folder, _, _, _ = fixtures["linux-x86_64"]
            snes = folder / "snes"; snes.mkdir()
            sega = folder / "sega"; sega.mkdir()
            pce = folder / "pce.zip"; pce.write_bytes(b"test source")
            five = {}
            for name in ("fceumm", "stella2014", "prosystem",
                         "mednafen_ngp", "mednafen_wswan"):
                five[name] = folder / name
                five[name].mkdir()
            mgba = folder / "mgba"; mgba.mkdir()
            n64 = folder / "n64"; n64.mkdir()
            dolphin = folder / "dolphin_sys"; dolphin.mkdir()
            evidence = [folder / "original", snes, sega, *five.values(),
                        mgba, n64, dolphin]
            # This regression isolates the pre-write filesystem guard.
            # The full source/rights contract is independently exercised by
            # the synthetic four-platform staging tests below.
            with patch.object(staging, "validate_source_inventory", return_value=True), \
                 patch.object(staging, "approved_core_map_from_lock", return_value={}), \
                 patch.dict(os.environ, {
                     "AP_RELEASE_BUILD": "1", "AP_V30_APPROVED_RELEASE": "1",
                     "AP_V30_GPL_TRIAL": "0", "AP_V30_TEST_CORES": "0",
                 }, clear=True):
                for protected in evidence:
                    marker = protected / "immutable-source-proof.txt"
                    marker.write_text("original", encoding="utf-8")
                    output = protected / "staged"
                    with self.subTest(protected=protected.name):
                        with self.assertRaisesRegex(ValueError, "overwrite original"):
                            staging.assemble_approved_inputs(
                                lock=lock, inventory=source, target="linux-x86_64",
                                original_dir=folder / "original",
                                snes_dir=snes, sega_dir=sega, pce_artifact=pce,
                                output_dir=output, five_dirs=five,
                                mgba_dir=mgba, n64_dir=n64, dolphin_sys_dir=dolphin,
                            )
                        self.assertFalse(output.exists())
                        self.assertEqual(marker.read_text("utf-8"), "original")


    def test_ten_source_lock_alone_never_satisfies_actual_license_approval(self):
        with TemporaryDirectory() as temp:
            lock, source, fixtures = synthetic_four_platform_review(temp)
            lock["core_set_id"] = "gpl-source-built-ten"
            with self.assertRaises(ValueError):
                selected_source_families(lock)
            lock["ten_source_built_families_reviewed"] = True
            with self.assertRaises(ValueError):
                selected_source_families(lock)
            lock["one_unchanged_dolphin_family_reviewed"] = True
            self.assertEqual(selected_source_families(lock), SOURCE_BUILT_TEN)
            # Current checked-in, real production source/license review is still false.
            with self.assertRaises(ValueError):
                staging.load_approved_lock()

    def test_current_3_0_staging_cli_will_not_claim_approval(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            target = "linux-x86_64"
            with self.assertRaises(SystemExit) as failure:
                staging.main([
                    "--target", target, "--original-dir", str(root / "old"),
                    "--snes-dir", str(root / "snes"),
                    "--sega-dir", str(root / "sega"),
                    "--pce-artifact", str(root / "pce.zip"),
                    "--output-dir", str(root / "out"),
                ])
            self.assertEqual(failure.exception.code, 1)
            self.assertFalse((root / "out").exists())

    def test_all_four_synthetic_reviewed_archives_stage_exact_8_plus_3_and_sys(self):
        with TemporaryDirectory() as temp:
            lock, source, fixtures = synthetic_four_platform_review(temp)
            with patch.dict(os.environ, {
                "AP_RELEASE_BUILD": "1", "AP_V30_APPROVED_RELEASE": "1",
                "AP_V30_GPL_TRIAL": "0", "AP_V30_TEST_CORES": "0",
            }, clear=True):
                for target, (folder, compiled, originals, runtime) in fixtures.items():
                    with self.subTest(target=target):
                        snes, sega = folder / "snes", folder / "sega"
                        snes.mkdir(); sega.mkdir()
                        artifact = folder / "pce.zip"
                        artifact.write_bytes(b"TEST-ONLY PCE source artifact stub")
                        output = folder / "output"
                        with patch.object(staging, "_source_original_family",
                                          side_effect=original_stub(compiled)):
                            row = staging.assemble_approved_inputs(
                                lock=lock, inventory=source, target=target,
                                original_dir=folder / "original",
                                snes_dir=snes, sega_dir=sega,
                                pce_artifact=artifact, output_dir=output,
                                windows_runtime=(folder / "runtime.dll" if runtime else None),
                            )
                        self.assertEqual(row["native_core_count"], 11)
                        self.assertEqual(row["system_profile_count"], 18)
                        self.assertEqual(row["unchanged_original_core_count"], 8)
                        self.assertEqual(set(row["source_built_families"]), set(EXPECTED))
                        self.assertFalse(row["auto_granted_license_rights"])
                        self.assertEqual(row["original_dolphin_sys_sha256"], sha(originals["Dolphin.zip"]))
                        self.assertEqual((output / "Dolphin.zip").read_bytes(),
                                         originals["Dolphin.zip"])
                        ext = staging.EXT[target]
                        for original_name in staging.UNCHANGED_8:
                            name = f"{original_name}_libretro{ext}.zip"
                            self.assertEqual((output / name).read_bytes(), originals[name])
                        for name in EXPECTED:
                            archive = output / f"{name}_libretro{ext}.zip"
                            self.assertTrue(archive.is_file())
                            self.assertEqual(sha(archive.read_bytes()),
                                             lock["targets"][target]["cores"][name]["original_archive_sha256"])
                            self.assertEqual((output / staging.NOTICES[name][1]).read_bytes(),
                                             compiled[name][1])
                        for forbidden in ("snes9x", "genesis_plus_gx"):
                            self.assertFalse((output / f"{forbidden}_libretro{ext}.zip").exists())
                        self.assertEqual((output / WINDOWS_RUNTIME).exists(), runtime is not None)
                        self.assertTrue((output / staging.RECEIPT).is_file())
                        expected = {f"{name}_libretro{ext}.zip" for name in ALTERNATIVE_CORE_ORDER}
                        expected.add("Dolphin.zip")
                        expected.update(x[1] for x in staging.NOTICES.values())
                        expected.add(staging.RECEIPT)
                        if runtime:
                            expected.add(WINDOWS_RUNTIME)
                        self.assertEqual({p.name for p in output.iterdir()}, expected)

    def test_tampering_source_or_original_nightly_never_creates_approved_inputs(self):
        with TemporaryDirectory() as temp:
            lock, source, fixtures = synthetic_four_platform_review(temp)
            folder, compiled, originals, runtime = fixtures["linux-x86_64"]
            (folder / "snes").mkdir()
            (folder / "sega").mkdir()
            (folder / "pce.zip").write_bytes(b"fake PCE")
            kwargs = {
                "lock": lock, "inventory": source, "target": "linux-x86_64",
                "original_dir": folder / "original",
                "snes_dir": folder / "snes", "sega_dir": folder / "sega",
                "pce_artifact": folder / "pce.zip", "output_dir": folder / "out",
            }
            with patch.dict(os.environ, {
                "AP_RELEASE_BUILD": "1", "AP_V30_APPROVED_RELEASE": "1",
                "AP_V30_GPL_TRIAL": "0", "AP_V30_TEST_CORES": "0",
            }, clear=True), patch.object(staging, "_source_original_family",
                                           side_effect=original_stub(compiled)):
                tamper = folder / "original" / "mgba_libretro.so.zip"
                saved = tamper.read_bytes()
                tamper.write_bytes(b"silently replaced original archive")
                with self.assertRaises(ValueError):
                    staging.assemble_approved_inputs(**kwargs)
                self.assertFalse((folder / "out").exists())
                tamper.write_bytes(saved)
                revised = dict(compiled)
                binary, notice, source_sha = revised["blastem"]
                revised["blastem"] = (binary + b"tamper", notice, source_sha)
                with patch.object(staging, "_source_original_family",
                                  side_effect=original_stub(revised)):
                    with self.assertRaises(ValueError):
                        staging.assemble_approved_inputs(**kwargs)
                self.assertFalse((folder / "out").exists())
                revised = dict(compiled)
                binary, notice, source_sha = revised["mednafen_supafaust"]
                revised["mednafen_supafaust"] = (binary, notice + b"unreviewed", source_sha)
                with patch.object(staging, "_source_original_family",
                                  side_effect=original_stub(revised)):
                    with self.assertRaises(ValueError):
                        staging.assemble_approved_inputs(**kwargs)
                self.assertFalse((folder / "out").exists())
                with patch.dict(os.environ, {"AP_V30_GPL_TRIAL": "1"}):
                    with self.assertRaises(ValueError):
                        staging.assemble_approved_inputs(**kwargs)
                with patch.dict(os.environ, {"AP_V30_GPL_TRIAL": "0",
                                             "AP_V30_APPROVED_RELEASE": "0"}):
                    with self.assertRaises(ValueError):
                        staging.assemble_approved_inputs(**kwargs)
                self.assertFalse((folder / "out").exists())

    def test_compromised_four_platform_source_or_license_record_blocked(self):
        with TemporaryDirectory() as temp:
            lock, source, fixtures = synthetic_four_platform_review(temp)
            folder, compiled, _, _ = fixtures["linux-x86_64"]
            (folder / "snes").mkdir(); (folder / "sega").mkdir()
            (folder / "pce.zip").write_bytes(b"fake PCE")
            kwargs = dict(lock=lock, inventory=source, target="linux-x86_64",
                          original_dir=folder / "original",
                          snes_dir=folder / "snes", sega_dir=folder / "sega",
                          pce_artifact=folder / "pce.zip", output_dir=folder / "out")
            with patch.dict(os.environ, {
                "AP_RELEASE_BUILD": "1", "AP_V30_APPROVED_RELEASE": "1",
                "AP_V30_GPL_TRIAL": "0", "AP_V30_TEST_CORES": "0",
            }, clear=True), patch.object(staging, "_source_original_family",
                                           side_effect=original_stub(compiled)):
                lock["license_compatibility_reviewed"] = False
                with self.assertRaises(ValueError):
                    staging.assemble_approved_inputs(**kwargs)
                lock["license_compatibility_reviewed"] = True
                source["targets"]["macos-arm64"]["cores"]["blastem"]["source_to_binary_verified"] = False
                with self.assertRaises(ValueError):
                    staging.assemble_approved_inputs(**kwargs)
                self.assertFalse((folder / "out").exists())

    def test_workflow_reads_approved_lock_before_download_and_never_uploads_unreviewed_binaries(self):
        repo = Path(__file__).resolve().parents[1]
        yml = (repo / ".github/workflows/v30-production-candidates.yml").read_text("utf-8")
        self.assertIn("refs/heads/main", yml)
        self.assertIn("tools/check_v30_release.py", yml)
        self.assertIn("tools.check_v30_source_gate", yml)
        self.assertIn("tools.stage_v30_approved_source_inputs", yml)
        self.assertIn("42494297281", yml)
        self.assertIn("42496671418", yml)
        self.assertIn("42444367068", yml)
        self.assertIn("source-built", yml.lower())
        self.assertIn("--pce-artifact original-source-built-pce.zip", yml)
        self.assertIn("--output-dir \"$AP_CORE_ARCHIVE_DIR\"", yml)
        self.assertNotIn("gh release create", yml)
        self.assertNotIn("AP_V30_GPL_TRIAL: '1'", yml)
        self.assertIn("APPROVED-3.0-DISTRIBUTION", yml)


if __name__ == "__main__":
    unittest.main()
