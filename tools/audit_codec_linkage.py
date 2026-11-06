"""Inspect frozen macOS OpenCV/FFmpeg dynamic links for release review.

Run on the macOS CI host against the *staged application*. `otool -L` shows
actual Mach-O load commands, not just Python package license claims.
This is technical evidence only, not a finding of legal compliance.
"""

import argparse
import json
from pathlib import Path
import re
import subprocess

CODECS = ("libx264", "libx265")
MEDIA = ("libavcodec", "libavformat", "libavutil", "libswscale",
         "libswresample", "libx264", "libx265")


def parse_otool(text):
    """Return link references from the output of `otool -L`."""
    return [line.strip().split(" (compatibility version", 1)[0]
            for line in text.splitlines()[1:]
            if " (compatibility version" in line]


def inspect_macos_bundle(bundle, command=None):
    """Inventory packaged Mach-O's FFmpeg and codec link edges."""
    bundle = Path(bundle).resolve(strict=True)
    cv2_root = bundle / "Contents" / "Frameworks" / "cv2"
    if not cv2_root.is_dir():
        raise ValueError(f"Missing packaged OpenCV Frameworks folder: {cv2_root}")
    if command is None:
        command = lambda f: subprocess.check_output(
            ["otool", "-L", str(f)], text=True, stderr=subprocess.STDOUT
        )
    candidates = sorted((*cv2_root.rglob("*.dylib"), *cv2_root.rglob("*.so")))
    links = []
    shipped = []
    codec_referrers = {name: [] for name in CODECS}
    for binary in candidates:
        if binary.is_symlink():
            continue
        relative = binary.relative_to(bundle).as_posix()
        if any(part in binary.name.lower() for part in MEDIA):
            shipped.append(relative)
        try:
            deps = parse_otool(command(binary))
        except (subprocess.CalledProcessError, OSError) as error:
            raise ValueError(f"Could not inspect native dynamic links: {relative}") from error
        media_deps = [dep for dep in deps if any(name in dep.lower() for name in MEDIA)]
        if media_deps:
            links.append({"binary": relative, "media_dependencies": media_deps})
        for codec in CODECS:
            if any(codec in dep.lower() for dep in deps):
                codec_referrers[codec].append(relative)
    return {
        "schema_version": 1,
        "scope": "Frozen OpenCV Mach-O load commands; not a complete legal/source audit",
        "redistribution_approved": False,
        "safe_to_delete_codec_libraries": False,
        "examined_files": len(candidates),
        "bundled_media_binaries": shipped,
        "codec_direct_link_referrers": codec_referrers,
        "media_link_edges": links,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = inspect_macos_bundle(args.bundle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Inspected {result['examined_files']} frozen OpenCV native files")
    for codec, refs in result["codec_direct_link_referrers"].items():
        print(f"{codec}: {len(refs)} direct consumers")
        for ref in refs[:8]:
            print(f"  {ref}")
    print("Evidence only; codec removal or redistribution NOT approved")


if __name__ == "__main__":
    main()
