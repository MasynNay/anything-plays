"""Stage four authentic 3.1.0 installers for private release review.

This tool does not publish releases, approve distribution, amend licenses, or
turn automated GUI acceptance into physical camera/controller testing.
It verifies byte-for-byte installer integrity, exact source provenance and
installed frozen-GUI/Stream Mode results on all four platforms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

TARGETS = {
    "linux-x64": ("anything-plays-31_3.1.0_amd64.deb", "FULL_LIBRARY_QA_RECEIPT.json"),
    "windows-x64": ("AnythingPlaysSetup-3.1.0.exe", "FULL_WINDOWS_QA_RECEIPT.json"),
    "macos-arm64": ("AnythingPlays-3.1.0-macos-arm64.dmg", "FULL_MACOS_QA_RECEIPT.json"),
    "macos-x64": ("AnythingPlays-3.1.0-macos-x64.dmg", "FULL_MACOS_QA_RECEIPT.json"),
}
FULL_STATUS = "PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA"
INSTALLED_STATUS = "PASSED_FINAL_REAL_FROZEN_TK_STARTUP_QA_ONLY"
CLEAN_SOURCE_RECEIPT = "FINAL_CAMERA_ONLY_OPENCV_SOURCE_QA.json"
OPENCV_ORIGINAL_SOURCE_SHA = "4afa2ea1214453648be88259f035712454faa9039b686de7753569ba8eec1577"


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_receipt(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Missing, linked or oversized QA receipt: " + path.name)
    value=json.loads(path.read_text("utf-8"))
    if not isinstance(value,dict):
        raise ValueError("Source/installed receipt must be a JSON object")
    return value


def validate(entry, expected, target):
    for key,value in expected.items():
        if type(entry.get(key)) is not type(value) or entry.get(key)!=value:
            raise ValueError("Invalid final QA receipt for " + target + ": " + key)


def stage(full_root, installed_root, output, *, source_sha, qa_run_id):
    """Verify all four OSes before creating even a private staged directory."""
    full_root,installed_root,output=map(Path,(full_root,installed_root,output))
    if (not isinstance(source_sha,str) or re.fullmatch(r"[a-f0-9]{40}",source_sha) is None
            or not isinstance(qa_run_id,int) or isinstance(qa_run_id,bool) or qa_run_id<1):
        raise ValueError("Source SHA and completed workflow run ID required")
    if (output.exists() or output.is_symlink() or not full_root.is_dir()
            or not installed_root.is_dir() or full_root.is_symlink()
            or installed_root.is_symlink()):
        raise ValueError("Review output must be new and both source roots regular directories")
    found={}
    clean_wheels={}
    for target,(filename,report_name) in TARGETS.items():
        full=full_root/target
        installed=installed_root/target
        if any(not p.is_dir() or p.is_symlink() for p in (full,installed)):
            raise ValueError("Missing independent platform QA: "+target)
        installer=full/filename
        if (not installer.is_file() or installer.is_symlink()
                or installer.stat().st_size<1024*1024):
            raise ValueError("Missing authentic 3.1.0 installer for "+target)
        digest=sha(installer)
        receipt=load_receipt(full/report_name)
        gui=load_receipt(installed/"FINAL_INSTALLED_RECEIPT.json")
        validate(receipt,{
            "status":FULL_STATUS,
            "target":target,
            "installer":filename,
            "sha256":digest,
            "source_preview_revision":source_sha,
            "identity_channel":"final_candidate",
            "settings_namespace":"anything-plays-31",
            "native_core_count":11,
            "console_profiles":18,
            "public_release_approved":False,
            "final_release_approved":False,
        },target)
        validate(gui,{
            "status":INSTALLED_STATUS,
            "target":target,
            "installer":filename,
            "installer_sha256":digest,
            "source_revision":source_sha,
            "actual_tk_window_started":True,
            "actual_app_initialized":True,
            "actual_tk_mainloop_ran":True,
            "stream_output_window_opened":True,
            "stream_appearance_configured":True,
            "stream_closed_cleanly":True,
            "console_profiles":18,
            "native_core_count":11,
            "camera_hardware_verified":False,
            "physical_controller_verified":False,
            "gameplay_verified":False,
            "relinking_reviewed":False,
            "public_release_approved":False,
        },target)
        clean_path=full/CLEAN_SOURCE_RECEIPT
        if clean_path.is_file() or clean_path.is_symlink():
            wheel=load_receipt(clean_path)
            validate(wheel,{
                "target":target,
                "source_sha256":OPENCV_ORIGINAL_SOURCE_SHA,
                "native_camera_capture_backend_proven":True,
                "frozen_installer_tested":False,
                "redistribution_approved":False,
                "public_release_approved":False,
            },target)
            # Every camera-only wheel originated from a successful
            # independent native OS source-build run, not the same full
            # installer run; links and hashes must be retained accurately.
            run=wheel.get("source_ci_run_id")
            digest_wheel=wheel.get("native_wheel_sha256")
            if (type(run) is not int or run<1
                    or not isinstance(digest_wheel,str)
                    or not re.fullmatch(r"[a-f0-9]{64}",digest_wheel)):
                raise ValueError("Missing original source-built camera wheel proof: "+target)
            clean_wheels[target]={
                "upstream_source_sha256":OPENCV_ORIGINAL_SOURCE_SHA,
                "native_wheel_sha256":digest_wheel,
                "independent_source_build_run_id":run,
                "independent_camera_backend_proven":True,
                "physical_camera_tested":False,
                "source_to_frozen_binary_correspondence_approved":False,
                "redistribution_approved":False,
            }
        found[target]=(installer,filename,digest)
    if clean_wheels and len(clean_wheels)!=len(TARGETS):
        raise ValueError("Cannot stage mixed stock-OpenCV and clean source-wheel final installers")

    output.mkdir(parents=True)
    summary={}
    for target,(binary,name,digest) in found.items():
        copied=output/name
        shutil.copyfile(binary,copied,follow_symlinks=False)
        if sha(copied)!=digest:
            raise ValueError("Staging changed verified native bytes: "+target)
        summary[target]={"filename":name,"sha256":digest,"bytes":copied.stat().st_size}
    manifest={
        "schema_version":1,
        "status":"PASSED_3_1_0_PRIVATE_BINARY_QA_RELEASE_RIGHTS_OPEN",
        "source_revision":source_sha,
        "qa_run_id":qa_run_id,
        "installers":summary,
        "native_core_count":11,
        "console_profiles":18,
        "actual_installed_gui_verified_on_four_platforms":True,
        "public_release_approved":False,
        "stable_3_1_0_published":False,
        "full_native_relinking_approved":False,
        "physical_gameplay_accepted":False,
        "clean_source_built_opencv_wheel_receipts":clean_wheels,
        "clean_original_camera_only_wheels_verified_on_four_hosts":len(clean_wheels)==4,
    }
    (output/"FINAL_QA_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n","utf-8")
    source=(
        "# Anything Plays 3.1.0 — private source access notes\n\n"
        "Exact 3.1.0 application source: "
        "https://github.com/MasynNay/anything-plays/tree/"+source_sha+"\n\n"
        "Original 11 emulator source trees, notices and 37 Dolphin Gitlink archives: "
        "https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources\n\n"
        "pygame-ce 2.5.8 upstream source: "
        "https://github.com/pygame-community/pygame-ce/tree/"
        "c8200a9eaa530f884a0a4c3384cefc48006e58be\n\n"
        "SDL2 upstream source used in changed-native technical tests: "
        "https://github.com/libsdl-org/SDL/tree/"
        "5d249570393f7a37e037abf22cd6012a4cc56a71\n\n"
        "These are pointers for further correspondence/relink review; this is not "
        "a declaration that all bundled native dependencies have complete source, "
        "approved relinking options, or redistribution clearance. The four binaries "
        "are private QA artifacts, not published stable installers. No ROMs included.\n"
    )
    if clean_wheels:
        source += (
            "\n## Four independent native camera-only source-built OpenCV wheel receipts\n\n"
            "Each final installer was independently built with a wheel compiled "
            "from the exact pinned opencv-python-headless 4.14.0.94 source "
            "archive (original source SHA-256: `"+OPENCV_ORIGINAL_SOURCE_SHA+"`). "
            "The source-build runs are separately reproducible and retained "
            "as time-limited GitHub Actions artifacts; release source files "
            "must be separately made available to end users before distribution.\n\n"
        )
        for target in sorted(clean_wheels):
            value=clean_wheels[target]
            source+=(
                "- "+target+": source wheel SHA-256 `"
                +value["native_wheel_sha256"]+"`; source/native-backend QA run "
                "https://github.com/MasynNay/anything-plays/actions/runs/"
                +str(value["independent_source_build_run_id"])+"\n"
            )
        source+=(
            "\nFFmpeg-disabled and camera backend compile proof is NOT a physical "
            "webcam test, confirmation of all pygame/SDL/source/relinking obligations, "
            "or a public redistribution approval.\n"
        )
    (output/"FINAL_SOURCE_ACCESS_REVIEW.md").write_text(source,"utf-8")
    assets=sorted(p for p in output.iterdir() if p.is_file())
    if len(assets)!=6:
        raise ValueError("Expected four installers, QA manifest and source access note")
    (output/"SHA256SUMS.txt").write_text(
        "".join(sha(p)+"  "+p.name+"\n" for p in assets),"ascii",
    )
    return manifest


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--full-root",type=Path,required=True)
    p.add_argument("--installed-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--qa-run-id",type=int,required=True)
    a=p.parse_args(argv)
    report=stage(a.full_root,a.installed_root,a.output,
                 source_sha=a.source_sha,qa_run_id=a.qa_run_id)
    print("Four verified 3.1.0 full installers staged for PRIVATE review:",
          ", ".join(sorted(report["installers"])))
    print("No public stable release or third-party native rights approval inferred.")


if __name__=="__main__":
    main()
