"""Download the two platform-matched Libretro cores used by Anything Plays.

Native cores are fetched *when building*, never when the app is running. Every
build records the downloaded binary's SHA-256 and source URL so maintainers can
identify exactly which nightly binaries entered a particular installer.

A hash manifest is provenance, not a substitute for upstream source archives,
license compliance, or reproducible pinned builds.
"""

from datetime import datetime, timezone
import hashlib
import io
import json
import platform
from pathlib import Path
import sys
from urllib import request
import zipfile

BUILD_BOT = "https://buildbot.libretro.com/nightly"
CORE_NAMES = ("mgba", "snes9x")
MAX_ARCHIVE_SIZE = 30 * 1024 * 1024
MAX_BINARY_SIZE = 60 * 1024 * 1024
CORE_FOLDER = Path(__file__).resolve().parent / "cores"


def build_target(platform_name=None, architecture=None):
    """Resolve the Libretro buildbot directory and OS library extension."""
    platform_name = sys.platform if platform_name is None else platform_name
    architecture = (platform.machine() if architecture is None else architecture).lower()

    if platform_name == "win32":
        if architecture not in ("amd64", "x86_64"):
            raise ValueError(f"Unsupported Windows architecture: {architecture} (x64 required)")
        return "windows/x86_64/latest", ".dll"
    if platform_name == "darwin":
        if architecture not in ("arm64", "x86_64"):
            raise ValueError(f"Unsupported macOS architecture: {architecture}")
        return f"apple/osx/{architecture}/latest", ".dylib"
    if platform_name.startswith("linux"):
        if architecture in ("x86_64", "amd64"):
            return "linux/x86_64/latest", ".so"
        if architecture in ("i386", "i686"):
            return "linux/x86/latest", ".so"
        raise ValueError(f"Unsupported Linux architecture: {architecture}")
    raise ValueError(f"Unsupported platform: {platform_name}")


def _validate_binary(content, extension):
    """Reject an HTML error page or a library for the wrong operating system."""
    magic = content[:4]
    allowed = {
        ".dll": (b"MZ",),
        ".so": (b"\x7fELF",),
        ".dylib": (
            b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",
            b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf",
        ),
    }
    if not any(content.startswith(signature) for signature in allowed[extension]):
        raise ValueError(f"Downloaded file is not a valid {extension} native library")


def fetch_core(name, destination=CORE_FOLDER):
    """Download one core and return its name, URL, size and binary SHA-256."""
    if name not in CORE_NAMES:
        raise ValueError(f"Unknown emulator core: {name}")
    folder, extension = build_target()
    filename = f"{name}_libretro{extension}"
    url = f"{BUILD_BOT}/{folder}/{filename}.zip"
    destination = Path(destination)
    print(f"Fetching {name}: {url}", flush=True)

    download = request.Request(
        url, headers={"User-Agent": "AnythingPlays-build/2.0.0"}
    )
    with request.urlopen(download, timeout=45) as response:
        archive_data = response.read(MAX_ARCHIVE_SIZE + 1)
    if len(archive_data) > MAX_ARCHIVE_SIZE:
        raise ValueError("Core archive exceeds 30 MB")

    with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
        candidates = [
            item for item in archive.infolist()
            if Path(item.filename).name == filename and not item.is_dir()
        ]
        if len(candidates) != 1:
            raise ValueError(f"Expected exactly one {filename} in the archive")
        item = candidates[0]
        if not 10_000 < item.file_size < MAX_BINARY_SIZE:
            raise ValueError("Unexpected core binary size")
        content = archive.read(item)

    _validate_binary(content, extension)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / filename
    target.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    print(f"{name} ready: {target} ({len(content):,} bytes)", flush=True)
    return {"name": name, "file": filename, "source_url": url,
            "sha256": digest, "size_bytes": len(content)}


def fetch_all(destination=CORE_FOLDER):
    """Retrieve every required core and write a per-build provenance manifest."""
    destination = Path(destination)
    binaries = [fetch_core(name, destination) for name in CORE_NAMES]
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "build_platform": sys.platform,
        "build_architecture": platform.machine(),
        "note": "Latest nightly downloads; source revisions are not pinned.",
        "cores": binaries,
    }
    (destination / "CORE_PROVENANCE.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    try:
        fetch_all()
    except Exception as exc:
        sys.exit(f"ERROR: {exc}\nBuild stopped; retry when online.")
