"""Synthetic proof that the FINAL eleven-source production mode remains fail-closed.

Test fixtures explicitly do NOT correspond to real emulators or real rights.
The tracked production lock stays unapproved, and no GitHub Release is created.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from anything_plays.v30_approved_core_map import (
    ELEVEN_EXPECTED, ELEVEN_REPOSITORIES, validate_installed_map, MARKER,
)
from tools.v30_release_lock import (
    SOURCE_BUILT_TEN, SOURCE_BUILT_ELEVEN, load_approved_lock,
    selected_source_families, TARGETS, DOLPHIN_REV, PINNED_SYS_TREE_SHA1,
)
from tools.stage_v30_approved_native_mapping import approved_core_map_from_lock
from test_v30_approved_alternative_contract import synthetic_approved, sha


def synthetic_eleven():
    lock, inventory = synthetic_approved()
    lock.update(
        core_set_id="gpl-source-built-eleven",
        eleven_source_built_families_reviewed=True,
        zero_unchanged_native_families_reviewed=True,
    )
    for target,row in lock["targets"].items():
        for name,revision in ELEVEN_EXPECTED.items():
            core=row["cores"][name]
            core["source_commit_sha"]=revision
            core["upstream_source_repository"]=ELEVEN_REPOSITORIES[name]
            core["original_license_notice_sha256"]=sha(name+" original source license test only")
        row["dolphin_sys"].update(
            original_upstream_source_commit=DOLPHIN_REV,
            original_git_data_sys_tree_sha1=PINNED_SYS_TREE_SHA1,
        )
        if target.startswith("windows"):
            row["runtime_dependency_source_reviewed"]=True
            row["runtime_dependencies"]={"libwinpthread-1.dll":sha("synthetic winpthread")}
        else:
            row["runtime_dependencies"]={}
    return lock, inventory


class AllElevenSourceReleaseContract(unittest.TestCase):
    def test_distinct_11_family_source_lineup_and_genuine_dolphin_pin(self):
        self.assertEqual(len(ELEVEN_EXPECTED),11)
        self.assertEqual(ELEVEN_EXPECTED["dolphin"],DOLPHIN_REV)
        self.assertEqual(ELEVEN_REPOSITORIES["dolphin"],"https://github.com/libretro/dolphin")
        self.assertEqual(SOURCE_BUILT_ELEVEN,SOURCE_BUILT_TEN | {"dolphin"})
        self.assertNotIn("snes9x", SOURCE_BUILT_ELEVEN)
        self.assertNotIn("genesis_plus_gx", SOURCE_BUILT_ELEVEN)

    def test_four_os_synthetic_review_maps_all_11_and_no_retained_buildbots(self):
        lock,_=synthetic_eleven()
        self.assertEqual(selected_source_families(lock), SOURCE_BUILT_ELEVEN)
        with TemporaryDirectory() as directory:
            path=Path(directory)/"SYNTHTETIC_NOT_A_REAL_RELEASE_LOCK.json"
            path.write_text(json.dumps(lock))
            reviewed=load_approved_lock(path)
            self.assertEqual(set(reviewed["targets"]),set(TARGETS))
        for target in sorted(TARGETS):
            data=approved_core_map_from_lock(lock,target)
            self.assertEqual(data["core_set_id"],"gpl-source-built-eleven")
            self.assertEqual(len(data["cores"]),11)
            self.assertTrue(data["eleven_source_built_families_reviewed"])
            self.assertTrue(data["zero_unchanged_native_families_reviewed"])
            self.assertEqual(data["cores"]["dolphin"]["source_commit"],DOLPHIN_REV)
            self.assertNotIn("snes9x",data["cores"])
            self.assertNotIn("genesis_plus_gx",data["cores"])
            with TemporaryDirectory() as temp:
                (Path(temp)/MARKER).write_text(json.dumps(data))
                validated=validate_installed_map(temp,
                    ".dll" if target.startswith("windows") else
                    ".dylib" if target.startswith("macos") else ".so",
                    verify_native=False)
                self.assertEqual(len(validated["cores"]),11)

    def test_unreviewed_last_family_never_becomes_approved(self):
        lock,_=synthetic_eleven()
        for key in ("eleven_source_built_families_reviewed",
                    "zero_unchanged_native_families_reviewed"):
            broken=dict(lock)
            broken[key]=False
            with self.assertRaisesRegex(ValueError,"independent review"):
                selected_source_families(broken)
        with self.assertRaises(ValueError):
            selected_source_families({**lock,"core_set_id":"unknown"})

    def test_pristine_dolphin_sys_source_is_immutable(self):
        lock,_=synthetic_eleven()
        with TemporaryDirectory() as temp:
            path=Path(temp)/"synthetic.json"
            for target in sorted(TARGETS):
                row=lock["targets"][target]["dolphin_sys"]
                old=row["original_upstream_source_commit"]
                row["original_upstream_source_commit"]="0"*40
                path.write_text(json.dumps(lock))
                with self.assertRaisesRegex(ValueError,"original Dolphin Git Sys"):
                    load_approved_lock(path)
                row["original_upstream_source_commit"]=old

    def test_actual_checked_in_rights_lock_stays_refused(self):
        with self.assertRaisesRegex(ValueError,"redistribution blocked"):
            load_approved_lock()


if __name__=="__main__":
    unittest.main()
