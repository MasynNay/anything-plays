"""Download the two platform-matched Libretro cores used by Anything Plays.

Native cores are fetched *when building*, never when the app is running. Every
build records the downloaded binary's SHA-256, source URL, reported core
version and embedded source revision, when present, so maintainers can trace
which nightly binaries entered a particular installer.

A hash manifest is provenance, not a substitute for upstream source archives,
license compliance, or reproducible pinned builds.
"""

from datetime import datetime, timezone
import ctypes as C
import hashlib
import io
import os
import json
import platform
import re
from pathlib import Path
import sys
from urllib import request
import zipfile

BUILD_BOT = "https://buildbot.libretro.com/nightly"
CORE_NAMES = ("mgba", "snes9x")
# Only on the 2.1 testing branch; never silently add cores to the
# already approved v2.0.0 release lock.
OPTIONAL_V21_CORES = ("fceumm", "genesis_plus_gx", "parallel_n64")


def core_names_for_build():
    if os.environ.get("AP_V21_TEST_CORES", "") == "1":
        if os.environ.get("AP_RELEASE_BUILD") == "1":
            raise ValueError("Unapproved 2.1 test cores cannot enter the v2.0 release path")
        return (*CORE_NAMES, *OPTIONAL_V21_CORES)
    return CORE_NAMES
MAX_ARCHIVE_SIZE = 30 * 1024 * 1024
MAX_BINARY_SIZE = 60 * 1024 * 1024
CORE_FOLDER = Path(__file__).resolve().parent / "cores"

SOURCE_REPOSITORIES = {
    "mgba": "https://github.com/libretro/mgba",
    "snes9x": "https://github.com/libretro/snes9x",
    "fceumm": "https://github.com/libretro/libretro-fceumm",
    "genesis_plus_gx": "https://github.com/libretro/Genesis-Plus-GX",
    "parallel_n64": "https://github.com/libretro/parallel-n64",
}


class _LibretroCoreInfo(C.Structure):
    """The stable retro_system_info structure from the Libretro ABI."""

    _fields_ = [
        ("library_name", C.c_char_p),
        ("library_version", C.c_char_p),
        ("valid_extensions", C.c_char_p),
        ("need_fullpath", C.c_bool),
        ("block_extract", C.c_bool),
    ]


def reported_git_revision(version):
    """Extract the short source revision advertised by a core, if provided."""
    match = re.search(r"(?<![0-9a-f])([0-9a-f]{7,40})$", version.lower())
    return match.group(1) if match else None


def inspect_core_identity(path, name):
    """Read a downloaded native core's identity without loading game content.

    Version-embedded hashes are the core's self-report, not independent proof
    of its build inputs. Keep exact binary hashes alongside this information.
    """
    if name not in SOURCE_REPOSITORIES:
        raise ValueError(f"Unknown core: {name}")
    library = C.CDLL(str(Path(path).resolve()))
    describe = library.retro_get_system_info
    describe.argtypes = [C.POINTER(_LibretroCoreInfo)]
    describe.restype = None
    info = _LibretroCoreInfo()
    describe(C.byref(info))
    library_name = (info.library_name or b"").decode("utf-8", "replace")
    version = (info.library_version or b"").decode("utf-8", "replace")
    if not library_name or not version:
        raise ValueError(f"Native core {name} does not expose version metadata")
    revision = reported_git_revision(version)
    repository = SOURCE_REPOSITORIES[name]
    return {
        "libretro_library_name": library_name,
        "libretro_library_version": version,
        "reported_source_revision": revision,
        "source_repository_url": repository,
        "reported_source_commit_url": (f"{repository}/commit/{revision}" if revision else None),
    }


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


def _read_core_archive(url, filename):
    """Read a Libretro ZIP from an offline release archive or the dev buildbot.

    Public release builds must never fetch mutable nightly URLs. The calling
    code separately checks the extracted native binary's approved SHA-256
    before writing it to disk or loading it via ctypes.
    """
    release_mode = os.environ.get("AP_RELEASE_BUILD", "0")
    if release_mode not in ("0", "1"):
        raise ValueError("AP_RELEASE_BUILD must be 0 or 1")
    archive_directory = os.environ.get("AP_CORE_ARCHIVE_DIR", "").strip()
    if release_mode == "1" and not archive_directory:
        raise ValueError(
            "Release builds require AP_CORE_ARCHIVE_DIR with preserved core ZIPs; "
            "mutable nightly downloads are forbidden"
        )

    if archive_directory:
        archive_path = Path(archive_directory).expanduser() / f"{filename}.zip"
        if archive_path.is_symlink():
            raise ValueError(f"Refusing symlinked core archive: {archive_path}")
        if not archive_path.is_file():
            raise FileNotFoundError(f"Required offline core archive missing: {archive_path}")
        print(f"Reading preserved core ZIP: {archive_path}", flush=True)
        with archive_path.open("rb") as handle:
            data = handle.read(MAX_ARCHIVE_SIZE + 1)
    else:
        download = request.Request(
            url, headers={"User-Agent": "AnythingPlays-build/2.0.0"}
        )
        with request.urlopen(download, timeout=45) as response:
            data = response.read(MAX_ARCHIVE_SIZE + 1)

    if len(data) > MAX_ARCHIVE_SIZE:
        raise ValueError("Core archive exceeds 30 MB")
    return data


