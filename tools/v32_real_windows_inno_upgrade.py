"""Execute actual 3.1.1 -> 3.2 Windows Inno setups in a disposable CI home.

Unpacking two Inno payloads into the same folder is NOT an installer
upgrade: it bypasses installer identity, registry and replacement logic.
This runner-only harness executes the ORIGINAL setup binaries, validates
each frozen embedded marker and records a narrowly scoped private receipt.
Never run against an end user's Windows account or installation directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from anything_plays.build_identity import make_identity
from tools.verify_v31_rc import validate_staged_identity

ORIGINAL = "AnythingPlaysSetup-3.1.1.exe"
CANDIDATE = "AnythingPlaysSetup-3.2.0-fullupgradeqa1-PRIVATE-UPGRADE-QA.exe"
STATUS = "PRIVATE_3_2_ACTUAL_WINDOWS_INNO_311_TO_320_UPGRADE_QA_NOT_RELEASE"


def installation_arguments(installer, destination, log):
    """The same install directory is passed to both actual Inno executables."""
    return [
        str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES",
        "/NORESTART", "/SP-", "/CURRENTUSER", "/NOICONS",
        "/DIR=" + str(destination), "/LOG=" + str(log),
    ]


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run_inno_upgrade(old_setup, new_setup, installation, runner_temp, source_sha):
    if (sys.platform != "win32" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("AP_V32_STABLE_CANDIDATE") != "1"
            or os.environ.get("AP_RELEASE_BUILD") == "1"):
        raise ValueError("Real Inno upgrade may run only inside private Windows CI")
    if not isinstance(source_sha, str) or re.fullmatch("[0-9a-f]{40}", source_sha) is None:
        raise ValueError("Full source SHA required")
    old_setup = Path(old_setup).resolve(strict=True)
    new_setup = Path(new_setup).resolve(strict=True)
    if (old_setup.name != ORIGINAL or new_setup.name != CANDIDATE
            or any(p.is_symlink() or not p.is_file()
                   or p.stat().st_size <= 1024 * 1024
                   for p in (old_setup, new_setup))):
        raise ValueError("Real Inno source installers must match pinned CI names")
    runner_temp = Path(runner_temp).resolve(strict=True)
    installation = Path(installation).resolve()
    if (runner_temp == installation
            or not installation.is_relative_to(runner_temp)
            or not runner_temp.is_dir()
            or (installation.exists()
                and (not installation.is_dir() or any(installation.iterdir())))):
        raise ValueError("Refuse installation outside a fresh disposable CI folder")
    installation.parent.mkdir(parents=True, exist_ok=True)
    if make_identity("v311_stable_candidate")["settings_namespace"] != (
            make_identity("v32_stable_candidate")["settings_namespace"]):
        raise ValueError("Stable settings namespaces must match")

    prior_digest = None
    log_dir = installation.parent / "inno-qa-logs"
    log_dir.mkdir(exist_ok=True)
    for label, setup, channel in (
        ("311", old_setup, "v311_stable_candidate"),
        ("320", new_setup, "v32_stable_candidate"),
    ):
        command = installation_arguments(
            setup, installation, log_dir / (label + ".log")
        )
        # This is the actual installer EXE, not an extracted Inno payload.
        subprocess.run(command, check=True, timeout=420)
        installed_exe = installation / "AnythingPlays.exe"
        if not installed_exe.is_file() or installed_exe.is_symlink():
            raise ValueError("Inno setup did not install an executable")
        validate_staged_identity(installation, channel=channel)
        digest = _sha256(installed_exe)
        if label == "311":
            prior_digest = digest
        elif digest == prior_digest:
            raise ValueError("Inno 3.2 setup did not replace the original EXE")

    uninstallers = sorted(installation.glob("unins*.exe"))
    if not any(p.is_file() and not p.is_symlink() for p in uninstallers):
        raise ValueError("Actual Inno installation did not register its uninstaller")
    return {
        "schema_version": 1,
        "status": STATUS,
        "source_revision": source_sha,
        "old_version": "3.1.1",
        "new_version": "3.2.0",
        "old_and_new_installers_executed": True,
        "same_disposable_directory": True,
        "real_inno_uninstaller_present": True,
        "old_executable_replaced": True,
        "old_exe_sha256": prior_digest,
        "new_exe_sha256": _sha256(installation / "AnythingPlays.exe"),
        "real_user_save_game_tested": False,
        "hardware_tested": False,
        "public_release_approved": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--old-installer", type=Path, required=True)
    p.add_argument("--new-installer", type=Path, required=True)
    p.add_argument("--installation", type=Path, required=True)
    p.add_argument("--runner-temp", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(argv)
    report = run_inno_upgrade(
        a.old_installer, a.new_installer, a.installation, a.runner_temp,
        a.source_sha,
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    print("Executed original Inno 3.1.1 and full-native 3.2 installers in CI: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
