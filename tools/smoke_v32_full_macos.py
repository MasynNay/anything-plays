"""Exercise the ACTUAL mounted private full-core 3.2 macOS frozen GUI.

The existing minimal-preview setup smoke intentionally expects SNES to be
unbundled. Do NOT reuse that test for the full 11-core variant: this test
instead checks the correct 18-profile installed GUI, preview identity,
public-settings canaries and honest unapproved-native receipt.
"""
import argparse
import json
from pathlib import Path
import os
import subprocess
import tempfile

from tools.assemble_v31_full_macos import mount
from tools.stage_v32_full_linux import sha256
from tools.stage_v32_full_macos import STATUS, names, verify_identity
from tools.verify_v32_installed_gui import STABLE_DIR, STABLE_FILES, seed


def verify(arch, dmg, receipt, source_sha, output):
    _, _, full_name = names(arch)
    dmg, receipt, output = Path(dmg), Path(receipt), Path(output)
    if (dmg.name != full_name or not dmg.is_file() or dmg.is_symlink()
            or not receipt.is_file() or receipt.is_symlink()
            or output.exists() or output.is_symlink()):
        raise ValueError("Missing or unsafe full Mac native QA smoke inputs")
    data = json.loads(receipt.read_text("utf-8"))
    expected = {
        "status": STATUS, "installer": full_name,
        "installer_sha256": sha256(dmg),
        "target": f"macos-{arch}", "source_revision": source_sha,
        "settings_namespace": "anything-plays-32-preview",
        "native_core_count": 11, "console_profiles": 18,
        "native_core_bytes_preserved": True,
        "public_release_approved": False,
        "all_18_consoles_gameplay_verified": False,
        "notarized": False,
    }
    if any(type(data.get(k)) is not type(value) or data.get(k) != value
           for k, value in expected.items()):
        raise ValueError("Full Mac QA receipt is not authentic or overstates approval")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"ap32-fullgui-{arch}-") as td:
        temp = Path(td)
        home = temp/"home"
        home.mkdir()
        seed(home)
        with mount(dmg, temp/"mounted"):
            app = temp/"mounted/AnythingPlays32Preview.app"
            verify_identity(app)
            subprocess.run(
                ["codesign", "--verify", "--verbose=2", str(app)],
                check=True, timeout=90,
            )
            executable = app/"Contents/MacOS/AnythingPlays"
            if not executable.is_file() or not os.access(executable, os.X_OK):
                raise ValueError("No executable in actual mounted 3.2 full Mac DMG")
            report_path = temp/"gui-result.json"
            env = dict(os.environ)
            env.update({
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home/".config"),
                "AP_V30_UI_SMOKE_CHECK": "1",
                "AP_V32_GUI_SMOKE_CHECK": "1",
                # This installed variant bundles SNES; the mGBA-only
                # setup smoke intentionally asserts that SNES is absent.
                "AP_V32_SETUP_SMOKE_CHECK": "0",
                "AP_V30_UI_SMOKE_REPORT": str(report_path),
                "SDL_AUDIODRIVER": "dummy",
                "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            })
            result = subprocess.run(
                [str(executable), "--ap-v30-ui-smoke"],
                env=env, text=True, capture_output=True, timeout=120,
            )
            if result.returncode:
                raise ValueError(
                    "Mounted full-native Mac GUI failed (exit "
                    + str(result.returncode) + "): "
                    + (result.stderr or "")[-2400:]
                )
            if not report_path.is_file() or report_path.is_symlink():
                raise ValueError("Mounted real 3.2 GUI did not create a smoke report")
            smoke = json.loads(report_path.read_text("utf-8"))
            checks = (
                "passed", "actual_tk_window_started",
                "actual_app_initialized", "actual_tk_mainloop_ran",
                "frozen_binary", "v32_frozen_isolation_verified",
            )
            if (not isinstance(smoke, dict)
                    or any(smoke.get(key) is not True for key in checks)
                    or smoke.get("console_profile_count") != 18
                    or smoke.get("v32_settings_namespace")
                    != "anything-plays-32-preview"
                    or smoke.get("public_distribution_approved") is not False
                    or smoke.get("camera_hardware_tested") is not False
                    or smoke.get("gameplay_hardware_tested") is not False):
                raise ValueError("Mounted full-native Mac GUI overclaimed or failed QA")
            stable = home/STABLE_DIR
            for name, before in STABLE_FILES.items():
                if (stable/name).read_bytes() != before:
                    raise ValueError("Full Mac 3.2 QA changed old stable settings")
            if not (home/".config/anything-plays-32-preview").is_dir():
                raise ValueError("Mounted Mac 3.2 QA did not use preview settings")
        # Emit only the allowlisted safe fields, never local home paths,
        # camera identifiers or the names of a user's game files.
        report = {
            "schema_version": 1,
            "target": f"macos-{arch}",
            "status": "PASSED_PRIVATE_V32_FULL_MACOS_REAL_FROZEN_GUI_NOT_RELEASE",
            "source_revision": source_sha,
            "installer_sha256": sha256(dmg),
            "actual_mounted_frozen_gui_started": True,
            "console_profiles": 18,
            "native_core_count": 11,
            "stable_settings_unchanged": True,
            "private_preview_identity_verified": True,
            "public_release_approved": False,
            "physical_camera_tested": False,
            "physical_controller_tested": False,
            "all_18_consoles_gameplay_verified": False,
            "notarized": False,
        }
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
        return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arch", choices=("arm64", "x64"), required=True)
    p.add_argument("--installer", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(
        verify(args.arch, args.installer, args.receipt, args.source_sha,
               args.output), indent=2, sort_keys=True,
    ))


if __name__ == "__main__":
    main()
