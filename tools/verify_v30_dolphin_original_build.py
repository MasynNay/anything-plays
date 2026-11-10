"""Audit a newly compiled *unmodified* pinned Dolphin Libretro native candidate.

Linux-only initial engineering probe, not proof of corresponding source for
the archived buildbot binary and NEVER public redistribution clearance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from tools.check_v30_dolphin_submodules import PINNED, validate_index
from tools.capture_v30_dolphin_nested_sources import NESTED, INDEX_STATUS

REV = "32c61f9d0e933331bb7087ba57e96883241b4960"
BUILD_ONLY_LINK_SHIM = Path(__file__).resolve().parents[1] / "tools" / "v30_dolphin_original_link_order.cmake"
MANDATORY_LIBRETRO_SYMBOLS = (
    "retro_init", "retro_deinit", "retro_load_game",
    "retro_run", "retro_unload_game", "retro_get_system_info",
)


def git(source, *args):
    return subprocess.check_output(
        ["git", "-C", str(source), *args], text=True, timeout=90,
        stderr=subprocess.PIPE).strip()


def require_clean_tracked_source(checkout, label):
    """Reject edits to tracked files in every source checkout, not just the parent."""
    if git(checkout, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError(f"Original Dolphin tracked source was edited: {label}")


def verify_original_source(source, *, direct_index=PINNED, nested_index=NESTED):
    source = Path(source)
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Missing original Dolphin Git checkout")
    if git(source, "rev-parse", "HEAD") != REV:
        raise ValueError("Original Dolphin parent source commit differs from exact pin")
    require_clean_tracked_source(source, "parent")
    direct_data = json.loads(Path(direct_index).read_text("utf-8"))
    nested_data = json.loads(Path(nested_index).read_text("utf-8"))
    direct = validate_index(direct_data)
    if (direct_data.get("parent_commit") != REV or
            nested_data.get("status") != INDEX_STATUS or
            nested_data.get("dolphin_parent_commit") != REV):
        raise ValueError("Immutable source lock does not belong to Dolphin candidate")
    if len(direct) != 34 or len(nested_data.get("parents", [])) != 2:
        raise ValueError("Missing 34 direct or nested source manifests")
    for path, row in direct.items():
        checkout = source / path
        if (checkout.is_symlink() or not checkout.is_dir()
                or git(source, "rev-parse", f"HEAD:{path}") != row["sha"]
                or git(checkout, "rev-parse", "HEAD") != row["sha"]):
            raise ValueError(f"Original Dolphin Gitlink mismatch: {path}")
        require_clean_tracked_source(checkout, path)
    nested = {}
    for parent in nested_data["parents"]:
        prefix = parent["parent_path"]
        if (prefix not in direct or
                direct[prefix]["sha"] != parent["parent_gitlink_commit"]):
            raise ValueError(f"Nested parent changed: {prefix}")
        parent_root = source / prefix
        for child in parent["nested"]:
            suffix = child["path"]
            key = f"{prefix}/{suffix}"
            if key in nested or not re.fullmatch(r"[0-9a-f]{40}", child["gitlink_commit"]):
                raise ValueError(f"Duplicate or invalid nested source: {key}")
            checkout = parent_root / suffix
            if (checkout.is_symlink() or not checkout.is_dir() or
                    git(parent_root, "rev-parse", f"HEAD:{suffix}") != child["gitlink_commit"] or
                    git(checkout, "rev-parse", "HEAD") != child["gitlink_commit"]):
                raise ValueError(f"Pinned Dolphin nested Gitlink missing: {key}")
            require_clean_tracked_source(checkout, key)
            nested[key] = child["gitlink_commit"]
    if len(nested) != 3:
        raise ValueError("Not all three exact nested source Gitlinks installed")
    return {"parent_commit": REV, "direct_gitlinks_verified": 34,
            "nested_gitlinks_verified": 3}


def verify_original_library(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.name != "dolphin_libretro.so":
        raise ValueError("Missing unmodified original Dolphin Linux Libretro shared library")
    size = path.stat().st_size
    if not 200_000 < size < 512 * 1024 * 1024:
        raise ValueError("Original Dolphin native library has implausible byte count")
    with path.open("rb") as reader:
        if reader.read(4) != b"\x7fELF":
            raise ValueError("Expected real ELF native Dolphin image")
    exported = subprocess.check_output(
        ["nm", "-D", "--defined-only", str(path)], text=True,
        timeout=45, stderr=subprocess.PIPE)
    names = {line.split()[-1] for line in exported.splitlines() if line.split()}
    missing = set(MANDATORY_LIBRETRO_SYMBOLS) - names
    if missing:
        raise ValueError(f"Original Dolphin Libretro API exports missing: {sorted(missing)}")
    digest = hashlib.sha256()
    with path.open("rb") as reader:
        for part in iter(lambda: reader.read(1024 * 1024), b""):
            digest.update(part)
    return {"filename": path.name, "native_sha256": digest.hexdigest(),
            "native_size_bytes": size, "verified_exports": sorted(MANDATORY_LIBRETRO_SYMBOLS)}


def audit(source, native, output, *, direct_index=PINNED, nested_index=NESTED):
    proof = verify_original_source(source, direct_index=direct_index, nested_index=nested_index)
    compiled = verify_original_library(native)
    if (BUILD_ONLY_LINK_SHIM.is_symlink()
            or not BUILD_ONLY_LINK_SHIM.is_file()
            or not BUILD_ONLY_LINK_SHIM.read_bytes()):
        raise ValueError("Missing original-source-preserving Dolphin CMake link repair")
    link_shim_sha = hashlib.sha256(BUILD_ONLY_LINK_SHIM.read_bytes()).hexdigest()
    output = Path(output)
    if output.is_symlink() or output.exists():
        raise ValueError("Refusing to overwrite a previous Dolphin source-build report")
    report = {
        "schema_version": 1,
        "status": "UNAPPROVED-ORIGINAL-PINNED-DOLPHIN-LINUX-SOURCE-BUILD",
        "upstream_source_repository": "https://github.com/libretro/dolphin",
        **proof, **compiled,
        "original_unmodified_dolphin_source_compiled": True,
        "built_from_original_pinned_git_tree": True,
        "source_build_target": "linux-x64",
        "build_only_original_source_link_order_cmake_sha256": link_shim_sha,
        "old_buildbot_binary_equivalence_claimed": False,
        "physical_gameplay_tested": False,
        "complete_corresponding_source_and_runtime_dependencies_reviewed": False,
        "combined_gpl_distribution_reviewed": False,
        "public_binary_distribution_approved": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args=parser.parse_args(argv)
    try:
        result=audit(args.source,args.native,args.output)
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError,
            subprocess.TimeoutExpired,json.JSONDecodeError) as err:
        parser.exit(1,f"Original Dolphin source/native build audit FAILED: {err}\n")
    print("Real original source-built Dolphin Linux ELF SHA256:",
          result["native_sha256"],"; distribution/old binary equivalence FALSE")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
