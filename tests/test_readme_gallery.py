"""Keep the Anything Plays README screenshot showcase backed by authentic images."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = ROOT / "docs" / "screenshots" / "3.0"

FILES = (
    "gamecube-wind-waker.webp",
    "n64-ocarina.webp",
    "gbc-pokemon-crystal.webp",
    "gba-warm-cream.webp",
    "camera-object-settings.webp",
    "advanced-settings.webp",
    "safety-and-profiles.webp",
)


class ReadmeScreenshotTests(unittest.TestCase):
    def test_all_seven_readme_images_exist_and_are_webp(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Screenshots", readme)
        for name in FILES:
            with self.subTest(name=name):
                image = SCREENSHOTS / name
                data = image.read_bytes()
                self.assertGreater(len(data), 10000)
                self.assertEqual(data[:4], b"RIFF")
                self.assertEqual(data[8:12], b"WEBP")
                self.assertIn(f"docs/screenshots/3.0/{name}", readme)

    def test_camera_privacy_note_is_visible(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("macOS menu bar and Dock have been cropped out", readme)
        self.assertIn("rather than private camera footage", readme)


if __name__ == "__main__":
    unittest.main()
