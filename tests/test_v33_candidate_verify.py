"""Private candidate verifier never confuses a QA build with stable."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from anything_plays.build_identity import make_identity
from tools.v33_candidate_verify import TARGETS, verify_candidate

SHA = "a" * 40


class V33CandidateVerifyTests(unittest.TestCase):
    def _fixture(self, root, target):
        bundle = root / "Bundle.app" if target.startswith("macos") else root / "Bundle"
        marker = bundle / "assets" / "v31_build_identity.json"
        marker.parent.mkdir(parents=True)
        marker.write_text(json.dumps(make_identity("v33_candidate")))
        core_root = (
            bundle / "Contents" / "Resources" / "cores"
            if target.startswith("macos") else bundle / "cores"
        )
        core_root.mkdir(parents=True)
        suffix = (".dylib" if target.startswith("macos") else
                  ".dll" if target == "windows-x64" else ".so")
        (core_root / ("mgba_libretro" + suffix)).write_bytes(b"qa fake core")
        installer = root / TARGETS[target]
        installer.write_bytes(b"not a real installer" * 1000)
        return bundle, installer, core_root

    def test_each_target_retains_exact_identity_hash_and_review_limit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for target in TARGETS:
                with self.subTest(target=target):
                    subdir = root / target
                    subdir.mkdir()
                    bundle, installer, _ = self._fixture(subdir, target)
                    report = verify_candidate(
                        target=target, bundle=bundle, installer=installer,
                        source_sha=SHA,
                    )
                    self.assertEqual(report["source_sha"], SHA)
                    self.assertEqual(report["channel"], "v33_candidate")
                    self.assertEqual(
                        report["settings_namespace"],
                        "anything-plays-33-candidate",
                    )
                    self.assertEqual(report["bundled_core_count"], 1)
                    self.assertEqual(report["installer_filename"], TARGETS[target])
                    self.assertEqual(
                        report["installer_sha256"],
                        hashlib.sha256(installer.read_bytes()).hexdigest(),
                    )
                    for field in (
                        "public_release_approved", "hardware_input_tested",
                        "physical_camera_tested", "gamecube_bundled",
                        "full_18_console_gameplay_tested",
                        "installer_fully_tested_on_real_host",
                    ):
                        self.assertFalse(report[field])

    def test_rejects_any_old_preview_identity_or_second_core(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle, installer, cores = self._fixture(root, "linux-x64")
            marker = bundle / "assets" / "v31_build_identity.json"
            marker.write_text(json.dumps(make_identity("v32_preview")))
            with self.assertRaises(ValueError):
                verify_candidate(
                    target="linux-x64", bundle=bundle, installer=installer,
                    source_sha=SHA,
                )
            marker.write_text(json.dumps(make_identity("v33_candidate")))
            (cores / "dolphin_libretro.so").write_bytes(b"fake")
            with self.assertRaises(ValueError):
                verify_candidate(
                    target="linux-x64", bundle=bundle, installer=installer,
                    source_sha=SHA,
                )
            (cores / "dolphin_libretro.so").unlink()
            (cores / "dolphin-emu").mkdir()
            with self.assertRaises(ValueError):
                verify_candidate(
                    target="linux-x64", bundle=bundle, installer=installer,
                    source_sha=SHA,
                )

    def test_fails_closed_for_invalid_source_or_misnamed_installer(self):
        with TemporaryDirectory() as tmp:
            bundle, installer, _ = self._fixture(Path(tmp), "windows-x64")
            for sha in ("a" * 39, "INVALID", "a" * 41):
                with self.subTest(sha=sha), self.assertRaises(ValueError):
                    verify_candidate(
                        target="windows-x64", bundle=bundle,
                        installer=installer, source_sha=sha,
                    )
            with self.assertRaises(ValueError):
                verify_candidate(
                    target="macos-arm64", bundle=bundle,
                    installer=installer, source_sha=SHA,
                )


if __name__ == "__main__":
    unittest.main()
