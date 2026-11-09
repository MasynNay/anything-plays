"""PCE trial CI must replace exactly one core, never touch stable release inputs."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PCESourceBuiltOfflineWorkflowTests(unittest.TestCase):
    def test_four_full_test_only_installers_use_original_preserved_archives(self):
        flow = (ROOT/".github/workflows/v30-pce-offline-integration.yml").read_text("utf-8")
        self.assertIn("42437133733", flow)
        self.assertIn("42444367068", flow)
        self.assertIn("Anything Plays 3.0 | Complete offline installer lab", flow)
        self.assertIn("Anything Plays 3.0 | PCE pinned-source replacement research", flow)
        self.assertIn("AP_V30_TEST_CORES: '1'", flow)
        self.assertIn("AP_RELEASE_BUILD: '0'", flow)
        self.assertIn("AP_V30_APPROVED_RELEASE: '0'", flow)
        for target in ("windows-x64", "linux-x64", "macos-arm64", "macos-x64"):
            self.assertIn("target: " + target, flow)
        self.assertIn("python -m tools.stage_v30_pce_trial_inputs", flow)
        self.assertIn("python -m tools.v30_pce_candidate", flow)
        self.assertIn("core=root/(name+\"_libretro.\"+ext)", flow)
        self.assertIn('pce["sha256"] == candidate["native_sha256"]', flow)
        self.assertIn("mednafen_pce_fast", flow)
        self.assertIn("dolphin-emu/Sys/codehandler.bin", flow)
        self.assertIn("probe_pce_homebrew.py", flow)
        self.assertIn("native_nonzero_pcm_samples", flow)
        self.assertIn("if: always()", flow)
        self.assertIn("test-evidence/*", flow)
        self.assertNotIn("gh release create", flow)
        self.assertNotIn("gh release upload", flow)
        self.assertNotIn("release/*.exe", flow)
        self.assertNotIn("release/*.dmg", flow)
        self.assertNotIn("release/*.deb", flow)

    def test_downloader_and_approved_release_mode_remain_unchanged(self):
        packer = (ROOT/"fetch_mgba_core.py").read_text("utf-8")
        self.assertIn("verify_core_payload", packer)
        self.assertIn("AP_CORE_ARCHIVE_DIR", packer)
        self.assertIn("AP_V30_APPROVED_RELEASE", packer)
        self.assertNotIn("AP_V30_PINNED_PCE_ARTIFACT_DIR", packer)

    def test_candidate_paths_are_not_full_license_approval(self):
        file = (ROOT/"tools/v30_pce_candidate.py").read_text("utf-8")
        stage = (ROOT/"tools/stage_v30_pce_trial_inputs.py").read_text("utf-8")
        self.assertIn("approved_for_public_binary_distribution", file)
        self.assertIn('"mixed_license_combined_distribution_reviewed": False', file)
        self.assertIn('"public_release_approved": False', stage)
        self.assertIn('"mixed_license_review_complete": False', stage)
        self.assertIn("AP_RELEASE_BUILD", stage)
        self.assertIn("AP_V30_TEST_CORES", stage)
        self.assertIn("PRESERVED_NATIVE_INPUTS.json", stage)


if __name__ == "__main__":
    unittest.main()
