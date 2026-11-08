"""Preserve test-only, newly compiled Beetle Supafaust SNES GPLv2+ source identity.

The original source and compiled candidate are retained together solely for
technical/license review. Neither native output nor this manifest approves
public redistribution of a combined emulator frontend.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

from tools.patch_v30_supafaust_macos_semaphore import (
    BEFORE as MAC_SEM_BEFORE,
    AFTER as MAC_SEM_AFTER,
    TARGET as MAC_SEM_PATH,
)

REPOSITORY = "https://github.com/libretro/supafaust"
COMMIT = "642d1d1b6684aa7e306a02a89885f3f5456a5157"
BINARY = "mednafen_supafaust_libretro.so"
NATIVE_BY_TARGET = {
    "linux-x64": "mednafen_supafaust_libretro.so",
    "windows-x64": "mednafen_supafaust_libretro.dll",
    "macos-arm64": "mednafen_supafaust_libretro.dylib",
    "macos-x64": "mednafen_supafaust_libretro.dylib",
}
HEADER_BY_TARGET = {
    "linux-x64": (b"\x7fELF",),
    "windows-x64": (b"MZ",),
    "macos-arm64": (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"),
    "macos-x64": (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"),
}
ORIGINAL_LICENSE = "COPYING"
LICENSE_SOURCE = "mednafen/snes_faust/snes.cpp"
MAX_UNCOMPRESSED_SOURCE = 128 * 1024 * 1024


def git(root, *args, binary=False):
    run = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True,
        check=True, timeout=40,
    )
    return run.stdout if binary else run.stdout.decode("utf-8").strip()


def capture(*, source, native, output, target="linux-x64"):
    if target not in NATIVE_BY_TARGET:
        raise ValueError("Unknown Supafaust target architecture")
    root, library, destination = map(
        lambda s: Path(s).expanduser(), (source, native, output))
    if any(p.is_symlink() for p in (root, library, destination)):
        raise ValueError("No symlinked source, library or output")
    root, library, destination = root.resolve(), library.resolve(), destination.resolve()
    if not root.is_dir() or not library.is_file() or library.parent != root:
        raise ValueError("Native SNES candidate not compiled in exact source checkout")
    if library.name != NATIVE_BY_TARGET[target] or library.stat().st_size < 50000:
        raise ValueError("Native Supafaust library name or size invalid")
    with library.open("rb") as native_stream:
        magic = native_stream.read(4)
    if not any(magic.startswith(signature) for signature in HEADER_BY_TARGET[target]):
        if target == "linux-x64":
            raise ValueError("Only actual Linux ELF research builds accepted")
        raise ValueError("Compiled native library header does not match target architecture")
    if destination.exists() and (
            not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Must provide an empty, new evidence destination")
    if destination == root or destination in root.parents or root in destination.parents:
        raise ValueError("Evidence output and source checkout must be distinct")
    if git(root, "rev-parse", "HEAD") != COMMIT:
        raise ValueError("Source revision not exactly pinned")
    upstream = git(root, "remote", "get-url", "origin").rstrip("/").removesuffix(".git")
    if upstream != REPOSITORY:
        raise ValueError("Unexpected original source repository")
    status = git(root, "status", "--porcelain", "--untracked-files=no")
    source_patch_bytes = None
    if target.startswith("macos-"):
        # Darwin has no sem_timedwait. Accept a documented SINGLE source
        # change and retain the actual Git diff beside original source.
        if status != f"M {MAC_SEM_PATH}":
            raise ValueError("macOS candidate missing exactly one reviewed config.h source patch")
        original_header = git(root, "show", f"HEAD:{MAC_SEM_PATH}", binary=True)
        if original_header.count(MAC_SEM_BEFORE.encode("utf-8")) != 1:
            raise ValueError("Upstream semaphore guard changed")
        expected_header = original_header.replace(
            MAC_SEM_BEFORE.encode("utf-8"), MAC_SEM_AFTER.encode("utf-8"), 1)
        if (root / MAC_SEM_PATH).read_bytes() != expected_header:
            raise ValueError("Unexpected modified GPL source beyond exact Mac semaphore fix")
        source_patch_bytes = git(root, "diff", "--", MAC_SEM_PATH, binary=True)
        if not source_patch_bytes:
            raise ValueError("Missing reproducible original source patch Git diff")
    elif status:
        raise ValueError("Tracked upstream SNES source changed during build")
    license_file, licensing_code = root / ORIGINAL_LICENSE, root / LICENSE_SOURCE
    if any(not p.is_file() or p.is_symlink() for p in (license_file, licensing_code)):
        raise ValueError("Original GPL license or its source-level grant is missing")
    license_bytes = license_file.read_bytes()
    source_grant = licensing_code.read_bytes()
    if (b"GNU GENERAL PUBLIC LICENSE" not in license_bytes
            or b"Version 2" not in license_bytes
            or b"either version 2" not in source_grant
            or b"any later version" not in source_grant):
        raise ValueError("Original GPL version 2 or later permission not verified")
    raw = git(root, "archive", "--format=tar", "HEAD", binary=True)
    if not raw or len(raw) > MAX_UNCOMPRESSED_SOURCE:
        raise ValueError("Pinned original Git source archive missing or oversized")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
        paths = set(tar.getnames())
        if not {ORIGINAL_LICENSE, LICENSE_SOURCE, "Makefile"} <= paths:
            raise ValueError("Source archive lacks verified GPL and build inputs")
    zipped = gzip.compress(raw, compresslevel=6, mtime=0)
    original_native = library.read_bytes()
    destination.mkdir(parents=True, exist_ok=True)
    tar_name = f"supafaust-{COMMIT}-source.tar.gz"
    (destination / tar_name).write_bytes(zipped)
    shutil.copyfile(library, destination / library.name)
    (destination / "SUPAFAUST_ORIGINAL_GPL2_LICENSE.txt").write_bytes(license_bytes)
    if source_patch_bytes is not None:
        (destination / "SUPAFAUST_MACOS_SOURCE_PATCH_UNAPPROVED.diff").write_bytes(
            source_patch_bytes)
    evidence = {
        "schema_version": 1,
        "status": "UNAPPROVED-GPL2-OR-LATER-SUPAFAUST-RESEARCH",
        "target": target,
        "source_repository": REPOSITORY,
        "source_commit": COMMIT,
        "source_archive": tar_name,
        "source_archive_sha256": hashlib.sha256(zipped).hexdigest(),
        "source_archive_bytes": len(zipped),
        "native_name": library.name,
        "native_sha256": hashlib.sha256(original_native).hexdigest(),
        "native_bytes": len(original_native),
        "original_license_sha256": hashlib.sha256(license_bytes).hexdigest(),
        "source_level_license_notice": LICENSE_SOURCE,
        "compiled_from_exact_upstream_checkout": True,
        "original_source_modified_for_macos": source_patch_bytes is not None,
        "reproducible_macos_source_patch_filename": (
            "SUPAFAUST_MACOS_SOURCE_PATCH_UNAPPROVED.diff"
            if source_patch_bytes is not None else None),
        "reproducible_macos_source_patch_sha256": (
            hashlib.sha256(source_patch_bytes).hexdigest()
            if source_patch_bytes is not None else None),
        "replaces_current_snes9x_in_app": False,
        "independently_reproducible_binary_reviewed": False,
        "source_dependent_licenses_reviewed": False,
        "complete_combined_core_license_reviewed": False,
        "real_4_os_hardware_gameplay_approved": False,
        "public_binary_redistribution_approved": False,
    }
    (destination / "SUPAFAUST_SOURCE_BUILD_UNAPPROVED.json").write_bytes(
        (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    entries = []
    for p in sorted(destination.iterdir()):
        if p.name != "SHA256SUMS.txt":
            entries.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
    (destination / "SHA256SUMS.txt").write_text(
        "\n".join(entries) + "\n", encoding="ascii")
    return evidence


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--target", choices=sorted(NATIVE_BY_TARGET), default="linux-x64")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        evidence = capture(source=args.source, native=args.native, output=args.output, target=args.target)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError,
            tarfile.TarError) as exc:
        p.exit(1, f"PINNED SUPAFAUST SOURCE REJECTED: {exc}\n")
    print(f"GPLv2+ candidate source SHA {evidence['source_commit']}; "
          f"native SHA {evidence['native_sha256']}; public release NOT APPROVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
