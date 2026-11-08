"""Source-only contracts for the complete unapproved 3.0 offline GPL trial."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
from zipfile import ZipFile

from anything_plays import core_locator
from anything_plays.v30_gpl_trial import (
    MARKER, STATUS, EXPECTED_SOURCE_COMMITS, PROFILE_TO_CORE,
    find_trial_core, validate_trial_core_directory,
)
from fetch_mgba_core import (
    CORE_NAMES, OPTIONAL_V21_CORES, V30_GPL_TRIAL_CORES,
    core_names_for_build, SOURCE_REPOSITORIES,
)
from tools.stage_v30_gpl_trial_inputs import stage_inputs, TARGET_EXT

HOST_TARGET = ("windows-x64" if sys.platform == "win32"
               else "macos-arm64" if sys.platform == "darwin"
               else "linux-x64")
EXT = TARGET_EXT[HOST_TARGET]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fake_source(folder, kind):
    folder.mkdir()
    native_name = ("mednafen_supafaust" if kind == "snes" else "blastem") + "_libretro" + EXT
    native = folder / native_name
    native.write_bytes(b"not executable: unit-test original-source fake" * 1500)
    source_manifest = {
        "target": HOST_TARGET,
        "source_commit": EXPECTED_SOURCE_COMMITS["mednafen_supafaust" if kind == "snes" else "blastem"],
        "native_sha256": digest(native.read_bytes()),
        "source_archive_sha256": "1" * 64,
    }
    if kind == "snes":
        source_manifest.update(
            native_name=native_name, compiled_from_exact_upstream_checkout=True,
            replaces_current_snes9x_in_app=False, public_binary_redistribution_approved=False)
        notice, manifest = "SUPAFAUST_ORIGINAL_GPL2_LICENSE.txt", "SUPAFAUST_SOURCE_BUILD_UNAPPROVED.json"
    else:
        source_manifest.update(
            native_filename=native_name, candidate="blastem",
            compiled_from_exact_pinned_source_checkout=True,
            matches_current_3_0_shipped_libretro_library=False,
            public_binary_distribution_approved=False)
        notice, manifest = "blastem-GPLv3-NOTICE.txt", "PINNED_GPL_ALTERNATIVE_SOURCE_BUILD_UNAPPROVED.json"
    (folder / notice).write_text("Synthetic GPL license fixture, NOT actual original license", "utf-8")
    (folder / manifest).write_text(json.dumps(source_manifest), "utf-8")
    (folder / "fake-original-source.tar.gz").write_bytes(b"fixture")
    (folder / "SHA256SUMS.txt").write_text(
        "".join(f"{digest(p.read_bytes())}  {p.name}\n" for p in sorted(folder.iterdir())
                if p.name != "SHA256SUMS.txt"),
        "ascii",
    )
    return native


def fake_original(folder):
    folder.mkdir()
    rows = []
    for name in (*CORE_NAMES, *OPTIONAL_V21_CORES):
        filename = f"{name}_libretro{EXT}.zip"
        raw = f"original research artifact for {name}".encode("ascii")
        (folder / filename).write_bytes(raw)
        rows.append({"name": filename, "sha256": digest(raw), "size_bytes": len(raw)})
    data = b"original unmodified dolphin sys zip"
    (folder / "Dolphin.zip").write_bytes(data)
    rows.append({"name": "Dolphin.zip", "sha256": digest(data), "size_bytes": len(data)})
    (folder / "PRESERVED_NATIVE_INPUTS.json").write_text(
        json.dumps({"target": HOST_TARGET, "status": "UNAPPROVED-TEST-INPUTS",
                    "public_distribution_approved": False,
                    "original_archive_count": 12, "files": rows}), "utf-8")


def env():
    return mock.patch.dict(os.environ, {
        "AP_V30_GPL_TRIAL": "1",
        "AP_V30_TEST_CORES": "1",
        "AP_RELEASE_BUILD": "0",
        "AP_V30_APPROVED_RELEASE": "0",
        "AP_CORE_ARCHIVE_DIR": "/tmp/only-test-no-real-installer",
    })


class FullGPLOfflineTrial(TestCase):
    def test_exact_11_core_slots_and_original_normal_mode_unchanged(self):
        expected_original = (*CORE_NAMES, *OPTIONAL_V21_CORES)
        self.assertEqual(len(expected_original), 11)
        self.assertEqual(len(V30_GPL_TRIAL_CORES), 11)
        self.assertIn("snes9x", expected_original)
        self.assertIn("genesis_plus_gx", expected_original)
        self.assertNotIn("snes9x", V30_GPL_TRIAL_CORES)
        self.assertNotIn("genesis_plus_gx", V30_GPL_TRIAL_CORES)
        self.assertIn("mednafen_supafaust", V30_GPL_TRIAL_CORES)
        self.assertIn("blastem", V30_GPL_TRIAL_CORES)
        self.assertEqual(len(PROFILE_TO_CORE), 5)
        from anything_plays.systems import SYSTEMS
        self.assertEqual(len(SYSTEMS), 18)
        self.assertEqual(SYSTEMS["snes"].core, "snes9x")
        self.assertEqual(SYSTEMS["genesis"].core, "genesis_plus_gx")
        for name in ("mednafen_supafaust", "blastem"):
            self.assertTrue(SOURCE_REPOSITORIES[name].startswith("https://github.com/libretro/"))
        with mock.patch.dict(os.environ, {"AP_V30_GPL_TRIAL": "0",
                                         "AP_V30_TEST_CORES": "1",
                                         "AP_RELEASE_BUILD": "0"},
                             clear=True):
            self.assertEqual(core_names_for_build(), expected_original)
        with env():
            self.assertEqual(core_names_for_build(), V30_GPL_TRIAL_CORES)
            with mock.patch.dict(os.environ, {"AP_RELEASE_BUILD": "1"}):
                with self.assertRaises(ValueError):
                    core_names_for_build()
            with mock.patch.dict(os.environ, {"AP_V30_APPROVED_RELEASE": "1"}):
                with self.assertRaises(ValueError):
                    core_names_for_build()

    def test_exact_original_12_archive_staging_no_nc_binaries(self):
        with TemporaryDirectory() as tmp, env():
            root = Path(tmp)
            original, snes, sega = (root / "old", root / "snes", root / "sega")
            fake_original(original)
            fake_source(snes, "snes")
            fake_source(sega, "sega")
            output, proof = root / "trial", root / "evidence" / "record.json"
            result = stage_inputs(original, snes, sega, output, proof, HOST_TARGET)
            self.assertEqual(result["status"], STATUS)
            self.assertEqual(result["native_core_count"], 11)
            self.assertEqual(result["all_console_profiles"], 18)
            self.assertFalse(result["combined_gpl_license_reviewed"])
            self.assertFalse(result["public_binary_distribution_approved"])
            self.assertEqual(result["original_unchanged_core_archives"], 9)
            expected = {f"{n}_libretro{EXT}.zip" for n in V30_GPL_TRIAL_CORES}
            expected |= {"Dolphin.zip", MARKER,
                         "GPL-TRIAL-Supafaust-COPYING.txt",
                         "GPL-TRIAL-BlastEm-COPYING.txt"}
            self.assertEqual({p.name for p in output.iterdir()}, expected)
            self.assertEqual((output / "Dolphin.zip").read_bytes(),
                             (original / "Dolphin.zip").read_bytes())
            for core in ("mednafen_supafaust", "blastem"):
                archive = output / (f"{core}_libretro{EXT}.zip")
                with ZipFile(archive) as z:
                    self.assertEqual(z.namelist(), [f"{core}_libretro{EXT}"])
                    self.assertEqual(digest(z.read(z.namelist()[0])),
                                     result["alternatives"][core]["native_sha256"])
            installed = root / "installed-cores"
            installed.mkdir()
            (installed / MARKER).write_bytes((output / MARKER).read_bytes())
            for name in ("mednafen_supafaust", "blastem"):
                with ZipFile(output / f"{name}_libretro{EXT}.zip") as z:
                    (installed / f"{name}_libretro{EXT}").write_bytes(
                        z.read(f"{name}_libretro{EXT}"))
            self.assertEqual(validate_trial_core_directory(installed, EXT)["status"], STATUS)
            self.assertEqual(find_trial_core([installed], "snes", EXT)[1],
                             str(installed / f"mednafen_supafaust_libretro{EXT}"))
            self.assertEqual(find_trial_core([installed], "mastersystem", EXT)[1],
                             str(installed / f"blastem_libretro{EXT}"))
            self.assertEqual(find_trial_core([installed], "gamecube", EXT), (False, None))
            with mock.patch.object(core_locator, "_search_directories", return_value=[installed]):
                self.assertEqual(core_locator.find_core("snes"),
                                 str(installed / f"mednafen_supafaust_libretro{EXT}"))
            (installed / f"blastem_libretro{EXT}").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                validate_trial_core_directory(installed, EXT)
            with mock.patch.object(core_locator, "_search_directories", return_value=[installed]):
                self.assertIsNone(core_locator.find_core("genesis"))

    def test_forged_approval_and_original_nc_library_both_fail_closed(self):
        with TemporaryDirectory() as tmp, env():
            root = Path(tmp)
            fake_original(root / "original")
            fake_source(root / "snes", "snes")
            fake_source(root / "sega", "sega")
            output = root / "output"
            stage_inputs(root / "original", root / "snes", root / "sega",
                         output, root / "proof.json", HOST_TARGET)
            info = json.loads((output / MARKER).read_text("utf-8"))
            for flag in ("public_binary_distribution_approved",
                         "combined_gpl_license_reviewed",
                         "physical_qa_approved",
                         "production_core_substitution_approved"):
                self.assertIs(info[flag], False)
            path = output / MARKER
            info["combined_gpl_license_reviewed"] = True
            path.write_text(json.dumps(info), "utf-8")
            with self.assertRaises(ValueError):
                validate_trial_core_directory(output, EXT, verify_native=False)
            info["combined_gpl_license_reviewed"] = False
            path.write_text(json.dumps(info), "utf-8")
            (output / f"snes9x_libretro{EXT}").write_bytes(b"forbidden")
            with self.assertRaises(ValueError):
                validate_trial_core_directory(output, EXT, verify_native=False)

    def test_stage_will_not_run_in_production_or_with_changed_original_zip(self):
        with TemporaryDirectory() as tmp, env():
            root = Path(tmp)
            fake_original(root / "original")
            fake_source(root / "snes", "snes")
            fake_source(root / "sega", "sega")
            (root / "original" / f"snes9x_libretro{EXT}.zip").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                stage_inputs(root / "original", root / "snes", root / "sega",
                             root / "dst", root / "proof.json", HOST_TARGET)
            self.assertFalse((root / "dst").exists())
            with mock.patch.dict(os.environ, {"AP_RELEASE_BUILD": "1"}):
                with self.assertRaises(ValueError):
                    stage_inputs(root / "original", root / "snes", root / "sega",
                                 root / "dst", root / "proof.json", HOST_TARGET)


if __name__ == "__main__":
    import unittest
    unittest.main()
