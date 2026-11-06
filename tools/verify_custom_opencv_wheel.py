"""Verify exact, trusted macOS arm64 camera-only OpenCV wheel input.

Only an explicitly selected, SHA-256-verified wheel is accepted. The wheel's
metadata must match the approved package name and pinned version. This is
a packaging integrity check; it does not approve third-party redistribution.
"""

import argparse
from email.parser import Parser
import hashlib
from pathlib import Path, PurePosixPath
import re
import zipfile

NAME = "opencv-python-headless"
VERSION = "4.14.0.94"
FORBIDDEN = ("libavcodec", "libavformat", "libavdevice", "libavfilter",
             "libavutil", "libswscale", "libswresample", "libx264",
             "libx265", "ffmpeg")


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_custom_wheel(wheel, expected_sha256):
    wheel = Path(wheel)
    if wheel.is_symlink() or not wheel.is_file():
        raise ValueError("Custom OpenCV wheel must be a regular file")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("Expected custom wheel SHA-256 must be 64 lowercase hex digits")
    if not wheel.name.startswith("opencv_python_headless-4.14.0.94-"):
        raise ValueError("Custom wheel must match the pinned opencv-python-headless version")
    if not wheel.name.endswith(".whl") or "macosx" not in wheel.name or "arm64" not in wheel.name:
        raise ValueError("Custom wheel must target macOS Apple Silicon")
    actual = hash_file(wheel)
    if actual != expected_sha256:
        raise ValueError("Custom OpenCV wheel SHA-256 mismatch")
    with zipfile.ZipFile(wheel) as archive:
        entries = archive.namelist()
        for entry in entries:
            parts = PurePosixPath(entry).parts
            if entry.startswith("/") or ".." in parts:
                raise ValueError("Unsafe path in custom OpenCV wheel")
        forbidden = [entry for entry in entries
                     if any(name in entry.lower() for name in FORBIDDEN)]
        if forbidden:
            raise ValueError(f"FFmpeg or GPL codec binaries appear in custom wheel: {forbidden[:5]}")
        metadata_paths = [p for p in entries
                          if p.endswith(".dist-info/METADATA")
                          and p.startswith("opencv_python_headless-")]
        if len(metadata_paths) != 1:
            raise ValueError("Missing or ambiguous OpenCV wheel metadata")
        metadata = Parser().parsestr(archive.read(metadata_paths[0]).decode("utf-8"))
        if metadata["Name"] != NAME or metadata["Version"] != VERSION:
            raise ValueError("Custom OpenCV wheel metadata differs from pinned package")
    return {
        "file": wheel.name, "sha256": actual,
        "distribution": NAME, "version": VERSION,
        "ffmpeg_omission_checked_by_filename": True,
        "redistribution_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("sha256")
    args = parser.parse_args()
    result = verify_custom_wheel(args.wheel, args.sha256)
    print(f"Verified custom macOS arm64 OpenCV wheel: {result['file']} sha256={result['sha256']}")
    print("NOTE: final build must also verify OpenCV reports FFMPEG: NO")


if __name__ == "__main__":
    main()
