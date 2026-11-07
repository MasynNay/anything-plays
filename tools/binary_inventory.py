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

from fetch_mgba_core import core_names_for_build

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

    # The CI inventory is recorded AFTER macOS signing. The original core
    # manifest must still match final bytes, otherwise codesign or a packaging
    # step silently changed the emulator libraries after verification.
    by_path = {entry["path"]: entry for entry in files}
    prefix = "Contents/Resources/" if target.startswith("macos-") else ""
    core_manifest = prefix + "cores/CORE_PROVENANCE.json"
    verified_cores = []
    if core_manifest in by_path:
        metadata = json.loads((bundle / core_manifest).read_text(encoding="utf-8"))
        for record in metadata.get("cores", []):
            relative = prefix + "cores/" + record["file"]
            observed = by_path.get(relative)
            if not observed:
                raise ValueError(f"Missing declared core in staged app: {relative}")
            if (observed["sha256"] != record["sha256"]
                    or observed["size_bytes"] != record["size_bytes"]):
                raise ValueError(f"Post-packaging core integrity mismatch: {relative}")
            verified_cores.append({"name": record["name"], "path": relative,
                                   "sha256": observed["sha256"]})
        # Reuse the exact downloader-approved core set. Inventories must
        # fail if a new native system is missing from the signed installer.
        expected = set(core_names_for_build())
        if {entry["name"] for entry in verified_cores} != expected:
            raise ValueError(f"Unexpected core manifest: expected {sorted(expected)}")

    # Record precise versions from the actual frozen build environment.
    # This inventory includes build-only Python packages: it is not an SBOM.
    license_prefix = "Contents/Resources/" if target.startswith("macos-") else ""
    python_inventory = license_prefix + "licenses/PYTHON_DISTRIBUTIONS.json"
    python_distributions = []
    if python_inventory in by_path:
        metadata = json.loads((bundle / python_inventory).read_text(encoding="utf-8"))
        for record in metadata.get("distributions", []):
            python_distributions.append({
                "name": record.get("name"),
                "version": record.get("version"),
                "license_expression": record.get("license_expression"),
                "bundled_notice_count": len(record.get("license_files", [])),
            })

    # Explicitly reject Qt GUI libraries if this is a headless OpenCV build.
    # The old Linux wheel bundled LGPL-3.0 Qt GUI components unnecessarily.
    if any((d["name"] or "").lower() == "opencv-python-headless"
           for d in python_distributions):
        gui_files = [
            entry["path"] for entry in files
            if "/cv2/qt/" in ("/" + entry["path"]).lower()
            or "/libqt5" in ("/" + entry["path"]).lower()
            or "/libqt6" in ("/" + entry["path"]).lower()
        ]
        if gui_files:
            raise ValueError("Unexpected Qt GUI binaries in headless OpenCV bundle: "
                             + ", ".join(gui_files[:5]))

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
        "verified_cores": verified_cores,
        "python_distributions": python_distributions,
        "python_inventory_scope": "Build environment; may include build-only packages",
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
