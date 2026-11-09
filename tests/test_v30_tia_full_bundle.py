"""Only a real original Tia source + original Atari RGB/PCM proof replaces Stella."""
from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import tarfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from tools.stage_v30_gpl_trial_inputs import package_native_zip
from tools.stage_v30_tia_source_overlay import (
    COPYING_NAME, SOURCE_NOTICE_NAME, EVIDENCE_STATUS, stage_tia,
)

COPYING = b"GNU GENERAL PUBLIC LICENSE Version 2\n" * 20
SPDX = b"/* SPDX-License-Identifier: GPL-2.0-or-later */\n" * 20
README = b"GPL-2.0-or-later\n" * 100


def tar_source():
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in (("COPYING", COPYING), ("src/libretro.c", SPDX),
                           ("README.md", README)):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, BytesIO(data))
    return buf.getvalue()


def fixture(root: Path):
    baseline = root / "original-eleven"
    baseline.mkdir()
    (baseline / "stella2014_libretro.dll.zip").write_bytes(
        package_native_zip("stella2014", ".dll", b"MZ" + b"source fake" * 12000))
    (baseline / "mgba_libretro.dll.zip").write_bytes(b"original core proof preserved")
    (baseline / "GPL-TRIAL-stella2014-ORIGINAL-COPYING.txt").write_bytes(COPYING)
    (baseline / "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json").write_text("{}")
    source = root / "tia-checkout"
    (source / "src").mkdir(parents=True)
    (source / "README.md").write_bytes(README)
    (source / "src" / "libretro.c").write_bytes(SPDX)
    tar = root / "original-tia.tar"
    tar.write_bytes(tar_source())
    core = root / "tia_libretro.dll"
    core.write_bytes(b"MZ" + b"original-source-compiled-tia" * 3000)
    proof = root / "real-original-homebrew.json"
    proof.write_text(json.dumps({
        "passed": True, "native_exit_code": 0, "timed_out": False,
        "details": {
            "passed": True, "video_frames": 181,
            "nonblank_frames_sampled": 12,
            "unique_frame_hashes": 4,
            "pcm_nonzero_samples": 3000,
            "pcm_sample_peak": 2818,
        },
    }))
    marker = {
        "target": "windows-x64", "total_source_built_core_families": 11,
        "original_unchanged_core_archives": 0,
        "source_built_remaining_five": {"fceumm": {}, "stella2014": {},
                                        "prosystem": {}, "mednafen_ngp": {},
                                        "mednafen_wswan": {}},
        "source_built_dolphin": {"source_commit": "PINNED"},
        "source_built_n64": {"source_commit": "PINNED"},
        "public_binary_distribution_approved": False,
        "combined_gpl_license_reviewed": False,
        "physical_qa_approved": False,
        "production_core_substitution_approved": False,
    }
    return {
        "baseline": baseline, "source": source, "native": core,
        "source_tar": tar, "playback_report": proof,
        "output": root / "eleven-tia",
        "evidence": root / "provenance" / "tia.json",
        "target": "windows-x64",
    }, marker


class PinnedGPL2PlusTiaOverlayTests(unittest.TestCase):
    def call(self, inputs, marker):
        env = {"AP_V30_GPL_TRIAL": "1", "AP_V30_TEST_CORES": "1",
               "AP_V30_TIA_TRIAL": "1", "AP_RELEASE_BUILD": "0",
               "AP_V30_APPROVED_RELEASE": "0"}
        with patch.dict("os.environ", env), \
             patch("tools.stage_v30_tia_source_overlay.validate_trial_core_directory",
                   return_value=marker), \
             patch("tools.stage_v30_tia_source_overlay._source",
                   return_value=(COPYING, SPDX)):
            return stage_tia(**inputs)

    def test_exact_original_profile_replacement_and_license(self):
        with TemporaryDirectory() as tmp:
            inputs, marker = fixture(Path(tmp))
            old = (inputs["baseline"] / "stella2014_libretro.dll.zip").read_bytes()
            result = self.call(inputs, marker)
            self.assertEqual(result["source_built_tia"]["source_commit"],
                             "6ae5bf998fe7a7842294089db17fc86fd73db1f0")
            self.assertEqual(len(result["source_built_remaining_five"]), 5)
            self.assertNotIn("stella2014", result["source_built_remaining_five"])
            self.assertIn("tia", result["source_built_remaining_five"])
            self.assertEqual(result["source_built_tia"],
                             result["source_built_remaining_five"]["tia"])
            self.assertFalse(result["public_binary_distribution_approved"])
            self.assertTrue(result["original_stella2014_native_excluded"])
            dst = inputs["output"]
            self.assertFalse((dst / "stella2014_libretro.dll.zip").exists())
            self.assertFalse((dst / "GPL-TRIAL-stella2014-ORIGINAL-COPYING.txt").exists())
            self.assertTrue((dst / COPYING_NAME).read_bytes() == COPYING)
            self.assertTrue((dst / SOURCE_NOTICE_NAME).read_bytes() == SPDX)
            self.assertEqual((inputs["baseline"] / "stella2014_libretro.dll.zip").read_bytes(), old)
            with ZipFile(dst / "tia_libretro.dll.zip") as zip:
                self.assertEqual(zip.namelist(), ["tia_libretro.dll"])
                self.assertEqual(zip.read("tia_libretro.dll"), inputs["native"].read_bytes())
            report = json.loads(inputs["evidence"].read_text())
            self.assertEqual(report["status"], EVIDENCE_STATUS)
            self.assertEqual(report["original_core_count"], 11)
            self.assertEqual(report["original_profile_count"], 18)

    def test_missing_original_audio_or_video_cannot_stage(self):
        with TemporaryDirectory() as tmp:
            inputs, marker = fixture(Path(tmp))
            proof = inputs["playback_report"]
            row = json.loads(proof.read_text())
            row["details"]["pcm_nonzero_samples"] = 0
            proof.write_text(json.dumps(row))
            with self.assertRaisesRegex(ValueError, "PCM"):
                self.call(inputs, marker)
            self.assertFalse(inputs["output"].exists())

    def test_pinned_source_tar_must_match_git_checkout_exact_bytes(self):
        with TemporaryDirectory() as tmp:
            inputs, marker = fixture(Path(tmp))
            (inputs["source"] / "README.md").write_text("changed")
            with self.assertRaisesRegex(ValueError, "source TAR differs"):
                self.call(inputs, marker)
            self.assertFalse(inputs["output"].exists())

    def test_no_overwrite_of_original_evidence(self):
        with TemporaryDirectory() as tmp:
            inputs, marker = fixture(Path(tmp))
            original = inputs["baseline"] / "stella2014_libretro.dll.zip"
            before = original.read_bytes()
            inputs["output"] = inputs["baseline"] / "output"
            with self.assertRaisesRegex(ValueError, "overwrite"):
                self.call(inputs, marker)
            self.assertFalse(inputs["output"].exists())
            self.assertEqual(original.read_bytes(), before)

    def test_release_mode_is_not_silently_enabled(self):
        with TemporaryDirectory() as tmp:
            inputs, marker = fixture(Path(tmp))
            with patch.dict("os.environ", {
                "AP_V30_GPL_TRIAL": "1", "AP_V30_TEST_CORES": "1",
                "AP_V30_TIA_TRIAL": "1", "AP_RELEASE_BUILD": "1",
                "AP_V30_APPROVED_RELEASE": "1",
            }):
                with self.assertRaisesRegex(ValueError, "research only"):
                    stage_tia(**inputs)


if __name__ == "__main__":
    unittest.main()
