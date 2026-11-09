"""Stage a separate checksummed 11-core SOURCE companion for stable 3.0.

The four app installers remain the only platform downloads in the main release.
Source ZIP is published in a separate linked release, never mixed with the
app installers. Original-source capture alone is NOT binary distribution rights.
This helper only checks byte identities; publication remains fully gated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from anything_plays.v30_approved_core_map import (ELEVEN_EXPECTED, ELEVEN_REPOSITORIES,
    ELEVEN_TIA_EXPECTED, ELEVEN_TIA_REPOSITORIES)

VERSION = re.compile(r"3\.0\.\d+\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
MANIFEST = "SOURCE_ACCESS_CANDIDATE_UNAPPROVED.json"
CHECKSUMS = "SHA256SUMS.txt"
STATUS = "UNAPPROVED-ORIGINAL-SOURCE-TREE-ACCESS-CANDIDATE"
MAX_SOURCE = 1024 * 1024 * 1024


def digest_file(path: Path):
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size < MAX_SOURCE:
        raise ValueError(f"Original corresponding source missing or unsafe: {path.name}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest(), path.stat().st_size


def validate_captured_sources(folder: Path):
    root = Path(folder)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Original source evidence directory missing or unsafe")
    path = root / MANIFEST
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Original source candidate manifest missing")
    manifest = json.loads(path.read_text("utf-8"))
    expected_status = {
        "schema_version": 1,
        "status": STATUS,
        "core_count": 11,
        "all_source_revisions_pinned": True,
        "newly_compiled_libretro_core_outputs_included": False,
        "source_to_bundled_binary_review_complete": False,
        "transitive_build_dependencies_review_complete": False,
        "combined_gpl_distribution_reviewed": False,
        "public_binary_distribution_approved": False,
    }
    if not isinstance(manifest, dict) or any(
        manifest.get(k) != v for k, v in expected_status.items()
    ):
        raise ValueError("Original source package has a fabricated approval or incomplete identity")
    variant = manifest.get("source_set_id")
    if variant not in (None, "original-eleven-gpl2plus-tia"):
        raise ValueError("Unrecognized original emulator source composition")
    tia = variant == "original-eleven-gpl2plus-tia"
    revisions = ELEVEN_TIA_EXPECTED if tia else ELEVEN_EXPECTED
    repos = ELEVEN_TIA_REPOSITORIES if tia else ELEVEN_REPOSITORIES
    sources = manifest.get("sources")
    if not isinstance(sources, dict) or set(sources) != set(revisions):
        raise ValueError("Expected all 11 exact originally pinned emulator sources")
    source_names = set()
    digest_lines = set()
    for name in sorted(revisions):
        row = sources[name]
        revision, repository = revisions[name], repos[name]
        expected_filename = f"source-{name}-{revision}.tar.gz"
        if (not isinstance(row, dict)
                or row.get("source_commit") != revision
                or row.get("source_repository") != repository
                or row.get("archive_file") != expected_filename
                or not isinstance(row.get("sha256"), str)
                or not SHA.fullmatch(row["sha256"])
                or (name == "dolphin" and row.get("nested_gitlink_source_count") != 37)):
            raise ValueError(f"Unmatched pinned source or Gitlinks: {name}")
        path = root / expected_filename
        observed, size = digest_file(path)
        if (observed != row["sha256"] or size != row.get("size_bytes")
                or not isinstance(row.get("source_files"), int)
                or row["source_files"] < 5):
            raise ValueError(f"Changed original core source checksum/size: {name}")
        source_names.add(expected_filename)
        digest_lines.add(f"{observed}  {expected_filename}")
    declared = root / CHECKSUMS
    if declared.is_symlink() or not declared.is_file():
        raise ValueError("Original source checksum index missing")
    if (len(declared.read_bytes()) > 65536
            or set(declared.read_text("ascii").splitlines()) != digest_lines
            or len(declared.read_text("ascii").splitlines()) != 11):
        raise ValueError("Original source SHA256SUMS do not match all 11 pinned cores")
    if {p.name for p in root.iterdir()} != source_names | {MANIFEST, CHECKSUMS}:
        raise ValueError("Unexpected source archive file or unsafe extra binary")
    return manifest


def prepare_source_companion(source_dir: Path, output_dir: Path, version: str):
    if not VERSION.fullmatch(version):
        raise ValueError("Only 3.0 stable source companion releases supported")
    src, dst = Path(source_dir), Path(output_dir)
    if (src.is_symlink() or dst.is_symlink()
            or dst.exists() or src.resolve() == dst.resolve()
            or src.resolve() in dst.resolve().parents
            or dst.resolve() in src.resolve().parents):
        raise ValueError("Original source and source-release destinations must be separate")
    captured = validate_captured_sources(src)
    dst.mkdir(parents=True)
    filename = f"AnythingPlays-{version}-Original-Emulator-Sources.zip"
    archive_path = dst / filename
    names = sorted(p.name for p in src.iterdir())
    readme = (
        f"Anything Plays {version} — pinned original emulator sources\n"
        + ("Atari2600 uses original GPL2-or-later Tia in place of old Stella2014.\n"
           if captured.get("source_set_id") == "original-eleven-gpl2plus-tia" else "")
        "Eleven upstream Git source trees with recursive submodule checkout.\n"
        "The corresponding application source, packaging scripts, patches and\n"
        f"build workflows are available at the Anything Plays v{version} tag.\n"
        "Core source content remains under each upstream project's own license.\n"
        "A source archive alone does NOT prove GPL version compatibility,\n"
        "complete toolchain correspondence or binary distribution rights.\n"
        "See SOURCE_ACCESS_CANDIDATE_UNAPPROVED.json and SHA256SUMS.txt.\n"
    )
    try:
        with ZipFile(archive_path, mode="w", compression=ZIP_STORED, allowZip64=True) as archive:
            for name in [*names, "SOURCE_ACCESS_README.txt"]:
                info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_STORED
                if name == "SOURCE_ACCESS_README.txt":
                    archive.writestr(info, readme.encode("utf-8"))
                else:
                    # Fixed ZIP timestamps and stream-copy avoid depending on
                    # Actions artifact extraction mtimes or reading huge
                    # original source TARs into memory.
                    with (src / name).open("rb") as original:
                        with archive.open(info, "w") as copied:
                            shutil.copyfileobj(original, copied, 1024 * 1024)
        digest, size = digest_file(archive_path)
        (dst / CHECKSUMS).write_text(f"{digest}  {filename}\n", "ascii")
        return {"filename": filename, "sha256": digest, "size_bytes": size,
                "upstream_core_count": captured["core_count"],
                "binary_distribution_approval_auto_granted": False}
    except BaseException:
        archive_path.unlink(missing_ok=True)
        (dst / CHECKSUMS).unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="3.0.0")
    args = parser.parse_args()
    info = prepare_source_companion(args.input, args.output, args.version)
    print(f"Verified source companion {info['filename']} SHA256 {info['sha256']}; NO rights inferred.")


if __name__ == "__main__":
    main()
