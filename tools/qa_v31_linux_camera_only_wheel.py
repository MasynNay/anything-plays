"""Source/ABI/camera-only receipt for an isolated Linux OpenCV wheel build.

Verifies immutable PyPI source bytes, exact self-built wheel integrity and a
real installed cv2 native import. Does not alter ANY published application,
constitute real camera testing, or provide public redistribution approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.check_opencv_build import verify_opencv_build
from tools.verify_custom_opencv_wheel import verify_custom_wheel

SOURCE_NAME = "opencv_python_headless-4.14.0.94.tar.gz"
SOURCE_SHA256 = "4afa2ea1214453648be88259f035712454faa9039b686de7753569ba8eec1577"
STATUS = "PRIVATE_SOURCE_BUILT_LINUX_V4L2_ONLY_WHEEL_QA_NO_RELEASE"


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def make_receipt(source, wheel, *, native_cv2=None, source_digest=SOURCE_SHA256):
    source, wheel = Path(source), Path(wheel)
    if (source.is_symlink() or not source.is_file() or source.name != SOURCE_NAME
            or not re.fullmatch(r"[a-f0-9]{64}", source_digest)
            or hash_file(source) != source_digest):
        raise ValueError("Original PyPI 4.14.0.94 sdist does not match pinned SHA256")
    if not wheel.is_file() or wheel.is_symlink():
        raise ValueError("Source-built OpenCV wheel missing")
    version = verify_custom_wheel(wheel, hash_file(wheel), "linux-x86_64")
    if native_cv2 is None:
        import cv2 as native_cv2
    import os
    old = os.environ.get("AP_REQUIRE_OPENCV_FFMPEG_OFF")
    os.environ["AP_REQUIRE_OPENCV_FFMPEG_OFF"] = "1"
    try:
        backend = verify_opencv_build(native_cv2, platform="linux")
    finally:
        if old is None:
            os.environ.pop("AP_REQUIRE_OPENCV_FFMPEG_OFF", None)
        else:
            os.environ["AP_REQUIRE_OPENCV_FFMPEG_OFF"] = old
    if backend["ffmpeg_enabled"] == "YES":
        raise ValueError("OpenCV build still enables FFmpeg")
    if backend["capture_backend"] != "V4L2":
        raise ValueError("Linux native camera capture backend missing")
    return {
        "schema_version": 1,
        "status": STATUS,
        "target": "linux-x64",
        "source": SOURCE_NAME,
        "source_sha256": source_digest,
        "package": "opencv-python-headless",
        "version": "4.14.0.94",
        "wheel": wheel.name,
        "wheel_sha256": hash_file(wheel),
        "wheel_metadata": version,
        "opencv_build": backend,
        "build_flags": [
            "-DWITH_FFMPEG=OFF", "-DWITH_GSTREAMER=OFF",
            "-DWITH_QT=OFF", "-DWITH_GTK=OFF", "-DWITH_V4L=ON",
            "-DBUILD_TESTS=OFF", "-DBUILD_PERF_TESTS=OFF"
        ],
        "opencv_native_module_imported": True,
        "opencv_linux_v4l2_backend_available": True,
        "opencv_ffmpeg_backend_disabled": True,
        "physical_camera_tested": False,
        "replaced_existing_installer": False,
        "tested_in_actual_frozen_3_1_app": False,
        "all_native_corresponding_source_verified": False,
        "redistribution_approved": False,
        "public_release_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--wheel", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    r = make_receipt(a.source, a.wheel)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(r, indent=2) + "\n", "utf-8")
    print("Pinned source-built Linux wheel and V4L2 backend PASS:", r["wheel"])
    print("Camera hardware, frozen app and redistribution NOT YET VERIFIED")


if __name__ == "__main__":
    main()
