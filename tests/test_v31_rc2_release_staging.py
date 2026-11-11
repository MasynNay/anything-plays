"""Strict checks for four original installed Stream Mode QA release assets."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.stage_v31_rc2_prerelease import TARGETS, sha, stage, STATUS, GUI_STATUS

SOURCE = "a" * 40


class RC2StagingTests(unittest.TestCase):
    def fixture(self, root):
        full, installed = root / "full", root / "installed"
        full.mkdir()
        installed.mkdir()
        for target, (name, report) in TARGETS.items():
            p = full / target
            q = installed / target
            p.mkdir()
            q.mkdir()
            binary = p / name
            binary.write_bytes(b"original frozen RC2" * 70000)
            digest = sha(binary)
            (p / report).write_text(json.dumps({
                "status": STATUS, "target": target, "installer": name,
                "sha256": digest, "source_preview_revision": SOURCE,
                "identity_channel": "rc2", "settings_namespace": "anything-plays-31-rc2",
                "native_core_count": 11, "console_profiles": 18,
                "public_release_approved": False, "final_release_approved": False,
            }))
            (q / "RC2_INSTALLED_RECEIPT.json").write_text(json.dumps({
                "status": GUI_STATUS, "target": target, "installer": name,
                "installer_sha256": digest, "source_revision": SOURCE,
                "actual_tk_window_started": True, "actual_app_initialized": True,
                "actual_tk_mainloop_ran": True,
                "stream_output_window_opened": True,
                "stream_appearance_configured": True,
                "stream_closed_cleanly": True, "console_profiles": 18,
                "native_core_count": 11, "public_release_approved": False,
                "relinking_reviewed": False,
            }))
        return full, installed

    def test_exact_four_host_technical_evidence_stages_unmodified_installers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            full, installed = self.fixture(root)
            result = stage(full, installed, root / "out", SOURCE, 123456789)
            self.assertEqual(set(result), set(TARGETS))
            self.assertEqual(len(list((root / "out").iterdir())), 7)
            self.assertIn("3.1.0.rc2full_amd64.deb", result["linux-x64"]["filename"])
            self.assertTrue(all((root / "out" / r["filename"]).is_file()
                                for r in result.values()))
            self.assertTrue(all(sha(root / "out" / r["filename"]) == r["sha256"]
                                for r in result.values()))
            manifest = json.loads((root / "out/RC2_QA_MANIFEST.json").read_text())
            self.assertFalse(manifest["public_release_approved"])
            self.assertFalse(manifest["stable_3_1_approved"])
            self.assertFalse(manifest["relinking_reviewed"])
            for line in (root / "out/SHA256SUMS.txt").read_text().splitlines():
                digest, filename = line.split("  ", 1)
                self.assertEqual(sha(root / "out" / filename), digest)
            with self.assertRaises(ValueError):
                stage(full, installed, root / "out", SOURCE, 123456789)

    def test_tampered_binary_receipt_or_missing_os_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            full, installed = self.fixture(root)
            target = "macos-arm64"
            name, _ = TARGETS[target]
            binary = full / target / name
            binary.write_bytes(binary.read_bytes() + b"corrupted!")
            with self.assertRaisesRegex(ValueError, "sha256"):
                stage(full, installed, root / "blocked", SOURCE, 123)
            self.assertFalse((root / "blocked").exists())
            binary.unlink()
            with self.assertRaises(ValueError):
                stage(full, installed, root / "blocked", SOURCE, 123)
            self.assertFalse((root / "blocked").exists())

    def test_cannot_accept_fake_stream_or_public_distribution_claim(self):
        for target, (name, filename) in TARGETS.items():
            for field, altered in (
                ("stream_output_window_opened", False),
                ("stream_closed_cleanly", False),
                ("public_release_approved", True),
                ("source_revision", "b" * 40),
            ):
                with self.subTest(target=target, field=field):
                    with tempfile.TemporaryDirectory() as temp:
                        root = Path(temp)
                        full, installed = self.fixture(root)
                        receipt = installed / target / "RC2_INSTALLED_RECEIPT.json"
                        data = json.loads(receipt.read_text())
                        data[field] = altered
                        receipt.write_text(json.dumps(data))
                        with self.assertRaises(ValueError):
                            stage(full, installed, root / "untrusted", SOURCE, 123)
                        self.assertFalse((root / "untrusted").exists())

    def test_reject_source_mismatch_and_unsafe_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            full, installed = self.fixture(root)
            with self.assertRaises(ValueError):
                stage(full, installed, root / "out", "not-a-sha", 123)
            with self.assertRaises(ValueError):
                stage(full, installed, root / "out", SOURCE, 0)
            link = root / "linked"
            try:
                link.symlink_to(full, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("No filesystem symlink support")
            with self.assertRaises(ValueError):
                stage(link, installed, root / "out", SOURCE, 123)


if __name__ == "__main__":
    unittest.main()
