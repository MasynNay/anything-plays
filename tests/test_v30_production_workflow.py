"""Approved production CI must match public publisher's strict artifact inputs."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProductionWorkflowTests(unittest.TestCase):
    def test_four_target_manual_production_cannot_auto_publish(self):
        script = (ROOT / ".github/workflows/v30-production-candidates.yml").read_text("utf-8")
        self.assertIn("name: Anything Plays 3.0 | Approved production candidates", script)
        self.assertIn("workflow_dispatch:", script)
        self.assertNotIn("\n  push:", script)
        self.assertNotIn("gh release create", script)
        self.assertNotIn("gh release upload", script)
        self.assertIn("refs/heads/main", script)
        self.assertIn("APPROVED-3.0-DISTRIBUTION", script)
        self.assertIn("environment: stable-v3-production-build", script)
        for runner in ("windows-2025", "macos-15", "macos-15-intel", "ubuntu-24.04"):
            self.assertIn("runner: " + runner, script)
        for target in ("windows-x64", "macos-arm64", "macos-x64", "linux-x64"):
            self.assertIn("target: " + target, script)
        self.assertIn("AP_RELEASE_BUILD: '1'", script)
        self.assertIn("AP_V30_APPROVED_RELEASE: '1'", script)
        self.assertIn("python tools/check_v30_release.py", script)
        self.assertIn("load_approved_lock()", script)
        self.assertIn("python -m tools.emit_v30_production_provenance", script)
        self.assertIn("PRODUCTION_PROVENANCE.json", script)
        self.assertIn("AnythingPlays-3.0.0-PRODUCTION-", script)
        self.assertIn("NATIVE-INPUTS-UNAPPROVED", script)
        self.assertIn("public_distribution_approved", script)

    def test_production_artifact_names_exactly_match_manual_publication(self):
        producer = (ROOT / ".github/workflows/v30-production-candidates.yml").read_text("utf-8")
        publisher = (ROOT / ".github/workflows/v30-publish-approved.yml").read_text("utf-8")
        names = (
            "AnythingPlaysSetup-3.0.0.exe",
            "AnythingPlays-3.0.0-macos-arm64.dmg",
            "AnythingPlays-3.0.0-macos-x64.dmg",
            "anything-plays_3.0.0_amd64.deb",
        )
        for name in names:
            self.assertIn("installer: " + name, producer)
        self.assertIn("AnythingPlays-$VERSION-PRODUCTION-$target", publisher)
        self.assertIn("candidate-platforms/$target", publisher)
        self.assertIn("--draft", publisher)
        self.assertIn("inputs.publish_publicly", publisher)
        self.assertIn("PRODUCTION_PROVENANCE.json", (ROOT/"tools/emit_v30_production_provenance.py").read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
