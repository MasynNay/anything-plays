"""Verify real 64-bit Windows Dolphin Libretro built from original pinned source.

Checks PE32+ x64 identity, six mandatory ABI exports via the native Windows
DLL loader, compiled SHA256, and all 34 direct + 3 nested pinned source Gitlinks.
This source-only research report DOES NOT grant third-party redistribution.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import struct

from tools.verify_v30_dolphin_original_build import (
    MANDATORY_LIBRETRO_SYMBOLS, verify_original_source,
)

AMD64 = 0x8664
PE32_PLUS = 0x20B
MAX_BYTES = 512 * 1024 * 1024


def verify_original_windows_native(path, *, loader=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.name != "dolphin_libretro.dll":
        raise ValueError("Missing source-built Windows Dolphin Libretro DLL")
    size = path.stat().st_size
    if not 200_000 < size <= MAX_BYTES:
        raise ValueError("Windows Dolphin DLL size outside expected range")
    with path.open("rb") as stream:
        hdr = stream.read(4096)
    if len(hdr) < 512 or hdr[:2] != b"MZ":
        raise ValueError("Not a Windows PE image")
    offset = struct.unpack_from("<I", hdr, 0x3c)[0]
    if offset < 64 or offset > len(hdr) - 27:
        raise ValueError("Invalid Windows PE header offset")
    if hdr[offset:offset + 4] != b"PE\x00\x00":
        raise ValueError("Missing Windows PE signature")
    if struct.unpack_from("<H", hdr, offset + 4)[0] != AMD64:
        raise ValueError("Windows original Dolphin binary is not AMD64")
    if struct.unpack_from("<H", hdr, offset + 24)[0] != PE32_PLUS:
        raise ValueError("Windows original Dolphin binary is not PE32+")
    if loader is None:
        if os.name != "nt":
            raise ValueError("Windows native load requires a real Windows host")
        loader = ctypes.WinDLL
    library = loader(str(path.resolve(strict=True)))
    missing = [name for name in MANDATORY_LIBRETRO_SYMBOLS
               if not callable(getattr(library, name, None))]
    if missing:
        raise ValueError(f"Windows Dolphin Libretro exports unavailable: {missing}")
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(data)
    return {
        "filename": path.name,
        "architecture": "x86_64",
        "source_build_target": "windows-x64",
        "native_size_bytes": size,
        "native_sha256": checksum.hexdigest(),
        "verified_libretro_exports": sorted(MANDATORY_LIBRETRO_SYMBOLS),
        "native_loadable_on_original_target_os": True,
    }


def audit(source, native, output, *, verify_source=verify_original_source,
          verify_library=verify_original_windows_native):
    proof = verify_source(source)
    core = verify_library(native)
    if proof.get("direct_gitlinks_verified") != 34 or proof.get("nested_gitlinks_verified") != 3:
        raise ValueError("Original Dolphin parent/37-source verification incomplete")
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Refusing to overwrite source audit")
    record = {
        "schema_version": 1,
        "status": "UNAPPROVED-PINNED-ORIGINAL-DOLPHIN-WINDOWS-SOURCE-COMPILE",
        "upstream_source_repository": "https://github.com/libretro/dolphin",
        **proof,
        **core,
        "original_unmodified_dolphin_source_compiled": True,
        "built_from_original_pinned_git_tree": True,
        "old_buildbot_binary_equivalence_claimed": False,
        "physical_gameplay_tested": False,
        "complete_corresponding_source_and_runtime_dependencies_reviewed": False,
        "combined_gpl_distribution_reviewed": False,
        "public_binary_distribution_approved": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", "utf-8")
    return record


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args=p.parse_args(argv)
    try:
        report=audit(args.source,args.native,args.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
        p.exit(1,f"Original source-built Dolphin Windows core rejected: {exc}\n")
    print("Exact source-built Windows Dolphin AMD64 SHA:",report["native_sha256"],
          "; public binary/source approval remains FALSE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
