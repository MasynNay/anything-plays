"""Isolated migration acceptance fixture for *installed* 3.1 RC1 builds.

Use only in an empty temporary QA home. This never modifies an actual
user account, copies a ROM, downloads anything or marks release approved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

from anything_plays.test_preferences import CANDIDATE_DIR, LEGACY_DIR


PREF_NAME = "preferences.json"
PROFILES_NAME = "system_profiles.json"
EXPECTED_THEME = "Plum Dark"
FIXTURE_PREFS = (
    b'{"theme":"Plum Dark","v31_settings_test":"candidate-migration-readonly"}\n'
)
FIXTURE_PROFILES = b'{}\n'
FILENAMES = (PREF_NAME, PROFILES_NAME)
STATUS = "UNRELEASED_3_1_INSTALLED_SETTINGS_MIGRATION_ONLY"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_home(home):
    home = Path(home)
    if not home.is_absolute() or home.is_symlink() or not home.is_dir():
        raise ValueError("Use a new absolute, real QA temporary directory")
    return home


def seed_fixture(home, *, manifest):
    """Create a known read-only 3.0-style seed only in a fresh empty home."""
    home = safe_home(home)
    manifest = Path(manifest)
    if home.resolve() == Path.home().resolve():
        raise ValueError("Refusing to seed the user's real HOME")
    if any(home.iterdir()) or manifest.resolve().is_relative_to(home.resolve()):
        raise ValueError("Refusing to write into populated or aliased QA HOME")
    stable = home / LEGACY_DIR
    stable.mkdir(parents=True)
    fixtures = {PREF_NAME: FIXTURE_PREFS, PROFILES_NAME: FIXTURE_PROFILES}
    expected = {}
    for name, value in fixtures.items():
        target = stable / name
        with target.open("xb") as stream:
            stream.write(value)
        target.chmod(stat.S_IRUSR | stat.S_IWUSR)
        expected[name] = sha256(target)
    report = {
        "schema_version": 1,
        "status": STATUS,
        "fixture_root": str(home.resolve()),
        "stable_relative_path": LEGACY_DIR.as_posix(),
        "rc_relative_path": CANDIDATE_DIR.as_posix(),
        "stable_file_sha256": expected,
        "migration_target_theme": EXPECTED_THEME,
        "stable_data_was_modified": False,
        "physical_controller_verified": False,
        "public_release_approved": False,
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    return report


def verify_fixture(home, *, manifest):
    """Fail if installed app changed stable files or failed to copy RC data."""
    home = safe_home(home)
    manifest = Path(manifest)
    report = json.loads(manifest.read_text("utf-8"))
    if (report.get("status") != STATUS
            or report.get("fixture_root") != str(home.resolve())
            or report.get("stable_relative_path") != LEGACY_DIR.as_posix()
            or report.get("rc_relative_path") != CANDIDATE_DIR.as_posix()
            or report.get("public_release_approved") is not False):
        raise ValueError("Not the original isolated migration test fixture")
    stable, rc = home / LEGACY_DIR, home / CANDIDATE_DIR
    if stable.is_symlink() or rc.is_symlink() or not rc.is_dir():
        raise ValueError("Missing candidate namespace or unsafe settings links")
    expected = report.get("stable_file_sha256")
    if not isinstance(expected, dict) or set(expected) != set(FILENAMES):
        raise ValueError("Original stable settings checksum receipt missing")
    for filename in FILENAMES:
        original, copied = stable / filename, rc / filename
        if (original.is_symlink() or copied.is_symlink()
                or not original.is_file() or not copied.is_file()):
            raise ValueError("Missing or redirected original/candidate settings")
        if sha256(original) != expected[filename]:
            raise ValueError("Stable version's settings were modified")
    prefs = json.loads((rc / PREF_NAME).read_text("utf-8"))
    if (not isinstance(prefs, dict)
            or prefs.get("theme") != EXPECTED_THEME):
        raise ValueError("Candidate did not import the tested stable theme")
    return {
        "schema_version": 1,
        "status": "UNRELEASED_3_1_INSTALLED_RC_SETTINGS_COPIED_STABLE_UNCHANGED",
        "stable_preferences_unchanged": True,
        "stable_profiles_unchanged": True,
        "rc_pref_namespace_created": True,
        "rc_profile_namespace_created": True,
        "migrated_theme": EXPECTED_THEME,
        "source_fixture_manifest": manifest.name,
        "physical_controller_verified": False,
        "public_release_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("seed", "verify"))
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.mode == "seed":
        result = seed_fixture(args.home, manifest=args.manifest)
    else:
        result = verify_fixture(args.home, manifest=args.manifest)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    print(result["status"])


if __name__ == "__main__":
    main()
