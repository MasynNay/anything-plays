"""Synthetic source-vs-archived Dolphin Sys byte comparison acceptance."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from tools import audit_v30_dolphin_original_sys as audit


def example(root, *, mutate=False, add_extra=False):
    root = Path(root)
    source = root / "original" / "Data" / "Sys"
    source.mkdir(parents=True)
    (source / "codehandler.bin").write_bytes(b"source-owned code handler bytes")
    (source / "GC").mkdir()
    (source / "GC" / "font-licenses.txt").write_bytes(b"sample copyright and license notices")
    (source / "GameSettings").mkdir()
    (source / "GameSettings" / "I.ini").write_bytes(b"example original game setting")
    archive = root / "Dolphin.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.write(source / "codehandler.bin", "dolphin-emu/Sys/codehandler.bin")
        z.write(source / "GC" / "font-licenses.txt",
                "dolphin-emu/Sys/GC/font-licenses.txt")
        z.writestr("dolphin-emu/Sys/GameSettings/I.ini",
                   b"altered" if mutate else b"example original game setting")
        if add_extra:
            z.writestr("dolphin-emu/Sys/not-in-source.ini", b"unknown original source")
    return root / "original", source, archive


class DolphinOriginalSysTests(unittest.TestCase):
    def test_exact_archived_sys_must_match_all_source_files(self):
        with TemporaryDirectory() as temp:
            checkout, source, zip_path = example(temp)
            output=Path(temp)/"report.json"
            result=audit.compare(checkout,zip_path,output,
                                 verify_git=lambda root: source)
            self.assertEqual(result["status"],
                             "UNAPPROVED-ORIGINAL-DOLPHIN-SYS-SOURCE-COMPARISON")
            self.assertEqual(result["pinned_source_file_count"],3)
            self.assertEqual(result["byte_identical_file_count"],3)
            self.assertTrue(result["archive_matches_pinned_upstream_source_byte_for_byte"])
            self.assertEqual(result,json.loads(output.read_text()))
            for item in ("public_binary_distribution_approved",
                         "third_party_source_and_license_rights_reviewed",
                         "original_source_native_binary_equivalence_proven"):
                self.assertFalse(result[item])
            with self.assertRaisesRegex(ValueError, "overwrite"):
                audit.compare(checkout,zip_path,output,
                              verify_git=lambda root: source)

    def test_changed_or_extra_archive_assets_are_recorded_as_not_source_matched(self):
        for mutate, add_extra in ((True,False),(False,True),(True,True)):
            with self.subTest(mutate=mutate,extra=add_extra), TemporaryDirectory() as temp:
                checkout,source,archive=example(temp,mutate=mutate,add_extra=add_extra)
                result=audit.compare(checkout,archive,Path(temp)/"result.json",
                                     verify_git=lambda root: source)
                self.assertFalse(result["archive_matches_pinned_upstream_source_byte_for_byte"])
                self.assertEqual(result["changed_source_files"],
                                 ["GameSettings/I.ini"] if mutate else [])
                self.assertEqual(result["extra_archive_files"],
                                 ["not-in-source.ini"] if add_extra else [])

    def test_missing_required_sys_codehandler_never_passes(self):
        with TemporaryDirectory() as temp:
            checkout,source,archive=example(temp)
            (source/"codehandler.bin").unlink()
            with self.assertRaisesRegex(ValueError, "codehandler"):
                audit.compare(checkout,archive,Path(temp)/"result.json",
                              verify_git=lambda root: source)

    def test_rejects_zip_traversal_and_duplicate_archive_member(self):
        with TemporaryDirectory() as temp:
            checkout,source,archive=example(temp)
            with zipfile.ZipFile(archive,"a") as z:
                z.writestr("dolphin-emu/Sys/../escape.txt", b"illegal")
            with self.assertRaises(ValueError):
                audit.compare(checkout,archive,Path(temp)/"result.json",
                              verify_git=lambda root: source)
        with TemporaryDirectory() as temp:
            checkout,source,archive=example(temp)
            with zipfile.ZipFile(archive,"a") as z:
                z.writestr("dolphin-emu/Sys/codehandler.bin", b"duplicate")
            with self.assertRaisesRegex(ValueError,"duplicate"):
                audit.compare(checkout,archive,Path(temp)/"result.json",
                              verify_git=lambda root: source)


if __name__ == "__main__":
    unittest.main()
