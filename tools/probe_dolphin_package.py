"""Exercise an actual platform-matched Dolphin + Sys catalog ZIP through the app.

This is an isolated BUILD-HOST TEST, never a public binary approval:
1. Obtain native Dolphin Libretro plus matching Sys files into a temp folder.
2. Produce a disposable ZIP with simulated review flags.
3. Verify GitHub-asset-shaped metadata and SHA256 using in-memory ZIP bytes.
4. Activate via the exact in-app managed-core installer and launcher path.
5. Run original licensed GameCube homebrew with actual GPU/input/audio hooks.
6. Roll back and verify the active pointer is removed.

No commercial ROMs, external Dolphin executable or user's game files.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from anything_plays.core_packs import (
    RELEASE_PREFIX, _release_asset, install_core_pack, managed_core_path,
    rollback_core, target_identity,
)
from anything_plays.gamecube_software import packaged_dolphin_system_directory
from fetch_mgba_core import fetch_core
from tools.create_core_packs import create_candidate_packs
from tools.fetch_dolphin_sys import fetch_dolphin_sys

TAG = "v3.0.0-alpha.2-cores"


class LocalResponse:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, maximum):
        return self.payload[:maximum]


def run_paired_core_experiment(report, seconds=12):
    report = Path(report).resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "kind": "Dolphin complete core and Sys managed-install integration",
        "passed": False,
        "download_verified": False,
        "installed_native_core_and_sys": False,
        "actual_gamecube_homebrew_video_audio_passed": False,
        "rollback_passed": False,
        "real_gameplay_sound_verified": False,
        "real_3d_game_compatibility_verified": False,
        "real_speakers_verified": False,
        "package_approved_for_distribution": False,
        "test_approval_fields_simulated_in_temporary_build_only": True,
    }
    try:
        if not 2 <= seconds <= 40:
            raise ValueError("Bounded native runtime must be 2..40 seconds")
        with TemporaryDirectory(prefix="ap-dolphin-pack-ci-") as folder:
            root = Path(folder)
            cores, packed, managed = (
                root / "cores", root / "zip", root / "managed"
            )
            cores.mkdir()
            record = fetch_core("dolphin", destination=cores)
            (cores / "CORE_PROVENANCE.json").write_text(
                json.dumps({"cores": [record]}) + "\n"
            )
            sys_meta = fetch_dolphin_sys(cores)
            target, ext = target_identity()
            candidate = create_candidate_packs(
                cores, packed, TAG, selected=["dolphin"], target=target,
                license_reviewed=True, runtime_tested=True,
            )[0]
            archive = Path(candidate["file"]).read_bytes()
            name = _release_asset("dolphin", target)
            item = {
                "name": "dolphin", "target": target,
                "release": TAG,
                "url": RELEASE_PREFIX + TAG + "/" + name,
                "sha256": hashlib.sha256(archive).hexdigest(),
                "size": len(archive),
            }
            core_file = Path(install_core_pack(
                item, root=managed,
                opener=lambda req, timeout: LocalResponse(archive),
            ))
            result["download_verified"] = True
            root_directory = packaged_dolphin_system_directory(core_file)
            # On macOS /var is an alias for /private/var. The validated
            # system directory resolves symlinks, while the temporary file
            # path may not. Compare canonical paths, never raw strings.
            if root_directory.resolve() != core_file.parent.resolve():
                raise AssertionError("Dolphin Sys root is not next to installed core")
            if managed_core_path("dolphin", root=managed) != str(core_file):
                raise AssertionError("Active managed Dolphin core cannot be resolved")
            result["installed_native_core_and_sys"] = True
            native_report = report.with_name(report.stem + "-playback.json")
            command = [
                sys.executable, str(ROOT / "tools/probe_gamecube_app.py"),
                "--core", str(core_file), "--seconds", str(seconds),
                "--report", str(native_report),
            ]
            played = subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True,
                timeout=seconds + 50, check=False,
            )
            result["native_exit_code"] = played.returncode
            result["native_console_tail"] = (
                played.stdout + "\n" + played.stderr
            )[-4000:]
            if native_report.is_file():
                result["native_report"] = json.loads(native_report.read_text())
            result["actual_gamecube_homebrew_video_audio_passed"] = (
                played.returncode == 0
                and result.get("native_report", {}).get("passed") is True
            )
            if not result["actual_gamecube_homebrew_video_audio_passed"]:
                raise AssertionError("Installed Dolphin failed native GameCube playback")
            if not rollback_core("dolphin", root=managed):
                raise AssertionError("Cannot roll back paired GameCube core")
            if managed_core_path("dolphin", root=managed) is not None:
                raise AssertionError("GameCube installed core still active after rollback")
            if not core_file.is_file():
                raise AssertionError("Rollback must preserve immutable installed binary")
            result["rollback_passed"] = True
            result["sys_file_count"] = sys_meta["file_count"]
        result["passed"] = True
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)
    return result["passed"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--seconds", type=int, default=12)
    args = parser.parse_args(argv)
    return 0 if run_paired_core_experiment(
        args.report, seconds=args.seconds
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
