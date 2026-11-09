"""Real installed GPL trial: SNES/Sega core switching and native PCM/video.

This is not the original native research artifact test. It reads native
images ONLY from the fully built offline GUI app's own core directory, checks
the ORIGINAL pinned-source/native manifest and full installer 11-slot core
inventory, and runs seven sequential actual Libretro sessions through the
existing frontend in a bounded isolated process. On Windows the child
deliberately uses the application's own verified embedded winpthread loader,
NOT the MSYS2 CI DLL directory bootstrap.

NEVER upload the installer, homebrew ROM, DLL or DYLIB from this check.
This test cannot approve licenses or replace physical speaker/camera QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from anything_plays.systems import SYSTEMS
from anything_plays.v30_gpl_trial import (
    EXPECTED_SOURCE_COMMITS, PROFILE_TO_CORE, STATUS as TRIAL_STATUS,
    enable_windows_trial_runtime, validate_trial_core_directory,
)
from fetch_mgba_core import V30_GPL_TRIAL_CORES
from tools.probe_v30_gpl_core_switch import CYCLES, FLAG_KEYS, _child

STATUS = "UNAPPROVED-REAL-INSTALLED-7-CYCLE-GPL-ALTERNATIVE-SWITCH"
SUFFIX = {
    "windows-x64": ".dll", "linux-x64": ".so",
    "macos-arm64": ".dylib", "macos-x64": ".dylib",
}
FLAGS = (
    "combined_gpl_license_reviewed", "public_binary_distribution_approved",
    "physical_audio_camera_save_qa_approved", "release_approved",
)


def verify_installed_payload(cores, target):
    """Prove this is the exact 18-profile 11-core offline app and not a lab DLL."""
    cores = Path(cores)
    if cores.is_symlink() or not cores.is_dir():
        raise ValueError("Missing or symlinked installed GUI core directory")
    if target not in SUFFIX:
        raise ValueError("Unknown 3.0 offline preview target")
    host = sys.platform
    arch = platform.machine().lower()
    if (target == "windows-x64" and (host != "win32" or arch not in ("amd64", "x86_64"))
            or target == "linux-x64" and (not host.startswith("linux") or arch != "x86_64")
            or target == "macos-arm64" and (host != "darwin" or arch not in ("arm64", "aarch64"))
            or target == "macos-x64" and (host != "darwin" or arch != "x86_64")):
        raise ValueError("Actual host architecture mismatches packaged test target")
    manifest_path = cores / "CORE_PROVENANCE.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("Installed native provenance is absent")
    if manifest_path.stat().st_size > 1024 * 1024:
        raise ValueError("Unexpectedly large installer native provenance")
    manifest = json.loads(manifest_path.read_text("utf-8"))
    rows = manifest.get("cores")
    if not isinstance(rows, list) or len(rows) != 11:
        raise ValueError("Packaged native manifest not exactly 11 cores")
    indexed = {r.get("name"): r for r in rows if isinstance(r, dict)}
    # The source-reviewed Tia variant takes the SAME one Atari 2600 native
    # slot. Require the marker + actual installed core identities to agree;
    # do not silently accept extra cores or a remaining GPL2-only Stella.
    expected_names = set(V30_GPL_TRIAL_CORES)
    if os.environ.get("AP_V30_TIA_TRIAL") == "1":
        expected_names.remove("stella2014")
        expected_names.add("tia")
    if set(indexed) != expected_names or len(indexed) != 11:
        raise ValueError("Packaged native inventory changed, missing or duplicated")
    if len(SYSTEMS) != 18 or len(PROFILE_TO_CORE) != 5:
        raise ValueError("Full 18-console 5-profile alternative scope changed")
    marker = validate_trial_core_directory(cores, SUFFIX[target])
    if marker.get("target") != target or marker.get("status") != TRIAL_STATUS:
        raise ValueError("Trial manifest host/source status changed")
    for core, revision in EXPECTED_SOURCE_COMMITS.items():
        entry = marker["alternatives"][core]
        path = cores / entry["native_filename"]
        row = indexed[core]
        if (row.get("sha256") != entry["native_sha256"]
                or row.get("file") != path.name
                or entry["source_commit"] != revision):
            raise ValueError("Installed alternate native identity is not source verified")
    for name in sorted(expected_names):
        row = indexed[name]
        path = cores / f"{name}_libretro{SUFFIX[target]}"
        if (path.is_symlink() or not path.is_file()
                or row.get("file") != path.name
                or row.get("size_bytes") != path.stat().st_size
                or hashlib.sha256(path.read_bytes()).hexdigest() != row.get("sha256")):
            raise ValueError(f"Installed offline original core integrity error: {name}")
    if not (cores / "dolphin-emu" / "Sys" / "codehandler.bin").is_file():
        raise ValueError("Entire GameCube system assets must remain offline")
    return {
        "snes": cores / marker["alternatives"]["mednafen_supafaust"]["native_filename"],
        "sega": cores / marker["alternatives"]["blastem"]["native_filename"],
        "source": marker,
        "core_hashes": {n: indexed[n]["sha256"] for n in sorted(expected_names)},
    }


def run(cores, target, seconds, report):
    if (os.environ.get("AP_V30_GPL_TRIAL") != "1"
            or os.environ.get("AP_V30_TEST_CORES") != "1"
            or os.environ.get("AP_V30_APPROVED_RELEASE") != "0"
            or os.environ.get("AP_RELEASE_BUILD") != "0"):
        raise ValueError("Only explicitly unapproved test-only GPL alternative mode allowed")
    if not 3 <= seconds <= 9:
        raise ValueError("Real native switching requires 3..9 seconds per session")
    report = Path(report)
    if report.exists() or report.is_symlink():
        raise ValueError("Native switch report must be a NEW file")
    installed = verify_installed_payload(cores, target)
    report.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ap-v30-installed-gpl-seven-cycle-") as temp:
        child = Path(temp) / "child-report.json"
        cmd = [
            sys.executable, str(Path(__file__).resolve()), "--child",
            "--cores", str(Path(cores).resolve()), "--target", target,
            "--seconds", str(seconds), "--report", str(child),
        ]
        env = os.environ.copy()
        env["HOME"] = str(temp)
        env["XDG_CONFIG_HOME"] = str(Path(temp) / "config")
        # CI's PythonPath Windows GPL lab is intentionally NOT inherited.
        # The real installed app must load the verified runtime itself.
        if target == "windows-x64":
            env.pop("AP_V30_MINGW_CI_DLL_DIR", None)
            env.pop("PYTHONPATH", None)
        timeout = len(CYCLES) * seconds + 65
        timed_out, exit_code, console = False, None, ""
        try:
            completed = subprocess.run(
                cmd, cwd=ROOT, env=env, capture_output=True,
                text=True, timeout=timeout, check=False)
            exit_code = completed.returncode
            console = (completed.stdout + completed.stderr)[-5000:]
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            raw = exc.stdout or b""
            console = (raw.decode("utf-8", "replace") if isinstance(raw, bytes)
                       else raw)[-5000:]
        details = json.loads(child.read_text("utf-8")) if child.is_file() else None
        passed = bool(
            not timed_out and exit_code == 0 and isinstance(details, dict)
            and details.get("all_cycles_passed") is True
            and details.get("cycles_completed") == len(CYCLES)
            and [r.get("system") for r in details["cycles"]] == list(CYCLES)
            and all(r.get("passed") is True and r.get("core_nonzero_pcm_values", 0) > 100
                    and r.get("distinct_rgb_frames", 0) >= 2 for r in details["cycles"])
            and all(details.get(flag) is False for flag in FLAG_KEYS))
    output = {
        "status": STATUS, "target": target, "passed": passed,
        "full_console_profiles": len(SYSTEMS),
        "actual_installed_native_cores": len(installed["core_hashes"]),
        "test_uses_real_installed_original_core_bytes": True,
        "installed_core_sha256": installed["core_hashes"],
        "snes_source_commit": EXPECTED_SOURCE_COMMITS["mednafen_supafaust"],
        "sega_source_commit": EXPECTED_SOURCE_COMMITS["blastem"],
        "sessions_expected": len(CYCLES),
        "sessions_completed": details.get("cycles_completed") if details else 0,
        "native_child_exit_code": exit_code, "timed_out": timed_out,
        "real_native_session_details": details, "child_console_tail": console,
        **{flag: False for flag in FLAGS},
    }
    report.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", "utf-8")
    return output


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cores", type=Path, required=True)
    ap.add_argument("--target", choices=tuple(SUFFIX), required=True)
    ap.add_argument("--seconds", type=int, default=5)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--child", action="store_true")
    args = ap.parse_args(argv)
    if args.child:
        installed = verify_installed_payload(args.cores, args.target)
        if args.target == "windows-x64":
            enable_windows_trial_runtime(args.cores)
        # Real core switcher uses the existing frontend's native CoreSession;
        # the test child is disposable and has no access to public release.
        return _child(installed["snes"], installed["sega"],
                      args.report, args.seconds)
    try:
        result = run(args.cores, args.target, args.seconds, args.report)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        ap.exit(1, f"ACTUAL INSTALLED GPL CORE SWITCH BLOCKED: {exc}\n")
    print(json.dumps({k: result[k] for k in (
        "status", "target", "passed", "sessions_completed",
        "native_child_exit_code", "timed_out",
        "combined_gpl_license_reviewed", "public_binary_distribution_approved")}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
