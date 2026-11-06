"""Smoke-test OpenCV source-built without FFmpeg on a CI platform."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import cv2
import numpy as np

from tools.check_opencv_build import verify_opencv_build

FORBIDDEN = ("libavcodec", "libavformat", "libavdevice", "libavfilter",
             "libavutil", "libswscale", "libswresample", "libx264",
             "libx265", "ffmpeg")


def test_camera_only(wheel):
    info = verify_opencv_build()
    if cv2.videoio_registry.hasBackend(cv2.CAP_FFMPEG):
        raise ValueError("Unexpected FFmpeg capture backend")
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    frame[10:40, 20:60] = (0, 255, 0)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (40, 100, 100), (85, 255, 255))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours or max(cv2.contourArea(c) for c in contours) < 500:
        raise ValueError("Camera frame tracking operations failed")
    with zipfile.ZipFile(wheel) as archive:
        media = [name for name in archive.namelist()
                 if any(fragment in name.lower() for fragment in FORBIDDEN)]
        if media:
            raise ValueError(f"Wheel contains media libraries: {media[:10]}")
    digest = hashlib.sha256()
    with Path(wheel).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "schema_version": 1,
        "platform": sys.platform,
        "opencv_version": cv2.__version__,
        "camera_backend": info["capture_backend"],
        "gui": info["gui"],
        "ffmpeg_runtime_backend": False,
        "wheel_sha256": digest.hexdigest(),
        "wheel_file": Path(wheel).name,
        "camera_frame_processing_tested": True,
        "camera_hardware_tested": False,
        "distribution_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = test_camera_only(args.wheel)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
