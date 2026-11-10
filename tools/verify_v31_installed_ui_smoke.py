"""Verify the actual, unpacked 3.1 full RC1 ran its frozen desktop UI.

The frozen app's existing --ap-v30-ui-smoke diagnostic is reused as
implemented in the pinned 3.1 source-app binary. It opens the actual Tk
window and runs one event-loop interval. This does *not* test a physical
camera, gamepad, game ROM, save, audio or complete licensing compliance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.verify_v31_rc import validate_staged_identity

SOURCE_COMMIT = "cdbd647fa8ef3f3db0a8d419f0396f6b191599d6"
TARGETS = {
    "linux-x64": ("UNRELEASED_3_1_FULL_LINUX_RC1_QA",
                  "anything-plays-31-rc1_3.1.0~rc1full_amd64.deb"),
    "windows-x64": ("UNRELEASED_3_1_FULL_WINDOWS_RC1_QA",
                    "AnythingPlaysSetup-3.1.0-rc1-full.exe"),
    "macos-arm64": ("UNRELEASED_3_1_FULL_MACOS_RC1_QA",
                    "AnythingPlays-3.1.0-rc1-full-macos-arm64.dmg"),
    "macos-x64": ("UNRELEASED_3_1_FULL_MACOS_RC1_QA",
                  "AnythingPlays-3.1.0-rc1-full-macos-x64.dmg"),
}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as binary:
        for block in iter(lambda: binary.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_installed_smoke(target, installer, bundle, receipt, smoke):
    if target not in TARGETS:
        raise ValueError("Unreviewed QA target")
    state, filename = TARGETS[target]
    installer, bundle = Path(installer), Path(bundle)
    if (installer.name != filename or not installer.is_file()
            or installer.is_symlink()):
        raise ValueError("Missing complete RC1 QA installer")
    if (receipt.get("target", target) != target
            or receipt.get("status") != state
            or receipt.get("installer") != filename
            or receipt.get("source_preview_revision") != SOURCE_COMMIT
            or receipt.get("sha256") != sha256(installer)
            or receipt.get("native_core_count") != 11
            or receipt.get("console_profiles") != 18
            or receipt.get("public_release_approved") is not False
            or receipt.get("final_release_approved") is not False):
        raise ValueError("UI smoke input does not match pinned 18-console RC1")
    marker = validate_staged_identity(bundle)
    if (smoke.get("status") != "UNAPPROVED-3.0-INSTALLED-DESKTOP-STARTUP-CHECK"
            or smoke.get("passed") is not True
            or smoke.get("actual_tk_window_started") is not True
            or smoke.get("actual_app_initialized") is not True
            or smoke.get("actual_tk_mainloop_ran") is not True
            or smoke.get("frozen_binary") is not True
            or smoke.get("console_profile_count") != 18
            or not isinstance(smoke.get("top_level_widgets"), int)
            or smoke["top_level_widgets"] < 1
            or not isinstance(smoke.get("initialized_system"), str)
            or smoke.get("error") is not None
            or smoke.get("camera_hardware_tested") is not False
            or smoke.get("gameplay_hardware_tested") is not False
            or smoke.get("physical_qa_approved") is not False
            or smoke.get("public_distribution_approved") is not False):
        raise ValueError("Actual RC1 frozen GUI startup failed or overstated acceptance")
    return {
        "schema_version": 1,
        "status": "UNRELEASED_3_1_RC1_INSTALLED_FROZEN_DESKTOP_SMOKE_PASSED",
        "target": target,
        "installer": filename,
        "installer_sha256": sha256(installer),
        "source_app_commit": SOURCE_COMMIT,
        "embedded_app_identity_marker": marker,
        "actual_tk_startup": True,
        "actual_app_initialized": True,
        "actual_mainloop_ran": True,
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
    p.add_argument("--target", choices=sorted(TARGETS), required=True)
    for key in ("installer", "bundle", "receipt", "smoke", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    for name in ("smoke", "receipt"):
        path = getattr(a, name)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
            p.error("Missing or unsafe " + name + " report")
    result = verify_installed_smoke(
        a.target, a.installer, a.bundle,
        json.loads(a.receipt.read_text("utf-8")),
        json.loads(a.smoke.read_text("utf-8")),
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    print(a.target, "actual frozen app Tk startup verified, 18 profiles; "
          "hardware and licensing remain unapproved")


if __name__ == "__main__":
    main()
