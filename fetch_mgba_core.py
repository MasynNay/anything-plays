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
import subprocess
from pathlib import Path
import sys
from urllib import request
import zipfile

BUILD_BOT = "https://buildbot.libretro.com/nightly"
CORE_NAMES = ("mgba", "snes9x")
# Only on the 2.1 testing branch; never silently add cores to the
# already approved v2.0.0 release lock.
OPTIONAL_V21_CORES = (
    "fceumm", "genesis_plus_gx", "parallel_n64", "dolphin",
    "stella2014", "prosystem", "mednafen_pce_fast",
    "mednafen_ngp", "mednafen_wswan",
)
# Explicit research-only full offline 3.0 preview: still 18 consoles and 11
# native Libretro core slots, but NO Snes9x/Genesis Plus GX binary. The
# replacement cores are validated source-built artifacts, never nightly.
V30_GPL_TRIAL_CORES = (
    "mgba", "mednafen_supafaust", "fceumm", "blastem", "parallel_n64",
    "dolphin", "stella2014", "prosystem", "mednafen_pce_fast",
    "mednafen_ngp", "mednafen_wswan",
)


def core_names_for_build():
    # Official 3.0 is a completely separate, 11-core release lane.
    if os.environ.get("AP_V30_GPL_TRIAL") == "1":
        if (os.environ.get("AP_RELEASE_BUILD", "0") != "0"
                or os.environ.get("AP_V30_APPROVED_RELEASE", "0") != "0"
                or os.environ.get("AP_V30_TEST_CORES") != "1"
                or not os.environ.get("AP_CORE_ARCHIVE_DIR", "").strip()):
            raise ValueError("GPL alternative trial requires offline, unapproved 11-core preview only")
        if len(V30_GPL_TRIAL_CORES) != 11 or len(set(V30_GPL_TRIAL_CORES)) != 11:
            raise ValueError("GPL alternative trial core inventory changed")
        # Same 18 profiles and eleven native images, Tia replaces the one
        # GPLv2-only Stella2014 only when an exact original source/AV marker
        # is present and checked. Never affect the stable v2 lanes.
        if os.environ.get("AP_V30_TIA_TRIAL") == "1":
            return tuple("tia" if name == "stella2014" else name
                         for name in V30_GPL_TRIAL_CORES)
        return V30_GPL_TRIAL_CORES
    # A tampered environment flag cannot substitute for the approved
    # per-architecture binary/source/license lock.
    if os.environ.get("AP_V30_APPROVED_RELEASE") == "1":
        if os.environ.get("AP_RELEASE_BUILD") != "1":
            raise ValueError("3.0 approved cores require release build mode")
        from tools.v30_release_lock import load_approved_lock, ordered_core_names_for_lock
        reviewed = load_approved_lock()
        return ordered_core_names_for_lock(reviewed)
    # Optional downloadable cores are packaged separately. Never fetch
    # Dolphin here: it depends on system assets and failed gameplay QA.
    if any(os.environ.get(flag, "") == "1" for flag in ("AP_V30_CORE_PACK_BUILD", "AP_V21_CORE_PACK_BUILD")):
        if os.environ.get("AP_RELEASE_BUILD") == "1":
            raise ValueError("Unreviewed optional packs cannot enter v2.0 release")
        return ("snes9x", *(name for name in OPTIONAL_V21_CORES if name != "dolphin"))
    # On 2.1 only, the starter installer ships mGBA for GB/GBC/GBA.
    # Unset: stable v2.0's two-core build remains unchanged.
    if any(os.environ.get(flag, "") == "1" for flag in ("AP_V30_MINIMAL_CORE_BUILD", "AP_V21_MINIMAL_CORE_BUILD")):
        if os.environ.get("AP_RELEASE_BUILD") == "1":
            raise ValueError("2.1 minimal build is not an approved v2.0 release")
        return ("mgba",)
    if any(os.environ.get(flag, "") == "1" for flag in ("AP_V30_TEST_CORES", "AP_V21_TEST_CORES")):
        if os.environ.get("AP_RELEASE_BUILD") == "1":
            raise ValueError("Unapproved 3.0 test cores cannot enter the v2.0 release path")
        return (*CORE_NAMES, *OPTIONAL_V21_CORES)
    return CORE_NAMES
MAX_ARCHIVE_SIZE = 30 * 1024 * 1024
MAX_BINARY_SIZE = 60 * 1024 * 1024
CORE_FOLDER = Path(__file__).resolve().parent / "cores"

