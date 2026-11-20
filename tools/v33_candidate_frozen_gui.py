"""Validate a *running frozen* 3.3 mGBA-only candidate in a disposable HOME.

Different from static binary identity validation: an actual Tk event loop
must initialize and exercise the Stream Output window without accessing a
physical camera, ROM, SDL controller or the user's existing installation.
This is synthetic host smoke, NOT a real-device release approval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


STABLE_CANARIES = {
    ".config/anything-plays-31/preferences.json":
        b'{"public_stable_canary":"do-not-touch"}\n',
    ".config/anything-plays-31/system_profiles.json":
        b'{"public_profiles_canary":"do-not-touch"}\n',
    ".config/anything-plays-32-preview/preferences.json":
        b'{"previous_preview_canary":"do-not-touch"}\n',
    ".config/anything-plays-32-preview/system_profiles.json":
        b'{"previous_profiles_canary":"do-not-touch"}\n',
}
PRIVATE_DIR = ".config/anything-plays-33-candidate"

REQUIRED_TRUE = (
    "passed",
    "actual_tk_window_started",
    "actual_app_initialized",
    "actual_tk_mainloop_ran",
    "frozen_binary",
    "v33_frozen_isolation_verified",
    "v33_input_disarmed_at_startup",
    "stream_output_window_opened",
    "stream_settings_separate",
    "stream_appearance_configured",
    "stream_camera_reference_rendered",
    "stream_closed_cleanly",
)
REQUIRED_FALSE = (
    "camera_hardware_tested",
    "gameplay_hardware_tested",
    "physical_qa_approved",
    "public_distribution_approved",
)


def _safe_directory(path):
    return path.is_dir() and not path.is_symlink()


def seed(home):
    """Create dummy historical settings ONLY in a new disposable home."""
    home = Path(home)
    if home.is_symlink() or not _safe_directory(home):
        raise ValueError("QA home must be an existing real directory")
    for relative in STABLE_CANARIES:
        path = home / relative
        if path.exists() or path.is_symlink():
            raise ValueError("QA historical canary already exists")
        if any(part.is_symlink() for part in
               (path.parent, path.parent.parent)):
            raise ValueError("Unsafe QA canary parent")
    private = home / PRIVATE_DIR
    if private.exists() or private.is_symlink():
        raise ValueError("QA private candidate destination already exists")
    for relative, payload in STABLE_CANARIES.items():
        path = home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(payload)


def verify(report, home):
    """Fail closed unless frozen Tk really ran and stable canaries survived."""
    report, home = Path(report), Path(home)
    if (not report.is_file() or report.is_symlink()
            or report.stat().st_nlink != 1
            or not 0 < report.stat().st_size <= 64 * 1024):
        raise ValueError("Missing, linked or oversized frozen QA report")
    if not _safe_directory(home):
        raise ValueError("Unsafe QA home directory")
    parsed = json.loads(report.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Frozen GUI report must be a JSON object")
    for field in REQUIRED_TRUE:
        if parsed.get(field) is not True:
            raise ValueError("Frozen 3.3 Tk startup was not verified: " + field)
    for field in REQUIRED_FALSE:
        if parsed.get(field) is not False:
            raise ValueError("Frozen 3.3 report claims unverified hardware: "
                             + field)
    if parsed.get("error") is not None:
        raise ValueError("Frozen 3.3 GUI had an exception")
    if parsed.get("v33_settings_namespace") != "anything-plays-33-candidate":
        raise ValueError("Wrong candidate settings namespace")
    if parsed.get("initialized_system") not in ("gb", "gbc", "gba"):
        raise ValueError("Frozen 3.3 startup selected an unbundled system")
    if parsed.get("console_profile_count") != 18:
        raise ValueError("Frozen 3.3 app did not initialize full system catalog")
    if not _safe_directory(home / PRIVATE_DIR):
        raise ValueError("Frozen app did not create its private settings directory")
    for relative, expected in STABLE_CANARIES.items():
        path = home / relative
        if (not path.is_file() or path.is_symlink()
                or path.stat().st_nlink != 1
                or path.read_bytes() != expected):
            raise ValueError("Frozen candidate modified historical settings")
    for filename in ("preferences.json", "system_profiles.json"):
        path = home / PRIVATE_DIR / filename
        if path.exists() or path.is_symlink():
            if (not path.is_file() or path.is_symlink()
                    or path.stat().st_nlink != 1
                    or not 0 < path.stat().st_size <= 8 * 1024 * 1024):
                raise ValueError("Unsafe private candidate settings")
    return {
        "passed": True,
        "frozen_candidate_gui_started": True,
        "real_tk_loop_verified": True,
        "synthetic_stream_window_verified": True,
        "historical_settings_unchanged": True,
        "hardware_camera_tested": False,
        "hardware_controller_tested": False,
        "physical_gamecube_tested": False,
        "obs_encoder_tested": False,
        "public_release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seed", "verify"))
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "seed":
        if args.report is not None or args.output is not None:
            parser.error("seed accepts only --home")
        seed(args.home)
        return
    if args.report is None or args.output is None:
        parser.error("verify requires --report and --output")
    outcome = verify(args.report, args.home)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(outcome, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Verified genuine frozen 3.3 candidate Tk startup, not hardware QA")


if __name__ == "__main__":
    main()
