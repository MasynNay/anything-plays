"""Launch the real full 3.1.1 installed desktop on each native CI host.

Uses a disposable HOME and original OS installer unpack/mount on the matching
native runner. Actual Tk and Stream Mode run in the frozen binary. This is
not a physical camera/controller/retail-ROM test or a release approval.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch

from tools.probe_v30_installed_desktop_window import run as run_frozen_window
from tools.verify_v31_rc import validate_staged_identity
from tools.verify_v311_installed_smoke import verify
from tools.verify_v311_stable_source_stage import INSTALLERS
from tools.assemble_v31_full_windows import unpack, source_app
from tools.assemble_v31_full_macos import mount


def launch(target, installer, receipt, source_sha, output):
    if target not in INSTALLERS:
        raise ValueError("Unsupported native 3.1.1 installed OS")
    installer, receipt, output = map(Path, (installer, receipt, output))
    if (installer.name != INSTALLERS[target]
            or not installer.is_file() or installer.is_symlink()
            or installer.stat().st_size < 1024 * 1024):
        raise ValueError("Not a real stable 3.1.1 native installer")
    if output.exists() or output.is_symlink():
        raise ValueError("Refusing to replace prior installed-desktop evidence")
    if (not receipt.is_file() or receipt.is_symlink()
            or not 0 < receipt.stat().st_size < 1024 * 1024):
        raise ValueError("Original installed core/source QA receipt missing")
    receipt_data = json.loads(receipt.read_text("utf-8"))
    if not isinstance(receipt_data, dict):
        raise ValueError("Original full assembler receipt must be an object")
    # Fail early on a one-core source stage before unpacking anything.
    if (receipt_data.get("identity_channel") != "v311_stable_candidate"
            or receipt_data.get("native_core_count") != 11
            or receipt_data.get("console_profiles") != 18
            or receipt_data.get("public_release_approved") is not False):
        raise ValueError("Not a previously verified full stable 3.1.1 package")
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="anything-plays-311-gui-") as temp:
        temp = Path(temp)
        extracted = temp / "installed"
        home = temp / "synthetic-home"
        home.mkdir()
        if target == "linux-x64":
            subprocess.run(["dpkg-deb", "-x", str(installer.resolve()),
                            str(extracted)], check=True, timeout=120)
            app = extracted / "opt" / "anything-plays-31"
            binary = app / "AnythingPlays"
        elif target == "windows-x64":
            unpack(installer.resolve(), extracted)
            app = source_app(extracted, "AnythingPlays.exe")
            binary = app / "AnythingPlays.exe"
        else:
            with mount(installer.resolve(), temp / "mounted"):
                source = temp / "mounted" / "AnythingPlays31.app"
                if not source.is_dir() or source.is_symlink():
                    raise ValueError("Mounted stable Mac 3.1.1 DMG lacks reviewed app")
                shutil.copytree(source, extracted / "AnythingPlays31.app",
                                symlinks=True)
            app = extracted / "AnythingPlays31.app"
            binary = app / "Contents" / "MacOS" / "AnythingPlays"
            subprocess.run(["codesign", "--verify", "--verbose=2", str(app)],
                           check=True, timeout=45)
        validate_staged_identity(app, channel="v311_stable_candidate")
        if not binary.is_file() or binary.is_symlink():
            raise ValueError("Genuine installed frozen 3.1.1 executable missing")
        smoke_path = output / "V311_ACTUAL_FROZEN_TK_SMOKE.json"
        env = {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "AP_V31_STREAM_SMOKE_CHECK": "1",
            "AP_RELEASE_BUILD": "0",
            "AP_V30_APPROVED_RELEASE": "0",
            "SDL_AUDIODRIVER": "dummy",
            "PYTHONUNBUFFERED": "1",
        }
        # The real frozen executable is launched synchronously, with a fresh
        # disposable HOME. Do not copy any source/fixture ROMs or user files.
        with patch.dict(os.environ, env):
            real_smoke = run_frozen_window(target, binary, smoke_path, timeout=110)
        receipt_result = verify(target, installer, app, receipt_data,
                                real_smoke, source_sha)
        path = output / "V311_INSTALLED_FULL_GUI_RECEIPT.json"
        path.write_text(json.dumps(receipt_result, indent=2) + "\n", "utf-8")
        return receipt_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=tuple(INSTALLERS))
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args=parser.parse_args()
    result=launch(args.target, args.installer, args.receipt, args.source_sha,
                  args.output)
    print("Validated REAL installed frozen 3.1.1 Stream Mode:",
          result["target"],"11 source cores, NOT public or physical QA")


if __name__ == "__main__":
    main()
