"""Execute genuinely source-modified pygame C from frozen Windows 3.1 RC1.

This is a *technical* modified-library test in a separate copied install.
Executes the newly compiled native method using CPython, then starts
the actual frozen Windows Tk desktop and independently verifies the
unmodified 18-console QA identity and isolated settings migration.
No real controller/ROM/camera or complete LGPL review is implied.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import types

from tools.build_v31_modified_pygame_probe import PROBE_VALUE
from tools.verify_v31_installed_ui_smoke import verify_installed_smoke


def run(bundle, installer, source_receipt, original_qa, smoke_file, qa_home):
    if sys.platform != "win32" or sys.version_info[:2] != (3, 13):
        raise ValueError("Actual native Windows Python 3.13 interpreter required")
    bundle, installer = Path(bundle).resolve(), Path(installer)
    smoke_file, qa_home = Path(smoke_file).resolve(), Path(qa_home).resolve()
    report = dict(source_receipt)
    if (report.get("status") != "AUTHENTIC_RC1_WINDOWS_SOURCE_MODIFIED_PYGAME_EXTENSION_STAGED_ONLY"
            or report.get("source_modified_native_is_distinct_pe_amd64") is not True
            or report.get("original_signed_installer_and_frozen_app_untouched") is not True
            or report.get("modified_native_method_executed_from_copied_app") is not False
            or report.get("stable_3_1_release_approved") is not False):
        raise ValueError("Not an independently vetted real copied Windows RC1")
    native = (bundle / report["native_replacement_path"]).resolve()
    if (not native.is_relative_to(bundle) or not native.is_file()
            or native.is_symlink()):
        raise ValueError("Modified native outside frozen copied package")
    exe = bundle/"AnythingPlays.exe"
    if not exe.is_file():
        raise ValueError("Actual frozen desktop binary missing")
    handles = []
    for directory in (bundle/"_internal",bundle/"_internal"/"pygame",
                      bundle/"_internal"/"pygame"/"__dot__dylibs",
                      bundle/"_internal"/"pygame"/"libs"):
        if directory.is_dir():
            handles.append(os.add_dll_directory(str(directory)))
    pkg = types.ModuleType("pygame")
    pkg.__path__ = [str(native.parent)]
    sys.modules["pygame"] = pkg
    spec = importlib.util.spec_from_file_location("pygame.base",native)
    if spec is None or spec.loader is None:
        raise ValueError("CPython cannot load source-modified Windows DLL")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pygame.base"] = mod
    spec.loader.exec_module(mod)
    actual = mod._ap31_relink_probe()
    if actual != PROBE_VALUE:
        raise ValueError("Source-modified pygame native method did not execute")
    report["modified_native_method_executed_from_copied_app"] = True
    print("ACTUAL CHANGED PYGAME C NATIVE METHOD EXECUTED:", actual, flush=True)
    smoke_file.parent.mkdir(parents=True,exist_ok=True)
    if smoke_file.exists() or qa_home.exists():
        raise ValueError("Smoke and user fixture must use fresh isolated paths")
    qa_home.mkdir(parents=True)
    settings = smoke_file.parent/"QA_LEGACY_SETTINGS_FIXTURE.json"
    subprocess.run(
        [sys.executable,"-m","tools.qa_v31_installed_settings_migration","seed",
         "--home",str(qa_home),"--manifest",str(settings)],
        check=True,timeout=35,
    )
    env=os.environ.copy()
    env.update({
        "HOME":str(qa_home),
        "USERPROFILE":str(qa_home),
        "SDL_AUDIODRIVER":"dummy",
        "AP_V30_UI_SMOKE_CHECK":"1",
        "AP_V30_UI_SMOKE_REPORT":str(smoke_file),
    })
    completed=subprocess.run([str(exe),"--ap-v30-ui-smoke"],cwd=bundle,
                             env=env,timeout=120)
    if completed.returncode!=0:
        raise RuntimeError("Modified-native copied frozen RC1 GUI failed: "+str(completed.returncode))
    if not smoke_file.is_file():
        raise ValueError("Frozen Tk startup report missing")
    subprocess.run(
        [sys.executable,"-m","tools.qa_v31_installed_settings_migration","verify",
         "--home",str(qa_home),"--manifest",str(settings),
         "--output",str(smoke_file.parent/"QA_STABLE_SETTINGS_PRESERVED.json")],
        check=True,timeout=35,
    )
    qa=verify_installed_smoke(
        "windows-x64", installer, bundle, original_qa,
        json.loads(smoke_file.read_text("utf-8")),
    )
    if qa["actual_mainloop_ran"] is not True or qa["console_profiles"] != 18:
        raise ValueError("Original 18-console frozen Tk startup unproven")
    report["copied_original_rc1_frozen_tk_gui_started"] = True
    report["status"] = "WINDOWS_MODIFIED_C_NATIVE_EXECUTED_AND_GENUINE_FROZEN_RC1_GUI_PASSED"
    report["all_lgpl_relinking_requirements_approved"] = False
    report["full_corresponding_source_approved"] = False
    report["stable_3_1_release_approved"] = False
    (smoke_file.parent/"QA_ORIGINAL_RC1_FROZEN_GUI_VERIFICATION.json").write_text(
        json.dumps(qa,indent=2)+"\n","utf-8")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("bundle","installer","original-receipt","staged-receipt","smoke","home","output"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args()
    report=run(
        a.bundle,a.installer,
        json.loads(a.staged_receipt.read_text("utf-8")),
        json.loads(a.original_receipt.read_text("utf-8")),
        a.smoke,a.home,
    )
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n","utf-8")
    print("PASS: real Windows source-modified native method and 18-profile frozen desktop")
    print("LGPL correspondence, physical hardware and stable release STILL OPEN")


if __name__=="__main__":
    main()
