"""Stage a clean, exact Anything Plays 3.0 public application asset list.

NO publication or approval occurs. This fail-closed tool accepts precisely
four installer files for the given semantic version and generates one
SHA256SUMS.txt. Emulator core ZIPs, diagnostic logs, source archives, build
provenance and test evidence must NOT be mixed with app downloads.

Only run for a real user release *after* the external license/source review,
platform signing and release acceptance gate have passed. Application cores
remain on their separate, fully approved catalog channel.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import shutil
import sys

VERSION = re.compile(r"^3\.0\.\d+$")
CHUNK = 1024 * 1024


def expected_installers(version):
    if not VERSION.fullmatch(version):
        raise ValueError("Only stable 3.0.x application release versions are allowed")
    return (
        f"AnythingPlaysSetup-{version}.exe",
        f"AnythingPlays-{version}-macos-arm64.dmg",
        f"AnythingPlays-{version}-macos-x64.dmg",
        f"anything-plays_{version}_amd64.deb",
    )


def stage_application_assets(input_dir, output_dir, *, version, strict=True):
    """Check *all* inputs before creating/mutating an output directory."""
    names = expected_installers(version)
    # Check the original paths before resolving. Path.resolve() follows
    # symlinks; checking is_symlink() afterward would miss a redirected
    # output destination and could put release files in an unexpected folder.
    input_path = Path(input_dir).expanduser()
    output_path = Path(output_dir).expanduser()
    if input_path.is_symlink() or output_path.is_symlink():
        raise ValueError("Release source and destination cannot be symlinks")
    input_dir = input_path.resolve()
    output_dir = output_path.resolve()
    if not input_dir.is_dir():
        raise FileNotFoundError("No application build directory")
    if input_dir == output_dir or input_dir in output_dir.parents or output_dir in input_dir.parents:
        raise ValueError("Source and clean release staging directories must be separate")
    if output_dir.exists():
        if any(output_dir.iterdir()):
            raise ValueError("Release staging directory must be new or empty")
    candidates = {}
    for name in names:
        path = input_dir / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError("Missing valid, nonempty 3.0 installer: " + name)
        candidates[name] = path
    if strict:
        extra = [
            p.name for p in input_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".exe", ".dmg", ".deb")
            and p.name not in names
        ]
        if extra:
            raise ValueError("Unexpected installer files: " + ", ".join(sorted(extra)))
    output_dir.mkdir(parents=True, exist_ok=True)
    digests = []
    for name in names:
        source, destination = candidates[name], output_dir / name
        shutil.copyfile(source, destination)
        h = hashlib.sha256()
        with destination.open("rb") as stream:
            for part in iter(lambda: stream.read(CHUNK), b""):
                h.update(part)
        digests.append(f"{h.hexdigest()}  {name}")
    checksums = output_dir / "SHA256SUMS.txt"
    checksums.write_text("\n".join(digests) + "\n", encoding="utf-8")
    result = [*names, checksums.name]
    if sorted(p.name for p in output_dir.iterdir()) != sorted(result):
        raise RuntimeError("Unexpected file appeared during release staging")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = stage_application_assets(
            args.input, args.output, version=args.version
        )
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"NOT STAGED: {exc}\n")
    print("PREPARED LOCALLY (NOT APPROVED OR PUBLISHED):")
    for name in result:
        print("  " + name)
    print("Do not publish until all release QA and third-party license "
          "obligations have been independently verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
