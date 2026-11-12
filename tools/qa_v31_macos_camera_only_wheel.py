"""Verify a freshly source-built macOS OpenCV wheel without FFmpeg or AVIF.

This is native source/wheel and AVFoundation camera-backend evidence only.
It does not establish physical camera support, LGPL compliance, platform
notarization, installed frozen-GUI QA or public distribution permission.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import zipfile

from tools.qa_v31_linux_camera_only_wheel import SOURCE_NAME, SOURCE_SHA256, hash_file
from tools.verify_custom_opencv_wheel import verify_custom_wheel
from tools.check_opencv_build import verify_opencv_build

STATUS = "PRIVATE_NATIVE_MAC_CAMERA_ONLY_FFMPEG_AVIF_OFF_SOURCE_WHEEL_UNAPPROVED"
TARGETS = ("macos-arm64", "macos-x86_64")


def inspect(source, wheel, *, target, native_cv2=None, source_sha=SOURCE_SHA256):
    if target not in TARGETS:
        raise ValueError("OpenCV wheel target must be native Mac Intel or Apple Silicon")
    source, wheel = Path(source), Path(wheel)
    if (source.name != SOURCE_NAME or source.is_symlink() or not source.is_file()
            or not re.fullmatch(r"[a-f0-9]{64}", source_sha)
            or hash_file(source) != source_sha):
        raise ValueError("Untrusted original OpenCV source distribution")
    if wheel.is_symlink() or not wheel.is_file():
        raise ValueError("Missing actual native wheel")
    wheel_hash = hash_file(wheel)
    verify = verify_custom_wheel(wheel, wheel_hash, target)
    with zipfile.ZipFile(wheel) as z:
        suspicious = [name for name in z.namelist()
                      if "libavif" in name.lower()]
    if suspicious:
        raise ValueError("Disallowed optional AVIF codec native libraries remain in wheel")
    if native_cv2 is None:
        import cv2 as native_cv2
    import os
    before = os.environ.get("AP_REQUIRE_OPENCV_FFMPEG_OFF")
    os.environ["AP_REQUIRE_OPENCV_FFMPEG_OFF"]="1"
    try:
        backend = verify_opencv_build(native_cv2,platform="darwin")
    finally:
        if before is None:
            os.environ.pop("AP_REQUIRE_OPENCV_FFMPEG_OFF",None)
        else:
            os.environ["AP_REQUIRE_OPENCV_FFMPEG_OFF"]=before
    if backend["capture_backend"]!="AVFoundation" or backend["ffmpeg_enabled"]=="YES":
        raise ValueError("Required AVFoundation camera backend or FFmpeg-disabled build absent")
    return {
        "schema_version":1,"status":STATUS,"target":target,
        "source_filename":SOURCE_NAME,"source_sha256":source_sha,
        "wheel_filename":wheel.name,"wheel_sha256":wheel_hash,
        "wheel_integrity":verify,
        "opencv_native_backend":backend,
        "source_build_flags":[
            "-DWITH_FFMPEG=OFF","-DWITH_GSTREAMER=OFF","-DWITH_QT=OFF",
            "-DWITH_AVIF=OFF","-DWITH_AVFOUNDATION=ON",
            "-DBUILD_TESTS=OFF","-DBUILD_PERF_TESTS=OFF",
        ],
        "ffmpeg_disabled_in_native_wheel":True,
        "avif_native_dependency_omitted":True,
        "avfoundation_backend_compiled":True,
        "physical_camera_tested":False,
        "installed_frozen_app_tested":False,
        "notarized":False,
        "all_native_corresponding_source_reviewed":False,
        "redistribution_approved":False,
        "public_release_approved":False,
    }


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--wheel",type=Path,required=True)
    p.add_argument("--target",choices=TARGETS,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=inspect(a.source,a.wheel,target=a.target)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2)+"\n","utf-8")
    print("Authentic source-built camera-only Mac",a.target,
          "wheel compiled and imported; FFmpeg/AVIF omitted; physical camera untested.")


if __name__=="__main__":
    main()
