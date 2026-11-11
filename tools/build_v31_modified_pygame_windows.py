"""Compile a genuinely source-modified pygame-ce 2.5.8 C extension on Windows.

Uses the original tagged pygame-ce source (changed by the shared probe),
the upstream SDL2 2.32.10 Visual C developer archive pinned to the SHA-1
published in pygame-ce 2.5.8's own dependency downloader, and MSVC.

No prebuilt pygame extension is copied and no public release is altered.
This only compiles pygame.base for an isolated compatibility experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import subprocess
import sys
import sysconfig
import zipfile

from tools.build_v31_modified_pygame_probe import (
    PYGAME_COMMIT, PROBE_VALUE, sha256,
)

SDL_ARCHIVE_NAME = "SDL2-devel-2.32.10-VC.zip"
SDL_ARCHIVE_SHA1 = "27f5179346a0b0db80c4dd1769c7c9d62b9a91f3"
SDL_ARCHIVE_ROOT = "SDL2-2.32.10"
MAX_ZIP_BYTES = 45 * 1024 * 1024
MAX_MEMBER_BYTES = 20 * 1024 * 1024
OUTPUT_NAME = "base.cp313-win_amd64.pyd"
PINNED_CHANGED_C_SHA256 = "89b4e97a1fe664a95d5e8c7ec8d7e2836747e19debdace6e87e463f3a3c8b050"


def validate_pe_amd64(path):
    """Reject arbitrary files, x86 DLLs, and synthetic non-PE data."""
    data = Path(path).read_bytes()
    if len(data) < 0x100 or data[:2] != b"MZ":
        raise ValueError("Source compile did not create a valid Windows PE image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if pe < 64 or pe + 6 > len(data) or data[pe:pe+4] != b"PE\0\0":
        raise ValueError("Missing real PE header")
    if struct.unpack_from("<H", data, pe + 4)[0] != 0x8664:
        raise ValueError("Not a native Windows x64 compiled extension")
    return len(data)


def unpack_pinned_sdl(archive, folder):
    """Extract only upstream headers and one import library from checksum-pinned ZIP."""
    archive, folder = Path(archive), Path(folder)
    if (archive.name != SDL_ARCHIVE_NAME or not archive.is_file()
            or archive.is_symlink() or not 100_000 <= archive.stat().st_size <= MAX_ZIP_BYTES):
        raise ValueError("Expected original upstream SDL2 2.32.10 MSVC developer ZIP")
    if hashlib.sha1(archive.read_bytes()).hexdigest() != SDL_ARCHIVE_SHA1:
        raise ValueError("SDL2 VC developer ZIP does not match original upstream SHA-1")
    if folder.exists() or folder.is_symlink():
        raise ValueError("SDL headers must use a new disposable extract directory")
    folder.mkdir(parents=True)
    extracted_headers = 0
    extracted_lib = False
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            p = PurePosixPath(item.filename)
            parts = p.parts
            if (not parts or parts[0] != SDL_ARCHIVE_ROOT
                    or p.is_absolute() or ".." in parts
                    or item.file_size > MAX_MEMBER_BYTES):
                raise ValueError("Unsafe or unexpected SDL2 developer archive member")
            if item.is_dir():
                continue
            is_header = (len(parts) == 3 and parts[1] == "include"
                         and parts[2].lower().endswith(".h"))
            is_lib = parts == (SDL_ARCHIVE_ROOT, "lib", "x64", "SDL2.lib")
            if not is_header and not is_lib:
                continue
            dest = folder.joinpath(*parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Only archive headers and the one official x64 import library needed.
            dest.write_bytes(z.read(item))
            if is_header:
                extracted_headers += 1
            if is_lib:
                extracted_lib = True
    include = folder / SDL_ARCHIVE_ROOT / "include"
    lib = folder / SDL_ARCHIVE_ROOT / "lib" / "x64"
    if not extracted_lib or extracted_headers < 30 or not (include/"SDL.h").is_file():
        raise ValueError("Incomplete pinned SDL2 2.32.10 header/import library")
    return include, lib


def compile_changed_c(source_root, sdl_archive, output_dir, source_receipt,
                      *, runner=subprocess.run):
    source_root, output_dir = Path(source_root), Path(output_dir)
    if (not source_root.is_dir() or source_root.is_symlink()
            or output_dir.exists() or output_dir.is_symlink()):
        raise ValueError("Missing C source or an existing output directory")
    native_c = source_root/"src_c/base.c"
    if (native_c.is_symlink() or not native_c.is_file()
            or sha256(native_c) != PINNED_CHANGED_C_SHA256
            or source_receipt.get("original_source_revision") != PYGAME_COMMIT
            or source_receipt.get("patched_base_c_sha256") != PINNED_CHANGED_C_SHA256
            or source_receipt.get("expected_modified_native_method") != "_ap31_relink_probe"
            or source_receipt.get("expected_modified_native_result") != PROBE_VALUE
            or source_receipt.get("not_official_unmodified_pygame_wheel") is not True
            or source_receipt.get("full_lgpl_compliance_approved") is not False
            or source_receipt.get("stable_3_1_release_approved") is not False):
        raise ValueError("Not the exact original LGPL tagged C source modification")
    if (sys.version_info[:2] != (3, 13) or sys.platform != "win32"
            or not shutil.which("cl.exe")):
        raise ValueError("Needs native Visual C compiler and CPython 3.13 for x64 Windows")
    output_dir.mkdir(parents=True)
    include, lib = unpack_pinned_sdl(sdl_archive, output_dir/"sdl2-original-headers")
    python_include = Path(sysconfig.get_path("include"))
    python_lib = Path(sys.base_prefix)/"libs"/"python313.lib"
    if not python_include.is_dir() or not python_lib.is_file():
        raise ValueError("Original CPython 3.13 Windows SDK headers/import lib missing")
    macros = output_dir/"qa_pygame_version_macros.h"
    macros.write_text(
        '#define PG_MAJOR_VERSION 2\n#define PG_MINOR_VERSION 5\n'
        '#define PG_PATCH_VERSION 8\n#define PG_VERSION_TAG ""\n',
        "utf-8",
    )
    compiled = output_dir/OUTPUT_NAME
    args = [
        "cl.exe", "/nologo", "/LD", "/O2", "/MD", "/W3",
        "/FI"+str(macros.resolve()),
        "/I"+str(python_include.resolve()),
        "/I"+str((source_root/"src_c").resolve()),
        "/I"+str((source_root/"src_c/include").resolve()),
        "/I"+str(include.resolve()),
        str(native_c.resolve()),
        "/link", "/NOLOGO", "/MACHINE:X64",
        "/LIBPATH:"+str(lib.resolve()),
        "/LIBPATH:"+str(python_lib.parent.resolve()),
        "SDL2.lib", "python313.lib",
        "/OUT:"+str(compiled.resolve()),
    ]
    runner(args, cwd=output_dir, check=True)
    byte_size = validate_pe_amd64(compiled)
    return {
        "status": "COMPILED_ACTUALLY_SOURCE_MODIFIED_PYGAME_C_WINDOWS_X64",
        "source_git_commit": PYGAME_COMMIT,
        "source_native_file": "src_c/base.c",
        "source_sha256": PINNED_CHANGED_C_SHA256,
        "sdl2_source_header_version": "2.32.10",
        "official_sdl2_dev_zip_sha1": SDL_ARCHIVE_SHA1,
        "compiler": "MSVC cl.exe",
        "python_abi": "cp313-win_amd64",
        "compiled_path": str(compiled.resolve()),
        "compiled_name": OUTPUT_NAME,
        "compiled_pe_x64_size": byte_size,
        "compiled_sha256": sha256(compiled),
        "expected_native_method": "_ap31_relink_probe",
        "expected_native_result": PROBE_VALUE,
        "frozen_app_with_modified_native_booted": False,
        "modified_method_executed_from_copied_original_rc1": False,
        "full_lgpl_section_6_approved": False,
        "stable_3_1_release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for item in ("source", "sdl-archive", "out", "source-receipt", "receipt"):
        parser.add_argument("--"+item, type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.source_receipt.read_text("utf-8"))
    output = compile_changed_c(args.source, args.sdl_archive, args.out, manifest)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(output, indent=2)+"\n", "utf-8")
    print("Genuine modified C compiled into an x64 native PE:", output["compiled_sha256"])


if __name__ == "__main__":
    main()
