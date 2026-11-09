"""Only genuine upstream GPL2+ Tia with Atari A/V may enter approved source builds.

All binary/source inputs below are entirely synthetic. This test never
approves an actual emulator for public release or changes the real lock.
"""
import io
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.verify_v30_tia_production_source import validate_production_tia
from tools.stage_v30_approved_source_inputs import SOURCE_BUILT_FIVE_TIA
from tools.v30_release_lock import SOURCE_BUILT_FIVE, SOURCE_BUILT_ELEVEN_TIA, load_approved_lock


COPYING = b"GNU GENERAL PUBLIC LICENSE Version 2 or later\n" * 30
SPDX = b"// SPDX-License-Identifier: GPL-2.0-or-later\n" * 100
README = b"Original Tia source, GPL-2.0-or-later\n" * 20


def make_inputs(root):
    root = Path(root)
    checkout = root / "original-tia"
    checkout.mkdir()
    (checkout / "README.md").write_bytes(README)
    tar = root / "original-source.tar"
    with tarfile.open(tar, "w") as z:
        for name, data in (
            ("COPYING", COPYING),
            ("src/libretro.c", SPDX),
            ("README.md", README),
            ("Makefile", b"all:\n"),
            ("src/libretro.h", b"void foo();\n"),
            ("src/input.c", b"void input(){}\n"),
            ("src/tia.c", b"void tia(){}\n"),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            z.addfile(info, io.BytesIO(data))
    native = root / "tia_libretro.dll"
    native.write_bytes(b"MZ" + b"SYNTHETIC-NOT-REAL-EMULATOR" * 1200)
    report = root / "report.json"
    report.write_text(json.dumps({
        "passed": True, "native_exit_code": 0, "timed_out": False,
        "details": {
            "passed": True, "video_frames": 300,
            "unique_frame_hashes": 4,
            "pcm_nonzero_samples": 1500,
            "pcm_sample_peak": 500,
        },
    }))
    return {
        "source_checkout": checkout,
        "source_tar": tar,
        "native": native,
        "playback_report": report,
        "target": "windows-x64",
    }


class OriginalTiaProduction(unittest.TestCase):
    def verify(self, paths):
        with patch("tools.verify_v30_tia_production_source._source",
                   return_value=(COPYING, SPDX)):
            return validate_production_tia(**paths)

    def test_same_five_family_slot_and_original_license_payload(self):
        self.assertEqual(SOURCE_BUILT_FIVE_TIA - SOURCE_BUILT_FIVE, {"tia"})
        self.assertEqual(SOURCE_BUILT_FIVE - SOURCE_BUILT_FIVE_TIA, {"stella2014"})
        self.assertEqual(len(SOURCE_BUILT_FIVE_TIA), 5)
        self.assertEqual(len(SOURCE_BUILT_ELEVEN_TIA), 11)
        with TemporaryDirectory() as tmp:
            paths = make_inputs(tmp)
            row = self.verify(paths)
            self.assertEqual(row["source_commit"],
                             "6ae5bf998fe7a7842294089db17fc86fd73db1f0")
            self.assertEqual(row["copying"], COPYING)
            self.assertEqual(row["source_spdx"], SPDX)
            self.assertEqual(row["native"], paths["native"].read_bytes())
            self.assertFalse(row["public_binary_distribution_approved_by_this_verifier"])

    def test_source_archive_must_match_immutable_original_git_contents(self):
        with TemporaryDirectory() as tmp:
            paths = make_inputs(tmp)
            (paths["source_checkout"]/"README.md").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "Malformed Tia source TAR member|source differs|differs from TAR"):
                self.verify(paths)

    def test_original_gameplay_must_render_video_and_emit_real_pcm(self):
        with TemporaryDirectory() as tmp:
            paths = make_inputs(tmp)
            report = paths["playback_report"]
            data=json.loads(report.read_text())
            data["details"]["pcm_nonzero_samples"]=0
            report.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "video/PCM"):
                self.verify(paths)

    def test_wrong_native_platform_is_rejected(self):
        with TemporaryDirectory() as tmp:
            paths = make_inputs(tmp)
            paths["target"]="macos-x64"
            with self.assertRaisesRegex(ValueError, "native"):
                self.verify(paths)

    def test_original_production_workflow_no_longer_requires_stella(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root/".github/workflows/v30-production-candidates.yml").read_text()
        self.assertIn("ALTERNATIVE_TIA_CORE_NAMES",workflow)
        self.assertIn("SOURCE_BUILT_ELEVEN_TIA",workflow)
        self.assertIn("--tia-dir original-tia",workflow)
        self.assertIn("--tia-native",workflow)
        self.assertIn("--tia-source-tar",workflow)
        self.assertIn("--tia-playback-report",workflow)
        self.assertIn("SPDX-License-Identifier: GPL-2.0-or-later",workflow)
        self.assertIn("tools/probe_atari_homebrew.py",workflow)
        self.assertNotIn("--stella2014-dir",workflow)
        self.assertNotIn("gh release create",workflow)

    def test_release_lock_is_not_fabricated(self):
        with self.assertRaisesRegex(ValueError, "redistribution blocked"):
            load_approved_lock()


if __name__=="__main__":
    unittest.main()
