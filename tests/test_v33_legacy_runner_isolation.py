"""Ensure superseded 3.1/3.1.1 native QA does not schedule on v3.3 PRs.

These static tests retain the legacy workflows for their original branches
while reserving scarce hosted macOS runners for current 3.3 installer QA.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LEGACY = (
    "v311-private-source-stage.yml",
    "v31-linux-full-camera-only-final-qa.yml",
    "v31-final-identity-private-qa.yml",
    "v311-camera-failure-native-regression.yml",
    "v311-sustained-session-qa.yml",
    "v31-rc2-isolated-source-app.yml",
    "v31-macos-arm64-full-source-opencv-qa.yml",
    "v31-macos-intel-full-source-opencv-qa.yml",
    "v311-save-atomic-four-platform-qa.yml",
    "v31-windows-full-source-opencv-qa.yml",
)
OLD = "github.event.pull_request.head.ref != 'feature/v3.2-integration'"
V33 = "github.event.pull_request.head.ref != 'feature/v3.3-stream-render-latency'"


class LegacyRunnerIsolationTests(unittest.TestCase):
    def test_every_legacy_build_job_skips_the_33_draft_pr(self):
        for filename in LEGACY:
            with self.subTest(workflow=filename):
                contents = (ROOT / ".github" / "workflows" / filename).read_text(
                    encoding="utf-8"
                )
                guards = [
                    line for line in contents.splitlines()
                    if line.strip().startswith("if: ") and OLD in line
                ]
                self.assertTrue(guards)
                for guard in guards:
                    self.assertIn(V33, guard)
                    self.assertIn(OLD, guard)
                self.assertIn("pull_request:", contents)
                self.assertIn("contents: read", contents)

    def test_current_private_33_installer_gate_still_builds_four_targets(self):
        contents = (ROOT / ".github" / "workflows"
                    / "v33-private-candidate-installers.yml").read_text(
                        encoding="utf-8"
                    )
        for target in ("linux-x64", "windows-x64",
                       "macos-arm64", "macos-x64"):
            self.assertIn("target: " + target, contents)
        self.assertIn("test_v33_legacy_runner_isolation.py", contents)
        self.assertIn('AP_RELEASE_BUILD: "0"', contents)
        self.assertIn("persist-credentials: false", contents)
        self.assertIn("github.event.pull_request.head.sha", contents)


if __name__ == "__main__":
    unittest.main()
