"""Dolphin core + Sys must install as ONE approved, immutable package.

All files are verified before activation; no RetroArch, Wii ROMs, external
Dolphin executable, standalone firmware install or in-place DLL replacement.
The public release gate remains closed until real gameplay/audio QA passes.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile

SYS_PREFIX = "dolphin-emu/Sys/"
SYS_MANIFEST = "dolphin-sys.json"
MAX_FILES = 4000
MAX_SYS_TOTAL = 80 * 1024 * 1024
MAX_SYS_SINGLE = 16 * 1024 * 1024
MAX_SYS_INDEX = 650000
MAX_CORE_BINARY = 65 * 1024 * 1024
HEX64 = re.compile(r"^[a-f0-9]{64}$")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _safe_name(name):
    return (isinstance(name, str) and 0 < len(name) <= 512
            and not PurePosixPath(name).is_absolute()
            and "\\" not in name and "\x00" not in name
            and all(p not in ("", ".", "..") and ":" not in p
                    for p in name.split("/")))


def _inventory(contents):
    if not isinstance(contents, dict) or not 5 <= len(contents) <= MAX_FILES:
        raise ValueError("Missing or oversized Dolphin system file inventory")
    total, items = 0, {}
    for name, value in sorted(contents.items()):
        if not _safe_name(name) or not isinstance(value, bytes):
            raise ValueError("Unsafe Dolphin Sys file name or data")
        if len(value) > MAX_SYS_SINGLE:
            raise ValueError("Oversized Dolphin Sys member")
        total += len(value)
        if total > MAX_SYS_TOTAL:
            raise ValueError("Oversized Dolphin Sys data")
        items[name] = {"sha256": sha256(value), "size_bytes": len(value)}
    if not contents.get("codehandler.bin"):
        raise ValueError("Missing required Dolphin codehandler.bin")
    return {"schema": 1, "file_count": len(items),
            "total_size_bytes": total, "files": items}


def make_sys_index(contents):
    return (json.dumps(_inventory(contents), sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def verify_dolphin_pack(data, item):
    from anything_plays.core_packs import target_identity, UPSTREAM_REPOS
    target, ext = target_identity()
    if item.get("name") != "dolphin" or item.get("target") != target:
        raise ValueError("Dolphin pack targets another system or platform")
    filename = "dolphin_libretro" + ext
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = [entry for entry in archive.infolist() if not entry.is_dir()]
        names = [entry.filename for entry in members]
        required = {"core-pack.json", filename, SYS_MANIFEST}
        extra = set(names) - required
        if (len(names) != len(set(names)) or not required.issubset(names)
                or not 5 <= len(extra) <= MAX_FILES
                or not all(name.startswith(SYS_PREFIX) for name in extra)
                or not all(_safe_name(name) for name in names)):
            raise ValueError("Invalid paired Dolphin archive files")
        for entry in members:
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("Dolphin archive contains symlink")
            budget = (16000 if entry.filename == "core-pack.json"
                      else MAX_SYS_INDEX if entry.filename == SYS_MANIFEST
                      else MAX_CORE_BINARY if entry.filename == filename
                      else MAX_SYS_SINGLE)
            if entry.file_size > budget:
                raise ValueError("Oversized Dolphin archive member")
        meta = json.loads(archive.read("core-pack.json"))
        index_bytes = archive.read(SYS_MANIFEST)
        binary = archive.read(filename)
        files = {name[len(SYS_PREFIX):]: archive.read(name) for name in extra}
    expected = _inventory(files)
    if json.loads(index_bytes) != expected:
        raise ValueError("Dolphin Sys checksum inventory mismatch")
    if (not isinstance(meta, dict) or meta.get("schema") != 2
            or meta.get("name") != "dolphin"
            or meta.get("release") != item["release"]
            or meta.get("target") != target or meta.get("file") != filename
            or meta.get("source_repository") != "https://github.com/" + UPSTREAM_REPOS["dolphin"]
            or meta.get("third_party_license_reviewed") is not True
            or meta.get("packaged_runtime_tested") is not True):
        raise ValueError("Unreviewed or mismatched Dolphin core+Sys package")
    core_sha, sys_sha = meta.get("sha256"), meta.get("sys_manifest_sha256")
    if (not isinstance(core_sha, str) or not HEX64.fullmatch(core_sha)
            or not isinstance(sys_sha, str) or not HEX64.fullmatch(sys_sha)
            or core_sha != sha256(binary) or sys_sha != sha256(index_bytes)
            or meta.get("sys_manifest_file") != SYS_MANIFEST
            or meta.get("sys_file_count") != expected["file_count"]
            or meta.get("sys_total_size_bytes") != expected["total_size_bytes"]
            or not isinstance(meta.get("sys_source_archive_sha256"), str)
            or not HEX64.fullmatch(meta["sys_source_archive_sha256"])):
        raise ValueError("Dolphin binary or Sys provenance failed SHA-256 validation")
    native = {".dll": (b"MZ",), ".so": (b"\x7fELF",),
              ".dylib": (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",
                         b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf")}[ext]
    if not 10000 < len(binary) <= MAX_CORE_BINARY or not binary.startswith(native):
        raise ValueError("Dolphin native library format invalid")
    return {"core_sha": core_sha, "sys_sha": sys_sha, "file": filename,
            "binary": binary, "sys_index": index_bytes, "sys_files": files}


def object_sha(core_sha, sys_sha):
    if not HEX64.fullmatch(core_sha) or not HEX64.fullmatch(sys_sha):
        raise ValueError("Invalid Dolphin immutable object identity")
    return sha256(bytes.fromhex(core_sha) + bytes.fromhex(sys_sha))


def verify_installed_dolphin(record, root, target, ext):
    """Return a core only if its binary and every Sys byte remain intact."""
    from anything_plays.core_packs import _no_symlinks, _sha_file
    if not isinstance(record, dict) or record.get("target") != target:
        return None
    core, syshash, identity = (
        record.get("sha256"), record.get("sys_manifest_sha256"),
        record.get("object_sha256"))
    if not all(isinstance(v, str) and HEX64.fullmatch(v)
               for v in (core, syshash, identity)):
        return None
    if object_sha(core, syshash) != identity:
        return None
    rel = f"objects/dolphin/{identity}/dolphin_libretro{ext}"
    if record.get("path") != rel:
        return None
    root = Path(root)
    folder = root / "objects" / "dolphin" / identity
    native, index = root / rel, folder / SYS_MANIFEST
    try:
        for path in (folder, native, index):
            _no_symlinks(path, root)
        if (not native.is_file() or native.stat().st_size > MAX_CORE_BINARY
                or _sha_file(native) != core or not index.is_file()
                or index.stat().st_size > MAX_SYS_INDEX
                or _sha_file(index) != syshash):
            return None
        inventory = json.loads(index.read_text("utf-8"))
        rows = inventory.get("files")
        if (inventory.get("schema") != 1 or not isinstance(rows, dict)
                or not 5 <= len(rows) <= MAX_FILES
                or "codehandler.bin" not in rows
                or inventory.get("file_count") != len(rows)):
            return None
        total = 0
        for name, item in rows.items():
            if (not _safe_name(name) or not isinstance(item, dict)
                    or not isinstance(item.get("sha256"), str)
                    or not HEX64.fullmatch(item["sha256"])
                    or type(item.get("size_bytes")) is not int):
                return None
            file = folder / SYS_PREFIX / name
            _no_symlinks(file, root)
            length = item["size_bytes"]
            if (length < 0 or length > MAX_SYS_SINGLE
                    or not file.is_file() or file.stat().st_size != length
                    or _sha_file(file) != item["sha256"]):
                return None
            total += length
            if total > MAX_SYS_TOTAL:
                return None
        if inventory.get("total_size_bytes") != total:
            return None
        sysdir = folder / "dolphin-emu" / "Sys"
        for file in sysdir.rglob("*"):
            _no_symlinks(file, root)
            if file.is_file() and file.relative_to(sysdir).as_posix() not in rows:
                return None
        return native
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def stage_dolphin_object(root, verified):
    """Atomic private directory rename; never overwrite a loaded DLL."""
    from anything_plays.core_packs import _no_symlinks
    root = Path(root)
    identity = object_sha(verified["core_sha"], verified["sys_sha"])
    parent = root / "objects" / "dolphin"
    parent.mkdir(parents=True, exist_ok=True)
    folder = parent / identity
    _no_symlinks(folder, root)
    if not folder.exists():
        staged = Path(tempfile.mkdtemp(prefix=".dolphin-stage-", dir=parent))
        try:
            (staged / verified["file"]).write_bytes(verified["binary"])
            (staged / SYS_MANIFEST).write_bytes(verified["sys_index"])
            for name, value in verified["sys_files"].items():
                file = staged / "dolphin-emu" / "Sys" / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(value)
            os.replace(staged, folder)
        finally:
            if staged.exists():
                shutil.rmtree(staged)
    return identity, folder
