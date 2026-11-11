"""Isolated RC2 installed-app migration fixture: stable + RC1 must be untouched.

All files are synthetic. Only creates files under a previously empty,
temporary QA HOME distinct from the real user account.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from anything_plays.test_preferences import CANDIDATE_DIR, RC2_DIR, LEGACY_DIR
from tools.qa_v31_installed_settings_migration import safe_home

FILENAMES = ("preferences.json", "system_profiles.json")
STATUS = "UNRELEASED_RC2_INSTALLED_SETTINGS_FIXTURE_ONLY"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_fixture_home(home, manifest):
    home = safe_home(home)
    if home.resolve() == Path.home().resolve():
        raise ValueError("Refusing actual HOME for RC2 migration fixture")
    manifest = Path(manifest)
    if manifest.resolve().is_relative_to(home.resolve()):
        raise ValueError("RC2 fixture manifest must be outside synthetic HOME")
    return home


def seed(home, *, manifest):
    home = safe_fixture_home(home, manifest)
    if any(home.iterdir()):
        raise ValueError("RC2 QA HOME must be empty before staging")
    source_hashes = {}
    for label, folder, theme in (
        ("stable", home / LEGACY_DIR, "Light"),
        ("rc1", home / CANDIDATE_DIR, "Plum Dark"),
    ):
        folder.mkdir(parents=True)
        files = {
            "preferences.json": json.dumps({
                "theme": theme,
                "rc2_test_origin": label,
            }).encode("utf-8"),
            "system_profiles.json": b"{}\n",
        }
        for name, data in files.items():
            with (folder / name).open("xb") as dst:
                dst.write(data)
        source_hashes[label] = {name: digest(folder / name) for name in FILENAMES}
    record = {
        "schema_version": 1,
        "status": STATUS,
        "fixture_root": str(home.resolve()),
        "stable_relative_dir": LEGACY_DIR.as_posix(),
        "rc1_relative_dir": CANDIDATE_DIR.as_posix(),
        "rc2_relative_dir": RC2_DIR.as_posix(),
        "original_sha256": source_hashes,
        "expected_rc2_theme": "Plum Dark",
        "public_release_approved": False,
    }
    manifest = Path(manifest)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(record, indent=2) + "\n", "utf-8")
    return record


def verify(home, *, manifest):
    home = safe_fixture_home(home, manifest)
    record = json.loads(Path(manifest).read_text("utf-8"))
    expected = {
        "schema_version": 1,
        "status": STATUS,
        "fixture_root": str(home.resolve()),
        "stable_relative_dir": LEGACY_DIR.as_posix(),
        "rc1_relative_dir": CANDIDATE_DIR.as_posix(),
        "rc2_relative_dir": RC2_DIR.as_posix(),
        "expected_rc2_theme": "Plum Dark",
        "public_release_approved": False,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError("RC2 settings fixture was modified: " + key)
    fingerprints = record.get("original_sha256")
    if not isinstance(fingerprints, dict) or set(fingerprints) != {"stable", "rc1"}:
        raise ValueError("Missing source settings fingerprint record")
    for label, folder in (
        ("stable", home / LEGACY_DIR), ("rc1", home / CANDIDATE_DIR)
    ):
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError("Original settings directory missing or symlinked")
        observed = {}
        for filename in FILENAMES:
            path = folder / filename
            if path.is_symlink() or not path.is_file():
                raise ValueError("Original settings have a linked or missing file")
            observed[filename] = digest(path)
        if observed != fingerprints[label]:
            raise ValueError("Installed RC2 touched existing " + label + " settings")
    rc2 = home / RC2_DIR
    if rc2.is_symlink() or not rc2.is_dir():
        raise ValueError("RC2 settings must be in a new, real directory")
    for filename in FILENAMES:
        candidate = rc2 / filename
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError("RC2 migration file linked or not found: " + filename)
    prefs = json.loads((rc2 / "preferences.json").read_text("utf-8"))
    if (not isinstance(prefs, dict)
            or prefs.get("theme") != "Plum Dark"
            or prefs.get("rc2_test_origin") != "rc1"):
        raise ValueError("RC2 failed to import RC1 preferences")
    # The actual app may normalize its own destination profiles on startup.
    # RC1 and stable source-profile hashes MUST remain unchanged, but RC2's
    # new profile can legitimately be enriched with default grid settings.
    profiles = json.loads((rc2 / "system_profiles.json").read_text("utf-8"))
    if not isinstance(profiles, dict) or "gba" not in profiles:
        raise ValueError("Installed RC2 did not initialize valid isolated profiles")
    return {
        "schema_version": 1,
        "status": "PASSED_RC2_COPIED_RC1_PREFERENCES_STABLE_AND_RC1_UNCHANGED",
        "rc2_theme": prefs["theme"],
        "stable_preferences_and_profiles_unchanged": True,
        "rc1_preferences_and_profiles_unchanged": True,
        "isolated_rc2_directory_created": True,
        "initialized_console_profiles": len(profiles),
        "hardware_verified": False,
        "public_release_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("seed", "verify"))
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = seed(args.home, manifest=args.manifest) if args.mode == "seed" else verify(
        args.home, manifest=args.manifest
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    print(result["status"])


if __name__ == "__main__":
    main()
