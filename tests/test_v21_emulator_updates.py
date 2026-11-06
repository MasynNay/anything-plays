"""2.1 emulator updater tests without external requests or native game files."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
import unittest

from anything_plays.emulator_updates import (
    check_emulator_updates, find_provenance, github_head, summary_text,
)


SHA = "b" * 40


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, maximum):
        return self.content[:maximum]


def fake_opener(request, timeout):
    assert request.full_url.startswith("https://api.github.com/repos/")
    assert timeout <= 5
    return FakeResponse(json.dumps([{"sha": SHA}]).encode("utf-8"))


class EmulatorUpdaterTests(unittest.TestCase):
    def _bundle(self, folder, *, version="bbbbbbbb", checksum_override=None):
        path = Path(folder)
        core = path / "mgba_libretro.so"
        core.write_bytes(b"test core binary, not executable")
        digest = hashlib.sha256(core.read_bytes()).hexdigest()
        record = {
            "name": "mgba",
            "file": core.name,
            "sha256": digest if checksum_override is None else checksum_override,
            "libretro_library_version": "0.10.5",
            "reported_source_revision": version,
        }
        (path / "CORE_PROVENANCE.json").write_text(
            json.dumps({"cores": [record]}), encoding="utf-8"
        )
        return core

    def test_matches_packaged_core_revision_and_does_not_modify_it(self):
        with TemporaryDirectory() as tmp:
            core = self._bundle(tmp)
            before = core.read_bytes()
            report = check_emulator_updates([tmp], opener=fake_opener)
            mgba = next(item for item in report["cores"] if item["key"] == "mgba")
            self.assertEqual(mgba["status"], "current-source")
            self.assertEqual(mgba["integrity"], "verified")
            self.assertEqual(core.read_bytes(), before)
            self.assertFalse(report["updates_install_automatically"])
            self.assertIn("signed", report["update_policy"])

    def test_source_mismatch_never_claims_binary_update_installed(self):
        with TemporaryDirectory() as tmp:
            self._bundle(tmp, version="aaaaaaaa")
            report = check_emulator_updates([tmp], opener=fake_opener)
            mgba = next(item for item in report["cores"] if item["key"] == "mgba")
            self.assertEqual(mgba["status"], "review-upstream")
            self.assertIn("requires tested app rebuild", summary_text(report))

    def test_tampered_bundle_is_reported_not_overwritten(self):
        with TemporaryDirectory() as tmp:
            core = self._bundle(tmp, checksum_override="a" * 64)
            report = check_emulator_updates([tmp], opener=fake_opener)
            mgba = next(item for item in report["cores"] if item["key"] == "mgba")
            self.assertEqual(mgba["status"], "modified")
            self.assertEqual(core.read_bytes(), b"test core binary, not executable")

    def test_no_manifest_is_not_mistaken_for_six_bundled_cores(self):
        with TemporaryDirectory() as tmp:
            self.assertEqual(find_provenance([tmp]), (None, None))
            report = check_emulator_updates([tmp], online=False)
            self.assertFalse(report["manifest_found"])
            self.assertTrue(all(
                item["status"] == "not-bundled" for item in report["cores"]
            ))

    def test_reject_untrusted_source_and_invalid_upstream_response(self):
        with self.assertRaises(ValueError):
            github_head("untrusted-repo/secret")
        with self.assertRaises(ValueError):
            github_head(
                "libretro/mgba",
                opener=lambda *_args, **_kwargs: FakeResponse(
                    b'[{"sha":"not-a-revision"}]'
                ),
            )


if __name__ == "__main__":
    unittest.main()
