"""Vetted, in-app Libretro core packs for Anything Plays 2.1.

Only assets published by MasynNay/anything-plays in a 2.1 release are allowed.
GitHub's release-asset SHA-256 digest is independently checked against the
downloaded ZIP, then the ZIP manifest and the native library are hash checked.
Libraries are staged outside the signed application and activated by an atomic
manifest change between game sessions. Never modify the application bundle,
download random buildbot executables or overwrite an already loaded library.

The first 2.1 release won't necessarily have separate approved core packs.
In that case the updater must report that none are published, not invent an
update. Public releases still require normal platform signing/QA.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import tempfile
from urllib.parse import quote
from urllib.request import Request, urlopen
import zipfile

from anything_plays.emulator_updates import UPSTREAM_REPOS
from anything_plays.update_check import version_key

RELEASES_API = "https://api.github.com/repos/MasynNay/anything-plays/releases?per_page=30"
RELEASE_PREFIX = "https://github.com/MasynNay/anything-plays/releases/download/"
PACK_PREFIX = "AnythingPlays21-Core-"
MAX_API_BYTES = 1_000_000
MAX_PACK_BYTES = 80 * 1024 * 1024
MAX_BINARY_BYTES = 65 * 1024 * 1024
MAX_STATE_BYTES = 150_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RELEASE_TAG_RE = re.compile(r"^v?2\.1\.\d+(?:-(?:alpha|beta|rc)[.-]\d+)?$", re.I)


def target_identity(platform_name=None, machine=None):
    platform_name = sys.platform if platform_name is None else platform_name
    machine = (platform.machine() if machine is None else machine).lower()
    if platform_name == "win32" and machine in ("amd64", "x86_64"):
        return "windows-x64", ".dll"
    if platform_name == "darwin" and machine in ("arm64", "aarch64"):
        return "macos-arm64", ".dylib"
    if platform_name == "darwin" and machine in ("x86_64", "amd64"):
        return "macos-x64", ".dylib"
    if platform_name.startswith("linux") and machine in ("x86_64", "amd64"):
        return "linux-x64", ".so"
    raise ValueError("Unapproved platform for Anything Plays core packs")


def managed_core_root():
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
        return base / "AnythingPlays" / "2.1" / "cores"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AnythingPlays" / "2.1" / "cores"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "anything-plays" / "2.1" / "cores"


def _no_symlinks(path, parent):
    path, parent = Path(path), Path(parent)
    if parent.is_symlink():
        raise ValueError("Managed core store is a symlink")
    try:
        path.relative_to(parent)
    except ValueError as exc:
        raise ValueError("Core file escapes managed store") from exc
    relative = path.relative_to(parent)
    check = parent
    for part in relative.parts:
        check = check / part
        if check.is_symlink():
            raise ValueError("Managed core path contains a symlink")


def _load_state(root):
    file = Path(root) / "active.json"
    if not file.is_file():
        return {"schema": 1, "active": {}}
    _no_symlinks(file, root)
    if file.stat().st_size > MAX_STATE_BYTES:
        raise ValueError("Oversized managed-core state")
    value = json.loads(file.read_text("utf-8"))
    if not isinstance(value, dict) or value.get("schema") != 1 or not isinstance(value.get("active"), dict):
        raise ValueError("Invalid managed-core state")
    return value


def _valid_installed(name, record, root, target, extension):
    if not isinstance(record, dict) or name not in UPSTREAM_REPOS:
        return None
    digest = record.get("sha256")
    rel = record.get("path")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        return None
    if record.get("target") != target or not isinstance(rel, str):
        return None
    expected = f"{name}_libretro{extension}"
    if rel != f"objects/{name}/{digest}/{expected}":
        return None
    path = Path(root) / rel
    try:
        _no_symlinks(path, root)
        if not path.is_file() or path.stat().st_size > MAX_BINARY_BYTES:
            return None
        if _sha_file(path) != digest:
            return None
    except (OSError, ValueError):
        return None
    return path


def managed_core_path(name, root=None):
    """Load only an active, immutable, hash-verified per-user core."""
    if name not in UPSTREAM_REPOS:
        return None
    root = Path(root) if root is not None else managed_core_root()
    try:
        target, extension = target_identity()
        state = _load_state(root)
        result = _valid_installed(name, state["active"].get(name), root, target, extension)
        return str(result) if result else None
    except (OSError, ValueError, json.JSONDecodeError):
        # An untrusted or corrupt overlay can NEVER block the bundled core.
        return None


def _sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_state(root, data):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    _no_symlinks(root / "active.json", root)
    raw = json.dumps(data, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    if len(raw) > MAX_STATE_BYTES:
        raise ValueError("Managed core manifest too large")
    fd, temp_name = tempfile.mkstemp(prefix=".active-", suffix=".tmp", dir=root)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, root / "active.json")
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _release_asset(name, target):
    return f"{PACK_PREFIX}{name}-{target}.zip"


def discover_core_packs(*, opener=None, target=None):
    """Return approved-repository release pack *metadata*, never nightly builds.

    Missing GitHub asset digests cause a fail-closed skip: we do not silently
    rely on a checksum downloaded from the same unverified ZIP.
    """
    target = target or target_identity()[0]
    valid_targets = {"windows-x64", "macos-arm64", "macos-x64", "linux-x64"}
    if target not in valid_targets:
        raise ValueError("Unknown core-pack target")
    req = Request(RELEASES_API, headers={
        "User-Agent": "AnythingPlays-2.1-CoreUpdater",
        "Accept": "application/vnd.github+json",
    })
    fetch = opener or urlopen
    with fetch(req, timeout=8) as response:
        raw = response.read(MAX_API_BYTES + 1)
    if len(raw) > MAX_API_BYTES:
        raise ValueError("Oversized GitHub release index")
    releases = json.loads(raw)
    if not isinstance(releases, list):
        raise ValueError("Invalid GitHub release index")
    candidates = {}
    for release in releases:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        tag = release.get("tag_name")
        if not isinstance(tag, str) or not RELEASE_TAG_RE.fullmatch(tag):
            continue
        version = version_key(tag)
        assets = release.get("assets")
        if not isinstance(assets, list):
            continue
        for item in assets:
            if not isinstance(item, dict):
                continue
            for name in UPSTREAM_REPOS:
                expected = _release_asset(name, target)
                if item.get("name") != expected:
                    continue
                digest = item.get("digest")
                url = item.get("browser_download_url")
                size = item.get("size")
                approved_url = RELEASE_PREFIX + quote(tag, safe="-._") + "/" + quote(expected, safe="-._")
                if (not isinstance(digest, str) or not digest.startswith("sha256:")
                        or not SHA256_RE.fullmatch(digest[7:])
                        or not isinstance(size, int) or not 100 < size <= MAX_PACK_BYTES
                        or url != approved_url):
                    continue
                result = {
                    "name": name, "target": target, "release": tag,
                    "sha256": digest[7:], "size": size,
                    "url": approved_url,
                }
                if name not in candidates or version > candidates[name][0]:
                    candidates[name] = (version, result)
    return [v[1] for _, v in sorted(candidates.items())]


def _validate_asset_metadata(item):
    if not isinstance(item, dict) or item.get("name") not in UPSTREAM_REPOS:
        raise ValueError("Unapproved core pack")
    if item["name"] == "dolphin":
        raise ValueError("GameCube core needs matching Sys assets: use a vetted full app update")
    target, _ = target_identity()
    if item.get("target") != target:
        raise ValueError("Core pack is for another operating system")
    tag, name = item.get("release"), item["name"]
    if not isinstance(tag, str) or not RELEASE_TAG_RE.fullmatch(tag):
        raise ValueError("Unapproved release tag")
    expected_url = RELEASE_PREFIX + quote(tag, safe="-._") + "/" + quote(_release_asset(name, target), safe="-._")
    if item.get("url") != expected_url:
        raise ValueError("Core pack does not come from official release")
    if (not isinstance(item.get("sha256"), str)
            or not SHA256_RE.fullmatch(item["sha256"])):
        raise ValueError("Core pack SHA-256 missing")
    if not isinstance(item.get("size"), int) or not 100 < item["size"] <= MAX_PACK_BYTES:
        raise ValueError("Core pack exceeds allowed size")


def _download(item, fetch):
    req = Request(item["url"], headers={"User-Agent": "AnythingPlays-2.1-CoreUpdater"})
    with fetch(req, timeout=45) as response:
        data = response.read(MAX_PACK_BYTES + 1)
    if len(data) > MAX_PACK_BYTES or len(data) != item["size"]:
        raise ValueError("Core pack download length does not match GitHub")
    if hashlib.sha256(data).hexdigest() != item["sha256"]:
        raise ValueError("Core pack failed official release SHA-256 verification")
    return data


def _verify_core_pack(data, item):
    """Read exact ZIP members; never extract arbitrary archive paths."""
    name, target = item["name"], item["target"]
    _, ext = target_identity()
    filename = f"{name}_libretro{ext}"
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [i.filename for i in archive.infolist() if not i.is_dir()]
        if len(names) != 2 or set(names) != {"core-pack.json", filename}:
            raise ValueError("Invalid core pack files")
        manifest_info = archive.getinfo("core-pack.json")
        binary_info = archive.getinfo(filename)
        if manifest_info.file_size > 16000 or binary_info.file_size > MAX_BINARY_BYTES:
            raise ValueError("Unsafe core pack decompressed size")
        meta = json.loads(archive.read("core-pack.json"))
        content = archive.read(filename)
    if (not isinstance(meta, dict) or meta.get("schema") != 1
            or meta.get("name") != name or meta.get("target") != target
            or meta.get("release") != item["release"]
            or meta.get("file") != filename
            or meta.get("source_repository") != "https://github.com/" + UPSTREAM_REPOS[name]):
        raise ValueError("Core pack manifest does not match approved release")
    if (meta.get("third_party_license_reviewed") is not True
            or meta.get("packaged_runtime_tested") is not True):
        raise ValueError("Core pack has not passed license and runtime review")
    sha = meta.get("sha256")
    if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
        raise ValueError("Invalid binary SHA-256")
    if hashlib.sha256(content).hexdigest() != sha:
        raise ValueError("Core library failed manifest SHA-256 verification")
    if len(content) < 10_000 or len(content) > MAX_BINARY_BYTES:
        raise ValueError("Native core library has unexpected size")
    magic = {".dll": (b"MZ",), ".so": (b"\x7fELF",),
             ".dylib": (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",
                        b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf")}
    if not any(content.startswith(prefix) for prefix in magic[ext]):
        raise ValueError("Core library has invalid native format")
    return sha, filename, content


def install_core_pack(item, *, root=None, opener=None, emulator_busy=False):
    """Install an approved core pack without ever overwriting an active DLL.

    The caller must ensure no native game session is running. Binary bytes
    remain immutable under objects/<name>/<sha256>; only a small JSON pointer
    is atomically switched. A subsequent game start loads the updated core.
    """
    if emulator_busy:
        raise RuntimeError("Stop the running game before updating emulator cores")
    _validate_asset_metadata(item)
    root = Path(root) if root is not None else managed_core_root()
    if root.is_symlink():
        raise ValueError("Refusing a symlinked managed-core folder")
    fetch = opener or urlopen
    data = _download(item, fetch)
    sha, filename, content = _verify_core_pack(data, item)
    target, ext = target_identity()
    root.mkdir(parents=True, exist_ok=True)
    directory = root / "objects" / item["name"] / sha
    destination = directory / filename
    _no_symlinks(destination, root)
    if not destination.is_file():
        directory.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".core-stage-", dir=root) as staging:
            staged = Path(staging) / filename
            staged.write_bytes(content)
            if _sha_file(staged) != sha:
                raise ValueError("Staged core hash mismatch")
            directory.mkdir(parents=True, exist_ok=True)
            os.replace(staged, destination)
    if _sha_file(destination) != sha:
        raise ValueError("Existing core object is modified; no activation performed")
    state = _load_state(root)
    old = state["active"].get(item["name"])
    relative = f"objects/{item['name']}/{sha}/{filename}"
    record = {
        "target": target, "path": relative, "sha256": sha,
        "release": item["release"], "asset_sha256": item["sha256"],
        "previous": old if isinstance(old, dict) else None,
    }
    state["active"][item["name"]] = record
    _atomic_state(root, state)
    return str(destination)


def rollback_core(name, *, root=None):
    """Switch back to a previously verified core or the untouched bundle."""
    if name not in UPSTREAM_REPOS:
        raise ValueError("Unknown emulator")
    root = Path(root) if root is not None else managed_core_root()
    state = _load_state(root)
    old = state["active"].get(name)
    if not isinstance(old, dict):
        return False
    target, ext = target_identity()
    previous = old.get("previous")
    if not _valid_installed(name, previous, root, target, ext):
        state["active"].pop(name, None)  # Original bundled core is always fallback.
    else:
        state["active"][name] = previous
    _atomic_state(root, state)
    return True


def installed_pack_revision(name, *, root=None):
    root = Path(root) if root is not None else managed_core_root()
    try:
        active = _load_state(root)["active"].get(name)
        return active.get("asset_sha256") if managed_core_path(name, root=root) and isinstance(active, dict) else None
    except (ValueError, OSError):
        return None


def managed_core_release(name, *, root=None):
    """Display the actual approved core-pack release instead of bundle metadata."""
    root = Path(root) if root is not None else managed_core_root()
    try:
        active = _load_state(root)["active"].get(name)
        if not isinstance(active, dict) or not managed_core_path(name, root=root):
            return None
        tag = active.get("release")
        return tag if isinstance(tag, str) and RELEASE_TAG_RE.fullmatch(tag) else None
    except (OSError, ValueError):
        return None

