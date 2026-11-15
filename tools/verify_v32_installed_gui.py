"""Independent installed-GUI acceptance for the unreleased 3.2 preview.

CI seeds deliberately fake public 3.1 files in a disposable HOME, then boots
the real frozen 3.2 executable (not the source runner). Acceptance checks the
reported Tk event loop, exact preview identity, a persisted preview profile,
and unchanged stable canaries. No ROM, camera, controller or real settings.
"""

import argparse
import json
from pathlib import Path

STABLE_DIR = ".config/anything-plays-31"
PREVIEW_DIR = ".config/anything-plays-32-preview"
STABLE_FILES = {
    "preferences.json": b'{"stable_test_canary":"do-not-change"}\n',
    "system_profiles.json": b'{"stable_profile_canary":"do-not-change"}\n',
}
REQUIRED_TRUE = (
    "passed",
    "actual_tk_window_started",
    "actual_app_initialized",
    "actual_tk_mainloop_ran",
    "frozen_binary",
    "v32_frozen_isolation_verified",
    "v32_setup_windows_verified",
    "v32_unbundled_core_launch_safe",
    "v32_setup_camera_untouched",
    "v32_setup_gamepad_untouched",
    "v32_setup_still_disarmed",
    "v32_control_archive_roundtrip_verified",
    "v32_console_artwork_isolation_verified",
    "v32_failed_console_switch_recovery_verified",
    "v32_single_control_export_isolated",
    "v32_unsaved_shutdown_guard_verified",
    "v32_setup_no_orphan_windows",
    "v32_setup_theme_traces_stable",
)
REQUIRED_FALSE = (
    "public_distribution_approved",
    "physical_qa_approved",
    "camera_hardware_tested",
    "gameplay_hardware_tested",
)


def seed(home):
    """Create only dummy baseline files; never overwrite anything existing."""
    home = Path(home)
    if home.is_symlink():
        raise ValueError("QA home must not be a link")
    stable = home / STABLE_DIR
    preview = home / PREVIEW_DIR
    if stable.exists() or stable.is_symlink() or preview.exists() or preview.is_symlink():
        raise ValueError("QA settings already exist: use a fresh disposable home")
    stable.mkdir(parents=True)
    for filename, content in STABLE_FILES.items():
        (stable / filename).write_bytes(content)


def verify(report, home):
    """Fail unless the real installed GUI started safely and left 3.1 intact."""
    report = Path(report)
    home = Path(home)
    if not report.is_file() or report.is_symlink():
        raise ValueError("Actual frozen GUI report missing or unsafe")
    if home.is_symlink():
        raise ValueError("QA home must not be a link")
    raw = report.read_bytes()
    if not 0 < len(raw) <= 64 * 1024:
        raise ValueError("Actual frozen GUI report missing or oversized")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Installed GUI report must be an object")
    for key in REQUIRED_TRUE:
        if data.get(key) is not True:
            raise ValueError("Installed frozen GUI failed: " + key)
    for key in REQUIRED_FALSE:
        if data.get(key) is not False:
            raise ValueError("Unapproved or hardware result is invalid: " + key)
    if data.get("error") is not None:
        raise ValueError("Frozen GUI reported an error")
    if data.get("v32_settings_namespace") != "anything-plays-32-preview":
        raise ValueError("Wrong installed application settings identity")
    if data.get("console_profile_count") != 18:
        raise ValueError("Installed GUI did not initialize all 18 console profiles")
    if data.get("v32_setup_repeat_cycles") != 8:
        raise ValueError("Installed GUI did not repeat the setup lifecycle")
    if data.get("v32_setup_dialog_count") != 40:
        raise ValueError("Installed GUI did not complete all forty setup roundtrips")
    if data.get("initialized_system") not in ("gb", "gbc", "gba"):
        raise ValueError("Installed preview did not start in a bundled console")

    for filename, content in STABLE_FILES.items():
        item = home / STABLE_DIR / filename
        if not item.is_file() or item.is_symlink() or item.read_bytes() != content:
            raise ValueError("Installed preview changed public stable settings")

    preview = home / PREVIEW_DIR
    if not preview.is_dir() or preview.is_symlink():
        raise ValueError("Preview did not create its isolated settings folder")
    profiles = preview / "system_profiles.json"
    if (not profiles.is_file() or profiles.is_symlink()
            or not 0 < profiles.stat().st_size <= 8 * 1024 * 1024
            or profiles.stat().st_nlink != 1):
        raise ValueError("Preview did not save its own safe console profile")
    parsed = json.loads(profiles.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict) or not parsed:
        raise ValueError("Invalid persisted preview console profiles")
    prefs = preview / "preferences.json"
    if prefs.exists() or prefs.is_symlink():
        if not prefs.is_file() or prefs.is_symlink() or prefs.stat().st_nlink != 1:
            raise ValueError("Unsafe preview preferences file")
    return {
        "passed": True,
        "installed_frozen_preview": True,
        "source_profile_count": 18,
        "stable_settings_unchanged": True,
        "preview_profiles_separate": True,
        "five_native_setup_windows_verified": True,
        "repeated_native_setup_cycles_verified": 8,
        "native_dialog_roundtrips_verified": 40,
        "unbundled_preview_launch_safely_rejected": True,
        "camera_hardware_tested": False,
        "controller_hardware_tested": False,
        "public_release_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("seed", "verify"))
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--report", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.action == "seed":
        if args.report or args.output:
            p.error("seed accepts only --home")
        seed(args.home)
        return
    if args.report is None or args.output is None:
        p.error("verify requires --report and --output")
    checked = verify(args.report, args.home)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(checked, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("Verified installed private 3.2 frozen GUI and stable canaries")


if __name__ == "__main__":
    main()
