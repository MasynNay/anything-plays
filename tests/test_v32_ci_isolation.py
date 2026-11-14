"""3.2 CI should own its own builds, not rerun historic 3.1 native installers.

These are source-contract checks only. They do not claim GitHub-hosted
runners have executed or that an artifact passed platform verification.
"""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / ".github/workflows"

SUPERSEDED = (
    "v31-rc2-isolated-source-app.yml",
    "v31-four-platform-controller-ui.yml",
    "v31-linux-full-camera-only-final-qa.yml",
    "v31-macos-arm64-full-source-opencv-qa.yml",
    "v31-macos-intel-full-source-opencv-qa.yml",
    "v31-windows-full-source-opencv-qa.yml",
    "v311-sustained-session-qa.yml",
    "v311-camera-failure-native-regression.yml",
    "v31-final-identity-private-qa.yml",
    "v311-private-source-stage.yml",
)


class V32CIIsolationTests(unittest.TestCase):
    def test_historic_native_jobs_skip_v32_integration_pr(self):
        for filename in SUPERSEDED:
            with self.subTest(workflow=filename):
                source = (ROOT / filename).read_text("utf-8")
                self.assertIn(
                    "github.event.pull_request.head.ref != "
                    "'feature/v3.2-integration'",
                    source,
                )
                # Every legacy job's guard must contain this condition.
                jobs = source.split("\njobs:\n", 1)[1]
                import re
                sections = re.split(r"(?m)^  [A-Za-z0-9_-]+:\s*$", jobs)[1:]
                self.assertGreater(len(sections), 0)
                for section in sections:
                    if_line = next(
                        (line for line in section.splitlines()
                         if line.startswith("    if:")),
                        None,
                    )
                    self.assertIsNotNone(if_line)
                    self.assertIn("feature/v3.2-integration", if_line)

    def test_linux_preview_requires_frozen_extracted_debian_gui_start(self):
        preview = (
            ROOT / "v32-private-preview-installers.yml"
        ).read_text("utf-8")
        for expected in (
            "Linux installed Debian application startup smoke (isolated)",
            "dpkg-deb -x",
            "anything-plays-32-preview/AnythingPlays",
            "xvfb-run -a",
            "--ap-v30-ui-smoke",
            "actual_tk_mainloop_ran",
            'data["frozen_binary"] is True',
            'data["public_distribution_approved"] is False',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, preview)

    def test_current_source_and_private_installer_checks_remain_enabled(self):
        source = (ROOT / "ci.yml").read_text("utf-8")
        self.assertIn("python -m unittest discover -s tests -v", source)
        self.assertIn("tests/smoke_v32_gui.py", source)
        preview = (
            ROOT / "v32-private-preview-installers.yml"
        ).read_text("utf-8")
        self.assertIn("feature/v3.2-integration", preview)
        self.assertIn("tools/verify_v32_preview.py", preview)
        self.assertIn("actions/upload-artifact@v4", preview)
        self.assertNotIn("gh release create", preview)
        self.assertNotIn("gh release upload", preview)
        self.assertNotIn("create-release", preview)


if __name__ == "__main__":
    unittest.main()
