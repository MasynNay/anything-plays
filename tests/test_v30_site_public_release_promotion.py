"""3.0 marketing must never present an unpublished draft as a public release."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PortfolioPublicReleasePromotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "site/index.html").read_text("utf-8")
        cls.js = (ROOT / "site/main.js").read_text("utf-8")

    def test_fallback_download_remains_stable_2_until_real_release_exists(self):
        self.assertIn('id="public-stable-download"', self.html)
        self.assertIn('releases/tag/v2.0.0', self.html)
        self.assertIn('STABLE 2.0 AVAILABLE', self.html)
        self.assertIn("releases/tags/v3.0.0", self.js)
        self.assertIn("published.draft !== false", self.js)
        self.assertIn("published.prerelease !== false", self.js)
        self.assertIn("published.tag_name !== 'v3.0.0'", self.js)
        self.assertIn("required.every(name => available.has(name))", self.js)

    def test_platform_downloads_and_release_provenance_required(self):
        for name in (
            "AnythingPlaysSetup-3.0.0.exe",
            "anything-plays_3.0.0_amd64.deb",
            "AnythingPlays-3.0.0-macos-arm64.dmg",
            "AnythingPlays-3.0.0-macos-x64.dmg",
            "SHA256SUMS.txt",
        ):
            with self.subTest(name=name):
                self.assertIn(name, self.js)
        for marker in (
            'id="download-summary"',
            'id="consoles-summary"',
            'id="roadmap-summary"',
            'id="stable-profiles-count"',
            'id="download-release-status"',
        ):
            self.assertIn(marker, self.html)
        self.assertIn("catch (_)", self.js)
        self.assertNotIn("localStorage", self.js)

    def test_static_javascript_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node interpreter unavailable")
        result = subprocess.run(
            [node, "--check", "site/main.js"],
            cwd=ROOT, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
