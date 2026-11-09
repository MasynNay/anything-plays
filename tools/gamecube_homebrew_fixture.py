"""Prepare an independently licensed GameCube homebrew CI smoke fixture.

This project does NOT bundle any Nintendo games, firmware, or test ROMs in
its application installers. For native integration checks, CI can fetch an
open-source GameCube controller-test homebrew release from a fixed URL,
verify its archive hash, and extract one DOL into a temporary location.

The first --inspect run records a *candidate hash only* and does not run or
install its binary. Commit a reviewed SHA-256 before allowing extraction.
The source project reports the zlib license; review it before reusing binary
artifacts in tests. Never bundle the fixture in the Anything Plays installer.
"""
import argparse
import hashlib
import io
from pathlib import Path, PurePosixPath
import urllib.request
import zipfile

SOURCE_URL = (
    "https://github.com/corenting/GC-Controller-Test/"
    "releases/download/v1.2/gc-1-2.zip"
)
# Pinned from the fixed v1.2 GitHub release in the 2.1 CI review on
# 2026-11-07. The upstream project states zlib licensing; this binary is
# used only as a short-lived CI fixture and is never redistributed.
PINNED_SHA256 = "5b6ebacd90791f7d1dfd7bad5c3b962f9ff03664131e45c00e31720e7f881905"
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024
MAX_DOL_BYTES = 4 * 1024 * 1024


def fetch_fixture():
    """Download a bounded archive from an approved, immutable release URL."""
    req = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "AnythingPlays-2.1-source-smoke/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        content = response.read(MAX_ARCHIVE_BYTES + 1)
    if len(content) < 32 or len(content) > MAX_ARCHIVE_BYTES:
        raise ValueError("Homebrew test release archive exceeds safety budget")
    return content


def inspect_archive(content):
    """Return archive identity and possible DOL test executables."""
    digest = hashlib.sha256(content).hexdigest()
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = []
        for info in archive.infolist():
            path = PurePosixPath(info.filename.replace("\\", "/"))
            if (path.is_absolute() or ".." in path.parts or
                    info.file_size > MAX_DOL_BYTES):
                raise ValueError("Unsafe or oversized homebrew fixture entry")
            if path.suffix.lower() == ".dol" and not info.is_dir():
                names.append(info.filename)
    if len(names) != 1:
        raise ValueError(f"Expected one GameCube homebrew DOL, got {len(names)}")
    return digest, names[0]


def verified_homebrew(destination):
    """Extract into a temporary CI folder, only when the exact hash is pinned."""
    data = fetch_fixture()
    digest, member = inspect_archive(data)
    if not PINNED_SHA256 or digest != PINNED_SHA256:
        raise ValueError(
            "Homebrew fixture hash not reviewed/approved: " + digest
        )
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        payload = archive.read(member)
    if not payload or len(payload) > MAX_DOL_BYTES:
        raise ValueError("Empty or oversized homebrew test executable")
    target.write_bytes(payload)
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.inspect:
        content = fetch_fixture()
        digest, member = inspect_archive(content)
        print(f"Review candidate fixture SHA256: {digest}")
        print(f"Review candidate DOL entry: {member}")
        print("Candidate only: no executable was run or installed.")
        return
    if not args.output:
        parser.error("--output is required when extracting a pinned fixture")
    print(f"Prepared verified test fixture: {verified_homebrew(args.output)}")


if __name__ == "__main__":
    main()
