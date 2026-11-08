"""Stage nine source-compiled Libretro families in the 18-profile, 11-core internal 3.0 preview.

The ninth core, mGBA, is the exact pinned MPL-2.0 source-compiled binary from
the owner's successful four-platform GB/GBC/GBA original-homebrew experiment.
This module never approves distribution, changes 2.0 or publishes binaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from anything_plays.v30_gpl_trial import MARKER
from tools.capture_v30_mgba_original_source import (
    STATUS as MGBA_STATUS, SOURCE_REPOSITORY, SOURCE_REVISION,
    validate_binary,
)
from tools.stage_v30_eight_source_inputs import FAMILIES, stage_eight
from tools.stage_v30_gpl_trial_inputs import TARGET_EXT, package_native_zip

MGBA_SOURCE_RUN = 42527449154
MGBA_LICENSE_NAME = "MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt"
MGBA_REPORTS = tuple(f"ORIGINAL_{system}_NATIVE_AV.json" for system in ("GB", "GBC", "GBA"))
STATUS = "UNAPPROVED-NINE-ORIGINAL-SOURCE-CORE-FULL-3.0-OFFLINE-TEST"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect_original_mgba(folder, target):
    """Authenticate original mGBA source/native/license/AV; never infer rights."""
    if target not in TARGET_EXT:
        raise ValueError("Unsupported exact source-built mGBA target")
    root = Path(folder)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Missing original mGBA research artifact")
    ext = TARGET_EXT[target]
    name = f"mgba_libretro{ext}"
    source = f"mgba-{SOURCE_REVISION}-ORIGINAL-SOURCE.tar"
    manifest = "PINNED_MGBA_SOURCE_NATIVE_UNAPPROVED.json"
    required = {manifest, name, source, "ORIGINAL_MPL_2_0_LICENSE.txt", *MGBA_REPORTS}
    files = list(root.iterdir())
    observed = {p.name for p in files}
    if (len(files) > 15 or not required.issubset(observed)
            or any(p.is_symlink() or not p.is_file() for p in files)
            or any(f not in required and not (f.endswith(".png") and len(f) < 90)
                   for f in observed)):
        raise ValueError("Original mGBA artifact has missing or unreviewed files")
    marker_path = root / manifest
    if marker_path.stat().st_size > 20000:
        raise ValueError("Oversized source/native manifest")
    row = json.loads(marker_path.read_text("utf-8"))
    expected = {
        "schema_version": 1, "status": MGBA_STATUS, "core": "mgba",
        "target": target, "original_upstream": SOURCE_REPOSITORY,
        "exact_upstream_revision": SOURCE_REVISION,
        "compiled_libretro_native": name, "original_source_tar": source,
        "original_license_path": "LICENSE", "license_family": "MPL-2.0",
        "source_checkout_verified": True,
        "original_upstream_source_tar_verified": True,
        "original_native_gb_gbc_gba_test_verified": False,
        "binary_redistribution_approved": False,
        "combined_gpl_license_review_approved": False,
        "third_party_compiler_and_link_deps_rights_reviewed": False,
        "production_source_inventory_approved": False, "physical_qa_approved": False,
    }
    if not isinstance(row, dict) or any(row.get(k) != v for k, v in expected.items()):
        raise ValueError("False original mGBA source identity or rights approval")
    def original(filename, digest, length, cap):
        path = root / filename
        if (type(length) is not int or not 0 < length < cap
                or not isinstance(digest, str) or len(digest) != 64
                or not path.is_file() or path.stat().st_size != length):
            raise ValueError(f"Unverifiable exact source-built mGBA file: {filename}")
        data = path.read_bytes()
        if sha(data) != digest:
            raise ValueError(f"Original mGBA source/native digest changed: {filename}")
        return data
    native = original(name, row.get("native_sha256"), row.get("native_size_bytes"),
                      70 * 1024 * 1024)
    validate_binary(name, native, target)
    original(source, row.get("original_source_sha256"), row.get("original_source_bytes"),
             160 * 1024 * 1024)
    license_bytes = original("ORIGINAL_MPL_2_0_LICENSE.txt",
                             row.get("original_license_sha256"),
                             row.get("original_license_bytes"), 200000)
    if (b"Mozilla Public License Version 2.0" not in license_bytes
            or b"1. Definitions" not in license_bytes
            or b"3. Responsibilities" not in license_bytes):
        raise ValueError("Unrecognized original mGBA MPL 2.0 notice")
    report_digests = {}
    for report in MGBA_REPORTS:
        path = root / report
        if not 0 < path.stat().st_size < 1000000:
            raise ValueError("Missing original native A/V report")
        obj = json.loads(path.read_text("utf-8"))
        if (not isinstance(obj, dict) or obj.get("passed") is not True
                or obj.get("native_exit_code") != 0):
            raise ValueError(f"Source-built mGBA genuine A/V did not pass: {report}")
        report_digests[report] = sha(path.read_bytes())
    return native, license_bytes, {
        "source_repository": SOURCE_REPOSITORY, "source_commit": SOURCE_REVISION,
        "native_filename": name, "native_sha256": row["native_sha256"],
        "source_archive_sha256": row["original_source_sha256"],
        "original_license_notice_sha256": row["original_license_sha256"],
        "native_archive_sha256": sha(package_native_zip("mgba", ext, native)),
        "original_native_av_report_sha256": report_digests,
        "source_build_run_id": MGBA_SOURCE_RUN,
        "old_unverified_source_buildbot_replaced": True,
        "original_mpl_notice_copied": True,
    }


def stage_nine(*, original_dir, snes_dir, sega_dir, pce_artifact,
               five_dirs, mgba_dir, target, output, evidence, windows_runtime=None):
    required_flags = ("AP_V30_GPL_TRIAL", "AP_V30_PINNED_PCE",
                      "AP_V30_PINNED_FIVE", "AP_V30_PINNED_MGBA")
    if (any(os.environ.get(flag) != "1" for flag in required_flags)
            or os.environ.get("AP_RELEASE_BUILD", "0") != "0"
            or os.environ.get("AP_V30_APPROVED_RELEASE", "0") != "0"):
        raise ValueError("Only nine-source research test mode is allowed, never production")
    output, evidence = Path(output), Path(evidence)
    if (output.exists() or output.is_symlink() or evidence.exists()
            or evidence.is_symlink() or output.resolve() == evidence.resolve()):
        raise ValueError("Nine-source destination and evidence must both be NEW")
    native, license_bytes, mgba = inspect_original_mgba(mgba_dir, target)
    extension = TARGET_EXT[target]
    with tempfile.TemporaryDirectory(prefix="anything-plays-nine-original-sources-") as temp:
        temp = Path(temp)
        stage_eight(
            original_dir=original_dir, snes_dir=snes_dir, sega_dir=sega_dir,
            pce_artifact=pce_artifact, five_dirs=five_dirs,
            target=target, output=temp / "eight", evidence=temp / "eight-report.json",
            windows_runtime=windows_runtime,
        )
        source = temp / "eight"
        marker = json.loads((source / MARKER).read_text("utf-8"))
        if (marker.get("original_unchanged_core_archives") != 3
                or marker.get("total_source_built_core_families") != 8
                or marker.get("source_built_mgba") is not None):
            raise ValueError("Authentic original eight-source precursor is missing")
        marker["source_built_mgba"] = mgba
        marker["original_unchanged_core_archives"] = 2
        marker["total_source_built_core_families"] = 9
        marker["public_binary_distribution_approved"] = False
        marker["combined_gpl_license_reviewed"] = False
        marker["physical_qa_approved"] = False
        marker["production_core_substitution_approved"] = False
        native_zip = package_native_zip("mgba", extension, native)
        output.mkdir(parents=True)
        original_mgba_zip = f"mgba_libretro{extension}.zip"
        if not (source / original_mgba_zip).is_file():
            raise ValueError("Missing old mGBA slot in full 11-core offline archive")
        for path in source.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValueError("Unexpected symlink in eight-family source candidate")
            if path.name == MARKER:
                content = (json.dumps(marker, indent=2, sort_keys=True) + "\n").encode("utf-8")
            elif path.name == original_mgba_zip:
                content = native_zip
            else:
                content = path.read_bytes()
            (output / path.name).write_bytes(content)
        (output / MGBA_LICENSE_NAME).write_bytes(license_bytes)
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n", "utf-8")
    return marker


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("original-dir", "snes-dir", "sega-dir", "pce-artifact",
                 "target", "output", "evidence", "mgba-dir"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--windows-runtime")
    for name in sorted(FAMILIES):
        p.add_argument("--" + name.replace("_", "-") + "-dir", required=True)
    args = vars(p.parse_args(argv))
    try:
        row = stage_nine(
            original_dir=args["original_dir"], snes_dir=args["snes_dir"],
            sega_dir=args["sega_dir"], pce_artifact=args["pce_artifact"],
            target=args["target"], output=args["output"], evidence=args["evidence"],
            five_dirs={name: args[name + "_dir"] for name in FAMILIES},
            mgba_dir=args["mgba_dir"], windows_runtime=args["windows_runtime"],
        )
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        p.exit(1, f"Nine-source internal offline candidate REFUSED: {exc}\n")
    print(f"{row['target']}: 18 profiles/11 cores, nine source-built, two unchanged; NOT public release")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
