"""Prove 18/18 console profiles resolve their installed cores *offline*.

This runs after the actual four-platform preview installer staging. It checks
real library bytes against the bundled manifest and invokes the application's
real find_core() for every console with a clean per-user core store and network
connections deliberately blocked. It is not gameplay, a physical installation
test, rights approval, or a public release.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
from unittest import mock

from anything_plays import core_locator, core_packs
from anything_plays.n64_software import find_parallel_n64_core
from anything_plays.gamecube_software import find_dolphin_core
from anything_plays.systems import SYSTEMS
from tools.v30_release_lock import CORE_NAMES

TARGETS = {
    "windows-x64": ".dll",
    "macos-arm64": ".dylib",
    "macos-x64": ".dylib",
    "linux-x64": ".so",
}
STATUS = "3.0-REAL-STAGED-BUNDLE-OFFLINE-RUNTIME-RESOLUTION-TEST-ONLY"


def _sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for part in iter(lambda: source.read(1024 * 1024), b""):
            result.update(part)
    return result.hexdigest()


def _blocked_network(*_args, **_kwargs):
    raise AssertionError("Unexpected network connection during bundled core lookup")


def check_offline_bundle(core_dir, target, *, lookup=None):
    """Fail closed on a missing, altered or remotely resolved native emulator."""
    if target not in TARGETS or type(target) is not str:
        raise ValueError("Unknown 3.0 offline installer target")
    if core_packs.target_identity()[0] != target:
        raise ValueError("Requested target does not match this native runner")
    if os.environ.get("AP_V21_DEVELOPER_EXTERNAL") == "1":
        raise ValueError("Developer external-core fallback must be disabled")
    core_dir = Path(core_dir)
    if not core_dir.is_dir() or core_dir.is_symlink():
        raise ValueError("No genuine staged native core directory")
    core_dir = core_dir.resolve()
    manifest_file = core_dir / "CORE_PROVENANCE.json"
    if not manifest_file.is_file() or manifest_file.is_symlink():
        raise ValueError("Staged bundle missing genuine native core provenance")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    source_records = manifest.get("cores")
    expected_names = set(CORE_NAMES)
    if len(SYSTEMS) != 18 or len(expected_names) != 11:
        raise ValueError("3.0 frozen console/core inventory changed")
    if not isinstance(source_records, list) or len(source_records) != 11:
        raise ValueError("Incomplete native core manifest")
    records = {}
    ext = TARGETS[target]
    for row in source_records:
        if not isinstance(row, dict):
            raise ValueError("Invalid native core manifest entry")
        name = row.get("name")
        if name not in expected_names or name in records:
            raise ValueError("Unknown or repeated native core entry")
        filename = f"{name}_libretro{ext}"
        if row.get("file") != filename:
            raise ValueError(f"Wrong platform core filename: {name}")
        native = core_dir / filename
        if not native.is_file() or native.is_symlink():
            raise ValueError(f"Bundled native core missing or symlinked: {name}")
        size = native.stat().st_size
        if type(row.get("size_bytes")) is not int or size != row["size_bytes"] or size <= 0:
            raise ValueError(f"Bundled native size mismatch: {name}")
        if _sha256(native) != row.get("sha256"):
            raise ValueError(f"Bundled native SHA-256 mismatch: {name}")
        records[name] = {"name": filename, "sha256": row["sha256"], "bytes": size}
    if set(records) != expected_names:
        raise ValueError("Some required emulator cores are not packaged")
    handler = core_dir / "dolphin-emu" / "Sys" / "codehandler.bin"
    if not handler.is_file() or handler.is_symlink() or handler.stat().st_size == 0:
        raise ValueError("Dolphin required Sys files missing")

    def application_resolver(system):
        # Match Emulator.find_system_core(), including its two intentional
        # non-generic native backends. Systems.n64 describes the legacy
        # external RetroArch path; actual in-panel N64 uses ParaLLEl-N64.
        if system == "n64":
            return find_parallel_n64_core()
        if system == "gamecube":
            return find_dolphin_core()
        return core_locator.find_core(system)

    resolve = lookup if lookup is not None else application_resolver
    resolved = {}
    with TemporaryDirectory(prefix="anything-plays-v30-fresh-core-store-") as folder:
        with ExitStack() as patches:
            # Use actual installed/staged core directory, not cores/ in the
            # developer checkout or preexisting global RetroArch directories.
            patches.enter_context(mock.patch(
                "anything_plays.core_locator._search_directories",
                return_value=[core_dir],
            ))
            # A never-before-launched user has no managed core-pack overlay.
            patches.enter_context(mock.patch(
                "anything_plays.n64_software._search_directories",
                return_value=[core_dir],
            ))
            patches.enter_context(mock.patch(
                "anything_plays.gamecube_software._search_directories",
                return_value=[core_dir],
            ))
            patches.enter_context(mock.patch(
                "anything_plays.core_packs.managed_core_root",
                return_value=Path(folder) / "uninitialized-core-overlays",
            ))
            patches.enter_context(mock.patch(
                "socket.socket.connect", side_effect=_blocked_network,
            ))
            patches.enter_context(mock.patch(
                "socket.create_connection", side_effect=_blocked_network,
            ))
            patches.enter_context(mock.patch(
                "urllib.request.urlopen", side_effect=_blocked_network,
            ))
            for system, config in sorted(SYSTEMS.items()):
                found = resolve(system)
                if not found:
                    raise ValueError(f"{system}: bundled runtime core unavailable offline")
                path = Path(found)
                if path.is_symlink() or not path.is_file():
                    raise ValueError(f"{system}: runtime core path unsafe")
                actual = path.resolve()
                if actual.parent != core_dir:
                    raise ValueError(f"{system}: runtime selected external emulator")
                actual_core = "parallel_n64" if system == "n64" else config.core
                expected_file = core_dir / records[actual_core]["name"]
                if actual != expected_file:
                    raise ValueError(f"{system}: runtime selected the wrong core")
                resolved[system] = actual_core
    return {
        "schema_version": 1,
        "status": STATUS,
        "target": target,
        "systems_resolved_without_network": len(resolved),
        "native_cores_hash_verified": len(records),
        "system_to_core": resolved,
        "native_payload_checksums": records,
        "staged_core_manifest_sha256": _sha256(manifest_file),
        "dolphin_sys_present": True,
        "clean_user_core_overlay": True,
        "no_external_emulator_setup_required_in_staged_bundle": True,
        "no_runtime_core_download_required_for_fresh_bundled_lookup": True,
        "physical_installer_launch_verified": False,
        "real_gameplay_video_audio_input_verified": False,
        "all_supported_games_verified": False,
        "legal_distribution_review_complete": False,
        "approved_for_public_release": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-dir", type=Path, required=True)
    parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = check_offline_bundle(args.core_dir, args.target)
        if args.report.is_symlink():
            raise ValueError("Cannot write a report through a symlink")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        parser.exit(1, f"Offline 3.0 launch readiness NOT PROVEN: {error}\n")
    print(f"{args.target}: 18/18 real console core lookups and "
          "11/11 native checksums verified without network or external emulators; "
          "gameplay, physical QA and legal distribution remain UNAPPROVED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
