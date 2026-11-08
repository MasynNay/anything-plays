"""Pinned third-party license texts must remain in 3.0 installer inputs."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PINNED_LICENSES = (
    "ProSystem-GPL-2.0.txt",
    "Beetle-NeoPop-GPL-2.0.txt",
    "Beetle-WonderSwan-GPL-2.0.txt",
    "Stella2014-GPL-2.0.txt",
    "Beetle-PCE-Fast-GPL-2.0.txt",
)


class V30PinnedLicensesTests(unittest.TestCase):
    def test_new_gplv2_notices_are_complete(self):
        notices = (ROOT / "docs/THIRD_PARTY_NOTICES.md").read_text("utf-8")
        for name in PINNED_LICENSES:
            with self.subTest(name=name):
                path = ROOT / "licenses" / name
                self.assertTrue(path.is_file())
                value = path.read_text(encoding="utf-8")
                self.assertGreater(len(value), 14000)
                self.assertIn("GNU GENERAL PUBLIC LICENSE", value)
                self.assertIn("Version 2, June 1991", value)
                self.assertIn(name, notices)

    def test_full_bundle_rebuilds_when_notices_change(self):
        workflow = (ROOT / ".github/workflows/v30-full-bundle.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("'licenses/**'", workflow)
        self.assertIn("'docs/THIRD_PARTY_NOTICES.md'", workflow)


if __name__ == "__main__":
    unittest.main()
