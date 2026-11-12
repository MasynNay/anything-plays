"""Public website must reflect the verified stable release without client polling."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            value = dict(attrs).get("href")
            if value:
                self.links.append(value)


class PublicThreeOhSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "site/index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "site/main.js").read_text(encoding="utf-8")
        cls.links = LinkParser()
        cls.links.feed(cls.html)

    def test_stable_3_release_is_visible_in_static_html(self):
        self.assertIn('id="public-stable-download-31"', self.html)
        self.assertIn('id="public-previous-stable-download"', self.html)
        self.assertIn('releases/tag/v3.1.0', self.html)
        self.assertIn('releases/tag/v3.0.0', self.html)
        self.assertIn("Download stable 3.1", self.html)
        self.assertIn("STABLE 3.1.0 AVAILABLE", self.html)
        self.assertIn("18 offline console profiles", self.html)
        self.assertIn("03 / RELEASED", self.html)
        self.assertNotIn("STABLE 2.0 AVAILABLE", self.html)
        self.assertNotIn("Public release is pending", self.html)
        self.assertNotIn("3.0 installers are not public", self.html)
        self.assertNotIn("REVIEW REQUIRED", self.html)

    def test_stable_3_1_and_previous_3_0_release_links_are_public_urls(self):
        expected = {
            "https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0",
            "https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0",
            "https://github.com/MasynNay/anything-plays/releases/download/v3.1.0/AnythingPlaysSetup-3.1.0.exe",
            "https://github.com/MasynNay/anything-plays/releases/download/v3.1.0/anything-plays-31_3.1.0_amd64.deb",
            "https://github.com/MasynNay/anything-plays/releases/download/v3.1.0/AnythingPlays-3.1.0-macos-arm64.dmg",
            "https://github.com/MasynNay/anything-plays/releases/download/v3.1.0/AnythingPlays-3.1.0-macos-x64.dmg",
        }
        self.assertTrue(expected.issubset(set(self.links.links)))
        # A public website must not point visitors at an owner-only draft
        # or misrepresent a release-candidate installer as stable.
        self.assertNotIn("untagged-", self.html)
        self.assertNotIn("v3.0.0-rc.1", self.html)

    def test_browser_concept_is_not_fake_playable_game(self):
        self.assertIn("INTERACTIVE CONCEPT", self.html)
        self.assertIn("This is an illustrative browser interaction", self.html)
        self.assertNotIn("fetch(", self.js)
        self.assertNotIn("localStorage", self.js)

    def test_static_javascript_parses(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node not installed")
        result = subprocess.run(
            [node, "--check", "site/main.js"], cwd=ROOT,
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
