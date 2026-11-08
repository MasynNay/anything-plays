"""Research GPLv3 candidate verification WITHOUT pretending binaries can ship."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from tools.stage_v30_gpl_alternative_candidates import (
    BASE, CANDIDATES, checked_candidate_zip, stage_candidate,
)


def zip_native(name, *, magic=b"\x7fELF", add_extra=False):
    original = magic + b"".join(hashlib.sha256(str(i).encode()).digest()
                                for i in range(1000))
    file = io.BytesIO()
    with zipfile.ZipFile(file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(CANDIDATES[name]["native_name"], original)
        if add_extra:
            archive.writestr("../unexpected", "unsafe")
    return file.getvalue(), original


class GPLAlternativeCandidateTests(unittest.TestCase):
    def test_candidates_replace_just_five_original_existing_profiles(self):
        from anything_plays.systems import SYSTEMS
        self.assertEqual(len(SYSTEMS), 18)
        self.assertEqual(
            set(CANDIDATES["snes"]["systems"]) |
            set(CANDIDATES["sega"]["systems"]),
            {"snes", "genesis", "mastersystem", "gamegear", "sg1000"},
        )
        self.assertEqual(len(CANDIDATES), 2)
        self.assertEqual(CANDIDATES["snes"]["license"], "GPLv3")
        self.assertEqual(CANDIDATES["sega"]["license"], "GPLv3")
        self.assertEqual(CANDIDATES["snes"]["native_name"], "bsnes_libretro.so")
        self.assertEqual(CANDIDATES["sega"]["native_name"], "blastem_libretro.so")
        self.assertEqual(SYSTEMS["snes"].core, "snes9x")
        for name in CANDIDATES["sega"]["systems"]:
            self.assertEqual(SYSTEMS[name].core, "genesis_plus_gx")

    def test_staged_research_native_is_hashed_but_distribution_unapproved(self):
        for candidate in CANDIDATES:
            with self.subTest(candidate=candidate), TemporaryDirectory() as folder:
                original_zip, native = zip_native(candidate)
                path = Path(folder)/"candidate"
                record = stage_candidate(candidate, path, source_bytes=original_zip)
                self.assertEqual(
                    record["native_elf_sha256"], hashlib.sha256(native).hexdigest())
                self.assertEqual(record["original_zip_sha256"],
                                 hashlib.sha256(original_zip).hexdigest())
                self.assertEqual((path/CANDIDATES[candidate]["native_name"]).read_bytes(),
                                 native)
                self.assertEqual(json.loads(
                    (path/"UNAPPROVED_CANDIDATE.json").read_text("utf-8")), record)
                self.assertTrue(record["archive_url"].startswith(BASE))
                for key in ("binary_source_correspondence_verified",
                            "redistribution_license_review_complete",
                            "combined_gpl_family_license_review_complete",
                            "physical_hardware_qa_complete",
                            "public_release_approved",
                            "selected_for_release"):
                    self.assertIs(record[key], False)
                with self.assertRaisesRegex(ValueError, "already exist"):
                    stage_candidate(candidate, path, source_bytes=original_zip)

    def test_rejects_unrecognized_or_wrong_architecture_native(self):
        with self.assertRaisesRegex(ValueError, "Unknown alternative"):
            checked_candidate_zip("not-a-core", b"bad"*10000)
        for name in CANDIDATES:
            data, _ = zip_native(name, magic=b"MZ??")
            with self.assertRaisesRegex(ValueError, "real Linux ELF"):
                checked_candidate_zip(name, data)
            data, _ = zip_native(name, add_extra=True)
            with self.assertRaisesRegex(ValueError, "exactly one"):
                checked_candidate_zip(name, data)
            with self.assertRaisesRegex(ValueError, "missing or exceeds"):
                checked_candidate_zip(name, b"<html>Error 404</html>")

    def test_workflow_runs_real_isolated_homebrew_for_every_replacement_profile(self):
        root=Path(__file__).resolve().parents[1]
        y=(root/".github/workflows/v30-gpl-alternative-research.yml").read_text("utf-8")
        self.assertIn("pull_request:", y)
        self.assertIn("tools/probe_snes_homebrew.py", y)
        self.assertIn("tools/probe_genesis_homebrew.py", y)
        self.assertIn("tools/probe_sega8_homebrew.py", y)
        self.assertIn("mastersystem gamegear sg1000", y)
        self.assertIn("stage_v30_gpl_alternative_candidates", y)
        self.assertIn("if: always()", y)
        self.assertNotIn("gh release create", y)
        self.assertNotIn("APPROVED-3.0-DISTRIBUTION", y)
        self.assertNotIn("continue-on-error: true", y)
        self.assertNotIn("candidate/*.so", y)


if __name__ == "__main__":
    unittest.main()
