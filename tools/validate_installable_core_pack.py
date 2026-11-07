"""Prove a 2.1 optional emulator pack can install and run entirely in-app.

CI-only: independently downloads a core, prepares a synthetic official-release
request around its *exact* ZIP bytes, then installs using the same verified
core-pack installer as the GUI. Attestation fields are intentionally set in
the isolated temporary fixture only, never in a published download.
The test runs an original video+audio ROM against the installed object and
then verifies rollback. Nothing is posted to a GitHub release or installed
in a user's actual Anything Plays profile.

This is an integration verification, NOT a license-review or release approval.
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
    PACK_PREFIX, RELEASE_PREFIX, install_core_pack,
    managed_core_path, rollback_core, target_identity
)
from fetch_mgba_core import fetch_core
from tools.create_core_packs import create_candidate_packs

RUNNABLE_TESTS = {
    "fceumm": "tools/probe_nes_homebrew.py",
    "stella2014": "tools/probe_atari_homebrew.py",
}
TAG = "v2.1.0-alpha.2"


class LocalAssetResponse:
    def __init__(self, data):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False

    def read(self, size):
        return self._data[:size]


def run_integration(core, result_path, *, seconds=8):
    if core not in RUNNABLE_TESTS:
        raise ValueError("End-to-end runtime fixture not available: " + str(core))
    result_path = Path(result_path).resolve()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "core": core, "passed": False, "real_core_downloaded": False,
        "test_pack_installed": False, "video_audio_probe_passed": False,
        "rollback_passed": False,
        "qa_notices": [
            "Temporary test attestations are not license or release approval",
            "Audio samples captured, no physical speakers were tested",
        ],
    }
    try:
        with TemporaryDirectory(prefix="ap-v21-pack-install-test-") as temp:
            root = Path(temp)
            cores, packs, managed = (
                root / "cores", root / "pack-zip", root / "managed"
            )
            cores.mkdir()
            record = fetch_core(core, destination=cores)
            (cores / "CORE_PROVENANCE.json").write_text(
                json.dumps({"cores": [record]}) + "\n", encoding="utf-8"
            )
            result["real_core_downloaded"] = True
            target, extension = target_identity()
            summaries = create_candidate_packs(
                cores, packs, TAG, selected=[core], target=target,
                # Simulates the *shape* of a future approved pack. These
                # fields are never uploaded as an actual release attestation.
                license_reviewed=True, runtime_tested=True,
            )
            archive = Path(summaries[0]["file"]).read_bytes()
            asset_name = f"{PACK_PREFIX}{core}-{target}.zip"
            item = {
                "name": core, "target": target, "release": TAG,
                "url": RELEASE_PREFIX + TAG + "/" + asset_name,
                "sha256": hashlib.sha256(archive).hexdigest(),
                "size": len(archive),
            }
            def fake_github_asset(req, timeout):
                if req.full_url != item["url"]:
                    raise ValueError("Unexpected non-project download URL")
                return LocalAssetResponse(archive)
            installed = Path(
                install_core_pack(item, root=managed,
                                  opener=fake_github_asset)
            )
            expected = cores / f"{core}_libretro{extension}"
            if (not installed.is_file()
                    or installed.read_bytes() != expected.read_bytes()):
                raise AssertionError("Installed core differs from downloaded core")
            if managed_core_path(core, root=managed) != str(installed):
                raise AssertionError("Core locator cannot resolve installed pack")
            result["test_pack_installed"] = True
            probe_path = result_path.with_name(
                result_path.stem + "-native-playback.json"
            )
            run = subprocess.run(
                [
                    sys.executable, str(ROOT / RUNNABLE_TESTS[core]),
                    "--core", str(installed), "--report", str(probe_path),
                    "--seconds", str(seconds),
                ],
                cwd=ROOT, check=False, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True,
                timeout=seconds + 50,
            )
            result["playback_exit_code"] = run.returncode
            result["playback_log_tail"] = run.stdout[-2500:]
            if probe_path.is_file():
                result["playback_report"] = json.loads(
                    probe_path.read_text(encoding="utf-8")
                )
            result["video_audio_probe_passed"] = (
                run.returncode == 0
                and result.get("playback_report", {}).get("passed") is True
            )
            if not result["video_audio_probe_passed"]:
                raise AssertionError("Installed emulator failed native video/audio")
            if not rollback_core(core, root=managed):
                raise AssertionError("Rollback did not remove active install")
            if managed_core_path(core, root=managed) is not None:
                raise AssertionError("Core still active after rollback")
            if not installed.is_file():
                raise AssertionError("Rollback destroyed immutable core object")
            result["rollback_passed"] = True
        result["passed"] = True
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        result_path.write_text(json.dumps(result, indent=2) + "\n",
                               encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
    return result["passed"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", choices=tuple(RUNNABLE_TESTS), required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=8)
    args = parser.parse_args(argv)
    if not 2 <= args.seconds <= 30:
        parser.error("--seconds must be between 2 and 30")
    return 0 if run_integration(args.core, args.report, seconds=args.seconds) else 1


if __name__ == "__main__":
    raise SystemExit(main())
