"""3.3.1: native-core manifest discovery handles bad removable media safely.

All tests use tiny synthetic core files; no game ROMs, drivers or network.
"""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.emulator_updates import (
    MAX_MANIFEST_BYTES, check_emulator_updates, find_provenance,
)


class ProvenanceIsolationTests(unittest.TestCase):
    def setUp(self):
        work = TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.first = self.root / "first"
        self.second = self.root / "second"
        self.first.mkdir()
        self.second.mkdir()

    def _manifest(self, folder, document=None):
        path = folder / "CORE_PROVENANCE.json"
        path.write_text(json.dumps(
            {"cores": []} if document is None else document
        ), encoding="utf-8")
        return path

    def _expect_fallback(self):
        found, data = find_provenance([self.first, self.second])
        self.assertEqual(found, self.second / "CORE_PROVENANCE.json")
        self.assertEqual(data, {"cores": []})

    def test_regular_manifest_still_loads(self):
        self._manifest(self.first)
        found, data = find_provenance([self.first])
        self.assertEqual(found, self.first / "CORE_PROVENANCE.json")
        self.assertEqual(data, {"cores": []})

    def test_disappearing_drive_during_file_probe_is_skipped(self):
        self._manifest(self.first)
        self._manifest(self.second)
        original = Path.is_file
        vanished = self.first / "CORE_PROVENANCE.json"

        def failing_file_probe(path):
            if path == vanished:
                raise FileNotFoundError("simulated removed drive")
            return original(path)

        with patch.object(Path, "is_file", failing_file_probe):
            self._expect_fallback()

    def test_permission_error_during_open_falls_back(self):
        self._manifest(self.first)
        self._manifest(self.second)
        original = os.open
        denied = self.first / "CORE_PROVENANCE.json"

        def failing_open(path, *args, **kwargs):
            if Path(path) == denied:
                raise PermissionError("simulated denied media")
            return original(path, *args, **kwargs)

        with patch("anything_plays.emulator_updates.os.open", failing_open):
            self._expect_fallback()

    def test_giant_manifest_is_skipped(self):
        (self.first / "CORE_PROVENANCE.json").write_bytes(
            b" " * (MAX_MANIFEST_BYTES + 200)
        )
        self._manifest(self.second)
        self._expect_fallback()

    def test_linked_manifest_does_not_redirect_read(self):
        outside = self.root / "private"
        outside.mkdir()
        secret = self._manifest(outside, {"cores": [{"name": "not-a-core"}]})
        link = self.first / "CORE_PROVENANCE.json"
        try:
            link.symlink_to(secret)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not supported")
        self._manifest(self.second)
        self._expect_fallback()
        self.assertTrue(link.is_symlink())

    def test_invalid_encoding_and_excessive_json_depth_are_skipped(self):
        self._manifest(self.second)
        broken = self.first / "CORE_PROVENANCE.json"
        broken.write_bytes(bytes([255, 254]))
        self._expect_fallback()
        broken.write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
        self._expect_fallback()

    def test_unhashable_record_name_does_not_hide_a_healthy_core(self):
        core = self.first / "mgba_libretro.so"
        core.write_bytes(b"synthetic local fixture, not a native executable")
        self._manifest(self.first, {"cores": [
            {"name": ["mgba"]}, {"name": {"wrong": "type"}},
            {"name": "mgba", "file": core.name,
             "sha256": hashlib.sha256(core.read_bytes()).hexdigest(),
             "libretro_library_version": "test",
             "reported_source_revision": "a" * 40},
        ]})
        with patch("anything_plays.core_packs.managed_core_path",
                   return_value=None):
            report = check_emulator_updates([self.first], online=False)
        mgba = next(item for item in report["cores"] if item["key"] == "mgba")
        self.assertTrue(report["manifest_found"])
        self.assertEqual(mgba["integrity"], "verified")
        self.assertEqual(mgba["status"], "not-checked")


if __name__ == "__main__":
    unittest.main()
