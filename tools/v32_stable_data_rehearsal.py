"""Private 3.2 stable upgrade frozen-GUI data preservation rehearsal.

This intentionally uses a brand-new temporary HOME with synthetic stable
3.1.1 prefs, console profiles and a save-file canary. No real ROM or user
file is copied. A successful test is still not proof of public upgrade
safety, native game-save compatibility or hardware operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import default_for

NAMESPACE = Path(".config") / "anything-plays-31"
PREFERENCES = {
    "system": "gba",
    "theme": "Ocean Dark",
    "rom_directories": {"gba": "/synthetic-existing-gba-roms"},
    "rom_directory": "/synthetic-existing-gba-roms",
    "key_bindings": {"gba": {"A": "v"}},
    "private_upgrade_canary": "synthetic-stable-preserve",
}
PROFILE_TOLERANCE = 61
SAVE_CANARY = b"AP32-SYNTHETIC-OLD-SRAM-DO-NOT-ALTER\x00\xfa"
STATUS = "PRIVATE_V32_FROZEN_STABLE_DATA_REHEARSAL_NOT_RELEASE"


def _safe_home(home):
    home = Path(home)
    if home.is_symlink():
        raise ValueError("Synthetic QA HOME must not be a symlink")
    return home


def seed(home):
    """Refuse any existing stable namespace; no overwrite is ever permitted."""
    home = _safe_home(home)
    root = home / NAMESPACE
    if root.exists() or root.is_symlink():
        raise ValueError("Stable QA fixture already exists")
    root.mkdir(parents=True)
    profile = default_for("gba", DEFAULT)
    profile["tolerance"] = PROFILE_TOLERANCE
    profile["private_profile_canary"] = "synthetic-existing-gba"
    (root / "preferences.json").write_text(
        json.dumps(PREFERENCES, indent=2) + "\n", "utf-8"
    )
    (root / "system_profiles.json").write_text(
        json.dumps({"gba": profile}, indent=2) + "\n", "utf-8"
    )
    # A canary beside the stable settings proves a genuinely unrelated old
    # save cannot be overwritten by a no-game startup and shutdown.
    (root / "synthetic-existing.sav").write_bytes(SAVE_CANARY)
    return root


def verify(home, report):
    home = _safe_home(home)
    report = Path(report)
    if (not report.is_file() or report.is_symlink()
            or not 0 < report.stat().st_size < 64 * 1024):
        raise ValueError("Frozen upgrade report missing or too large")
    data = json.loads(report.read_text("utf-8"))
    if type(data) is not dict:
        raise ValueError("Invalid frozen app report")
    expected_true = (
        "passed", "actual_tk_window_started", "actual_app_initialized",
        "actual_tk_mainloop_ran", "frozen_binary",
    )
    if any(data.get(k) is not True for k in expected_true):
        raise ValueError("The actual installed stable upgrade did not launch")
    if any(data.get(k) is not False for k in (
        "public_distribution_approved", "physical_qa_approved",
        "camera_hardware_tested", "gameplay_hardware_tested",
    )):
        raise ValueError("Fake hardware/release success in source upgrade QA")
    if (data.get("initialized_system") != "gba"
            or data.get("console_profile_count") != 18
            or data.get("error") is not None):
        raise ValueError("3.2 could not load the old selected GBA profile")

    root = home / NAMESPACE
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Stable settings namespace missing or redirected")
    def read_obj(filename):
        file = root / filename
        if (not file.is_file() or file.is_symlink()
                or not 0 < file.stat().st_size <= 8 * 1024 * 1024
                or file.stat().st_nlink != 1):
            raise ValueError("Stable fixture damaged during launch: " + filename)
        result = json.loads(file.read_text("utf-8"))
        if type(result) is not dict:
            raise ValueError("Stored stable data must remain a JSON object")
        return result
    prefs = read_obj("preferences.json")
    for key, value in PREFERENCES.items():
        if prefs.get(key) != value:
            raise ValueError("3.2 lost existing stable preference: " + key)
    profile = read_obj("system_profiles.json").get("gba")
    if (type(profile) is not dict
            or profile.get("tolerance") != PROFILE_TOLERANCE
            or profile.get("private_profile_canary") != "synthetic-existing-gba"
            or not profile.get("zones")
            or not profile.get("mapping")):
        raise ValueError("3.2 destroyed the previous GBA control profile")
    save = root / "synthetic-existing.sav"
    if (not save.is_file() or save.is_symlink()
            or save.read_bytes() != SAVE_CANARY):
        raise ValueError("3.2 modified a saved-game canary during startup")
    if (home / ".config" / "anything-plays-32-preview").exists():
        raise ValueError("Stable upgrade accidentally created preview settings")
    return {
        "schema_version": 1,
        "status": STATUS,
        "real_frozen_gui_started": True,
        "old_selected_gba_profile_preserved": True,
        "old_rom_folder_preference_preserved": True,
        "old_keyboard_and_theme_preferences_preserved": True,
        "old_save_canary_sha256": hashlib.sha256(SAVE_CANARY).hexdigest(),
        "old_save_canary_byte_identical": True,
        "old_preview_settings_not_used": True,
        "synthetic_test_data_only": True,
        "real_gameplay_or_save_emulation_tested": False,
        "physical_devices_tested": False,
        "stable_upgrade_release_approved": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("seed", "verify"))
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.operation == "seed":
        if args.report or args.output:
            parser.error("Seed only accepts --home")
        seed(args.home)
        return 0
    if not args.report or not args.output:
        parser.error("Verify requires --report and --output")
    checked = verify(args.home, args.report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(checked, indent=2, sort_keys=True) + "\n", "utf-8")
    print("Synthetic old stable GBA settings and save survived real 3.2 frozen startup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
