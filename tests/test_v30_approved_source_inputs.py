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
from tools.v30_release_lock import ALTERNATIVE_CORE_ORDER, TARGETS
from tools.stage_v30_gpl_trial_inputs import package_native_zip
from tools import stage_v30_approved_source_inputs as staging
from anything_plays.v30_approved_core_map import EXPECTED, REPOSITORIES, WINDOWS_RUNTIME


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