SOURCE_REPOSITORIES = {
    "mgba": "https://github.com/libretro/mgba",
    "snes9x": "https://github.com/libretro/snes9x",
    "mednafen_supafaust": "https://github.com/libretro/supafaust",
    "blastem": "https://github.com/libretro/blastem",
    "fceumm": "https://github.com/libretro/libretro-fceumm",
    "genesis_plus_gx": "https://github.com/libretro/Genesis-Plus-GX",
    "parallel_n64": "https://github.com/libretro/parallel-n64",
    "dolphin": "https://github.com/libretro/dolphin",
    "stella2014": "https://github.com/libretro/stella2014-libretro",
    "tia": "https://github.com/warmenhoven/tia",
    "prosystem": "https://github.com/libretro/prosystem-libretro",
    "mednafen_pce_fast": "https://github.com/libretro/beetle-pce-fast-libretro",
    "mednafen_ngp": "https://github.com/libretro/beetle-ngp-libretro",
    "mednafen_wswan": "https://github.com/libretro/beetle-wswan-libretro",
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


def _inspect_core_identity_in_process(path, name):
    """Read core metadata directly; call in a child on Windows to release DLLs.

    Version-embedded hashes are the core's self-report, not independent proof
    of its build inputs. Keep exact binary hashes alongside this information.
    """
    if name not in SOURCE_REPOSITORIES:
        raise ValueError(f"Unknown core: {name}")
    if (os.name == "nt" and os.environ.get("AP_V30_APPROVED_RELEASE") == "1"
            and name in ("mednafen_supafaust", "blastem", "mednafen_pce_fast")):
        from anything_plays.v30_approved_core_map import enable_windows_offline_runtime
        # The archive and DLL fingerprint have already passed the reviewed
        # native lock. All remaining core binaries may not yet be extracted.
        enable_windows_offline_runtime(Path(path).parent, verify_native=False)
    if os.name == "nt" and os.environ.get("AP_V30_GPL_TRIAL") == "1":
        # Original Windows Supafaust/BlastEm use MinGW winpthread. Python
        # excludes PATH during ctypes dependency lookup; use the exact
        # bundled SHA-verified runtime without requiring user-installed MSYS2.
        from anything_plays.v30_gpl_trial import enable_windows_trial_runtime
        enable_windows_trial_runtime(Path(path).parent)
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



def _inspect_core_identity_isolated(path, name):
    """Inspect a Windows DLL in a disposable Python process.

    ctypes.CDLL keeps the library loaded for the parent process's lifetime.
    Windows will then reject deleting or updating the source DLL, even after
    a core is copied into an immutable user-owned pack. A short-lived child
    is both safer for arbitrary native code and guarantees its handle exits.
    """
    if name not in SOURCE_REPOSITORIES:
        raise ValueError(f"Unknown core: {name}")
    script = (
        "import json,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "from fetch_mgba_core import _inspect_core_identity_in_process;"
        "value=_inspect_core_identity_in_process(sys.argv[2],sys.argv[3]);"
        "print('AP_NATIVE_IDENTITY='+json.dumps(value,sort_keys=True))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script,
         str(Path(__file__).resolve().parent), str(Path(path).resolve()), name],
        capture_output=True, text=True, timeout=20, check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"Native core identity inspection failed for {name}: "
            + (result.stderr or result.stdout)[-900:]
        )
    for line in reversed(result.stdout.splitlines()):
        if line.startswith("AP_NATIVE_IDENTITY="):
            value = json.loads(line.partition("=")[2])
            if (not isinstance(value, dict)
                    or not isinstance(value.get("libretro_library_name"), str)
                    or not isinstance(value.get("libretro_library_version"), str)):
                break
            return value
    raise ValueError(f"No valid native core identity from {name}")


