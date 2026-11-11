"""Summarize unresolved native linkage from genuine 3.1 RC1 macOS QA reports.

This is a read-only *review aid*, not a native loader simulation, a
corresponding-source certificate, a license determination or release approval.
Only report what inspected Mach-O files and their otool dependency names show.
In particular, matching a dylib basename does not prove where dyld loads it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

SOURCE_REVISION = "26de1e1ad1b701d0735e085158347f8c213ce437"
TARGET_ARCHES = {"macos-arm64": "arm64", "macos-x64": "x86_64"}
REPORT_STATUS = "UNRELEASED_3_1_MACOS_NATIVE_LINKAGE_REVIEW"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_REPORT_SIZE = 20 * 1024 * 1024


def _native_path(value):
    """Reject absolute, traversal and Windows-style paths in QA metadata."""
    if (not isinstance(value, str) or not value
            or value.startswith("/") or "\\" in value
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise ValueError("Unsafe or missing native file path")
    return value


def _read_report(path):
    path = Path(path)
    if (path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= MAX_REPORT_SIZE):
        raise ValueError("Missing, linked or oversized macOS linkage QA report")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid macOS linkage QA JSON") from exc
    return record


def inspect_linkage_report(report, target):
    """Validate one immutable QA report and classify observed dependencies."""
    if target not in TARGET_ARCHES or not isinstance(report, dict):
        raise ValueError("Expected one of the two supported Mac targets")
    if (report.get("schema_version") != 1
            or report.get("status") != REPORT_STATUS
            or report.get("target") != target
            or report.get("source_app_commit") != SOURCE_REVISION
            or report.get("expected_architecture") != TARGET_ARCHES[target]
            or report.get("redistribution_approved") is not False
            or report.get("lgpl_relinking_reviewed") is not False
            or report.get("upstream_sdl_sources_correspondence_verified") is not False):
        raise ValueError("Unpinned, incomplete or improperly approved linkage report")

    files = report.get("native_files")
    if (not isinstance(files, list) or not files
            or report.get("native_file_count") != len(files)):
        raise ValueError("Missing native file inventory or inconsistent count")
    names = {}
    observed_paths = set()
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Malformed native file entry")
        path = _native_path(item.get("path"))
        digest = item.get("sha256")
        if (path in observed_paths or not isinstance(digest, str)
                or not SHA256.fullmatch(digest)
                or not isinstance(item.get("size_bytes"), int)
                or isinstance(item.get("size_bytes"), bool)
                or item["size_bytes"] < 1):
            raise ValueError("Duplicate or unverified native file identity")
        observed_paths.add(path)
        names.setdefault(path.rsplit("/", 1)[-1], []).append(
            {"path": path, "sha256": digest}
        )

    dependencies = {}
    for item in files:
        result = item.get("otool_result")
        deps = item.get("otool_dependencies")
        if (not isinstance(result, dict) or result.get("return_code") != 0
                or not isinstance(deps, list) or not deps):
            raise ValueError("Failed or missing otool dependency inspection")
        for dep in deps:
            name = dep.get("name") if isinstance(dep, dict) else None
            if (not isinstance(name, str) or not 0 < len(name) <= 2048
                    or any(char in name for char in "\r\n\0")):
                raise ValueError("Malformed native dependency name")
            if name.startswith(("/usr/lib/", "/System/Library/")):
                category = "observed_system_library_path"
                candidates = []
            elif name.startswith("/"):
                category = "external_absolute_path_requires_review"
                candidates = []
            else:
                # Only a *name* match. @rpath and @loader_path must still
                # be resolved by the real dynamic loader on actual hosts.
                candidates = sorted(
                    names.get(name.rsplit("/", 1)[-1], []),
                    key=lambda candidate: candidate["path"],
                )
                distinct_hashes = {entry["sha256"] for entry in candidates}
                if not candidates:
                    category = "not_found_in_audited_native_subset"
                elif len(distinct_hashes) > 1:
                    category = "ambiguous_same_basename_different_binaries"
                else:
                    category = "audited_basename_match_only"
            entry = dependencies.setdefault(name, {
                "dependency": name,
                "classification": category,
                "possible_audited_files": candidates,
                "referenced_by": [],
                "actual_loader_resolution_verified": False,
                "corresponding_source_and_notices_reviewed": False,
            })
            if item["path"] not in entry["referenced_by"]:
                entry["referenced_by"].append(item["path"])

    rows = sorted(dependencies.values(), key=lambda item: item["dependency"])
    for row in rows:
        row["referenced_by"].sort()
    attention = [
        row["dependency"] for row in rows
        if row["classification"] not in
        ("audited_basename_match_only", "observed_system_library_path")
    ]
    return {
        "target": target,
        "source_app_commit": SOURCE_REVISION,
        "native_files_examined": len(files),
        "dependency_name_count": len(rows),
        "unresolved_or_ambiguous_names": attention,
        "dependencies": rows,
        "complete_dependency_scope_verified": False,
        "actual_loader_resolution_verified": False,
        "complete_corresponding_source_verified": False,
        "redistribution_approved": False,
    }


def assemble_gap_report(arm_report, intel_report):
    """Require both Mac architectures; never present one as complete."""
    reports = {
        "macos-arm64": inspect_linkage_report(arm_report, "macos-arm64"),
        "macos-x64": inspect_linkage_report(intel_report, "macos-x64"),
    }
    return {
        "schema_version": 1,
        "status": "REVIEW_ONLY_3_1_MACOS_NATIVE_LINKAGE_GAPS",
        "source_app_commit": SOURCE_REVISION,
        "scope": "SDL/pygame native candidates audited in original RC1 DMGs; not all packaged libraries",
        "mac_targets_examined": list(TARGET_ARCHES),
        "reports": reports,
        "next_review": [
            "Resolve each @rpath, @loader_path and @executable_path against the actual signed app",
            "Inventory native libraries omitted from the original SDL/pygame subset",
            "Trace SDL and transitive dependencies to exact corresponding source and build options",
            "Prepare testable end-user LGPL library replacement and notices where required",
            "Independently review applicable redistribution duties and physical hardware acceptance",
        ],
        "actual_loader_resolution_verified": False,
        "corresponding_source_complete": False,
        "lgpl_compliance_approved": False,
        "stable_3_1_release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-report", type=Path, required=True)
    parser.add_argument("--intel-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.arm_report, args.intel_report):
        if args.output.resolve() == path.resolve():
            parser.error("Output must not overwrite source QA evidence")
    report = assemble_gap_report(
        _read_report(args.arm_report), _read_report(args.intel_report)
    )
    output = args.output.resolve()
    if output.exists() and output.is_symlink():
        parser.error("Refusing symlink output")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unresolved = sum(
        len(row["unresolved_or_ambiguous_names"])
        for row in report["reports"].values()
    )
    print(f"Read-only Mac native dependency triage: "
          f"{unresolved} unresolved/ambiguous dependency names; "
          "LGPL correspondence and stable 3.1 release remain unapproved")


if __name__ == "__main__":
    main()
