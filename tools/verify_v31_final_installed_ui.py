"""Verify real installed final 3.1.0 18-console Tk startup against original QA receipts.

No success here authorizes a public 3.1 release, claims real hardware support,
or substitutes for complete LGPL native corresponding-source obligations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.verify_v31_rc import validate_staged_identity
from tools.v31_final_source import FULL_STATUS

FILENAMES = {
    "linux-x64": "anything-plays-31_3.1.0_amd64.deb",
    "windows-x64": "AnythingPlaysSetup-3.1.0.exe",
    "macos-arm64": "AnythingPlays-3.1.0-macos-arm64.dmg",
    "macos-x64": "AnythingPlays-3.1.0-macos-x64.dmg",
}
SMOKE_STATUS = "UNAPPROVED-3.0-INSTALLED-DESKTOP-STARTUP-CHECK"


def hash_file(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verify_installed_final(target, installer, bundle, receipt, smoke, source_sha):
    if target not in FILENAMES:
        raise ValueError("Unreviewed final 3.1.0 desktop QA target")
    if not isinstance(source_sha, str) or not re.fullmatch(r"[a-f0-9]{40}", source_sha):
        raise ValueError("final 3.1.0 installed QA must have exact source head revision")
    installer, bundle = Path(installer), Path(bundle)
    filename = FILENAMES[target]
    if (installer.name != filename or not installer.is_file()
            or installer.is_symlink() or installer.stat().st_size < 1024 * 1024):
        raise ValueError("Missing or incorrectly named final 3.1.0 full installer")
    digest = hash_file(installer)
    expected = {
        "status": FULL_STATUS,
        "target": target,
        "installer": filename,
        "sha256": digest,
        "source_preview_revision": source_sha,
        "identity_channel": "final_candidate",
        "settings_namespace": "anything-plays-31",
        "native_core_count": 11,
        "console_profiles": 18,
        "public_release_approved": False,
        "final_release_approved": False,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ValueError("final 3.1.0 18-console installer receipt invalid: " + key)
    marker = validate_staged_identity(bundle, channel="final_candidate")
    observed = {
        "status": SMOKE_STATUS,
        "passed": True,
        "actual_tk_window_started": True,
        "actual_app_initialized": True,
        "actual_tk_mainloop_ran": True,
        "frozen_binary": True,
        "console_profile_count": 18,
        "stream_output_window_opened": True,
        "stream_settings_separate": True,
        "stream_appearance_configured": True,
        "stream_camera_reference_rendered": True,
        "stream_closed_cleanly": True,
        "error": None,
        "camera_hardware_tested": False,
        "gameplay_hardware_tested": False,
        "physical_qa_approved": False,
        "public_distribution_approved": False,
    }
    for key, value in observed.items():
        if smoke.get(key) != value:
            raise ValueError("Actual final 3.1.0 frozen Tk smoke failed or overstated QA: " + key)
    if (not isinstance(smoke.get("top_level_widgets"), int)
            or smoke["top_level_widgets"] < 1
            or not isinstance(smoke.get("initialized_system"), str)
            or not smoke["initialized_system"]):
        raise ValueError("final 3.1.0 smoke has no real window or system initialization")
    return {
        "schema_version": 1,
        "status": "PASSED_FINAL_REAL_FROZEN_TK_STARTUP_QA_ONLY",
        "target": target,
        "installer": filename,
        "installer_sha256": digest,
        "source_revision": source_sha,
        "embedded_final_marker": marker,
        "actual_tk_window_started": True,
        "actual_app_initialized": True,
        "actual_tk_mainloop_ran": True,
        "stream_output_window_opened": True,
        "stream_appearance_configured": True,
        "stream_closed_cleanly": True,
        "console_profiles": 18,
        "native_core_count": 11,
        "camera_hardware_verified": False,
        "physical_controller_verified": False,
        "gameplay_verified": False,
        "relinking_reviewed": False,
        "public_release_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", choices=sorted(FILENAMES), required=True)
    p.add_argument("--source-sha", required=True)
    for arg in ("installer", "bundle", "receipt", "smoke", "output"):
        p.add_argument("--" + arg, type=Path, required=True)
    args = p.parse_args()
    reports = {}
    for name in ("receipt", "smoke"):
        path = getattr(args, name)
        if (path.is_symlink() or not path.is_file()
                or path.stat().st_size > 1024 * 1024):
            p.error("final 3.1.0 QA report missing or invalid: " + name)
        reports[name] = json.loads(path.read_text("utf-8"))
    report = verify_installed_final(
        args.target, args.installer, args.bundle,
        reports["receipt"], reports["smoke"], args.source_sha,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print(report["target"], "frozen final 3.1.0 GUI 18-console startup verified; hardware and licenses open")


if __name__ == "__main__":
    main()
