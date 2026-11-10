"""Preserve independently checked SDL2 upstream source candidates for 3.1.

These observed-version candidates are NOT proof of exact wheel/build source,
complete transitive dependency source, or LGPL replacement compliance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tarfile

COMPONENTS = {
    "sdl2-2.32.8": {
        "repository": "libsdl-org/SDL",
        "tag": "release-2.32.8",
        "commit": "98d1f3a45aae568ccd6ed5fec179330f47d4d356",
        "observed_macho_current_version": "3201.8.0",
        "observation": "macos-arm64 cv2-bundled SDL2",
    },
    "sdl2-2.32.10": {
        "repository": "libsdl-org/SDL",
        "tag": "release-2.32.10",
        "commit": "5d249570393f7a37e037abf22cd6012a4cc56a71",
        "observed_macho_current_version": "3201.10.0",
        "observation": "both macOS pygame-bundled SDL2",
    },
    "sdl2-image-2.8.12": {
        "repository": "libsdl-org/SDL_image",
        "tag": "release-2.8.12",
        "commit": "12cb2e40330d256d9b1329647be8f366546d715c",
        "observed_macho_current_version": "801.12.0",
        "observation": "both macOS pygame-bundled SDL2_image",
    },
    "sdl2-mixer-2.8.2": {
        "repository": "libsdl-org/SDL_mixer",
        "tag": "release-2.8.2",
        "commit": "b208916aed9250fe434360e6c6a95f0697bb7b01",
        "observed_macho_current_version": "801.2.0",
        "observation": "both macOS pygame-bundled SDL2_mixer",
    },
    "sdl2-ttf-2.24.0": {
        "repository": "libsdl-org/SDL_ttf",
        "tag": "release-2.24.0",
        "commit": "2a891473eaf05ba1707a4b7913e6c4db7de7458a",
        "observed_macho_current_version": "0.0.0",
        "observation": "both macOS pygame-bundled SDL2_ttf filename 2400.0",
    },
}
MIN_ARCHIVE_BYTES = 15_000
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_archive(name, archive):
    if name not in COMPONENTS:
        raise ValueError("Unknown or unreviewed SDL component name")
    archive = Path(archive)
    if (archive.is_symlink() or not archive.is_file()
            or not MIN_ARCHIVE_BYTES <= archive.stat().st_size <= MAX_ARCHIVE_BYTES):
        raise ValueError("Missing or implausible original SDL source archive")
    prefix = name + "/"
    count = 0
    c_files = 0
    with tarfile.open(archive, "r:gz") as tar:
        for entry in tar:
            path = entry.name
            if (path.startswith("/") or "\\" in path or
                    ".." in path.split("/") or entry.isdev() or
                    (path != name and not path.startswith(prefix))):
                raise ValueError("Unsafe or incorrectly named SDL source archive entry")
            count += 1
            if entry.isfile() and path.endswith((".c", ".cpp", ".cc", ".h")):
                c_files += 1
            if count > 80_000:
                raise ValueError("Unbounded SDL source archive")
    if count < 20 or c_files < 8:
        raise ValueError("Archive does not resemble complete SDL2 source")
    return {"archive": archive.name, "sha256": digest(archive),
            "member_count": count, "compiled_source_header_files": c_files}


def build_manifest(source_dir, output_dir):
    source_dir, output_dir = Path(source_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    checks = []
    for name, info in COMPONENTS.items():
        archive = source_dir / (name + ".tar.gz")
        record = verify_archive(name, archive)
        rows.append({
            "name": name, "git_repository": info["repository"],
            "git_tag": info["tag"], "pinned_commit": info["commit"],
            "observed_macho_version": info["observed_macho_current_version"],
            "observed_installed_component": info["observation"],
            "source_archive": record,
            "exact_binary_to_source_correspondence_verified": False,
        })
        checks.append(f"{record['sha256']}  {record['archive']}\n")
    result = {
        "schema_version": 1,
        "status": "UNRELEASED_3_1_SDL_OBSERVED_VERSION_SOURCE_CANDIDATES",
        "source_provenance": "Official SDL upstream tagged git trees at exact pinned commits",
        "source_selection": "Observed Mach-O version and filename hints; not a demonstrated build-source chain",
        "original_binary_source_correspondence_verified": False,
        "complete_transitive_source_verified": False,
        "lgpl_relinking_reviewed": False,
        "redistribution_approved": False,
        "components": rows,
    }
    (output_dir / "SDL_CANDIDATE_SOURCE_MANIFEST.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output_dir / "SDL_SOURCE_SHA256SUMS.txt").write_text(
        "".join(checks), encoding="utf-8")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sources", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = build_manifest(args.sources, args.output)
    print(f"Verified {len(report['components'])} pinned original SDL upstream "
          "source-tag candidates; binary correspondence and LGPL rights NOT approved.")


if __name__ == "__main__":
    main()
