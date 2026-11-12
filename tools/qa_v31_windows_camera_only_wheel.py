"""Verify source-built, patched Windows OpenCV with native DirectShow.

The source and Windows-specific patch are from the SHA-verified public
2.0.0 corresponding-source release. Native backend/import and missing codec
filenames are technical QA only, not public licensing approval.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from tools.qa_v31_linux_camera_only_wheel import SOURCE_NAME, SOURCE_SHA256, hash_file
from tools.verify_custom_opencv_wheel import verify_custom_wheel
from tools.check_opencv_build import verify_opencv_build

STATUS = "PRIVATE_SOURCE_BUILT_WINDOWS_DIRECTSHOW_FFMPEG_OFF_UNAPPROVED"
PATCH_NAME = "WINDOWS_OPENCV_SETUP_PATCH.diff"


def inspect(source, patch, wheel, *, native_cv2=None, source_sha=SOURCE_SHA256,
            patch_sha=None):
    source,patch,wheel = map(Path,(source,patch,wheel))
    if (source.name != SOURCE_NAME or source.is_symlink() or not source.is_file()
            or not re.fullmatch(r"[a-f0-9]{64}",source_sha)
            or hash_file(source)!=source_sha):
        raise ValueError("Unexpected original 4.14.0.94 source")
    if (patch.name!=PATCH_NAME or patch.is_symlink() or not patch.is_file()
            or not patch_sha or not re.fullmatch(r"[a-f0-9]{64}",patch_sha)
            or hash_file(patch)!=patch_sha):
        raise ValueError("Windows packaging source patch is missing or altered")
    if wheel.is_symlink() or not wheel.is_file():
        raise ValueError("Independent native Windows source wheel missing")
    wheel_sha=hash_file(wheel)
    meta=verify_custom_wheel(wheel,wheel_sha,"windows-x86_64")
    if native_cv2 is None:
        import cv2 as native_cv2
    import os
    previous=os.environ.get("AP_REQUIRE_OPENCV_FFMPEG_OFF")
    os.environ["AP_REQUIRE_OPENCV_FFMPEG_OFF"]="1"
    try:
        backend=verify_opencv_build(native_cv2,platform="win32")
    finally:
        if previous is None:
            os.environ.pop("AP_REQUIRE_OPENCV_FFMPEG_OFF",None)
        else:
            os.environ["AP_REQUIRE_OPENCV_FFMPEG_OFF"]=previous
    if backend["capture_backend"]!="DirectShow" or backend["ffmpeg_enabled"]=="YES":
        raise ValueError("Native DirectShow camera support absent or FFmpeg still active")
    return {
        "schema_version":1,"status":STATUS,"target":"windows-x64",
        "source_filename":SOURCE_NAME,"source_sha256":source_sha,
        "windows_source_patch_filename":PATCH_NAME,"windows_source_patch_sha256":patch_sha,
        "wheel_filename":wheel.name,"wheel_sha256":wheel_sha,
        "wheel_integrity":meta,"opencv_native_backend":backend,
        "source_build_flags":["-DWITH_FFMPEG=OFF","-DWITH_GSTREAMER=OFF",
                              "-DWITH_QT=OFF","-DWITH_DSHOW=ON",
                              "-DBUILD_TESTS=OFF","-DBUILD_PERF_TESTS=OFF"],
        "directshow_backend_compiled":True,
        "opencv_ffmpeg_disabled":True,
        "camera_hardware_tested":False,"installed_frozen_app_tested":False,
        "source_companion_review_complete":False,
        "redistribution_approved":False,"public_release_approved":False,
    }


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--patch",type=Path,required=True)
    p.add_argument("--wheel",type=Path,required=True)
    p.add_argument("--patch-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=inspect(a.source,a.patch,a.wheel,patch_sha=a.patch_sha)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n","utf-8")
    print("Pinned Windows native OpenCV source + patch + DirectShow backend PASS; FFmpeg disabled")
    print("No actual camera or frozen installer/redistribution acceptance inferred.")


if __name__=="__main__":
    main()
