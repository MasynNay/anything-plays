"""Reconcile all 34 pinned Dolphin source archives from six *actual* CI shards.

Strictly review-only; collecting source does not show that shipped Dolphin
binaries were built with these inputs, resolve nested dependencies, or grant
GPL/noncommercial distribution rights. No binary files are produced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from tools.check_v30_dolphin_submodules import PINNED, validate_index
from tools.capture_v30_dolphin_submodule_sources import STATUS as SHARD_STATUS

SOURCE_STATUS = "UNAPPROVED-DOLPHIN-34-SOURCE-ARCHIVE-REVIEW"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_SIZE = 512 * 1024 * 1024


def _regular_file(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise ValueError(f"Unexpected source artifact filename: {name!r}")
    path = root / name
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Missing or unsafe source review file: {path}")
    return path


def _checksum(path: Path, limit=MAX_SIZE):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            size += len(chunk)
            if size > limit:
                raise ValueError(f"Source review artifact exceeds size limit: {path}")
            digest.update(chunk)
    return digest.hexdigest(), size


def _load_json(path: Path):
    digest, size = _checksum(path, 5 * 1024 * 1024)
    if size == 0:
        raise ValueError("Empty Dolphin source inventory")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Malformed Dolphin source inventory")
    return data, digest


def _require_false(record, fields, *, label):
    if any(record.get(name) is not False for name in fields):
        raise ValueError(f"{label}: unreviewed binary/source/license approval asserted")


def reconcile(index_record: dict, input_dir: Path, output_dir: Path, *, shards=6):
    """Rehash all original source candidates; reject duplicate/missing/extra data."""
    original = validate_index(index_record)
    if type(shards) is not int or not 1 <= shards <= 34:
        raise ValueError("Invalid expected Dolphin source shard count")
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    if (not input_dir.is_dir() or input_dir.is_symlink()
            or any(p.name not in {f"shard-{n}" for n in range(shards)}
                   for p in input_dir.iterdir())
            or len(list(input_dir.iterdir())) != shards):
        raise ValueError("Expected exactly the original six source review shards")
    if (output_dir.is_symlink()
            or (output_dir.exists()
                and (not output_dir.is_dir() or any(output_dir.iterdir())))):
        raise ValueError("Review output must be an empty non-symlink directory")
    if output_dir.resolve() == input_dir.resolve() or input_dir.resolve() in output_dir.resolve().parents:
        raise ValueError("Do not write source review into the original shard inputs")
    combined = {}
    expected_paths = sorted(original)
    shard_evidence = []
    for number in range(shards):
        folder = input_dir / f"shard-{number}"
        if not folder.is_dir() or folder.is_symlink():
            raise ValueError(f"Unsafe or missing Dolphin shard {number}")
        manifest_file = _regular_file(folder, "DOLPHIN_SUBMODULE_SOURCE_CANDIDATES_UNAPPROVED.json")
        checksum_file = _regular_file(folder, "SHA256SUMS.txt")
        source, manifest_sha = _load_json(manifest_file)
        if (source.get("schema_version") != 1
                or source.get("status") != SHARD_STATUS
                or source.get("parent_commit") != index_record["parent_commit"]
                or source.get("shard_index") != number
                or source.get("shard_count") != shards
                or source.get("total_pinned_gitlinks") != 34
                or source.get("complete_shard") is not True):
            raise ValueError(f"Dolphin source shard {number}: wrong provenance or completeness")
        _require_false(source, (
            "approved_for_binary_distribution",
            "source_to_shipped_binary_correspondence_verified",
            "complete_corresponding_source_and_build_dependencies_verified",
            "independent_license_review_complete",
        ), label=f"Dolphin source shard {number}")
        rows = source.get("submodules")
        expected_shard = {name for i, name in enumerate(expected_paths)
                          if i % shards == number}
        if (not isinstance(rows, dict) or set(rows) != expected_shard
                or source.get("expected_archive_count_this_shard") != len(rows)):
            raise ValueError(f"Dolphin shard {number}: incomplete/duplicate Gitlink coverage")

        exact_files = {
            "SHA256SUMS.txt",
            "DOLPHIN_SUBMODULE_SOURCE_CANDIDATES_UNAPPROVED.json",
        }
        entries = {
            manifest_file.name: manifest_sha,
        }
        for name in sorted(rows):
            row = rows[name]
            upstream = original[name]
            filename = f"dolphin-submodule-{expected_paths.index(name):02d}-{upstream['sha']}.tar.gz"
            if (not isinstance(row, dict)
                    or row.get("source_repository") != upstream["url"]
                    or row.get("pinned_gitlink_commit") != upstream["sha"]
                    or row.get("archive_file") != filename
                    or row.get("source_archive_captured") is not True
                    or name in combined):
                raise ValueError(f"Dolphin source shard {number}: changed or duplicate Gitlink {name}")
            _require_false(row, ("corresponding_shipped_binary_verified",
                                 "recursive_dependencies_verified", "license_reviewed"),
                           label=name)
            archive = _regular_file(folder, filename)
            digest, size = _checksum(archive)
            if (not SHA256.fullmatch(str(row.get("archive_sha256")))
                    or row["archive_sha256"] != digest
                    or type(row.get("archive_size_bytes")) is not int
                    or size != row["archive_size_bytes"] or size <= 0):
                raise ValueError(f"Dolphin source shard {number}: archive SHA/size mismatch {name}")
            exact_files.add(filename)
            entries[filename] = digest
            combined[name] = {
                "source_repository": upstream["url"],
                "pinned_gitlink_commit": upstream["sha"],
                "archive_sha256": digest,
                "archive_size_bytes": size,
                "original_source_shard": number,
                "nested_gitmodules_reported": row.get("nested_gitmodules_in_archive", []),
                "corresponding_shipped_binary_verified": False,
                "complete_transitive_source_verified": False,
                "license_reviewed": False,
            }
        if {p.name for p in folder.iterdir()} != exact_files:
            raise ValueError(f"Dolphin shard {number}: missing/extra source files")
        saved = checksum_file.read_text("utf-8").splitlines()
        should = [f"{digest}  {filename}" for filename, digest in sorted(entries.items())]
        if sorted(saved) != sorted(should) or len(saved) != len(should):
            raise ValueError(f"Dolphin shard {number}: SHA256SUMS mismatch")
        shard_evidence.append({
            "shard_index": number,
            "original_manifest_sha256": manifest_sha,
            "source_archive_count": len(rows),
            "original_checksum_file_sha256": _checksum(checksum_file)[0],
        })
    if set(combined) != set(original) or len(combined) != 34:
        raise ValueError("Not all 34 Dolphin source candidates independently rehashed")
    record = {
        "schema_version": 1,
        "status": SOURCE_STATUS,
        "pinned_dolphin_parent_commit": index_record["parent_commit"],
        "pinned_gitlink_count": 34,
        "captured_source_archive_count": len(combined),
        "verified_shard_count": shards,
        "upstream_source_archive_candidates_collected": True,
        "approved_for_binary_distribution": False,
        "source_to_shipped_binary_correspondence_verified": False,
        "complete_corresponding_source_and_build_dependencies_verified": False,
        "independent_license_review_complete": False,
        "dolphin_sys_source_and_rights_verified": False,
        "shards": shard_evidence,
        "submodules": {name: combined[name] for name in sorted(combined)},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "DOLPHIN_34_SOURCE_ARCHIVE_REVIEW_UNAPPROVED.json"
    output_file.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    (output_dir / "SHA256SUMS.txt").write_text(
        f"{_checksum(output_file)[0]}  {output_file.name}\n", encoding="utf-8")
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=PINNED)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        index = json.loads(args.index.read_text("utf-8"))
        report = reconcile(index, args.input, args.output)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        parser.exit(1, f"Dolphin source evidence reconciliation failed: {error}\n")
    print(f"Rehashed {report['captured_source_archive_count']}/34 exact-source "
          "candidates across 6 original CI artifacts. Rights, nested source "
          "and binary-to-source correspondence remain UNAPPROVED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
