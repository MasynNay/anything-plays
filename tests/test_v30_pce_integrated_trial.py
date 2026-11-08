"""The source-built PC Engine trial is fully isolated from release inputs."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_STORED

from fetch_mgba_core import CORE_NAMES, OPTIONAL_V21_CORES
from tools.stage_v30_pce_trial_inputs import stage_inputs
from tools.v30_pce_candidate import (
    COMMIT, INDEX, RUN_ID, TARGETS, load_index, inspect_artifact,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SourceBuiltPCETests(unittest.TestCase):
    def test_four_platform_identities_pin_exact_original_actions_evidence(self):
        index = load_index()
        self.assertEqual(index["original_run_id"], RUN_ID)
        self.assertEqual(index["pinned_source_commit"], COMMIT)
        self.assertEqual(set(index["targets"]), set(TARGETS))
        self.assertFalse(index["approved_for_public_binary_distribution"])
        self.assertFalse(index["mixed_license_combined_distribution_reviewed"])
        self.assertFalse(index["source_equivalence_to_existing_buildbot_core_verified"])
        for target, row in index["targets"].items():
            with self.subTest(target=target):
                self.assertGreater(row["native_nonzero_pcm_values"], 1_000_000)
                self.assertGreater(row["native_video_frames"], 600)
                self.assertGreater(row["native_bytes"], 100_000)

    def test_locked_index_cannot_claim_unreviewed_rights_or_change_missing_platform(self):
        index = load_index()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"index.json"
            for change in (
                lambda d: d.update(approved_for_public_binary_distribution=True),
                lambda d: d.update(added_to_existing_preview=True),
                lambda d: d["targets"].pop("macos-x64"),
                lambda d: d["targets"]["linux-x64"].update(native_sha256="latest"),
            ):
                new = deepcopy(index)
                change(new)
                path.write_text(json.dumps(new), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_index(path)

    def test_original_artifact_core_hash_audio_source_and_license_must_all_match(self):
        original = load_index()
        target = "linux-x64"
        native = b"\x7fELF" + (b"source-built GPL native" * 4000)
        source = b"original matching GPLv2 source archive"
        license_data = b"GNU GENERAL PUBLIC LICENSE\nVersion 2, June 1991\n"
        details = {"passed": True, "native_video_frames": 718,
                   "native_nonzero_pcm_samples": 1054139}
        report = json.dumps({"passed": True, "details": details}).encode()
        row = original["targets"][target]
        row.update(native_sha256=sha(native), native_bytes=len(native),
                   source_archive_sha256=sha(source), source_archive_bytes=len(source),
                   native_report_sha256=sha(report))
        data = {
            "status": "UNAPPROVED-EXPERIMENTAL-PINNED-PCE-SOURCE-BUILD",
            "target": target,
            "source_repository": original["upstream_source_repository"],
            "source_commit": COMMIT,
            "native_core": row["core_filename"],
            "native_core_sha256": sha(native),
            "source_archive_sha256": sha(source),
            "third_party_distribution_approved": False,
            "mixed_core_licenses_reviewed": False,
        }
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/"artifact.zip"
            def write(fake_binary=native, changed_report=report, changed_license=license_data):
                with ZipFile(path,"w",ZIP_STORED) as zipped:
                    zipped.writestr(row["core_filename"], fake_binary)
                    zipped.writestr(original["source_archive_name"], source)
                    zipped.writestr("PCE_ORIGINAL_HUCARD_NATIVE_AV.json", changed_report)
                    zipped.writestr("PCE_COPYING_GPL-2.0.txt", changed_license)
                    zipped.writestr("PCE_SOURCE_BUILD_UNAPPROVED.json", json.dumps(data))
                    zipped.writestr("pce-frame.png", b"test image bytes")
            write()
            self.assertEqual(inspect_artifact(path,target,original),native)
            write(fake_binary=native + b"!")
            with self.assertRaisesRegex(ValueError,"native library bytes"):
                inspect_artifact(path,target,original)
            write(changed_license=b"no license notice")
            with self.assertRaisesRegex(ValueError,"GPL-2.0"):
                inspect_artifact(path,target,original)
            write(changed_report=b'{"passed":false}')
            with self.assertRaisesRegex(ValueError,"test evidence hash"):
                inspect_artifact(path,target,original)

    def test_frozen_ten_original_cores_survive_trial_and_release_mode_is_blocked(self):
        names = [*CORE_NAMES, *OPTIONAL_V21_CORES]
        self.assertEqual(len(names),11)
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            original = base/"unchanged-originals"
            original.mkdir()
            target="linux-x64"
            entries={}
            for name in names:
                archive_name=f"{name}_libretro.so.zip"
                payload=("unchanged original "+name).encode()
                (original/archive_name).write_bytes(payload)
                entries[archive_name]=payload
            entries["Dolphin.zip"] = b"original Dolphin Sys"
            (original/"Dolphin.zip").write_bytes(entries["Dolphin.zip"])
            record={
                "target":target,"status":"UNAPPROVED-TEST-INPUTS",
                "public_distribution_approved":False,
                "original_archive_count":12,
                "source_revision":"a"*40,
                "files":[{"name":name,"sha256":sha(data),"size_bytes":len(data)}
                         for name,data in entries.items()],
            }
            (original/"PRESERVED_NATIVE_INPUTS.json").write_text(json.dumps(record))
            sample_core=b"\x7fELF" + b"source-built PCE new binary" * 1000
            idx=load_index()
            idx["targets"][target]["native_sha256"]=sha(sample_core)
            with patch.dict(os.environ, {"AP_RELEASE_BUILD":"0","AP_V30_TEST_CORES":"1","AP_V30_APPROVED_RELEASE":"0"}):
                with patch("tools.stage_v30_pce_trial_inputs.load_index", return_value=idx):
                    with patch("tools.stage_v30_pce_trial_inputs.inspect_artifact", return_value=sample_core):
                        trial = stage_inputs(original,base/"candidate.zip",base/"staged",base/"evidence.json",target)
            self.assertEqual(trial["cores"],11)
            self.assertFalse(trial["public_release_approved"])
            self.assertEqual(len(list((base/"staged").iterdir())),12)
            for name,data in entries.items():
                self.assertEqual((original/name).read_bytes(),data)
                if not name.startswith("mednafen_pce_fast"):
                    self.assertEqual((base/"staged"/name).read_bytes(),data)
            with ZipFile(base/"staged/mednafen_pce_fast_libretro.so.zip") as packed:
                self.assertEqual(packed.read("mednafen_pce_fast_libretro.so"),sample_core)
            with patch.dict(os.environ, {"AP_RELEASE_BUILD":"1","AP_V30_TEST_CORES":"1","AP_V30_APPROVED_RELEASE":"0"}):
                with self.assertRaisesRegex(ValueError,"preview mode"):
                    stage_inputs(original,base/"candidate.zip",base/"blocked",base/"block.json",target)
            self.assertFalse((base/"blocked").exists())
            # Original archived source fingerprints remain intact throughout.
            self.assertEqual(json.loads((original/"PRESERVED_NATIVE_INPUTS.json").read_text()),record)


if __name__ == "__main__":
    unittest.main()
