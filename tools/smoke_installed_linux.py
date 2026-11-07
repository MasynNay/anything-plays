"""Acceptance gate for installed Linux preview: a REAL non-root Tk window.

The source checkout's GUI tests can pass while an installed .deb fails to
launch. Run this against /usr/bin/anything-plays-30-preview *after* dpkg -i,
from a regular user under xvfb-run; do not mark a package successful merely
because PyInstaller compiled or a core produced video.

Tests a fresh HOME and a previous GameCube selection. Never reads or edits
the maintainer's real preferences, ROMs or camera footage.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def run_once(executable, home, *, prior_gamecube=False, seconds=18):
    home = Path(home)
    if prior_gamecube:
        prefs = home / ".config" / "anything-plays-30-preview" / "preferences.json"
        prefs.parent.mkdir(parents=True, exist_ok=True)
        prefs.write_text(json.dumps({
            "system": "gamecube", "view_mode": "Windowed",
            "theme": "Ocean Dark", "gamecube_embedded": True,
            "rom_directories": {},
        }), encoding="utf-8")
    environment = os.environ.copy()
    environment["HOME"] = str(home)
    environment["XDG_CONFIG_HOME"] = str(home / ".config")
    environment["XDG_DATA_HOME"] = str(home / ".local" / "share")
    environment["XDG_STATE_HOME"] = str(home / ".local" / "state")
    environment["AP_V30_DISABLE_AUTO_UPDATES"] = "1"
    begun = time.monotonic()
    process = subprocess.Popen(
        [str(executable)], env=environment, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    appeared = False
    error = None
    try:
        while time.monotonic() - begun < seconds:
            if process.poll() is not None:
                error = f"preview exited early: {process.returncode}"
                break
            windows = subprocess.run(
                ["xwininfo", "-root", "-tree"], capture_output=True,
                text=True, timeout=5, check=True,
            ).stdout
            if "Anything Plays 3.0" in windows:
                appeared = True
                # A window that appears and immediately crashes isn't a pass.
                time.sleep(2.0)
                if process.poll() is not None:
                    appeared = False
                    error = f"preview crashed after opening: {process.returncode}"
                break
            time.sleep(.4)
        if not appeared and error is None:
            error = f"No Anything Plays Tk window appeared within {seconds}s"
    finally:
        process.terminate()
        try:
            log, _ = process.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill()
            log, _ = process.communicate(timeout=4)
    local_log = home / ".local" / "state" / "anything-plays-preview" / "startup.log"
    if local_log.is_file():
        log += "\nINSTALLER-STARTUP-LOG:\n" + local_log.read_text(
            encoding="utf-8", errors="replace")[-5000:]
    result = {
        "prior_gamecube": prior_gamecube,
        "gui_window_appeared": appeared,
        "elapsed_seconds": round(time.monotonic() - begun, 2),
        "error": error,
        "output_tail": log[-5000:],
        "executed_as_uid": os.getuid(),
    }
    print(json.dumps(result, indent=2), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("This installed desktop test requires Linux/X11/Xvfb")
    if os.geteuid() == 0:
        parser.error("Refusing root test: the preview must run as a normal user")
    if not os.environ.get("DISPLAY"):
        parser.error("DISPLAY is absent: run under xvfb-run")
    with tempfile.TemporaryDirectory(prefix="ap-installed-smoke-") as root:
        all_results = [
            run_once(args.executable, Path(root) / "clean"),
            run_once(args.executable, Path(root) / "existing-gamecube",
                     prior_gamecube=True),
        ]
    passed = all(x["gui_window_appeared"] for x in all_results)
    report = {"passed": passed, "installed_deb_gui": True,
              "tested_without_root": True, "results": all_results}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n",
                               encoding="utf-8")
    print("INSTALLED-LINUX-GUI:", "PASS" if passed else "FAIL", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
