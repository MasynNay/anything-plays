"""Capture genuine source-built 3.0 2D Libretro family evidence.

NOT a distribution permission or license compatibility verdict. The original
5 candidate libraries are built from exact checked-out Git revisions on each
of four OS architectures. Source archives and original unmodified license
files are captured with exact SHA-256. The final GitHub artifacts are private
Actions research archives; NEVER publish any core or source as a 3.0 release
until the independent complete corresponding-source rights gate passes.

This tool does not fetch source or modify any third-party repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

CANDIDATES = {
    "fceumm": ("libretro/libretro-fceumm", "Copying"),
    "stella2014": ("libretro/stella2014-libretro", None),
    "prosystem": ("libretro/prosystem-libretro", "License.txt"),
    "mednafen_ngp": ("libretro/beetle-ngp-libretro", "COPYING"),
    "mednafen_wswan": ("libretro/beetle-wswan-libretro", "COPYING"),
}
# The immutable source revisions actually built and tested 20/20 in run
# 42513615955; never attribute an unrelated old buildbot ZIP to these commits.
PINNED_COMMITS = {
    "fceumm": "e0f3086a8104f8fbbe49a2615b10401504a9533f",
    "stella2014": "7d1361e407e63f29e52892655069e5fb4096e691",
    "prosystem": "8a88014287c7a01cd568067e5a557d0a2b2a051f",
    "mednafen_ngp": "a50d5ac288a81f2104ddf43195a4efdd15c72227",
    "mednafen_wswan": "4b01295838ea89e3f1355bbe4cb5cf98aa6108cd",
}
EXTENSIONS = {
    "windows-x64": ".dll",
    "linux-x64": ".so",
    "macos-arm64": ".dylib",
    "macos-x64": ".dylib",
}
MAGICS = {
    ".dll": (b"MZ",),
    ".so": (b"\x7fELF",),
    ".dylib": (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"),
}
MAX_NATIVE = 45 * 1024 * 1024
MAX_SOURCE = 140 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def capture(source, native, candidate, target, expected_commit, output):
    if os.getenv("AP_RELEASE_BUILD", "0") != "0" or os.getenv("AP_V30_APPROVED_RELEASE", "0") != "0":
        raise ValueError("This source archive capture is research only")
    if candidate not in CANDIDATES or target not in EXTENSIONS:
        raise ValueError("Unknown source-native candidate/architecture")
    if (not isinstance(expected_commit, str) or len(expected_commit) != 40
            or any(c not in "0123456789abcdef" for c in expected_commit)):
        raise ValueError("Source revision must be a full exact 40-character commit")
    root, binary, dst = Path(source), Path(native), Path(output)
    if (root.is_symlink() or not root.is_dir()
            or binary.is_symlink() or not binary.is_file() or dst.exists() or dst.is_symlink()):
        raise ValueError("Missing/unsafe source or compiled native, or output already exists")
    project, notice_path = CANDIDATES[candidate]
    if binary.name != candidate + "_libretro" + EXTENSIONS[target]:
        raise ValueError("Compiled native does not have its genuine Libretro identity")
    compiled = binary.read_bytes()
    if not 30000 < len(compiled) < MAX_NATIVE or not compiled.startswith(MAGICS[EXTENSIONS[target]]):
        raise ValueError("Wrong architecture/native binary header/size")
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if revision != expected_commit:
        raise ValueError("Upstream source checkout unexpectedly changed")
    # Archive tracked original source without any build outputs, stale
    # submodules, compiler cache, linked binaries or other untracked material.
    archived = subprocess.check_output(
        ["git", "-C", str(root), "archive", "--format=tar", "HEAD"],
        timeout=120)
    if not 40000 < len(archived) < MAX_SOURCE:
        raise ValueError("Missing or implausibly sized tracked source archive")
    notice = None
    if notice_path:
        orig = root / notice_path
        if orig.is_symlink() or not orig.is_file():
            raise ValueError("Source-verified original GPL notice missing")
        notice = orig.read_bytes()
        if b"GENERAL PUBLIC LICENSE" not in notice or b"Version 2" not in notice:
            raise ValueError("Original core GPL2 source notice is wrong")
    dst.mkdir(parents=True)
    archive_name = f"{candidate}-{expected_commit}-SOURCE.tar"
    (dst / archive_name).write_bytes(archived)
    (dst / binary.name).write_bytes(compiled)
    if notice is not None:
        (dst / "ORIGINAL_UPSTREAM_GPL_NOTICE.txt").write_bytes(notice)
    report = {
        "schema_version": 1,
        "status": "UNAPPROVED-ORIGINAL-5-CORE-SOURCE-NATIVE-RESEARCH",
        "candidate": candidate,
        "target": target,
        "original_source_repository": f"https://github.com/{project}",
        "exact_source_revision": revision,
        "real_checkout_head_verified": True,
        "original_source_archive": archive_name,
        "source_archive_sha256": sha(archived),
        "source_archive_size_bytes": len(archived),
        "native_filename": binary.name,
        "native_sha256": sha(compiled),
        "native_size_bytes": len(compiled),
        "original_license_source_file": notice_path,
        "original_license_notice_sha256": sha(notice) if notice else None,
        "original_license_notice_copied": notice is not None,
        "source_submodules_and_deps_independently_reviewed": False,
        "binary_redistribution_approved": False,
        "combined_gpl_version_license_review_approved": False,
        "physical_gameplay_and_webcam_qa_approved": False,
        "production_source_to_binary_approved": False,
    }
    (dst / "PINNED_ORIGINAL_SOURCE_RESEARCH_UNAPPROVED.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--candidate", choices=CANDIDATES, required=True)
    p.add_argument("--target", choices=EXTENSIONS, required=True)
    p.add_argument("--source-commit", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        result = capture(args.source, args.native, args.candidate, args.target,
                         args.source_commit, args.output)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        p.exit(1, f"PINNED ORIGINAL SOURCE BUILD CAPTURE BLOCKED: {exc}\n")
    print(json.dumps({key: result[key] for key in (
        "candidate", "target", "native_sha256", "source_archive_sha256",
        "original_license_notice_copied", "binary_redistribution_approved")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
