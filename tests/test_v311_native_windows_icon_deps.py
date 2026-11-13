"""Windows full 3.1.1 Inno setup needs original NumPy + Pillow icon runtime.

A source-shell PyInstaller venv has NumPy already, but the full assembler's
icon renderer executes in the runner's *global* Python, before Inno packing.
"""
from pathlib import Path
import unittest

BASE=Path(__file__).resolve().parents[1]


class WindowsOriginalIconDependencies(unittest.TestCase):
    def test_both_real_full_windows_build_jobs_install_global_icon_dependencies(self):
        for workflow in (".github/workflows/v311-stable-upgrade-source-stage.yml",
                         ".github/workflows/v311-private-source-stage.yml"):
            with self.subTest(workflow=workflow):
                text=(BASE/workflow).read_text("utf-8")
                # Require both dependencies, the exact importer preflight and
                # its native full assembler after the dependency installation.
                self.assertIn("python -m pip install 'Pillow>=10,<13' 'numpy>=2,<3'",text)
                self.assertIn("anything_plays.icon_cleanup import clean_icon_background",text)
                self.assertIn("python -m tools.assemble_v311_full_windows",text)
                setup=text.index("python -m pip install 'Pillow>=10,<13' 'numpy>=2,<3'")
                build=text.index("python -m tools.assemble_v311_full_windows")
                self.assertLess(setup,build)


if __name__=="__main__":
    unittest.main()
