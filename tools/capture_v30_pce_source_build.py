"""Capture an ORIGINAL pinned-source Beetle PCE Fast build for review.

This lab exists because the mutable Libretro buildbot PCE Fast binary reports
no source commit. A locally compiled alternative can have its *own* pinned
source identity. This code does not replace any shipped core, endorse mixed
GPL/noncommercial redistribution, or certify that the old binary matched it.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import io

PINNED_REPOSITORY = "https://github.com/libretro/beetle-pce-fast-libretro"
PINNED_COMMIT = "2de1ce1c3f237b161c126c54ba407990bb86d1e9"
SHA = re.compile(r"[0-9a-f]{40}\Z")
PLATFORM_FILES = {
    "linux-x64": "mednafen_pce_fast_libretro.so",
    "macos-arm64": "mednafen_pce_fast_libretro.dylib",
    "macos-x64": "mednafen_pce_fast_libretro.dylib",
    "windows-x64": "mednafen_pce_fast_libretro.dll",
}


def _git(source, *args, raw=False):
    result = subprocess.run(
        ["git", "-C", str(source), *args], check=True, capture_output=True,
    )
    return result.stdout if raw else result.stdout.decode("utf-8").strip()


def capture_pinned_build(source, native_binary, destination, *, target):
    if target not in PLATFORM_FILES:
        raise ValueError("Unknown PC Engine native target")
    root, binary, out = (
        Path(source).expanduser(),
        Path(native_binary).expanduser(),
        Path(destination).expanduser(),
    )
    if any(p.is_symlink() for p in (root, binary, out)):
        raise ValueError("Refusing symlinked source, core or output")
    root, binary, out = root.resolve(), binary.resolve(), out.resolve()
    if not root.is_dir() or not binary.is_file() or binary.parent != root:
        raise ValueError("Expected compiled native core inside checked-out pinned source")
    if binary.name != PLATFORM_FILES[target] or binary.stat().st_size < 50000:
        raise ValueError("Wrong or suspiciously small native PCE core")
    if out.exists() and any(out.iterdir()):
        raise ValueError("PCE evidence output must be new or empty")
    if out == root or out in root.parents or root in out.parents:
        raise ValueError("Source and evidence output paths must be separate")
    actual = _git(root, "rev-parse", "HEAD")
    if not SHA.fullmatch(actual) or actual != PINNED_COMMIT:
        raise ValueError("PCE candidate did not build from the exact approved research commit")
    origin = _git(root, "remote", "get-url", "origin")
    if origin.removesuffix(".git").rstrip("/") != PINNED_REPOSITORY:
        raise ValueError("PCE candidate repository origin unexpectedly changed")
    if _git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Tracked PCE source tree modified after checkout")
    notice = root / "COPYING"
    if not notice.is_file() or notice.is_symlink():
        raise ValueError("GPL-2.0 corresponding-source notice is missing")
    license_text = notice.read_bytes()
    if b"GNU GENERAL PUBLIC LICENSE" not in license_text or b"Version 2" not in license_text:
        raise ValueError("PCE core's GPLv2 source license cannot be verified")

    original_tar = _git(root, "archive", "--format=tar", "HEAD", raw=True)
    if not original_tar or len(original_tar) > 100 * 1024 * 1024:
        raise ValueError("PCE source archive missing/oversized")
    with tarfile.open(fileobj=io.BytesIO(original_tar), mode="r:") as tar:
        if "COPYING" not in tar.getnames():
            raise ValueError("Pinned Git source archive lacks GPL license")
    compressed = gzip.compress(original_tar, compresslevel=6, mtime=0)
    binary_hash = hashlib.sha256(binary.read_bytes()).hexdigest()
    source_hash = hashlib.sha256(compressed).hexdigest()
    evidence = {
        "status": "UNAPPROVED-EXPERIMENTAL-PINNED-PCE-SOURCE-BUILD",
        "target": target,
        "native_core": binary.name,
        "native_core_sha256": binary_hash,
        "native_core_bytes": binary.stat().st_size,
        "source_repository": PINNED_REPOSITORY,
        "source_commit": actual,
        "source_archive": f"pce-fast-{PINNED_COMMIT}-SOURCE.tar.gz",
        "source_archive_sha256": source_hash,
        "source_archive_bytes": len(compressed),
        "native_binary_built_from_checked_out_commit": True,
        "matches_old_libretro_buildbot_binary": False,
        "current_3_0_core_replaced": False,
        "gameplay_native_video_audio_verified": False,
        "third_party_distribution_approved": False,
        "mixed_core_licenses_reviewed": False,
        "corresponding_dependencies_independently_reviewed": False,
        "rights_notice": "GPL-2.0; exact source archive included for review. No redistribution decision for combined Anything Plays 3.0 bundle.",
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / evidence["source_archive"]).write_bytes(compressed)
    shutil.copyfile(binary, out / binary.name)
    (out / "PCE_SOURCE_BUILD_UNAPPROVED.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(notice, out / "PCE_COPYING_GPL-2.0.txt")
    return evidence


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--native-core", type=Path, required=True)
    p.add_argument("--target", choices=PLATFORM_FILES, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        result = capture_pinned_build(args.source, args.native_core, args.output,
                                      target=args.target)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError,
            tarfile.TarError) as err:
        p.exit(1, f"PCE SOURCE BUILD REJECTED: {err}\n")
    print(f"Saved source and core SHA-256 for {result['target']} from pinned "
          f"commit {result['source_commit']}; preview-only, unapproved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
