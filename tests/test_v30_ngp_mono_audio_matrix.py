"""Fail-closed checks for all genuine pinned mono Neo Geo Pocket sound probes."""
from __future__ import annotations

from io import BytesIO
import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.probe_v30_ngp_mono_candidates import (
    INDEX, PROBE, STATUS, _check_native_child, fetch_candidate, scan,
    validate_index,
)


def gitblob(data):
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def report_for_child(*, has_audio=False, has_video=True, has_input=True):
    return {
        "system": "ngp",
        "native_audio_frames": 48000 if has_audio else 55000,
        "native_nonzero_pcm_values": 800 if has_audio else 0,
        "native_audio_peak": 140 if has_audio else 0,
        "sampled_nonblank_frames": 9 if has_video else 0,
        "manual_a_native_positive_samples": 5 if has_input else 0,
        "camera_b_native_positive_samples": 3 if has_input else 0,
        "audio_gate_passed": has_audio,
        "video_gate_passed": has_video,
        "input_gate_passed": has_input,
        "passed": has_audio and has_video and has_input,
    }


class OriginalMonoAudioResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads(INDEX.read_text("utf-8"))

    def test_upstream_git_tree_has_14_exact_mit_mono_candidates(self):
        records = validate_index(self.index)
        self.assertEqual(len(records), 14)
        self.assertIn("hw_calibration/a_align_calib_v12.ngp",
                      [x["path"] for x in records])
        self.assertTrue(all(x["path"].endswith(".ngp") for x in records))
        self.assertFalse(self.index["candidate_native_audio_verified"])
        self.assertFalse(self.index["distribution_in_app"])

    def test_fake_unpinned_or_reordered_roms_and_forged_rights_fail_closed(self):
        for mutate in (
            lambda x: x["candidates"].pop(),
            lambda x: x["candidates"].reverse(),
            lambda x: x["candidates"][0].update(git_blob_sha1="fake"),
            lambda x: x["candidates"][0].update(path="../../wrong.ngp"),
            lambda x: x.update(source_commit="f" * 40),
            lambda x: x.update(public_release_approved=True),
            lambda x: x.update(candidate_native_audio_verified=True),
        ):
            data = copy.deepcopy(self.index)
            mutate(data)
            with self.assertRaises(ValueError):
                validate_index(data)

    def test_download_exact_source_blob_and_reject_corruption(self):
        data = copy.deepcopy(self.index)
        entry = data["candidates"][0]
        payload = b"ORIGINAL MIT HOME BREW TEST CONTENTS" * 450
        entry["size_bytes"] = len(payload)
        entry["git_blob_sha1"] = gitblob(payload)
        with TemporaryDirectory() as root:
            name = Path(root) / "research.ngp"
            class Context(BytesIO):
                def __enter__(self):
                    return self
                def __exit__(self, *exc):
                    self.close()
            result = fetch_candidate(
                data, entry, name, opener=lambda *a, **k: Context(payload)
            )
            self.assertEqual(name.read_bytes(), payload)
            self.assertEqual(result["source_blob_sha1"], gitblob(payload))
            self.assertEqual(result["candidate_sha256"], hashlib.sha256(payload).hexdigest())
            entry["git_blob_sha1"] = "0" * 40
            with self.assertRaisesRegex(ValueError, "SHA-1 mismatch"):
                fetch_candidate(
                    data, entry, name, opener=lambda *a, **k: Context(payload)
                )

    def test_explicit_silence_cannot_count_as_audio_and_no_fake_full_pass(self):
        quiet = _check_native_child(report_for_child())
        self.assertFalse(quiet["audio_gate_passed"])
        self.assertFalse(quiet["passed"])
        with self.assertRaisesRegex(ValueError, "Impossible NGP PCM"):
            forged = report_for_child()
            forged["audio_gate_passed"] = True
            _check_native_child(forged)
        with self.assertRaisesRegex(ValueError, "Impossible native NGP complete"):
            forged = report_for_child()
            forged["passed"] = True
            _check_native_child(forged)
        self.assertIsNone(_check_native_child({"system": "ngp", "passed": True}))

    def test_all_fourteen_attempted_and_only_real_native_pcm_marks_candidate(self):
        invocations = []
        def fake_fetch(index, row, path):
            path.write_bytes(b"FIXTURE NOT REAL")
            return {"source_blob_sha1": row["git_blob_sha1"],
                    "size_bytes": row["size_bytes"],
                    "candidate_sha256": "f" * 64}
        def fake_run(argv, **kw):
            self.assertIn(str(PROBE), argv)
            self.assertEqual(argv[argv.index("--system") + 1], "ngp")
            rom = Path(argv[argv.index("--rom") + 1])
            self.assertEqual(rom.suffix, ".ngp")
            self.assertTrue(rom.exists())
            output = Path(argv[argv.index("--report") + 1])
            num = len(invocations)
            entry = report_for_child(has_audio=(num == 6), has_input=(num != 6))
            output.write_text(json.dumps(entry))
            invocations.append(argv)
            class Result:
                returncode = 0 if entry["passed"] else 1
                stdout = "actual native probe returned a report"
                stderr = ""
            return Result()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            core = root / "mednafen_ngp_libretro.so"
            core.write_bytes(b"INERT INDEPENDENT CORE FIXTURE")
            result = scan(self.index, core, root / "out", seconds=4,
                          fetcher=fake_fetch, runner=fake_run)
            self.assertEqual(len(invocations), 14)
            self.assertEqual(result["attempted_original_mono_cartridges"], 14)
            self.assertEqual(result["source_downloads_integrity_verified"], 14)
            self.assertTrue(result["all_source_candidate_downloads_verified"])
            self.assertEqual(len(result["native_audio_pass_candidates"]), 1)
            self.assertEqual(result["full_native_av_input_pass_candidates"], [])
            self.assertEqual(result["status"], STATUS)
            self.assertFalse(result["public_release_approved"])
            self.assertFalse(result["real_game_compatibility_verified"])
            self.assertEqual(
                len(list((root / "out").iterdir())), 2,
                "Never attach game ROMs, BIOS, or native binaries",
            )

    def test_workflow_only_probes_not_bundles_audio_or_publishes(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/v30-ngp-mono-mit-matrix.yml").read_text("utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("probe_v30_ngp_mono_candidates", workflow)
        self.assertIn("NGP_MONO_NATIVE_AUDIO_RESEARCH_UNAPPROVED.json", workflow)
        self.assertIn("NGP-MONO-ALL-14-RESEARCH-CANDIDATES-UNAPPROVED", workflow)
        self.assertNotIn("gh release create", workflow)
        self.assertNotIn("gh release upload", workflow)
        self.assertNotIn("continue-on-error: true", workflow)


if __name__ == "__main__":
    unittest.main()
