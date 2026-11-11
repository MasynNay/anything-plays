"""Public RC2 site navigation and illustrative Stream Mode art contracts."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "index.html"
STYLES = ROOT / "site" / "styles.css"
README = ROOT / "README.md"
TAG = "v3.1.0-rc2"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = {}
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if "id" in data:
            self.ids.add(data["id"])
        if tag == "a" and "id" in data:
            self.links[data["id"]] = data.get("href")


class StreamPortfolioTests(unittest.TestCase):
    def test_primary_rc2_download_and_stable_download_are_distinct(self):
        html = SITE.read_text("utf-8")
        links = Links()
        links.feed(html)
        self.assertEqual(
            links.links["public-rc-download"],
            "https://github.com/MasynNay/anything-plays/releases/tag/" + TAG,
        )
        self.assertEqual(
            links.links["public-stable-download"],
            "https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0",
        )
        self.assertNotIn("Download 3.1 RC1", html)
        self.assertIn("latest stable", README.read_text("utf-8"))
        self.assertIn("3.1 RC2", html)

    def test_stream_mode_is_unambiguously_an_illustration(self):
        html = SITE.read_text("utf-8")
        css = STYLES.read_text("utf-8")
        links = Links()
        links.feed(html)
        self.assertIn("stream", links.ids)
        self.assertIn("stream-heading", links.ids)
        self.assertIn("stream-illustration", html)
        self.assertIn("not a captured game or camera feed", html)
        self.assertIn("external emulator", html.lower())
        self.assertIn("Separate Stream Settings window", html)
        self.assertIn("16 themes", html)
        self.assertIn("DS-inspired", html)
        self.assertIn("@media(max-width:910px)", css)
        self.assertIn("@media(max-width:580px)", css)

    def test_release_notes_are_cautious_and_old_artifacts_not_faked(self):
        html = SITE.read_text("utf-8")
        readme = README.read_text("utf-8")
        self.assertIn("complete native LGPL corresponding-source/relinking review", html)
        self.assertIn("3.0.0 remains the latest stable release", readme)
        self.assertIn("RC2 is a prerelease", readme)
        self.assertIn("3.1 RC2", readme)
        self.assertIn("docs/screenshots/3.0", readme)
        self.assertIn("LINUX · 3.0 DEVELOPMENT CAPTURE", html)


if __name__ == "__main__":
    unittest.main()
