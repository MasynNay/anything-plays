"""Join verified native 3.0 identities with captured upstream source for review.

This generates a machine-readable *UNAPPROVED* source inventory from the
four-platform original native-core candidate lock and 10 archived upstream
source trees. It verifies every archive's SHA and byte size and all reported
Git revision prefixes. It deliberately never claims binary-to-source
reproducibility, license clearance, full submodule source or hardware QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

from tools.v30_release_lock import CORE_NAMES, TARGETS

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
FULL_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
SOURCE_MANIFEST = "SOURCE_SNAPSHOTS_UNAPPROVED.json"


def _archive_hash(archive, name):
    digest = hashlib.sha256()
    count = 0
    with archive.open(name) as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
            count += len(block)
    return digest.hexdigest(), count


def capture_index(zip_file):
    """Validate all original source tarballs without extracting untrusted tar."""
    with zipfile.ZipFile(zip_file) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or SOURCE_MANIFEST not in names:
            raise ValueError("Missing or duplicate upstream source provenance")
        record = json.loads(archive.read(SOURCE_MANIFEST))
        if (record.get("schema_version") != 1
                or record.get("approved_for_binary_distribution") is not False
                or record.get("independent_binary_to_source_match_proven") is not False):
            raise ValueError("Unapproved source snapshot evidence has unexpected status")
        entries = record.get("cores")
        if not isinstance(entries, dict) or set(entries) != CORE_NAMES:
            raise ValueError("Expected eleven upstream source identities")
        expected_names = {SOURCE_MANIFEST}
        for name, row in entries.items():
            revision = row.get("reported_commit")
            if name == "mednafen_pce_fast":
                if revision is not None or row.get("status") != "NO_REPORTED_SOURCE_REVISION":
                    raise ValueError("PCE Fast revision is unknown: do not guess")
                continue
            if (not isinstance(revision, str)
                    or not FULL_COMMIT.fullmatch(revision)
                    or row.get("status") != "REPORTED-COMMIT-SNAPSHOT-CAPTURED-NOT-APPROVED"
                    or row.get("redistribution_reviewed") is not False
                    or row.get("source_to_binary_independently_verified") is not False):
                raise ValueError(f"{name}: missing or falsely approved source snapshot")
            filename = f"source-{name}-{revision}.tar.gz"
            if row.get("archive_file") != filename:
                raise ValueError(f"{name}: source archive is not tied to exact Git commit")
            if (not isinstance(row.get("sha256"), str)
                    or not SHA256.fullmatch(row["sha256"])):
                raise ValueError(f"{name}: invalid original source digest")
            digest, count = _archive_hash(archive, filename)
            if digest != row["sha256"] or count != row.get("size_bytes"):
                raise ValueError(f"{name}: source archive checksum/size mismatch")
            expected_names.add(filename)
        if set(names) != expected_names:
            raise ValueError("Unexpected/missing source archive in review ZIP")
    return entries


def make_inventory(native_lock, snapshots):
    if (not isinstance(native_lock, dict)
            or native_lock.get("schema_version") != 1
            or native_lock.get("status") != "UNAPPROVED-FOUR-PLATFORM-3.0-CANDIDATE"
            or native_lock.get("approved_for_binary_distribution") is not False
            or native_lock.get("native_core_count") != 11
            or native_lock.get("system_profile_count") != 18):
        raise ValueError("Expected unapproved original 11-core production candidate")
    targets = native_lock.get("targets")
    if not isinstance(targets, dict) or set(targets) != TARGETS:
        raise ValueError("Expected all four platform-specific original native candidate targets")
    if not isinstance(snapshots, dict) or set(snapshots) != CORE_NAMES:
        raise ValueError("Expected eleven upstream core sources")
    report = {
        "schema_version": 1,
        "status": "UNAPPROVED-SOURCE-REVIEW-CANDIDATE",
        "approved_for_public_binary_distribution": False,
        "corresponding_source_inventory_verified": False,
        "independent_binary_to_source_match_proven": False,
        "source_commit": native_lock.get("source_commit"),
        "native_core_count": 11,
        "system_profile_count": 18,
        "source_snapshots_captured": 10,
        "source_snapshots_missing": ["mednafen_pce_fast"],
        "unresolved_tasks": [
            "Determine matching Beetle PCE Fast source revision from build provenance",
            "Archive and review exact Dolphin Gitlink submodule sources and dependencies",
            "Review all native core transitive libraries, build scripts and license notices",
            "Verify bit-for-bit native binary/source correspondence or independently supported source identification",
            "Obtain third-party GPL/noncommercial combined-distribution review and permission",
            "Complete physical and real-game acceptance across supported platforms",
        ],
        "targets": {},
    }
    if (not isinstance(report["source_commit"], str)
            or not FULL_COMMIT.fullmatch(report["source_commit"])):
        raise ValueError("Native candidate build commit is missing")
    for target in sorted(TARGETS):
        original = targets[target]
        if original.get("approved_for_distribution") is not False:
            raise ValueError(f"{target}: native candidate is unexpectedly approved")
        cores = original.get("cores")
        if not isinstance(cores, dict) or set(cores) != CORE_NAMES:
            raise ValueError(f"{target}: native candidate lacks eleven cores")
        source_rows = {}
        for name in sorted(CORE_NAMES):
            core, snap = cores[name], snapshots[name]
            if (core.get("redistribution_approved") is not False
                    or core.get("corresponding_source_verified") is not False
                    or snap.get("repository") != core.get("upstream_source_repository")):
                raise ValueError(f"{target}/{name}: source/core identity mismatched")
            for digest_name in ("native_sha256", "original_archive_sha256"):
                value = core.get(digest_name)
                if not isinstance(value, str) or not SHA256.fullmatch(value):
                    raise ValueError(f"{target}/{name}: missing binary identity")
            revision, binary_revision = snap.get("reported_commit"), core.get("upstream_reported_revision")
            if revision is None:
                if name != "mednafen_pce_fast" or binary_revision is not None:
                    raise ValueError(f"{target}/{name}: unknown core revision")
                archive_sha = archive_size = None
            else:
                if (not isinstance(binary_revision, str)
                        or not revision.startswith(binary_revision)):
                    raise ValueError(f"{target}/{name}: reported Git revision doesn't match archived source")
                archive_sha, archive_size = snap["sha256"], snap["size_bytes"]
            source_rows[name] = {
                "native_sha256": core["native_sha256"],
                "original_native_archive_sha256": core["original_archive_sha256"],
                "source_repository": core["upstream_source_repository"],
                "source_commit_sha": revision,
                "source_archive_sha256": archive_sha,
                "source_archive_size_bytes": archive_size,
                "source_build_dependencies_reviewed": False,
                "source_to_binary_verified": False,
                "redistribution_license_reviewed": False,
            }
        sys = original.get("dolphin_sys")
        if (not isinstance(sys, dict)
                or sys.get("source_correspondence_verified") is not False
                or not isinstance(sys.get("original_archive_sha256"), str)
                or not SHA256.fullmatch(sys["original_archive_sha256"])):
            raise ValueError(f"{target}: Dolphin Sys archive not verified")
        report["targets"][target] = {
            "cores": source_rows,
            "dolphin_sys": {
                "original_archive_sha256": sys["original_archive_sha256"],
                "original_archive_size_bytes": sys["original_archive_size_bytes"],
                "source_and_license_reviewed": False,
            },
        }
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-candidate", type=Path, required=True)
    p.add_argument("--source-snapshots", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.output.is_symlink() or args.output.exists():
            raise ValueError("Refusing to replace an existing source review record")
        original = json.loads(args.native_candidate.read_text("utf-8"))
        captured = capture_index(args.source_snapshots)
        review = make_inventory(original, captured)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(review, output, indent=2, sort_keys=True)
            output.write("\n")
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as err:
        p.exit(1, f"SOURCE REVIEW INVENTORY REJECTED: {err}\n")
    print("Recorded 44 native binaries, 4 Dolphin Sys original archives, "
          "10 pinned Git source snapshots and unresolved PCE revision. "
          "All correspondence and redistribution flags remain FALSE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
