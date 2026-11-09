"""Make a source-exact, unapproved Dolphin Sys ZIP from pinned original Git tree.

The independent immutable Git TREE SHA (Data/Sys from exact libretro/dolphin
revision 32c61f9...) is validated by reconstructing every Git blob/tree
digest from the original pinned source TAR. Neither old mutable buildbot
Dolphin.zip nor a separate installed Dolphin is required.

Creates an internal research-only source-backed Sys candidate. Source identity
and reproducibility do NOT independently approve file-level copyrights,
third-party fonts, GPL compatibility, new Dolphin native binaries or release.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import zipfile

DOLPHIN_REV = "32c61f9d0e933331bb7087ba57e96883241b4960"
PINNED_SYS_TREE_SHA1 = "6abd87498928d5362d83f698a562e956072b8700"
SYS_PREFIX = f"dolphin-{DOLPHIN_REV}/Data/Sys/"
ZIP_PREFIX = "dolphin-emu/Sys/"
MAX_TAR_BYTES = 300 * 1024 * 1024
MAX_FILES = 4000
MAX_SINGLE = 16 * 1024 * 1024
MAX_TOTAL = 80 * 1024 * 1024
MAX_ZIP_BYTES = 16 * 1024 * 1024


def _git_object(kind, payload):
    return hashlib.sha1(
        kind.encode("ascii") + b" " + str(len(payload)).encode("ascii") +
        b"\x00" + payload
    ).digest()


def _git_tree_sha(entries):
    """Compute the exact Git tree hash using original mode bits and tree order."""
    root = {}
    for name, (body, executable) in entries.items():
        cur = root
        path = name.split("/")
        for component in path[:-1]:
            cur = cur.setdefault(component, {})
            if not isinstance(cur, dict):
                raise ValueError("File and folder collision in original Dolphin source")
        leaf = path[-1]
        if leaf in cur:
            raise ValueError("Duplicate Git tree source path")
        cur[leaf] = (body, executable)

    def _hash(tree):
        records = []
        for name, row in tree.items():
            if isinstance(row, dict):
                binary = _hash(row)
                mode = b"40000"
                is_dir = True
            else:
                content, executable = row
                binary = _git_object("blob", content)
                mode = b"100755" if executable else b"100644"
                is_dir = False
            records.append((name.encode("utf-8") + (b"/" if is_dir else b""),
                            mode + b" " + name.encode("utf-8") + b"\x00" + binary))
        full = b"".join(payload for _, payload in sorted(records))
        return _git_object("tree", full)

    return _hash(root).hex()


def _read_sys(tar_path):
    source = Path(tar_path)
    if (source.is_symlink() or not source.is_file()
            or not 100_000 <= source.stat().st_size <= MAX_TAR_BYTES):
        raise ValueError("Original pinned Dolphin parent source archive absent or unsafe")
    sha = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    entries = {}
    paths_casefold = set()
    length = 0
    with tarfile.open(source, "r:gz") as archive:
        for member in archive:
            if not member.name.startswith(SYS_PREFIX):
                continue
            relative = member.name[len(SYS_PREFIX):].rstrip("/")
            if not relative:
                continue
            pieces = relative.split("/")
            if (len(relative) > 512 or "\\" in relative or "\x00" in relative
                    or any(part in ("", ".", "..") or ":" in part
                           for part in pieces)):
                raise ValueError("Unsafe original Dolphin Sys source path")
            if member.isdir():
                continue
            if (not member.isfile() or member.issym() or member.islnk()
                    or member.size < 0 or member.size > MAX_SINGLE):
                raise ValueError("Original Sys source contains unsafe file/size")
            if relative in entries or relative.casefold() in paths_casefold:
                raise ValueError("Duplicate case-insensitive Dolphin Sys source path")
            if len(entries) >= MAX_FILES or length + member.size > MAX_TOTAL:
                raise ValueError("Original Dolphin Sys source exceeds verified limits")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Cannot read pinned original Sys source file")
            data = stream.read(member.size + 1)
            if len(data) != member.size:
                raise ValueError("Truncated or changed pinned original Sys source")
            entries[relative] = (data, bool(member.mode & stat.S_IXUSR))
            paths_casefold.add(relative.casefold())
            length += len(data)
    if "codehandler.bin" not in entries or len(entries) < 5:
        raise ValueError("Pinned original Dolphin source missing required Sys files")
    return sha.hexdigest(), entries


def create_pinned_sys(source_tar, output_zip, output_manifest, *,
                      expected_tree=PINNED_SYS_TREE_SHA1):
    source_tar, output_zip, output_manifest = map(
        Path, (source_tar, output_zip, output_manifest))
    if (output_zip == output_manifest or any(x.exists() or x.is_symlink()
        for x in (output_zip, output_manifest))):
        raise ValueError("Refusing to overwrite original source Sys candidate files")
    source_sha, entries = _read_sys(source_tar)
    actual_tree = _git_tree_sha(entries)
    if actual_tree != expected_tree:
        raise ValueError(
            f"Dolphin Sys source tree does not match pinned original Git: {actual_tree}"
        )
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    # Reproducible ZIP: alphabetical order, no local timestamps or machine-specific
    # compressor metadata, and no rights-changing source modification.
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=7, allowZip64=False) as out:
        for relative in sorted(entries):
            data, executable = entries[relative]
            info = zipfile.ZipInfo(ZIP_PREFIX + relative,
                                   date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = ((0o100755 if executable else 0o100644) << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED,
                         compresslevel=7)
    if output_zip.stat().st_size > MAX_ZIP_BYTES:
        output_zip.unlink(missing_ok=True)
        raise ValueError("Pinned source Sys ZIP exceeds existing offline installer size budget")
    with zipfile.ZipFile(output_zip) as check:
        names = check.namelist()
        if len(names) != len(entries) or len(set(names)) != len(entries):
            raise ValueError("Generated Sys zip failed source file inventory check")
        for name, (body, _) in entries.items():
            if check.read(ZIP_PREFIX + name) != body:
                raise ValueError(f"Generated pinned source Sys bytes changed: {name}")
    zip_sha = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1,
        "status": "UNAPPROVED-SOURCE-EXACT-DOLPHIN-SYS-CANDIDATE",
        "upstream_source_repository": "https://github.com/libretro/dolphin",
        "original_parent_source_commit": DOLPHIN_REV,
        "original_parent_source_tar_sha256": source_sha,
        "pinned_git_data_sys_tree_sha1": expected_tree,
        "independently_reconstructed_git_data_sys_tree_sha1": actual_tree,
        "dolphin_sys_zip_sha256": zip_sha,
        "dolphin_sys_zip_size": output_zip.stat().st_size,
        "dolphin_sys_file_count": len(entries),
        "dolphin_sys_extracted_bytes": sum(len(data) for data, _ in entries.values()),
        "files": {
            name: {"size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, (data, _) in sorted(entries.items())
        },
        "matches_original_source_bytes": True,
        "binary_to_source_compilation_verified": False,
        "all_third_party_fonts_and_asset_rights_independently_reviewed": False,
        "public_binary_distribution_approved": False,
    }
    output_manifest.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n",
                               encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-tar", type=Path, required=True)
    parser.add_argument("--output-zip", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    a = parser.parse_args(argv)
    try:
        manifest = create_pinned_sys(a.source_tar, a.output_zip, a.output_manifest)
    except (ValueError, TypeError, OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Original pinned Dolphin Sys construction rejected: {error}\n")
    print(f"Original data Sys Git tree {manifest['pinned_git_data_sys_tree_sha1']}"
          f" matched: {manifest['dolphin_sys_file_count']} exact files, "
          "rights and release UNAPPROVED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
