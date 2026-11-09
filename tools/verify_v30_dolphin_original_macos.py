"""Audit pristine source-built Dolphin Libretro macOS native candidates.

Engineering only: checks original upstream parent + 37 immutable Gitlinks,
real Mach-O exports/architecture and dynamic loader dependencies. No public
binary-source equivalence, playable GameCube or distribution rights inferred.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from tools.verify_v30_dolphin_original_build import (
    MANDATORY_LIBRETRO_SYMBOLS, verify_original_source,
)

TARGET_ARCHES = {
    "macos-arm64": "arm64",
    "macos-x86_64": "x86_64",
}
MAGIC_MACHO_64 = b"\xcf\xfa\xed\xfe"
MAX_LIBRARY = 512 * 1024 * 1024


def _command(*argv):
    return subprocess.check_output(
        list(argv), text=True, timeout=60, stderr=subprocess.PIPE,
    ).strip()


def verify_original_macos_native(path, target):
    if target not in TARGET_ARCHES:
        raise ValueError("Unexpected Apple architecture for source-built Dolphin")
    path = Path(path)
    if (path.name != "dolphin_libretro.dylib" or path.is_symlink()
            or not path.is_file()):
        raise ValueError("Missing original Dolphin macOS Libretro dylib")
    size = path.stat().st_size
    if not 200_000 < size <= MAX_LIBRARY:
        raise ValueError("Source-built Dolphin macOS dylib outside size limits")
    with path.open("rb") as stream:
        if stream.read(4) != MAGIC_MACHO_64:
            raise ValueError("Expected a native 64-bit little-endian Mach-O dylib")
    archs = _command("lipo", "-archs", str(path)).split()
    if archs != [TARGET_ARCHES[target]]:
        raise ValueError(f"Dolphin original native target architecture mismatch: {archs}")
    symbols = _command("nm", "-gU", str(path))
    names = {line.split()[-1].removeprefix("_")
             for line in symbols.splitlines() if line.split()}
    absent = sorted(set(MANDATORY_LIBRETRO_SYMBOLS) - names)
    if absent:
        raise ValueError(f"Missing Dolphin macOS Libretro entrypoints: {absent}")
    dyld = _command("otool", "-L", str(path))
    deps = [
        line.strip().split(" (compatibility version", 1)[0].strip()
        for line in dyld.splitlines()[1:] if line.strip()
    ]
    if not deps:
        raise ValueError("Cannot audit native Dolphin Mach-O runtime link dependencies")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "filename": path.name,
        "source_build_target": target,
        "architecture": TARGET_ARCHES[target],
        "native_sha256": digest.hexdigest(),
        "native_size_bytes": size,
        "verified_exports": sorted(MANDATORY_LIBRETRO_SYMBOLS),
        "mach_o_runtime_dependency_paths_not_yet_rights_reviewed": deps,
    }


def audit(source, native, output, target, *, verify_source=verify_original_source,
          verify_library=verify_original_macos_native):
    source_proof = verify_source(source)
    native_proof = verify_library(native, target)
    if (source_proof.get("direct_gitlinks_verified") != 34
            or source_proof.get("nested_gitlinks_verified") != 3):
        raise ValueError("Incomplete verified original Dolphin source graph")
    output = Path(output)
    if output.is_symlink() or output.exists():
        raise ValueError("Source-build audit output must not already exist")
    result = {
        "schema_version": 1,
        "status": "UNAPPROVED-ORIGINAL-PINNED-DOLPHIN-MACOS-SOURCE-BUILD",
        "upstream_source_repository": "https://github.com/libretro/dolphin",
        **source_proof,
        **native_proof,
        "original_unmodified_dolphin_source_compiled": True,
        "built_from_original_pinned_git_tree": True,
        "old_buildbot_binary_equivalence_claimed": False,
        "physical_gameplay_tested": False,
        "complete_corresponding_source_and_runtime_dependencies_reviewed": False,
        "combined_gpl_distribution_reviewed": False,
        "public_binary_distribution_approved": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", "utf-8")
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--target", choices=tuple(TARGET_ARCHES), required=True)
    args=p.parse_args(argv)
    try:
        result=audit(args.source,args.native,args.output,args.target)
    except (OSError,ValueError,TypeError,KeyError,subprocess.CalledProcessError,
            subprocess.TimeoutExpired,json.JSONDecodeError) as exc:
        p.exit(1,f"Original Dolphin macOS source build rejected: {exc}\n")
    print(f"Source-built native Dolphin {args.target}: {result['native_sha256']}; "
          "release and source rights remain UNAPPROVED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
