"""Detect duplicate SDL install-name identities in signed 3.1 macOS RC1.

Consumes the *previously verified*, read-only native linker JSON reports
from run 42875616776. Same-basename libraries with distinct hashes or
Mach-O current versions can bind differently depending on @rpath order.
This is a diagnostic, not proof of a crash or permission to redistribute.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path, PurePosixPath
import re

SOURCE_COMMIT = "86baa6972ed923540f6ab49b636652a0f499d45c"
EXPECTED_COUNTS = {"macos-arm64": 121, "macos-x64": 120}
EXPECTED_ARCH = {"macos-arm64": "arm64", "macos-x64": "x86_64"}
SHA = re.compile(r"^[0-9a-f]{64}$")


def _safe_path(path):
    if (not isinstance(path, str) or not path
            or path.startswith("/") or "\\" in path
            or any(x in (".", "..", "") for x in path.split("/"))):
        raise ValueError("Unsafe native dylib path")
    return PurePosixPath(path).name


def audit(report):
    """Detect collisions without ever conflating different host architectures."""
    target = report.get("target")
    if (target not in EXPECTED_COUNTS
            or report.get("status") != "UNRELEASED_3_1_MACOS_NATIVE_LINKAGE_REVIEW"
            or report.get("source_app_commit") != SOURCE_COMMIT
            or report.get("redistribution_approved") is not False
            or report.get("upstream_sdl_sources_correspondence_verified") is not False
            or report.get("lgpl_relinking_reviewed") is not False):
        raise ValueError("Unreviewed, modified or already-approved macOS linkage report")
    natives = report.get("native_files")
    if (not isinstance(natives, list)
            or len(natives) != EXPECTED_COUNTS[target]
            or report.get("native_file_count") != len(natives)):
        raise ValueError("Incorrect complete native library inventory")
    groups = defaultdict(list)
    distinct = set()
    signed = 0
    for entry in natives:
        if not isinstance(entry, dict):
            raise ValueError("Malformed native record")
        path = entry.get("path")
        basename = _safe_path(path)
        if path in distinct:
            raise ValueError("Duplicate native record path")
        distinct.add(path)
        digest = entry.get("sha256")
        if not isinstance(digest, str) or not SHA.fullmatch(digest):
            raise ValueError("Invalid native library SHA-256")
        result = entry.get("lipo_result")
        signature = entry.get("codesign_metadata")
        otool = entry.get("otool_result")
        if (not isinstance(result, dict) or result.get("return_code") != 0
                or result.get("stdout", "").strip() != EXPECTED_ARCH[target]
                or not isinstance(signature, dict) or signature.get("return_code") != 0
                or "Signature=adhoc" not in signature.get("stderr", "")
                or not isinstance(otool, dict) or otool.get("return_code") != 0):
            raise ValueError("Missing authentic single-arch signed Mach-O inspection")
        signed += 1
        if "sdl" not in basename.lower():
            continue
        deps = entry.get("otool_dependencies")
        if not isinstance(deps, list) or not deps:
            raise ValueError("Missing SDL Mach-O install-name dependencies")
        first = deps[0]
        if not isinstance(first, dict):
            raise ValueError("Malformed SDL install-name")
        # Duplicate basenames can co-exist only by loader search context.
        # Even an identical dependency install name with different versions
        # is a potential @rpath ambiguity, not proof of incompatible ABI.
        groups[basename].append({
            "path": path,
            "sha256": digest,
            "install_name": first.get("name"),
            "macho_current_version": first.get("current_version"),
            "architecture": EXPECTED_ARCH[target],
        })
    collisions = []
    for name, entries in sorted(groups.items()):
        distinct_hashes = {e["sha256"] for e in entries}
        distinct_versions = {e["macho_current_version"] for e in entries}
        if len(distinct_hashes) > 1 or len(distinct_versions) > 1:
            collisions.append({
                "basename": name,
                "reason": "Different compiled versions/hashes sharing a basename",
                "variants": sorted(entries, key=lambda e: e["path"]),
                "runtime_resolution_proven": False,
            })
    return {
        "schema_version": 1,
        "status": "UNRELEASED_3_1_SDL_LIBRARY_COLLISION_REVIEW",
        "target": target,
        "source_app_commit": SOURCE_COMMIT,
        "signed_native_files_checked": signed,
        "sdl_library_name_groups": len(groups),
        "conflicting_sdl_basenames": collisions,
        "potential_loader_conflict_count": len(collisions),
        "actual_runtime_conflict_verified": False,
        "controller_camera_coexistence_hardware_accepted": False,
        "original_sources_correspondence_verified": False,
        "redistribution_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arm", type=Path, required=True)
    p.add_argument("--intel", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    reports = [
        audit(json.loads(args.arm.read_text("utf-8"))),
        audit(json.loads(args.intel.read_text("utf-8"))),
    ]
    if [v["target"] for v in reports] != ["macos-arm64", "macos-x64"]:
        p.error("Wrong signed native evidence architecture")
    result = {
        "schema_version": 1,
        "status": "UNRELEASED_3_1_SDL_LOADER_REVIEW_OPEN",
        "macos": reports,
        "has_potential_conflicting_sdl_load_paths": any(
            v["potential_loader_conflict_count"] for v in reports),
        "redistribution_approved": False,
        "hardware_coexistence_verified": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    for arch in reports:
        print(arch["target"], "signed native files:", arch["signed_native_files_checked"],
              "SDL basename collisions:", arch["potential_loader_conflict_count"])
        for conflict in arch["conflicting_sdl_basenames"]:
            print("  CONFLICT", conflict["basename"])
            for entry in conflict["variants"]:
                print("   ", entry["path"], entry["macho_current_version"])
    print("No actual runtime conflict or licensing approval asserted.")


if __name__ == "__main__":
    main()
