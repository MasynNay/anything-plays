"""Source-built PCE replacement hashes are fixed technical evidence, not release approval."""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/v3.0-pce-source-built-candidates.json"
SHA = re.compile(r"[0-9a-f]{64}\Z")
CANDIDATES = {
    "windows-x64": "mednafen_pce_fast_libretro.dll",
    "linux-x64": "mednafen_pce_fast_libretro.so",
    "macos-arm64": "mednafen_pce_fast_libretro.dylib",
    "macos-x64": "mednafen_pce_fast_libretro.dylib",
}


class SourceBuiltPCECandidateEvidenceTests(unittest.TestCase):
    def test_all_four_independently_verified_binary_and_source_hashes(self):
        document = json.loads(MANIFEST.read_text("utf-8"))
        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(
            document["status"],
            "UNAPPROVED-FOUR-PLATFORM-PINNED-PCE-REPLACEMENT-CANDIDATE",
        )
        self.assertEqual(
            document["source_commit"],
            "2de1ce1c3f237b161c126c54ba407990bb86d1e9",
        )
        self.assertEqual(document["source_license"], "GPL-2.0")
        self.assertEqual(set(document["targets"]), set(CANDIDATES))
        self.assertTrue(document["independent_artifact_checksum_verification_complete"])
        self.assertTrue(document["binary_to_new_source_build_verified"])
        self.assertFalse(document["binary_to_old_buildbot_source_match_proven"])
        self.assertFalse(document["old_preview_pce_binary_replaced"])
        self.assertFalse(document["mixed_gpl_noncommercial_distribution_approved"])
        self.assertFalse(document["rights_reviewed"])
        self.assertFalse(document["full_eleven_core_release_lock_approved"])

        linux_source_sha = document["targets"]["linux-x64"]["source_archive_sha256"]
        for target, expected_file in CANDIDATES.items():
            with self.subTest(target=target):
                row = document["targets"][target]
                self.assertEqual(row["native_file"], expected_file)
                for key in ("native_sha256", "source_archive_sha256", "test_report_sha256"):
                    self.assertRegex(row[key], SHA)
                self.assertGreater(row["native_size_bytes"], 100000)
                self.assertGreater(row["source_archive_size_bytes"], 100000)
                self.assertGreater(row["native_video_frames"], 100)
                self.assertGreater(row["native_pcm_nonzero_values"], 100000)
                self.assertFalse(row["approved_for_public_distribution"])
                self.assertFalse(row["bundled_into_stable_3_0"])
                self.assertGreater(row["artifact_id"], 0)
                if target != "windows-x64":
                    self.assertEqual(row["source_archive_sha256"], linux_source_sha)
        self.assertNotEqual(
            document["targets"]["windows-x64"]["source_archive_sha256"],
            linux_source_sha,
            "Do not erase Windows source archive normalization differences",
        )


if __name__ == "__main__":
    unittest.main()
