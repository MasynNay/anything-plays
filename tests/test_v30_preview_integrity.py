"""Validate 3.0 preview evidence without claiming release approval."""
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PreviewCandidateIntegrityTests(unittest.TestCase):
    def test_evidence_is_complete_and_not_publicly_approved(self):
        evidence = json.loads(
            (ROOT / "config/v3.0-preview-candidate-integrity.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(evidence["schema_version"], 1)
        self.assertFalse(evidence["public_release_approved"])
        self.assertEqual(len(evidence["installers"]), 4)
        self.assertEqual(
            set(evidence["installers"]),
            {"linux-x64", "windows-x64", "macos-arm64", "macos-x64"},
        )
        for record in evidence["installers"].values():
            self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", record["sha256"]))
            self.assertGreater(record["size_bytes"], 1024 * 1024)
        self.assertEqual(
            len({v["sha256"] for v in evidence["installers"].values()}), 4
        )
        cores = evidence["linux_native_cores"]
        self.assertEqual(len(cores), 11)
        self.assertEqual(len({v["name"] for v in cores}), 11)
        for core in cores:
            with self.subTest(name=core["name"]):
                self.assertEqual(core["filename"], core["name"] + "_libretro.so")
                self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", core["sha256"]))
                self.assertFalse(core["source_matches_binary_independently_verified"])
                sha = core["reported_source_commit"]
                self.assertTrue(sha is None or re.fullmatch(r"[0-9a-f]{40}", sha))
        self.assertFalse(
            next(v for v in cores if v["name"] == "mednafen_pce_fast")
            ["full_commit_exists_upstream"]
        )


if __name__ == "__main__":
    unittest.main()
