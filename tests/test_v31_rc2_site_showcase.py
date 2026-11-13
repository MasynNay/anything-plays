"""Public stable 3.1 site navigation and honest historical Stream Mode art contracts."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "index.html"
STYLES = ROOT / "site" / "styles.css"
README = ROOT / "README.md"
TAG = "v3.1.1"


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
    def test_primary_stable_31_and_previous_30_are_distinct(self):
        html = SITE.read_text("utf-8")
        links = Links()
        links.feed(html)
        self.assertEqual(
            links.links["public-stable-download-31"],
            "https://github.com/MasynNay/anything-plays/releases/tag/" + TAG,
        )
        self.assertEqual(
            links.links["public-previous-stable-download"],
            "https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0",
        )
        self.assertNotIn("Download 3.1 RC1", html)
        self.assertIn("latest stable", README.read_text("utf-8"))
        self.assertIn("STABLE 3.1.1 AVAILABLE", html)

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
        self.assertIn("Separately licensed sources and notices accompany the release", html)
        self.assertIn("Anything Plays 3.1.1 — public stable maintenance release", readme)
        self.assertIn("3.1 RC2", readme)
        self.assertIn("3.1 RC2", readme)
        self.assertIn("docs/screenshots/3.0", readme)
        self.assertIn("LINUX · 3.0 DEVELOPMENT CAPTURE", html)


if __name__ == "__main__":
    unittest.main()