def fetch_core(name, destination=CORE_FOLDER):
    """Acquire one core and record its binary SHA-256 and upstream identity."""
    if name not in core_names_for_build():
        raise ValueError(f"Unapproved emulator core for this build: {name}")
    folder, extension = build_target()
    filename = f"{name}_libretro{extension}"
    url = f"{BUILD_BOT}/{folder}/{filename}.zip"
    destination = Path(destination)
    print(f"Preparing {name}; upstream reference: {url}", flush=True)

    archive_data = _read_core_archive(url, filename)

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
    digest = hashlib.sha256(content).hexdigest()
    archive_digest = hashlib.sha256(archive_data).hexdigest()
    release_mode = os.environ.get("AP_RELEASE_BUILD", "0")
    if release_mode not in ("0", "1"):
        raise ValueError("AP_RELEASE_BUILD must be 0 or 1")
    if release_mode == "1":
        # Enforce binary integrity before writing or executing a native core.
        from tools.core_release_lock import LOCK_PATH, verify_download_before_loading

        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        verify_download_before_loading(
            lock, sys.platform, platform.machine(), name,
            filename, url, len(content), digest,
        )
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / filename
    target.write_bytes(content)
    identity = inspect_core_identity(target, name)
    # Preserve exact ZIP bytes separately from the extracted core when a
    # candidate audit explicitly requests them. Capturing never approves them.
    capture_directory = os.environ.get("AP_CORE_ARCHIVE_CAPTURE_DIR", "").strip()
    if capture_directory:
        archive_folder = Path(capture_directory).expanduser()
        if archive_folder.is_symlink():
            raise ValueError("Refusing symlinked core archive capture directory")
        archive_folder.mkdir(parents=True, exist_ok=True)
        archive_path = archive_folder / f"{filename}.zip"
        if archive_path.is_symlink():
            raise ValueError("Refusing symlinked captured core archive")
        archive_path.write_bytes(archive_data)
        print(f"Preserved candidate ZIP {archive_path} sha256={archive_digest}",
              flush=True)
    print(f"{name} ready: {target} ({len(content):,} bytes), "
          f"reported version {identity['libretro_library_version']}", flush=True)
    return {"name": name, "file": filename, "source_url": url,
            "sha256": digest, "size_bytes": len(content),
            "archive_sha256": archive_digest, "archive_size_bytes": len(archive_data),
            **identity}


def fetch_all(destination=CORE_FOLDER):
    """Retrieve every required core and write a per-build provenance manifest."""
    destination = Path(destination)
    binaries = [fetch_core(name, destination) for name in core_names_for_build()]
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "build_platform": sys.platform,
        "build_architecture": platform.machine(),
        "note": (
            "Local preserved core ZIPs; extracted binaries must match approved hashes."
            if os.environ.get("AP_CORE_ARCHIVE_DIR", "").strip()
            else "Latest nightly downloads; source revisions are not pinned."
        ),
        "cores": binaries,
    }
    (destination / "CORE_PROVENANCE.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    from tools.core_release_lock import (
        LOCK_PATH, candidate_fingerprint, verify_release_lock,
    )
    release_mode = os.environ.get("AP_RELEASE_BUILD", "0")
    if release_mode not in ("0", "1"):
        raise ValueError("AP_RELEASE_BUILD must be 0 or 1")
    if release_mode == "1":
        # Only the four approved v2.0 release architectures are allowed here.
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        target = verify_release_lock(manifest, lock)
        print(f"Release core lock verified for {target}", flush=True)
    else:
        # Development still supports architectures outside the public
        # release matrix (for example, 32-bit Linux builds).
        try:
            candidate = candidate_fingerprint(manifest)
        except ValueError as exc:
            print(f"Development-only core build (not a release target): {exc}", flush=True)
        else:
            print("Core build candidate (NOT approved for public distribution):")
            print(json.dumps(candidate, sort_keys=True), flush=True)
    return manifest


if __name__ == "__main__":
    try:
        fetch_all()
    except Exception as exc:
        sys.exit(f"ERROR: {exc}\nBuild stopped; retry when online.")
