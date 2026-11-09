"""Synthetic 4OS Tia production identity + source-first release, never real approvals."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from test_v30_eleven_approved_production import synthetic_eleven
from test_v30_approved_alternative_contract import sha
from tools.v30_release_lock import (
    ALTERNATIVE_TIA_CORE_ORDER, ALTERNATIVE_TIA_CORE_NAMES,
    SOURCE_BUILT_ELEVEN_TIA, TARGETS, load_approved_lock,
    selected_source_families,
)
from anything_plays.v30_approved_core_map import (
    MARKER, ELEVEN_TIA_EXPECTED, ELEVEN_TIA_REPOSITORIES, validate_installed_map,
)
from tools.stage_v30_approved_native_mapping import approved_core_map_from_lock


def synthetic_tia():
    lock, _ = synthetic_eleven()
    lock.update(
        core_set_id="gpl-source-built-eleven-tia",
        gpl2plus_atari_source_replacement_reviewed=True,
        original_gpl2_only_stella_excluded=True,
    )
    for target, row in lock["targets"].items():
        stella = row["cores"].pop("stella2014")
        ext = {"windows-x86_64":".dll", "linux-x86_64":".so",
               "macos-arm64":".dylib", "macos-x86_64":".dylib"}[target]
        stella.update(
            file=f"tia_libretro{ext}",
            source_commit_sha=ELEVEN_TIA_EXPECTED["tia"],
            upstream_source_repository=ELEVEN_TIA_REPOSITORIES["tia"],
            original_license_notice_sha256=sha("TIA-ORIGINAL-GPL2PLUS-TEST-NOT-ACTUAL-NOTICE"),
        )
        row["cores"]["tia"] = stella
    return lock


class GPL2PlusAtariReleaseGates(unittest.TestCase):
    def test_all_four_reviewed_synthetic_lineups_preserve_eleven_and_routing(self):
        lock = synthetic_tia()
        self.assertEqual(selected_source_families(lock), SOURCE_BUILT_ELEVEN_TIA)
        self.assertEqual(set(ALTERNATIVE_TIA_CORE_ORDER), ALTERNATIVE_TIA_CORE_NAMES)
        self.assertEqual(len(ELEVEN_TIA_EXPECTED), 11)
        self.assertNotIn("stella2014", ELEVEN_TIA_EXPECTED)
        with TemporaryDirectory() as temp:
            path=Path(temp)/"SYNTHETIC-NOT-REAL-PUBLIC-RIGHTS.json"
            path.write_text(json.dumps(lock), encoding="utf-8")
            loaded=load_approved_lock(path)
            self.assertEqual(set(loaded["targets"]), TARGETS)
        for target in TARGETS:
            with self.subTest(target=target):
                data=approved_core_map_from_lock(lock, target)
                self.assertEqual(data["core_set_id"], "gpl-source-built-eleven-tia")
                self.assertEqual(set(data["cores"]), ALTERNATIVE_TIA_CORE_NAMES)
                self.assertEqual(len(data["cores"]), 11)
                self.assertTrue(data["gpl2plus_atari_source_replacement_reviewed"])
                self.assertTrue(data["original_gpl2_only_stella_excluded"])
                self.assertEqual(data["cores"]["tia"]["source_commit"], ELEVEN_TIA_EXPECTED["tia"])
                with TemporaryDirectory() as temp:
                    folder=Path(temp)
                    (folder/MARKER).write_text(json.dumps(data), encoding="utf-8")
                    if target.startswith("windows"):
                        (folder/"libwinpthread-1.dll").write_bytes(
                            ("SYNTHETIC-NOT-REAL-WINDOWS-DLL"*500).encode("utf-8"))
                    extension = ".dll" if target.startswith("windows") else ".so" if target.startswith("linux") else ".dylib"
                    validated=validate_installed_map(folder, extension, verify_native=False)
                    self.assertNotIn("stella2014", validated["cores"])
                    (folder/f"stella2014_libretro{extension}").write_bytes(b"GPL2ONLY")
                    with self.assertRaisesRegex(ValueError, "noncommercial|stella|Original"):
                        validate_installed_map(folder, extension, verify_native=False)

    def test_tia_requires_original_exclusion_and_pinned_upstream_source(self):
        lock=synthetic_tia()
        for field in ("gpl2plus_atari_source_replacement_reviewed",
                      "original_gpl2_only_stella_excluded"):
            with self.subTest(field=field):
                bad={**lock,field:False}
                with self.assertRaisesRegex(ValueError,"Atari"):
                    approved_core_map_from_lock(bad,"linux-x86_64")
        lock["targets"]["linux-x86_64"]["cores"]["tia"]["upstream_source_repository"] = "https://evil.example/tia"
        with self.assertRaisesRegex(ValueError,"source-reviewed"):
            approved_core_map_from_lock(lock,"linux-x86_64")

    def test_publisher_binds_source_artifact_to_fully_approved_native_lock(self):
        root=Path(__file__).resolve().parents[1]
        s=(root/".github/workflows/v30-publish-approved.yml").read_text(encoding="utf-8")
        self.assertIn("load_approved_lock()", s)
        self.assertIn("ALTERNATIVE_TIA_CORE_NAMES",s)
        self.assertIn("gpl-source-built-eleven-tia",s)
        self.assertIn("AnythingPlays-3.0.0-ELEVEN-TIA-ORIGINAL-CORE-SOURCES-UNAPPROVED",s)
        self.assertIn("original-eleven-gpl2plus-tia",s)
        self.assertIn("manifest.get(\"source_set_id\") != expected_id",s)
        self.assertIn("--draft",s)
        self.assertIn("gh release edit",s)
        self.assertNotIn("\n  push:",s)

    def test_checked_in_lock_is_still_unapproved(self):
        with self.assertRaisesRegex(ValueError, "redistribution blocked"):
            load_approved_lock()


if __name__ == "__main__":
    unittest.main()
