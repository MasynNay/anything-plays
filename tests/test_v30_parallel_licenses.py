"""Guard ParaLLEl-N64 component notice completeness in the 3.0 installers."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ("ParaLLEl-N64-GPL-3.0.txt", "GNU GENERAL PUBLIC LICENSE"),
    ("ParaLLEl-N64-Mupen64Plus-Core-LICENSES.txt", "Mupen64Plus"),
    ("ParaLLEl-N64-RSP-LICENSE.txt", "dual licensed"),
    ("ParaLLEl-N64-RSP-LGPL-3.0.txt", "GNU LESSER GENERAL PUBLIC LICENSE"),
    ("ParaLLEl-N64-RSP-MIT.txt", "Permission is hereby granted"),
)


class V30ParallelNoticesTests(unittest.TestCase):
    def test_upstream_component_texts_and_notices_are_present(self):
        notices = (ROOT / "docs/THIRD_PARTY_NOTICES.md").read_text("utf-8")
        self.assertIn("e0ef5d673257e2e83bf9b7cffe62eda141af8493", notices)
        for file, phrase in FILES:
            with self.subTest(file=file):
                source = ROOT / "licenses" / file
                self.assertTrue(source.is_file(), str(source))
                text = source.read_text(encoding="utf-8")
                self.assertIn(phrase.lower(), text.lower())
                self.assertIn(file, notices)

    def test_packagers_copy_all_license_texts_and_rebuild_on_change(self):
        workflow = (ROOT / ".github/workflows/v30-full-bundle.yml").read_text("utf-8")
        self.assertIn("'licenses/**'", workflow)
        for path in (
            "packaging/build_windows.bat",
            "packaging/build_macos_dmg.sh",
            "packaging/build_linux_deb.sh",
        ):
            script = (ROOT / path).read_text("utf-8")
            self.assertIn("licenses", script)
            self.assertIn("*.txt", script)


if __name__ == "__main__":
    unittest.main()
