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

REPOSITORY = "https://github.com/libretro/supafaust"
COMMIT = "642d1d1b6684aa7e306a02a89885f3f5456a5157"
BINARY = "mednafen_supafaust_libretro.so"
ORIGINAL_LICENSE = "COPYING"
LICENSE_SOURCE = "mednafen/snes_faust/snes.cpp"
MAX_UNCOMPRESSED_SOURCE = 128 * 1024 * 1024


def git(root, *args, binary=False):
    run = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True,
        check=True, timeout=40,
    )
    return run.stdout if binary else run.stdout.decode("utf-8").strip()


def capture(*, source, native, output):
    root, library, destination = map(
        lambda s: Path(s).expanduser(), (source, native, output))
    if any(p.is_symlink() for p in (root, library, destination)):
        raise ValueError("No symlinked source, library or output")
    root, library, destination = root.resolve(), library.resolve(), destination.resolve()
    if not root.is_dir() or not library.is_file() or library.parent != root:
        raise ValueError("Native SNES candidate not compiled in exact source checkout")
    if library.name != BINARY or library.stat().st_size < 50000:
        raise ValueError("Native Supafaust library name or size invalid")
    if library.open("rb").read(4) != b"\x7fELF":
        raise ValueError("Only actual Linux ELF research builds accepted")
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
    if git(root, "status", "--porcelain", "--untracked-files=no"):
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
    shutil.copyfile(library, destination / BINARY)
    (destination / "SUPAFAUST_ORIGINAL_GPL2_LICENSE.txt").write_bytes(license_bytes)
    evidence = {
        "schema_version": 1,
        "status": "UNAPPROVED-GPL2-OR-LATER-SUPAFAUST-RESEARCH",
        "source_repository": REPOSITORY,
        "source_commit": COMMIT,
        "source_archive": tar_name,
        "source_archive_sha256": hashlib.sha256(zipped).hexdigest(),
        "source_archive_bytes": len(zipped),
        "native_name": BINARY,
        "native_sha256": hashlib.sha256(original_native).hexdigest(),
        "native_bytes": len(original_native),
        "original_license_sha256": hashlib.sha256(license_bytes).hexdigest(),
        "source_level_license_notice": LICENSE_SOURCE,
        "compiled_from_exact_upstream_checkout": True,
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
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        evidence = capture(source=args.source, native=args.native, output=args.output)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError,
            tarfile.TarError) as exc:
        p.exit(1, f"PINNED SUPAFAUST SOURCE REJECTED: {exc}\n")
    print(f"GPLv2+ candidate source SHA {evidence['source_commit']}; "
          f"native SHA {evidence['native_sha256']}; public release NOT APPROVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
