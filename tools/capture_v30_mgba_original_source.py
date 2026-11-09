"""Record ORIGINAL source-compiled mGBA four-platform native evidence.

mGBA is MPL-2.0, not GPL-2.0: preserve the exact original upstream LICENSE
and git-archived source with each native DLL/SO/DYLIB. A successful audit does
not prove third-party dependency compatibility, legal review or owner hardware
testing and MUST NOT enable any actual distribution approvals.

Read-only source research. Never submit to third-party repositories.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

SOURCE_REPOSITORY = "https://github.com/libretro/mgba"
SOURCE_REVISION = "7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6"
EXTENSIONS = {
    "windows-x64": ".dll", "linux-x64": ".so",
    "macos-arm64": ".dylib", "macos-x64": ".dylib",
}
ORIGINAL_MPL = "LICENSE"
OUTPUT_CORE_NAME = "mgba_libretro"
STATUS = "UNAPPROVED-ORIGINAL-SOURCE-COMPILED-MGBA-MPL2-FOUR-PLATFORM-RESEARCH"


def digest(content):
    return hashlib.sha256(content).hexdigest()


def validate_binary(name, content, target):
    ext = EXTENSIONS[target]
    magic = {
        ".dll": (b"MZ",), ".so": (b"\x7fELF",),
        ".dylib": (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"),
    }[ext]
    if name != OUTPUT_CORE_NAME + ext or not 50000 <= len(content) <= 70 * 1024 * 1024 or not content.startswith(magic):
        raise ValueError("Original compiled mGBA image is missing/wrong platform or implausible")


def capture(source: Path, binary: Path, output: Path, target: str):
    if (os.environ.get("AP_RELEASE_BUILD", "0") != "0"
            or os.environ.get("AP_V30_APPROVED_RELEASE", "0") != "0"):
        raise ValueError("Release mode cannot consume a raw research source capture")
    if target not in EXTENSIONS:
        raise ValueError("Unsupported 3.0 original mGBA source capture target")
    source, binary, output = Path(source), Path(binary), Path(output)
    if (source.is_symlink() or not source.is_dir() or binary.is_symlink()
            or not binary.is_file() or output.exists() or output.is_symlink()):
        raise ValueError("Missing pristine upstream checkout, real native or fresh output")
    head = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if head != SOURCE_REVISION:
        raise ValueError("Original upstream exact pinned SHA changed")
    image = binary.read_bytes()
    validate_binary(binary.name, image, target)
    notice_path = source / ORIGINAL_MPL
    if notice_path.is_symlink() or not notice_path.is_file() or notice_path.stat().st_size > 200000:
        raise ValueError("Exact MPL 2.0 upstream license is missing or unsafe")
    license_bytes = notice_path.read_bytes()
    if (b"Mozilla Public License Version 2.0" not in license_bytes
            or b"1. Definitions" not in license_bytes
            or b"3. Responsibilities" not in license_bytes):
        raise ValueError("Unrecognized original MPL 2.0 license text")
    original = subprocess.check_output(
        ["git", "-C", str(source), "archive", "--format=tar", "HEAD"], timeout=180)
    if not 250000 < len(original) < 160 * 1024 * 1024:
        raise ValueError("Incomplete/implausible original Git source TAR")
    original_name = f"mgba-{SOURCE_REVISION}-ORIGINAL-SOURCE.tar"
    output.mkdir(parents=True)
    (output / binary.name).write_bytes(image)
    (output / original_name).write_bytes(original)
    (output / "ORIGINAL_MPL_2_0_LICENSE.txt").write_bytes(license_bytes)
    result = {
        "schema_version": 1, "status": STATUS,
        "core": "mgba", "target": target,
        "original_upstream": SOURCE_REPOSITORY,
        "exact_upstream_revision": SOURCE_REVISION,
        "compiled_libretro_native": binary.name,
        "native_sha256": digest(image), "native_size_bytes": len(image),
        "original_source_tar": original_name,
        "original_source_sha256": digest(original),
        "original_source_bytes": len(original),
        "original_license_path": ORIGINAL_MPL,
        "original_license_sha256": digest(license_bytes),
        "original_license_bytes": len(license_bytes),
        "license_family": "MPL-2.0",
        "source_checkout_verified": True,
        "original_upstream_source_tar_verified": True,
        "original_native_gb_gbc_gba_test_verified": False,
        "third_party_compiler_and_link_deps_rights_reviewed": False,
        "binary_redistribution_approved": False,
        "combined_gpl_license_review_approved": False,
        "production_source_inventory_approved": False,
        "physical_qa_approved": False,
    }
    (output / "PINNED_MGBA_SOURCE_NATIVE_UNAPPROVED.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--native", type=Path, required=True)
    ap.add_argument("--target", choices=sorted(EXTENSIONS), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        result = capture(args.source, args.native, args.output, args.target)
    except (ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        ap.exit(1, f"Original mGBA pinned source research REFUSED: {exc}\n")
    print(json.dumps({k: result[k] for k in (
        "core", "target", "exact_upstream_revision", "native_sha256",
        "original_source_sha256", "binary_redistribution_approved",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
