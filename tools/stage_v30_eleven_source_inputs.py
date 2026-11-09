"""Replace the last 3.0 buildbot-native slot with a REAL pristine-source Dolphin.

Research-only: transform a verified, already-staged TEN-original-family offline
input set into ELEVEN independently compiled upstream-native families. This
does not approve redistribution, GPL combinations, Apple/Windows retail
gameplay, or any production installer. No network, ROM, BIOS, or Dolphin app
installation is performed here.

Dolphin source is the immutable upstream parent plus all 37 Gitlinks. All
original source license notices and corresponding build inputs must remain
available at eventual approved distribution time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from zipfile import ZipFile

from anything_plays.v30_gpl_trial import MARKER
from tools.stage_v30_gpl_trial_inputs import TARGET_EXT, package_native_zip
from tools.verify_v30_dolphin_original_build import (
    REV, verify_original_library, verify_original_source,
)
from tools.verify_v30_dolphin_original_windows import verify_original_windows_native
from tools.verify_v30_dolphin_original_macos import verify_original_macos_native

NOTICE_PATHS = {
    "COPYING": "GPL-TRIAL-DOLPHIN-ORIGINAL-COPYING.txt",
    "LICENSES/GPL-2.0-or-later.txt": "GPL-TRIAL-DOLPHIN-ORIGINAL-GPL2-OR-LATER.txt",
    "LICENSES/BSD-3-Clause.txt": "GPL-TRIAL-DOLPHIN-ORIGINAL-BSD3.txt",
    "LICENSES/CC0-1.0.txt": "GPL-TRIAL-DOLPHIN-ORIGINAL-CC0.txt",
    "LICENSES/MIT.txt": "GPL-TRIAL-DOLPHIN-ORIGINAL-MIT.txt",
}

STATUS = "UNAPPROVED-ELEVEN-ORIGINAL-SOURCE-FAMILIES-NO-BUILDBOT-DOLPHIN"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verified_native(path: Path, target: str) -> dict:
    if target == "linux-x64":
        return verify_original_library(path)
    if target == "windows-x64":
        return verify_original_windows_native(path)
    if target in ("macos-arm64", "macos-x64"):
        return verify_original_macos_native(
            path, "macos-arm64" if target == "macos-arm64" else "macos-x86_64")
    raise ValueError("Unrecognized actual original Dolphin native target")


def _staged_ten(root: Path, target: str) -> tuple[dict, Path]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Missing safely staged ten-original-family source inputs")
    marker_path = root / MARKER
    if (marker_path.is_symlink() or not marker_path.is_file()
            or marker_path.stat().st_size > 32768):
        raise ValueError("Missing authentic exact ten-native trial marker")
    marker = json.loads(marker_path.read_text("utf-8"))
    expected = {
        "schema_version": 1,
        "target": target,
        "native_core_count": 11,
        "all_console_profiles": 18,
        "total_source_built_core_families": 10,
        "original_unchanged_core_archives": 1,
        "public_binary_distribution_approved": False,
        "combined_gpl_license_reviewed": False,
        "physical_qa_approved": False,
        "production_core_substitution_approved": False,
    }
    if (not isinstance(marker, dict)
            or any(marker.get(k) != v for k, v in expected.items())
            or marker.get("source_built_dolphin") is not None
            or not isinstance(marker.get("source_built_n64"), dict)
            or not isinstance(marker.get("source_exact_original_dolphin_sys"), dict)):
        raise ValueError("Not the complete authentic ten-original-source/Dolphin-Sys baseline")
    filename = f"dolphin_libretro{TARGET_EXT[target]}.zip"
    archive = root / filename
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size > 512 * 1024 * 1024:
        raise ValueError("Original preserved buildbot Dolphin native ZIP missing")
    with ZipFile(archive) as z:
        if z.namelist() != [f"dolphin_libretro{TARGET_EXT[target]}"]:
            raise ValueError("Unexpected historical Dolphin archive members")
    return marker, archive


def stage_eleven(*, ten_dir, original_source, native, target, output, evidence,
                 inspect_native=verified_native, inspect_source=verify_original_source):
    """Never copy a new native until all source, license and hash checks pass."""
    if target not in TARGET_EXT:
        raise ValueError("Unexpected eleven-source target")
    if (os.environ.get("AP_V30_GPL_TRIAL") != "1"
            or os.environ.get("AP_V30_TEST_CORES") != "1"
            or os.environ.get("AP_RELEASE_BUILD", "0") != "0"
            or os.environ.get("AP_V30_APPROVED_RELEASE", "0") != "0"):
        raise ValueError("Unapproved research only; production rights must be independently reviewed")
    old_root, source, native, out, report = map(
        lambda p: Path(p).expanduser(),
        (ten_dir, original_source, native, output, evidence),
    )
    if (any(p.is_symlink() for p in (source, native, out, report))
            or not source.is_dir() or not native.is_file()
            or out.exists() or report.exists()
            or out.resolve() in (old_root.resolve(), source.resolve())
            or report.resolve() == out.resolve()):
        raise ValueError("Unsafe original source/native or overwritten staging destination")
    marker, old_archive = _staged_ten(old_root, target)
    proof = inspect_source(source)
    if (not isinstance(proof, dict)
            or proof.get("parent_commit") != REV
            or proof.get("direct_gitlinks_verified") != 34
            or proof.get("nested_gitlinks_verified") != 3):
        raise ValueError("Not the FULL original pinned Dolphin parent plus 37 source Gitlinks")
    expected_name = f"dolphin_libretro{TARGET_EXT[target]}"
    if native.name != expected_name:
        raise ValueError("Native filename does not match target architecture")
    compiled = inspect_native(native, target)
    if (not isinstance(compiled, dict)
            or compiled.get("native_sha256") is None
            or compiled.get("native_size_bytes") != native.stat().st_size
            or compiled.get("native_sha256") != sha(native.read_bytes())):
        raise ValueError("Native Dolphin differs from the actual newly compiled source proof")
    license_notices = {}
    for upstream, name in NOTICE_PATHS.items():
        path = source / upstream
        if path.is_symlink() or not path.is_file() or not 50 < path.stat().st_size < 1024 * 1024:
            raise ValueError(f"Missing exact original Dolphin source license: {upstream}")
        data = path.read_bytes()
        license_notices[name] = {"source_path": upstream, "sha256": sha(data), "data": data}
    if not b"GPL" in license_notices[NOTICE_PATHS["COPYING"]]["data"]:
        raise ValueError("Original upstream Dolphin copyright statement missing")
    compiled_native = native.read_bytes()
    replacement = package_native_zip("dolphin", TARGET_EXT[target], compiled_native)
    row = {
        "source_repository": "https://github.com/libretro/dolphin",
        "source_commit": REV,
        "native_filename": expected_name,
        "native_sha256": sha(compiled_native),
        "native_size_bytes": len(compiled_native),
        "native_archive_sha256": sha(replacement),
        "direct_original_gitlinks": 34,
        "nested_original_gitlinks": 3,
        "old_unverified_buildbot_replaced": True,
        "pristine_unmodified_original_source_compiled": True,
        "original_source_notices": {
            name: {"source_path": v["source_path"], "sha256": v["sha256"]}
            for name, v in sorted(license_notices.items())
        },
        "production_hardware_gameplay_reviewed": False,
        "full_corresponding_source_and_transitive_rights_reviewed": False,
        "public_binary_distribution_approved": False,
    }
    result = dict(marker)
    result["source_built_dolphin"] = row
    result["total_source_built_core_families"] = 11
    result["original_unchanged_core_archives"] = 0
    # Never infer rights from matching source, gameplay, or package ZIP.
    for key in ("public_binary_distribution_approved", "combined_gpl_license_reviewed",
                "physical_qa_approved", "production_core_substitution_approved"):
        result[key] = False
    out.mkdir(parents=True)
    for item in old_root.iterdir():
        if item.is_symlink() or not item.is_file():
            raise ValueError("Unexpected non-file in ten-original input baseline")
        dst = out / item.name
        if item.name == old_archive.name:
            dst.write_bytes(replacement)
        elif item.name == MARKER:
            dst.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", "utf-8")
        else:
            shutil.copyfile(item, dst)
    for name, license_row in license_notices.items():
        target_path = out / name
        if target_path.exists():
            raise ValueError("Original source notice collides with source stage output")
        target_path.write_bytes(license_row["data"])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({
        "status": STATUS,
        "target": target,
        "native_core_count": 11,
        "source_built_families": 11,
        "old_buildbot_dolphin_excluded": True,
        "source_built_dolphin": row,
        "public_binary_distribution_approved": False,
    }, sort_keys=True, indent=2) + "\n", "utf-8")
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("ten-dir", "original-source", "native", "target", "output", "evidence"):
        p.add_argument("--"+name, required=True)
    a=p.parse_args(argv)
    try:
        result=stage_eleven(
            ten_dir=a.ten_dir, original_source=a.original_source,
            native=a.native, target=a.target, output=a.output, evidence=a.evidence)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        p.exit(1, f"Original 11-source native family staging BLOCKED: {exc}\n")
    print(f"Native source-built {result['source_built_dolphin']['native_filename']} replaced last unverified buildbot core; 11 original families; public rights FALSE")


if __name__=="__main__":
    main()
