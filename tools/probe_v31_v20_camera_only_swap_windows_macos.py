"""Swap public 2.0 camera-only OpenCV inside disposable 3.1 Windows/Mac apps.

This is a compatibility experiment, NOT a public installer generator. Require
a true CI-owned scratch folder, isolated extracted original bundles and the
SHA-pinned 3.1 package. Never modify owners' real app or release assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

from tools.probe_v31_v20_camera_only_swap import checked_scratch_path, SOURCE_SHA

STATUS = "UNAPPROVED_DISPOSABLE_V20_CAMERA_ONLY_CV2_IN_FINAL_V31"
TARGETS = {
    "windows-x64": ("_internal/cv2/cv2.pyd", "AnythingPlays.exe"),
    "macos-arm64": ("Contents/Frameworks/cv2/cv2.abi3.so", "Contents/MacOS/AnythingPlays"),
    "macos-x64": ("Contents/Frameworks/cv2/cv2.abi3.so", "Contents/MacOS/AnythingPlays"),
}


def hash_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def swap(*, target, old_app, new_app, scratch, source_sha, environ=None):
    env = os.environ if environ is None else environ
    if target not in TARGETS or source_sha != SOURCE_SHA:
        raise ValueError("Unrecognized source revision or target for private camera QA")
    # Keep the original lexical sandbox spelling for the parent's symlink
    # safety traversal. On macOS /var is a symlink to /private/var; resolving
    # scratch alone before walking raw child paths mislabels the trusted
    # runner's own temporary directory as an untrusted in-sandbox link.
    scratch = Path(scratch).absolute()
    if (env.get("CI") != "true" or env.get("AP_V31_DISPOSABLE_QA") != "1"
            or env.get("AP_V31_QA_SANDBOX") != str(scratch.resolve())):
        raise ValueError("Only isolated CI experiments are permitted")
    old_app = checked_scratch_path(old_app, scratch)
    new_app = checked_scratch_path(new_app, scratch)
    if old_app == new_app or not old_app.is_dir() or not new_app.is_dir():
        raise ValueError("Original source must differ from modified disposable target")
    native, launcher = TARGETS[target]
    original = old_app/native
    replaced = new_app/native
    for item in (original,replaced):
        checked_scratch_path(item, scratch)
        if not item.is_file() or item.stat().st_size < 1024:
            raise ValueError("Missing trusted original OpenCV source or target extension")
    if not (new_app/launcher).is_file():
        raise ValueError("Expected genuine full final 3.1 frozen executable")
    old_hash, new_hash = hash_file(original), hash_file(replaced)
    if old_hash == new_hash:
        raise ValueError("Original 2.0 and stock 3.1 extensions unexpectedly identical")
    to_remove = []
    if target=="windows-x64":
        deps = new_app/"_internal/cv2"
        extra = sorted(deps.glob("opencv_videoio_ffmpeg*.dll"))
        if len(extra)!=1:
            raise ValueError("Expected exactly one stock Windows OpenCV FFmpeg DLL")
        for item in extra:
            checked_scratch_path(item,scratch)
            if not item.is_file(): raise ValueError("Not a native dependency")
        to_remove.extend(extra)
    else:
        deps = new_app/"Contents/Frameworks/cv2/__dot__dylibs"
        checked_scratch_path(deps,scratch)
        if not deps.is_dir(): raise ValueError("Expected stock Mac OpenCV native library folder")
        members=list(deps.rglob("*"))
        if not members or any(path.is_symlink() for path in members):
            raise ValueError("Missing or symlinked Mac native dependency inputs")
        # Other frozen modules, notably Pillow/libtiff, may legitimately
        # resolve shared libraries through this directory. Deleting it
        # wholesale broke Apple Silicon PIL when liblzma disappeared.
        # Prune only libraries tied directly to the FFmpeg codec stack here.
        # Any other optional native components remain visible to the
        # independent license inventory and still require review.
        ffmpeg_prefixes = (
            "libavcodec.", "libavdevice.", "libavfilter.",
            "libavformat.", "libavutil.", "libswresample.",
            "libswscale.", "libpostproc.", "libx264.", "libx265.",
        )
        to_remove.extend(path for path in members
                         if path.is_file()
                         and path.name.lower().startswith(ffmpeg_prefixes))
        if target == "macos-arm64" and not to_remove:
            raise ValueError("Expected FFmpeg-bearing native ARM OpenCV runtime")
    # The public 2.0 Intel Mac camera-only extension was linked against
    # libavif.16.dylib. The 3.1 stock OpenCV wheel on Intel does not ship
    # that dependency, so the frozen copied extension needs its ORIGINAL
    # SHA-identifiable 2.0 native library in the disposable app as well.
    # This is NOT a license or source/relinking review for libavif itself.
    copied_shared_dependency = None
    if target == "macos-x64":
        filename = "libavif.16.dylib"
        matches = [p for p in old_app.rglob(filename)
                   if p.is_file() and not p.is_symlink()]
        if not matches:
            raise ValueError("Original 2.0 Intel camera-only libavif dependency missing")
        checksums = {hash_file(path) for path in matches}
        if len(checksums) != 1:
            raise ValueError("Ambiguous original libavif binaries")
        avif_original = matches[0]
        checked_scratch_path(avif_original, scratch)
        target_dir = new_app/"Contents/Frameworks"
        checked_scratch_path(target_dir, scratch)
        avif_destination = target_dir/filename
        if avif_destination.exists() or avif_destination.is_symlink():
            raise ValueError("Refusing to overwrite an existing 3.1 shared native dylib")
        shutil.copyfile(avif_original, avif_destination)
        if hash_file(avif_destination) != hash_file(avif_original):
            raise ValueError("Source-built camera wheel dependency copy changed bytes")
        copied_shared_dependency = {
            "filename": filename,
            "sha256": hash_file(avif_destination),
            "target": str(avif_destination.relative_to(new_app)),
        }
    previous = [{"path": str(f.relative_to(new_app)), "sha256":hash_file(f)}
                for f in to_remove]
    # Only these original public v2.0.0 native bytes are copied into the
    # throwaway v3.1.0 extracted app; original downloads are untouched.
    shutil.copyfile(original,replaced)
    for file in to_remove:
        file.unlink()
    if hash_file(replaced)!=old_hash or any(path.exists() for path in to_remove):
        raise ValueError("Temporary camera-only swap was incomplete")
    return {
        "schema_version":1, "status":STATUS,"target":target,
        "source_revision":SOURCE_SHA,
        "public_2_0_native_sha256":old_hash,
        "stock_final_3_1_native_sha256":new_hash,
        "disposable_final_3_1_native_sha256":hash_file(replaced),
        "removed_stock_cv2_libraries":previous,
        "removed_library_count":len(previous),
        "copied_original_camera_only_shared_dependency":copied_shared_dependency,
        "ad_hoc_resign_required":target.startswith("macos"),
        "actual_frozen_app_smoke_passed":False,
        "physical_camera_tested":False,
        "native_relinking_approved":False,
        "redistribution_approved":False,
        "public_release_approved":False,
        "original_public_packages_unchanged":True,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target",choices=sorted(TARGETS),required=True)
    parser.add_argument("--old-app",type=Path,required=True)
    parser.add_argument("--new-app",type=Path,required=True)
    parser.add_argument("--scratch",type=Path,required=True)
    parser.add_argument("--source-sha",required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=swap(target=args.target,old_app=args.old_app,new_app=args.new_app,
                scratch=args.scratch,source_sha=args.source_sha)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n","utf-8")
    print("Swapped",args.target,"inside disposable original-core 3.1 app;"
          " actual frozen GUI and camera still need separate proof")


if __name__=="__main__":
    main()
