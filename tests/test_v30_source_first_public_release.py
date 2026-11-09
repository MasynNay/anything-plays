"""The source-first publisher must never silently turn a preview into stable 3.0."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/v30-publish-source-first-public-3-0.yml"
DECISION = ROOT / "docs/V3_0_SOURCE_FIRST_RELEASE_DECISION.md"


class SourceFirstPublicReleaseTests(unittest.TestCase):
    def test_public_release_requires_four_true_versioned_core_verified_installer_artifacts(self):
        s = WORKFLOW.read_text("utf-8")
        for filename in (
            "AnythingPlaysSetup-3.0.0.exe",
            "anything-plays_3.0.0_amd64.deb",
            "AnythingPlays-3.0.0-macos-arm64.dmg",
            "AnythingPlays-3.0.0-macos-x64.dmg",
        ):
            with self.subTest(filename=filename):
                self.assertIn(filename, s)
        self.assertIn("STABLE_IDENTITY_CANDIDATE_SHA256_UNAPPROVED.json", s)
        self.assertIn("44 native", s)
        self.assertIn("original_source_count", s)
        self.assertIn("original_dolphin_gitlink_trees", s)
        self.assertIn('h.hexdigest()==receipt["sha256"]', s)
        self.assertIn("gh run view", s)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", s)

    def test_original_source_is_released_before_any_public_binary(self):
        s = WORKFLOW.read_text("utf-8")
        self.assertIn("python -m tools.audit_v30_current_tia_sources", s)
        self.assertIn("python -m tools.prepare_v30_source_companion", s)
        self.assertIn("--target \"$BUILD_SHA\"", s)
        source_step = s.index("      - name: Make the full original corresponding source companion PUBLIC first")
        binary_step = s.index("      - name: Publish the exact FOUR source-built true 3.0.0 installers")
        self.assertLess(source_step, binary_step)
        self.assertIn('gh release create "$SOURCE_TAG"', s[source_step:binary_step])
        self.assertIn('gh release create "$MAIN_TAG"', s[binary_step:])
        self.assertIn("SHA256SUMS.txt", s)
        self.assertIn("public_binary_distribution_approved", s)
        self.assertNotIn("gh release edit v2.0.0", s)

    def test_maintainer_decision_discloses_real_rights_and_hardware_limits(self):
        note = DECISION.read_text("utf-8")
        for phrase in (
            "eleven original-source Libretro", "GPL-2.0-or-later",
            "ENABLE_QT=OFF", "HAVE_PARALLEL_RSP=0", "44 native",
            "Known", "not legal advice", "2.0.0",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), note.lower())
        self.assertIn("source-first", note.lower())


if __name__ == "__main__":
    unittest.main()
