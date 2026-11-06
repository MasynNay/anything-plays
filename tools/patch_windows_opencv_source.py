"""Patch the upstream OpenCV wheel *packager*, not OpenCV itself.

The opencv-python Windows setup.py unconditionally requires a copied FFmpeg
plugin DLL even when the explicit CMAKE_ARGS disables FFmpeg. This script
makes that file list conditional, retaining the upstream behavior when FFmpeg
is enabled. The patch is isolated to a private experimental source build.
"""

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

NEEDLE = '            if os.name == "nt"\n            else []'
REPLACEMENT = (
    '            if os.name == "nt" and '
    '"-DWITH_FFMPEG=OFF" not in os.environ.get("CMAKE_ARGS", "")\n'
    '            else []'
)


def patch_source(sdist, destination):
    sdist = Path(sdist)
    destination = Path(destination)
    if not sdist.is_file() or not sdist.name.endswith(".tar.gz"):
        raise ValueError("Expected exact PyPI OpenCV .tar.gz source distribution")
    if destination.exists():
        raise ValueError("Refusing to overwrite an existing source directory")
    destination.mkdir(parents=True)
    with tarfile.open(sdist, "r:gz") as archive:
        archive.extractall(destination, filter="data")
    roots = [p for p in destination.iterdir()
             if p.is_dir() and (p / "setup.py").is_file()]
    if len(roots) != 1:
        raise ValueError("Expected exactly one source root with setup.py")
    root = roots[0]
    setup = root / "setup.py"
    original = setup.read_text(encoding="utf-8")
    start = original.find("rearrange_cmake_output_data =")
    ffmpeg_line = original.find("bin/opencv_videoio_ffmpeg", start)
    old_condition = original.find(NEEDLE, ffmpeg_line)
    if min(start, ffmpeg_line, old_condition) < 0:
        raise ValueError("Cannot find expected FFmpeg DLL packaging assumption")
    if old_condition - ffmpeg_line > 180:
        raise ValueError("Ambiguous FFmpeg DLL packaging assumption")
    updated = original[:old_condition] + REPLACEMENT + original[old_condition + len(NEEDLE):]
    setup.write_text(updated, encoding="utf-8")
    patch = "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile="setup.py (PyPI source)", tofile="setup.py (FFmpeg-free build)"
    ))
    (destination / "WINDOWS_OPENCV_SETUP_PATCH.diff").write_text(patch, encoding="utf-8")
    provenance = {
        "distribution": "opencv-python-headless",
        "version": "4.14.0.94",
        "source_archive": sdist.name,
        "source_archive_sha256": hashlib.sha256(sdist.read_bytes()).hexdigest(),
        "patch_file": "WINDOWS_OPENCV_SETUP_PATCH.diff",
        "patch_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
        "why": "Disable mandatory FFmpeg DLL file-list entry when CMAKE_ARGS disables FFmpeg",
        "public_redistribution_approved": False,
    }
    (destination / "WINDOWS_OPENCV_PATCH_PROVENANCE.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return root, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdist", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    root, record = patch_source(args.sdist, args.destination)
    print("Patched FFmpeg DLL packaging assumption in: " + str(root))
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
