"""Pinned, public-domain Nintendo 64 homebrew CI fixture.

Christopher Bonhage's SaveTest-N64 is Unlicensed/public-domain software.
The file is fetched only inside disposable CI tests, never shipped with
Anything Plays. Pin both the upstream commit and exact Git blob object;
do not execute or install unreviewed binaries.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_COMMIT = "74235925e30d21f89e68151f554bdb577cdbcf37"
SOURCE_URL = (
    "https://raw.githubusercontent.com/meeq/SaveTest-N64/"
    + SOURCE_COMMIT + "/savetest.z64"
)
GIT_BLOB_SHA1 = "ddf6d3bd484556db0a3c35e72a359b8201b2255f"
ROM_BYTES = 1064960
MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024
N64_MAGIC = bytes.fromhex("80371240")


def checked_rom(data: bytes) -> dict:
    """Validate size, header and Git's length-delimited blob identity."""
    if len(data) != ROM_BYTES or len(data) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Nintendo 64 fixture has unexpected length")
    if not data.startswith(N64_MAGIC):
        raise ValueError("Nintendo 64 fixture has incorrect ROM byte order/header")
    git_blob = hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()
    if git_blob != GIT_BLOB_SHA1:
        raise ValueError("Nintendo 64 fixture differs from reviewed upstream blob")
    return {
        "source_commit": SOURCE_COMMIT,
        "git_blob_sha1": git_blob,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "license": "Unlicense (public domain)",
    }


def verified_homebrew(destination: Path) -> dict:
    """Fetch bounded test-only bytes and store them under a caller-owned temp dir."""
    req = Request(SOURCE_URL, headers={"User-Agent": "AnythingPlays-2.1-CI"})
    with urlopen(req, timeout=30) as response:
        data = response.read(MAX_DOWNLOAD_BYTES + 1)
    manifest = checked_rom(data)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise ValueError("Refusing to overwrite a symlink with the test fixture")
    destination.write_bytes(data)
    return manifest