def inspect_core_identity(path, name):
    """Return metadata without pinning a Windows core DLL in the parent."""
    if sys.platform == "win32":
        return _inspect_core_identity_isolated(path, name)
    return _inspect_core_identity_in_process(path, name)


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
    if os.environ.get("AP_V30_GPL_TRIAL") == "1" and name in ("mednafen_supafaust", "blastem"):
        # The trial inputs originate from original immutable upstream-source
        # CI artifacts, NOT a mutable Libretro nightly/buildbot ZIP.
        url = ("https://github.com/MasynNay/anything-plays/actions/runs/"
               + ("42494297281" if name == "mednafen_supafaust" else "42496671418"))
    if os.environ.get("AP_V30_TIA_TRIAL") == "1" and name == "tia":
        url = "https://github.com/warmenhoven/tia/tree/6ae5bf998fe7a7842294089db17fc86fd73db1f0"
    destination = Path(destination)
    print(f"Preparing {name}; upstream reference: {url}", flush=True)

    archive_data = _read_core_archive(url, filename)
    v30_release = (
        os.environ.get("AP_RELEASE_BUILD") == "1"
        and os.environ.get("AP_V30_APPROVED_RELEASE") == "1"
    )
    if v30_release:
        from tools.v30_release_lock import (
            load_approved_lock, verify_core_archive,
        )
        approved_lock = load_approved_lock()
        verify_core_archive(
            approved_lock, sys.platform, platform.machine(), name, archive_data,
        )

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
        # Validate the complete core payload BEFORE writing it or loading it
        # through the Libretro native API. The 2.0 lock is unchanged.
        if v30_release:
            from tools.v30_release_lock import verify_core_payload
            verify_core_payload(
                approved_lock, sys.platform, platform.machine(),
                name, filename, content,
            )
        else:
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
    if os.environ.get("AP_V30_APPROVED_RELEASE") == "1":
        # A reviewed alternate production lock selects the genuine 3-family
        # core metadata and pinned offline native runtime BEFORE ctypes opens
        # any source-built Windows library. This is NOT the trial marker.
        from tools.v30_release_lock import (
            ALTERNATIVE_CORE_NAMES, ALTERNATIVE_TIA_CORE_NAMES,
            load_approved_lock, selected_core_set,
        )
        reviewed = load_approved_lock()
        if selected_core_set(reviewed) in (ALTERNATIVE_CORE_NAMES, ALTERNATIVE_TIA_CORE_NAMES):
            from tools.core_release_lock import release_target
            from tools.stage_v30_approved_native_mapping import stage_approved_map
            destination.mkdir(parents=True, exist_ok=True)
            stage_approved_map(
                reviewed, release_target(sys.platform, platform.machine()),
                destination, Path(os.environ["AP_CORE_ARCHIVE_DIR"]))
    if os.environ.get("AP_V30_GPL_TRIAL") == "1":
        # Stage the original marker (and verified Windows native runtime)
        # BEFORE Python opens the first experimental native library.
        from anything_plays.v30_gpl_trial import (
            MARKER, WINDOWS_RUNTIME, validate_trial_core_directory,
        )
        archived = Path(os.environ["AP_CORE_ARCHIVE_DIR"])
        source_marker = archived / MARKER
        if source_marker.is_symlink() or not source_marker.is_file():
            raise ValueError("Original alternative source-built manifest missing")
        destination.mkdir(parents=True, exist_ok=True)
        (destination / MARKER).write_bytes(source_marker.read_bytes())
        if os.name == "nt":
            native_dep = archived / WINDOWS_RUNTIME
            if native_dep.is_symlink() or not native_dep.is_file():
                raise ValueError("Required exact Windows offline native DLL missing")
            (destination / WINDOWS_RUNTIME).write_bytes(native_dep.read_bytes())
        validate_trial_core_directory(destination, build_target()[1], verify_native=False)
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
    if "dolphin" in core_names_for_build():
        # GameCube users must never need to install Dolphin or fetch system
        # data themselves. The test build fails if assets cannot be bundled.
        from tools.fetch_dolphin_sys import fetch_dolphin_sys

        manifest["dolphin_system_assets"] = fetch_dolphin_sys(destination)
        (destination / "CORE_PROVENANCE.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    # Distinct exact-review production marker must still resolve genuine
    # native PCE/SNES/Sega bytes after all eleven approved cores are extracted.
    if os.environ.get("AP_V30_APPROVED_RELEASE") == "1":
        from anything_plays.v30_approved_core_map import (
            MARKER as PRODUCTION_CORE_MAP, validate_installed_map,
        )
        if (destination / PRODUCTION_CORE_MAP).exists():
            validate_installed_map(destination, build_target()[1])
    # Distinct, source-identical preview marker goes into installed core
    # directory and is validated before packaging and on every trial launch.
    # The production source/native lock cannot consume this trial mode.
    if os.environ.get("AP_V30_GPL_TRIAL") == "1":
        from anything_plays.v30_gpl_trial import (
            MARKER, validate_trial_core_directory,
        )
        validate_trial_core_directory(destination, build_target()[1])
    from tools.core_release_lock import (
        LOCK_PATH, candidate_fingerprint, verify_release_lock,
    )
    release_mode = os.environ.get("AP_RELEASE_BUILD", "0")
    if release_mode not in ("0", "1"):
        raise ValueError("AP_RELEASE_BUILD must be 0 or 1")
    if release_mode == "1":
        if os.environ.get("AP_V30_APPROVED_RELEASE") == "1":
            from tools.v30_release_lock import (
                load_approved_lock, verify_native_bundle,
            )
            target = verify_native_bundle(load_approved_lock(), manifest)
            print(f"Approved 3.0 native lock verified for {target}", flush=True)
        else:
            # The historical v2.0 release lock stays unchanged.
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
