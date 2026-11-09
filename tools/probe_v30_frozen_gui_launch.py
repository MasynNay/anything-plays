"""Launch the ACTUAL frozen Anything Plays GUI and verify its Tk startup.

Unlike core-only A/V tests, this executes the PyInstaller desktop executable
produced inside the complete 18-console/11-core offline installer. It uses an
explicit test-only CLI flag to close the real initialized Tk window after
entering the event loop. Windows/macOS invoke their genuine GUI executables,
Linux runs in a virtual display in CI. Never distribute the unapproved build.

A passing result is narrowly "installed desktop app opens and renders a
configured Tk UI"; no physical camera, gameplay, signed installer, legal rights,
long-run stability or complete end-user installation is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

BINARIES = {
    "windows-x64": Path("dist/AnythingPlays/AnythingPlays.exe"),
    "linux-x64": Path("dist/AnythingPlays/AnythingPlays"),
    "macos-arm64": Path("dist/AnythingPlays30Preview.app/Contents/MacOS/AnythingPlays"),
    "macos-x64": Path("dist/AnythingPlays30Preview.app/Contents/MacOS/AnythingPlays"),
}
STATUS = "UNAPPROVED-3.0-INSTALLED-FROZEN-DESKTOP-LAUNCH-EVIDENCE"


def prove_frozen_window(target, report):
    if target not in BINARIES:
        raise ValueError("Unsupported actual installed desktop target")
    report=Path(report)
    if report.exists() or report.is_symlink():
        raise ValueError("Original GUI launch report must not already exist")
    binary=BINARIES[target]
    if (binary.is_symlink() or not binary.is_file()
            or not 80000 < binary.stat().st_size < 250 * 1024 * 1024):
        raise ValueError("Missing actual frozen PyInstaller GUI executable")
    program_hash=hashlib.sha256(binary.read_bytes()).hexdigest()
    outcome={
        "schema_version":1,
        "status":STATUS,
        "target":target,
        "actual_frozen_binary":str(binary),
        "actual_frozen_binary_sha256":program_hash,
        "passed":False,
        "frozen_ui_initialized":False,
        "original_console_profiles":0,
        "camera_hardware_tested":False,
        "physical_qa_approved":False,
        "license_review_approved":False,
        "public_binary_distribution_approved":False,
        "native_exit_code":None,
        "timed_out":False,
        "error":None,
    }
    with tempfile.TemporaryDirectory(prefix="ap-v30-actual-frozen-window-") as temporary:
        root=Path(temporary)
        child=root/"ORIGINAL_TK_DESKTOP_WINDOW.json"
        env=os.environ.copy()
        env["AP_V30_UI_SMOKE_CHECK"]="1"
        env["AP_V30_UI_SMOKE_REPORT"]=str(child.resolve())
        # Separate temporary settings from user/CI profile, while retaining
        # PATH and platform DLL lookup for the genuine bundled executable.
        env["HOME"]=str(root.resolve())
        env["XDG_CONFIG_HOME"]=str((root/"config").resolve())
        if os.name=="nt":
            env["APPDATA"]=str((root/"AppData").resolve())
            env["LOCALAPPDATA"]=str((root/"LocalAppData").resolve())
        try:
            childproc=subprocess.run(
                [str(binary.resolve()),"--ap-v30-ui-smoke"],
                env=env,capture_output=True,text=True,
                timeout=70,check=False,errors="replace")
            outcome["native_exit_code"]=childproc.returncode
            outcome["console_tail"]=(childproc.stdout+"\n"+childproc.stderr)[-5000:]
        except subprocess.TimeoutExpired as err:
            outcome["timed_out"]=True
            payload=err.stderr or b""
            outcome["console_tail"]=(payload.decode("utf-8","replace")
                                     if isinstance(payload,bytes) else payload)[-5000:]
        except OSError as err:
            outcome["error"]=f"{type(err).__name__}: {err}"
        if child.is_file() and not child.is_symlink() and child.stat().st_size<32*1024:
            try:
                evidence=json.loads(child.read_text("utf-8"))
                outcome["child_original_tk_report"]=evidence
                outcome["frozen_ui_initialized"]=(evidence.get("actual_app_initialized") is True
                    and evidence.get("actual_tk_mainloop_ran") is True
                    and evidence.get("actual_tk_window_started") is True
                    and evidence.get("frozen_binary") is True)
                outcome["original_console_profiles"]=evidence.get("console_profile_count",0)
                outcome["passed"]=(
                    outcome["native_exit_code"]==0
                    and outcome["frozen_ui_initialized"] is True
                    and outcome["original_console_profiles"]==18
                    and evidence.get("passed") is True
                    and evidence.get("camera_hardware_tested") is False
                    and evidence.get("physical_qa_approved") is False
                    and evidence.get("public_distribution_approved") is False)
            except (OSError,ValueError,TypeError) as err:
                outcome["error"]=f"Invalid original frozen UI report: {err}"
        else:
            outcome["error"]=outcome["error"] or (
                "Actual frozen UI did not write a valid original Tk initialization result")
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(outcome,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return outcome


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target",choices=tuple(BINARIES),required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        result=prove_frozen_window(args.target,args.report)
    except (ValueError,OSError) as err:
        p.exit(1,f"REAL DESKTOP UI COLD LAUNCH BLOCKED: {err}\n")
    print(json.dumps({key:result[key] for key in (
        "status","target","passed","frozen_ui_initialized","native_exit_code",
        "original_console_profiles","error")},indent=2))
    if not result["passed"]:
        print(result.get("console_tail","")[-2000:],file=sys.stderr)
    return 0 if result["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
