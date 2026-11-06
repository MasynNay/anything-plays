"""Tests for build-time Python wheel notices and version inventory."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.collect_python_notices import collect_python_notices


class _Distribution:
    metadata = {"Name": "Example Package", "License-Expression": "MIT"}
    version = "1.2.3"
    files = [Path("example_package-1.2.3.dist-info/licenses/LICENSE.txt")]

    def __init__(self, root):
        self.root = Path(root)

    def locate_file(self, relative):
        return self.root / relative


class PythonNoticeTests(unittest.TestCase):
    def test_collects_full_notice_and_records_installed_version(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            distribution = _Distribution(root)
            license_file = distribution.locate_file(distribution.files[0])
            license_file.parent.mkdir(parents=True)
            license_file.write_text("Example License Text\n")
            destination = root / "output"
            result = collect_python_notices(destination, [distribution])
            self.assertEqual(len(result["distributions"]), 1)
            record = result["distributions"][0]
            self.assertEqual((record["name"], record["version"]),
                             ("Example Package", "1.2.3"))
            notice_path = destination / record["license_files"][0]["bundled_path"]
            self.assertEqual(notice_path.read_text(), "Example License Text\n")
            self.assertFalse(result["redistribution_approved"])
            self.assertEqual(json.loads((destination / "PYTHON_DISTRIBUTIONS.json")
                                        .read_text())["schema_version"], 1)

    def test_rejects_empty_notice_collection(self):
        with TemporaryDirectory() as directory:
            dist = _Distribution(directory)
            dist.files = []
            with self.assertRaisesRegex(ValueError, "No Python distribution"):
                collect_python_notices(Path(directory) / "output", [dist])


if __name__ == "__main__":
    unittest.main()
