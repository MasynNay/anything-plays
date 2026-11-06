"""Produce a reviewable, metadata-only inventory of a frozen app bundle.

This report identifies actual staged files and native executable payloads.
It does not identify every transitive package, certify license compliance,
or authorize publishing the audited binaries.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

MAGIC = {
    b"\x7fELF": "ELF",
    b"\xcf\xfa\xed\xfe": "Mach-O",
    b"\xfe\xed\xfa\xcf": "Mach-O",
    b"\xce\xfa\xed\xfe": "Mach-O",
    b"\xfe\xed\xfa\xce": "Mach-O",
    b"\xca\xfe\xba\xbe": "Mach-O universal",
    b"\xca\xfe\xba\xbf": "Mach-O universal",
}
MAGIC_PE = b"MZ"
CHUNK_SIZE = 1024 * 1024


def digest_and_type(path):
    """Hash a staged file in bounded chunks and identify executable magic."""
    sha = hashlib.sha256()
    size = 0
    prefix = b""
    with path.open("rb") as handle:
        while True:
            block = handle.read(CHUNK_SIZE)
            if not block:
                break
            if not prefix:
                prefix = block[:4]
            sha.update(block)
            size += len(block)
    kind = next((description for magic, description in MAGIC.items()
                 if prefix.startswith(magic)), None)
    if kind is None and prefix.startswith(MAGIC_PE):
        kind = "PE"
    return sha.hexdigest(), size, kind


def collect_bundle_inventory(bundle, target, source_sha=None):
    """Inventory frozen bundle bytes; report symlinks without following them."""
    bundle = Path(bundle).resolve(strict=True)
    if not bundle.is_dir():
        raise ValueError("A staged application directory is required")
    if not target or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in target):
        raise ValueError("Invalid target identifier")

    files, native_files, links = [], [], []
    total_bytes = 0
    for item in sorted(bundle.rglob("*"), key=lambda p: p.relative_to(bundle).as_posix()):
        relative = item.relative_to(bundle).as_posix()
        if item.is_symlink():
            resolved = item.resolve(strict=True)
            if not resolved.is_relative_to(bundle):
                raise ValueError(f"External symlink in bundle: {relative}")
            links.append({"path": relative, "target": item.readlink().as_posix()})
        elif item.is_dir():
            continue
        elif item.is_file():
            digest, size, kind = digest_and_type(item)
            entry = {"path": relative, "sha256": digest, "size_bytes": size}
            files.append(entry)
            total_bytes += size
            if kind:
                native_files.append({**entry, "binary_format": kind})
        else:
            raise ValueError(f"Unsupported staged filesystem entry: {relative}")
    if not files:
        raise ValueError("Empty staged application directory")
    return {
        "schema_version": 1,
        "target": target,
        "source_sha": source_sha,
        "redistribution_approved": False,
        "scope": "Staged app file inventory; not a complete SBOM or license approval",
        "file_count": len(files),
        "native_file_count": len(native_files),
        "symlink_count": len(links),
        "total_regular_file_bytes": total_bytes,
        "native_files": native_files,
        "symlinks": links,
        "files": files,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="Platform and architecture identifier")
    parser.add_argument("bundle", type=Path, help="Staged app directory or .app")
    parser.add_argument("output", type=Path, help="JSON evidence output outside the app")
    args = parser.parse_args()
    bundle = args.bundle.resolve(strict=True)
    output = args.output.resolve()
    if output.is_relative_to(bundle):
        parser.error("Evidence output must be outside the staged app")
    report = collect_bundle_inventory(bundle, args.target, os.environ.get("GITHUB_SHA"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Evidence: {args.target}: {report['file_count']} files, "
          f"{report['native_file_count']} executable libraries, "
          f"{report['symlink_count']} symlinks")
    print(f"Metadata report: {output} (no binaries uploaded)")


if __name__ == "__main__":
    main()
