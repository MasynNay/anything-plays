"""Adversarial preserved-native manifest checks for the production stager.

These fixtures are synthetic and grant no release or redistribution approval.
"""
import json
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.stage_v30_approved_source_inputs import _original_inputs
# The test directory is not a Python package; load the existing synthetic
# fixture module by file path without modifying application import paths.
_fixture_path = Path(__file__).with_name("test_v30_approved_source_inputs.py")
_spec = importlib.util.spec_from_file_location("v30_approved_fixture", _fixture_path)
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)
synthetic_target = _fixture.synthetic_target


class PreservedNativeManifestSchemaTests(unittest.TestCase):
    def test_malformed_manifest_rejected_without_touching_originals(self):
        mutations = {
            "null": lambda record: None,
            "array": lambda record: [],
            "string": lambda record: "untrusted",
            "unhashable_name": lambda record: {
                **record, "files": [{**record["files"][0], "name": ["not-a-path"]}]
                + record["files"][1:]},
            "missing_name": lambda record: {
                **record, "files": [{"sha256": "0" * 64}]
                + record["files"][1:]},
            "duplicate_name": lambda record: {
                **record, "files": [record["files"][1]]
                + record["files"][1:]},
            "boolean_count": lambda record: {
                **record, "original_archive_count": True},
        }
        for case, mutate in mutations.items():
            with self.subTest(case=case), TemporaryDirectory() as temp:
                root = Path(temp)
                synthetic_target(root, "linux-x86_64")
                folder = root / "original"
                manifest = folder / "PRESERVED_NATIVE_INPUTS.json"
                original = json.loads(manifest.read_text("utf-8"))
                snapshots = {p.name: p.read_bytes() for p in folder.iterdir()
                             if p.name != manifest.name}
                manifest.write_text(json.dumps(mutate(original)), "utf-8")
                with self.assertRaises(ValueError):
                    _original_inputs(folder, "linux-x64", ".so")
                self.assertEqual(snapshots, {
                    p.name: p.read_bytes() for p in folder.iterdir()
                    if p.name != manifest.name
                })

    def test_valid_synthetic_preserved_manifest_still_passes(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            synthetic_target(root, "linux-x86_64")
            actual = _original_inputs(root / "original", "linux-x64", ".so")
            self.assertEqual(len(actual), 12)
            self.assertIn("Dolphin.zip", actual)


if __name__ == "__main__":
    unittest.main()
