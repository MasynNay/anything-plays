"""Verify exact original-source-built 3.1.1 STABLE-UPGRADE identity, privately.

This verifies the mGBA-only *new* stable-version app shell, not the 18-console
public release. It may run in a disposable CI VM but NEVER installs on users'
machines, creates releases or approves redistribution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import plistlib
import subprocess

from anything_plays.build_identity import make_identity
from tools.verify_v31_rc import validate_staged_identity
from tools.verify_v311_source_stage import SOURCE, digest
from tools.v311_camera_source_gate import require_pinned_native_camera_wheel

INSTALLERS = {
    "linux-x64": "anything-plays-31_3.1.1_amd64.deb",
    "windows-x64": "AnythingPlaysSetup-3.1.1.exe",
    "macos-arm64": "AnythingPlays-3.1.1-macos-arm64.dmg",
    "macos-x64": "AnythingPlays-3.1.1-macos-x64.dmg",
}
STATUS = "PRIVATE_STABLE_3_1_1_SOURCE_SHELL_ONE_CORE_NOT_RELEASED"


def verify(target, installer, bundle, camera_receipt, source_revision, *,
           checkout_sha=None):
    if target not in INSTALLERS:
        raise ValueError("No reviewed 3.1.1 stable upgrade target")
    if not isinstance(source_revision, str) or not SOURCE.fullmatch(source_revision):
        raise ValueError("Expected exact 3.1.1 source commit SHA")
    if checkout_sha is None:
        checkout_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, timeout=15,
        ).strip()
    if checkout_sha != source_revision:
        raise ValueError("Stable-version source binary and original checkout differ")
    installer, bundle = Path(installer), Path(bundle)
    if (installer.name != INSTALLERS[target] or not installer.is_file()
            or installer.is_symlink() or installer.stat().st_size <= 1024*1024):
        raise ValueError("This is not the exact original 3.1.1 stable update installer")
    if not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("Stable update must have a real frozen app directory")
    marker = validate_staged_identity(bundle, channel="v311_stable_candidate")
    identity = make_identity("v311_stable_candidate")
    if (identity["version"] != "3.1.1"
            or identity["settings_namespace"] != "anything-plays-31"
            or identity["public_release_approved"] is not False):
        raise ValueError("Wrong shared stable preference namespace or publication state")
    if target.startswith("macos"):
        if bundle.name != "AnythingPlays31.app":
            raise ValueError("Mac version cannot update existing AnythingPlays31.app")
        with (bundle/"Contents"/"Info.plist").open("rb") as stream:
            plist=plistlib.load(stream)
        if (plist.get("CFBundleIdentifier") != "com.anythingplays.release31"
                or plist.get("CFBundleShortVersionString") != "3.1.1"
                or plist.get("CFBundleVersion") != "3.1.1"):
            raise ValueError("Mac upgrade is not the original stable 3.1 bundle ID")
        cores=bundle/"Contents"/"Resources"/"cores"
        suffix=".dylib"
    else:
        cores=bundle/"cores"
        suffix=".dll" if target=="windows-x64" else ".so"
    if not cores.is_dir() or cores.is_symlink():
        raise ValueError("Stable source-stage native core dir missing")
    real=[p for p in cores.iterdir() if p.name.endswith("_libretro"+suffix)]
    if len(real)!=1 or real[0].name!="mgba_libretro"+suffix:
        raise ValueError("Stable source stage cannot be relabeled as full 18 consoles")
    if real[0].is_symlink() or real[0].stat().st_size <= 1024:
        raise ValueError("Missing frozen native mGBA core")
    if target=="linux-x64":
        fields=subprocess.check_output(
            ["dpkg-deb","-f",str(installer),"Package","Version"],
            text=True,timeout=15,
        ).splitlines()
        if fields != ["anything-plays-31","3.1.1"]:
            raise ValueError("3.1.1 DEB does not update the existing stable package")
    elif target=="windows-x64":
        with installer.open("rb") as stream:
            if stream.read(2)!=b"MZ":
                raise ValueError("3.1.1 Inno installer lacks Windows PE header")
    camera=require_pinned_native_camera_wheel(camera_receipt,target)
    return {
        "schema_version":1, "status":STATUS,
        "target":target,"installer":installer.name,
        "sha256":digest(installer),
        "size_bytes":installer.stat().st_size,
        "source_revision":source_revision,
        "version":"3.1.1",
        "identity_channel":"v311_stable_candidate",
        "settings_namespace":"anything-plays-31",
        "marker_path":marker,
        "opencv_sourcebuilt_ffmpeg_off_wheel_sha256":camera["native_wheel_sha256"],
        "native_core_count":1,
        "full_18_console_installer":False,
        "native_hardware_accepted":False,
        "redistribution_approved":False,
        "public_release_approved":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target",choices=tuple(INSTALLERS),required=True)
    p.add_argument("--installer",type=Path,required=True)
    p.add_argument("--bundle",type=Path,required=True)
    p.add_argument("--camera-receipt",type=Path,required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=verify(args.target,args.installer,args.bundle,args.camera_receipt,
                  args.source_sha)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n","utf-8")
    print("Original-source PRIVATE 3.1.1 upgrade stage:",result["target"],
          result["sha256"],"NOT A PUBLIC RELEASE")


if __name__=="__main__":
    main()
