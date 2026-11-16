"""ROM-free, process-isolated dynamic-link QA for private 3.3 full-native cores.

This does NOT call retro_init, load content, use a GPU/audio device, open a
camera, run a game, or authorize public redistribution. Each untrusted
native library is loaded in its own bounded subprocess so a segfault, DLL
failure or stall cannot take down the CI orchestrator.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from anything_plays.v30_gpl_trial import (
    enable_windows_trial_runtime, validate_trial_core_directory,
)

EXTENSIONS = {
    "linux-x64": ".so",
    "windows-x64": ".dll",
    "macos-x64": ".dylib",
    "macos-arm64": ".dylib",
}
STATUS = "UNRELEASED_V33_FULL_NATIVE_LINK_ONLY_NOT_GAMEPLAY"
SYMBOLS = (
    "retro_api_version",
    "retro_get_system_info",
    "retro_get_system_av_info",
    "retro_set_environment",
    "retro_set_video_refresh",
    "retro_set_audio_sample",
    "retro_set_input_poll",
    "retro_set_input_state",
    "retro_init",
    "retro_deinit",
    "retro_load_game",
    "retro_unload_game",
    "retro_run",
)


def core_files(directory, target):
    if target not in EXTENSIONS:
        raise ValueError("Unknown private 3.3 native host architecture")
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("Unsafe or missing native source core directory")
    extension = EXTENSIONS[target]
    files = sorted(directory.glob("*_libretro" + extension))
    if len(files) != 11:
        raise ValueError("Expected exactly 11 private source-built native cores")
    for path in files:
        if (path.is_symlink() or not path.is_file()
                or not re.fullmatch(r"[a-z0-9_]+_libretro" +
                                    re.escape(extension), path.name)):
            raise ValueError("Unsafe native core name, link or missing file")
    # Source-built provenance marker verifies exact original-source hashes,
    # including Dolphin/Tia alternatives and bundled Windows runtime.
    row = validate_trial_core_directory(directory, extension)
    if (row.get("native_core_count") != 11
            or row.get("all_console_profiles") != 18
            or not isinstance(row.get("source_built_dolphin"), dict)
            or not isinstance(row.get("source_built_tia"), dict)):
        raise ValueError("Full-native original-source provenance mismatch")
    return files


def isolated_probe(core):
    """Execute only the standard C ABI probe, never initialize the core."""
    core = Path(core)
    if os.name == "nt":
        enable_windows_trial_runtime(core.parent)
    lib = ctypes.CDLL(str(core.resolve(strict=True)))
    api = lib.retro_api_version
    api.restype = ctypes.c_uint
    api.argtypes = []
    if api() != 1:
        raise ValueError("Unsupported native libretro ABI")
    for name in SYMBOLS:
        getattr(lib, name)


def audit(directory, target, *, timeout=20, run=subprocess.run):
    if not isinstance(timeout, (int, float)) or not 1 <= timeout <= 60:
        raise ValueError("Native load timeout must be bounded")
    files = core_files(directory, target)
    records = []
    for core in files:
        try:
            child = run(
                [sys.executable, "-m", "tools.v33_full_native_link",
                 "--probe", str(core)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
            )
            linked = child.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            linked = False
        records.append({"core": core.name, "abi_symbols_loadable": linked})
    # No device ID, path, exception, ROM, memory dump, stderr or OS account.
    return {
        "schema": "anything-plays-v33-native-link-qa",
        "status": STATUS,
        "target": target,
        "native_cores_checked": len(records),
        "all_core_abi_symbols_loadable": all(x["abi_symbols_loadable"]
                                              for x in records),
        "physical_gameplay_tested": False,
        "gamecube_gpu_audio_tested": False,
        "camera_or_controller_tested": False,
        "redistribution_approved": False,
        "public_release_approved": False,
        "cores": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path)
    parser.add_argument("--cores", type=Path)
    parser.add_argument("--target", choices=tuple(EXTENSIONS))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.probe is not None:
        if args.cores is not None or args.target is not None or args.output is not None:
            parser.error("Probing a core and auditing a package are exclusive")
        try:
            isolated_probe(args.probe)
        except Exception:
            # No raw native or driver exception messages in CI.
            raise SystemExit(1) from None
        return
    if args.cores is None or args.target is None or args.output is None:
        parser.error("Audit requires --cores, --target and --output")
    record = audit(args.cores, args.target)
    if args.output.exists() or args.output.is_symlink():
        raise SystemExit("Native-link QA receipt must not already exist")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    if not record["all_core_abi_symbols_loadable"]:
        raise SystemExit("One or more original 3.2 source-built cores did not link")
    print("All 11 private original-source native cores link (no game run).")


if __name__ == "__main__":
    main()
