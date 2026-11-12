"""Disposable final 3.1.0 settings migration: stable, RC1 and RC2 untouched.

The fixture creates only synthetic user directories in CI. No access to a
developer's real HOME, no symlinked source/destination settings, and no
claim that hardware or licensing obligations were verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from anything_plays.test_preferences import CANDIDATE_DIR, RC2_DIR, FINAL_DIR, LEGACY_DIR
from tools.qa_v31_installed_settings_migration import safe_home

FILES = ("preferences.json", "system_profiles.json")
STATUS = "UNRELEASED_FINAL_3_1_INSTALLED_SETTINGS_FIXTURE_ONLY"
SOURCES = (("stable", LEGACY_DIR, "Light"),
           ("rc1", CANDIDATE_DIR, "Plum Dark"),
           ("rc2", RC2_DIR, "Ocean Dark"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_fixture_home(home, manifest):
    home = safe_home(home)
    if home.resolve() == Path.home().resolve():
        raise ValueError("Refusing real HOME for final migration fixture")
    if Path(manifest).resolve().is_relative_to(home.resolve()):
        raise ValueError("Fixture manifest must be outside synthetic HOME")
    return home


def seed(home, *, manifest):
    home = safe_fixture_home(home, manifest)
    if any(home.iterdir()):
        raise ValueError("Final QA HOME must be empty before seeding")
    snapshots = {}
    for label, directory, theme in SOURCES:
        folder = home / directory
        folder.mkdir(parents=True)
        values = {
            "preferences.json": json.dumps({
                "theme": theme, "final_test_origin": label,
            }, separators=(",", ":")).encode("utf-8"),
            "system_profiles.json": b"{}\n",
        }
        for name, payload in values.items():
            (folder / name).write_bytes(payload)
        snapshots[label] = {name:digest(folder/name) for name in FILES}
    record = {
        "schema_version":1,"status":STATUS,
        "fixture_root":str(home.resolve()),
        "stable_relative_dir":LEGACY_DIR.as_posix(),
        "rc1_relative_dir":CANDIDATE_DIR.as_posix(),
        "rc2_relative_dir":RC2_DIR.as_posix(),
        "final_relative_dir":FINAL_DIR.as_posix(),
        "original_sha256":snapshots,
        "expected_final_theme":"Ocean Dark",
        "public_release_approved":False,
    }
    path=Path(manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record,indent=2)+"\n","utf-8")
    return record


def verify(home, *, manifest):
    home = safe_fixture_home(home, manifest)
    record = json.loads(Path(manifest).read_text("utf-8"))
    expected={
        "schema_version":1,"status":STATUS,
        "fixture_root":str(home.resolve()),
        "stable_relative_dir":LEGACY_DIR.as_posix(),
        "rc1_relative_dir":CANDIDATE_DIR.as_posix(),
        "rc2_relative_dir":RC2_DIR.as_posix(),
        "final_relative_dir":FINAL_DIR.as_posix(),
        "expected_final_theme":"Ocean Dark",
        "public_release_approved":False,
    }
    for field, value in expected.items():
        if record.get(field)!=value:
            raise ValueError("Final settings fixture tampered: "+field)
    hashes=record.get("original_sha256")
    if not isinstance(hashes,dict) or set(hashes)!={"stable","rc1","rc2"}:
        raise ValueError("Missing existing user settings snapshots")
    for label, relative, theme in SOURCES:
        root=home/relative
        if root.is_symlink() or not root.is_dir():
            raise ValueError("Missing or symlinked "+label+" source")
        for name in FILES:
            file=root/name
            if file.is_symlink() or not file.is_file() or digest(file)!=hashes[label].get(name):
                raise ValueError("Final build changed "+label+" settings "+name)
    final=home/FINAL_DIR
    if final.is_symlink() or not final.is_dir():
        raise ValueError("Final settings directory not independent")
    for name in FILES:
        file=final/name
        if file.is_symlink() or not file.is_file():
            raise ValueError("Final settings missing or symlinked "+name)
    prefs=json.loads((final/"preferences.json").read_text("utf-8"))
    if not isinstance(prefs,dict) or prefs.get("theme")!="Ocean Dark" or prefs.get("final_test_origin")!="rc2":
        raise ValueError("Final 3.1 did not migrate RC2 user preferences")
    profiles=json.loads((final/"system_profiles.json").read_text("utf-8"))
    if not isinstance(profiles,dict) or "gba" not in profiles:
        raise ValueError("Final profiles were not initialized by real GUI")
    return {
        "schema_version":1,
        "status":"PASSED_FINAL_COPIED_RC2_PREFERENCES_STABLE_RC1_RC2_UNCHANGED",
        "final_theme":prefs["theme"],
        "stable_preferences_and_profiles_unchanged":True,
        "rc1_preferences_and_profiles_unchanged":True,
        "rc2_preferences_and_profiles_unchanged":True,
        "isolated_final_directory_created":True,
        "initialized_console_profiles":len(profiles),
        "hardware_verified":False,
        "public_release_approved":False,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("seed","verify"))
    parser.add_argument("--home",type=Path,required=True)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    record=(seed(args.home,manifest=args.manifest) if args.mode=="seed"
            else verify(args.home,manifest=args.manifest))
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(record,indent=2)+"\n","utf-8")
    print(record["status"])


if __name__=="__main__":
    main()
