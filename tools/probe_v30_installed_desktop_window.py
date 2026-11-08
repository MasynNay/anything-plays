"""Launch the ACTUAL frozen Anything Plays desktop binary and verify real Tk UI.

Unlike prior 18/11 native core checks, this executes the frozen application
and waits for its real Tk root, actual App() UI construction, and event loop.
It does NOT claim any physical camera/audio/gameplay or legal QA.
No ROMs, emulator downloads, release uploads or third-party contacts.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

VALID_PLATFORMS = ("windows-x64", "linux-x64", "macos-arm64", "macos-x64")
STATUS = "UNAPPROVED-3.0-INSTALLED-DESKTOP-STARTUP-CHECK"


def default_binary(platform):
    if platform == "windows-x64":
        return Path("dist/AnythingPlays/AnythingPlays.exe")
    if platform == "linux-x64":
        return Path("dist/AnythingPlays/AnythingPlays")
    return Path("dist/AnythingPlays30Preview.app/Contents/MacOS/AnythingPlays")


def validate_report(report, platform):
    if (not isinstance(report, dict) or report.get("schema_version") != 1
            or report.get("status") != STATUS
            or report.get("passed") is not True
            or report.get("frozen_binary") is not True
            or report.get("actual_tk_window_started") is not True
            or report.get("actual_app_initialized") is not True
            or report.get("actual_tk_mainloop_ran") is not True
            or report.get("console_profile_count") != 18
            or not isinstance(report.get("initialized_system"), str)
            or report.get("top_level_widgets", 0) < 1
            or report.get("error") is not None):
        raise ValueError(f"{platform}: original installed desktop startup did NOT pass: {report.get('error') if isinstance(report, dict) else repr(report)}")
    for flag in ("camera_hardware_tested", "gameplay_hardware_tested",
                 "physical_qa_approved", "public_distribution_approved"):
        if report.get(flag) is not False:
            raise ValueError(f"{platform}: false physical/legal claim: {flag}")
    return True


def run(platform, binary, report, *, timeout=55):
    if platform not in VALID_PLATFORMS:
        raise ValueError("Unknown real installed-app target")
    binary, report = Path(binary), Path(report)
    if (binary.is_symlink() or not binary.is_file()
            or report.exists() or report.is_symlink()
            or timeout < 5 or timeout > 120):
        raise ValueError("Missing real frozen executable, unsafe report or invalid timeout")
    binary = binary.resolve()
    report = report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "AP_V30_UI_SMOKE_CHECK": "1",
        "AP_V30_UI_SMOKE_REPORT": str(report),
        "AP_RELEASE_BUILD": "0",
        "AP_V30_APPROVED_RELEASE": "0",
        "AP_V30_TEST_PREFERENCES": "1",
        "PYTHONUNBUFFERED": "1",
    })
    args = [str(binary), "--ap-v30-ui-smoke"]
    if platform == "linux-x64":
        args = ["xvfb-run", "-a", "-s", "-screen 0 1680x1050x24", *args]
    try:
        proc = subprocess.run(
            args, cwd=binary.parent, env=env, timeout=timeout, check=False,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"{platform}: real installed Tk window launch TIMED OUT ({timeout}s)") from exc
    if not report.is_file() or report.is_symlink() or report.stat().st_size > 32000:
        output = (proc.stdout or "")[-5500:]
        raise ValueError(f"{platform}: real installed executable exited {proc.returncode} without startup report: {output}")
    original = json.loads(report.read_text(encoding="utf-8"))
    if proc.returncode != 0:
        raise ValueError(f"{platform}: actual installed executable returned {proc.returncode}; {original.get('error')}; stdout={(proc.stdout or '')[-1600:]}")
    validate_report(original, platform)
    print(f"REAL FROZEN GUI STARTED: {platform}; widgets={original['top_level_widgets']}; 18 profiles; no camera or rights claim", flush=True)
    return original


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--platform", required=True, choices=VALID_PLATFORMS)
    p.add_argument("--binary", type=Path)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--timeout", type=int, default=55)
    args = p.parse_args(argv)
    try:
        run(args.platform, args.binary or default_binary(args.platform),
            args.report, timeout=args.timeout)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        p.exit(1, f"UNAPPROVED INSTALLED GUI LAUNCH FAILED: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
