"""Capture the original ParaLLEl N64 Libretro core actually compiled from pinned Git source.

This preserves original core bytes, exact pristine Git tree source and every
embedded original license notice. It NEVER approves combined GPL distribution
or misattributes an older buildbot core to a newly compiled native.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "config/v3.0-parallel-n64-source-notice-candidates.json"
SOURCE_REVISION = "e0ef5d673257e2e83bf9b7cffe62eda141af8493"
SOURCE_REPOSITORY = "https://github.com/libretro/parallel-n64"
STATUS = "UNAPPROVED-ORIGINAL-PARALLEL-N64-SOURCE-BUILT-NATIVE-4OS"
EXTENSIONS = {
    "windows-x64": ".dll", "linux-x64": ".so",
    "macos-arm64": ".dylib", "macos-x64": ".dylib",
}
MAX_NATIVE = 120 * 1024 * 1024
MAX_SOURCE = 260 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def gitblob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def validate_native(name, raw, target):
    if target not in EXTENSIONS:
        raise ValueError("Unknown exact N64 source-built platform")
    ext = EXTENSIONS[target]
    magic = {
        ".dll": (b"MZ",),
        ".so": (b"\x7fELF",),
        ".dylib": (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",
                   b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"),
    }[ext]
    if (name != "parallel_n64_libretro" + ext
            or not 100000 <= len(raw) <= MAX_NATIVE
            or not raw.startswith(magic)):
        raise ValueError("Original source-compiled ParaLLEl N64 native is invalid")


def _git(source, *args):
    return subprocess.check_output(
        ["git", "-C", str(source), *args], timeout=200,
    )


def validate_source_and_notices(source, index):
    """Reject dirty original source or changed embedded GPL/LGPL/MIT notices."""
    if (not isinstance(index, dict)
            or index.get("reported_source_commit") != SOURCE_REVISION
            or index.get("source_repository") != SOURCE_REPOSITORY
            or index.get("gitlink_count") != 0
            or index.get("license_notice_file_count") != 11
            or index.get("source_tree_entry_count") != 1970
            or index.get("source_to_native_binary_independently_verified") is not False
            or index.get("public_binary_redistribution_approved") is not False):
        raise ValueError("N64 original source and rights inventory changed")
    if _git(source, "rev-parse", "HEAD").decode().strip() != SOURCE_REVISION:
        raise ValueError("Original ParaLLEl-N64 checkout revision differs")
    if _git(source, "status", "--porcelain", "--untracked-files=no").strip():
        raise ValueError("Original pinned source has unexpected tracked changes")
    if (source / ".gitmodules").is_symlink() or (source / ".gitmodules").read_bytes() != b"":
        raise ValueError("Unexpected source submodule contents")
    # A source-capture archive must actually include all original notices.
    notes = index.get("notices")
    if not isinstance(notes, list) or len(notes) != 11:
        raise ValueError("Eleven exact original N64 license notices required")
    verified = {}
    for note in notes:
        if not isinstance(note, dict):
            raise ValueError("Malformed source license inventory")
        filename = note.get("path")
        if (not isinstance(filename, str) or not filename
                or PurePosixPath(filename).is_absolute()
                or ".." in PurePosixPath(filename).parts
                or note.get("notice_reviewed") is not False):
            raise ValueError("Unexpected or preapproved original N64 license path")
        item = source / filename
        if item.is_symlink() or not item.is_file():
            raise ValueError("Missing or unsafe checked-out original N64 license")
        # On Windows, actions/checkout can render tracked text as CRLF. An
        # immutable Git object's original bytes, NOT the platform-specific
        # working tree rendering, are the correct source-license evidence.
        # Git status above separately rejects *actual tracked modifications*.
        raw = _git(source, "show", "HEAD:" + filename)
        if (not 0 < len(raw) <= 1024 * 1024
                or len(raw) != note.get("size_bytes")
                or gitblob(raw) != note.get("git_blob_sha1")):
            raise ValueError(f"Original N64 upstream license Git blob changed: {filename}")
        verified[filename] = {"sha256": sha(raw), "size_bytes": len(raw)}
    if len(verified) != 11:
        raise ValueError("Duplicate original N64 license notices")
    # An empty .gitmodules is insufficient if Git actually tracks another Gitlink.
    entries = _git(source, "ls-tree", "-r", "HEAD").decode("utf-8", "replace").splitlines()
    # GitHub's recursive tree count includes directory nodes; git ls-tree -r
    # omits those directories. The *exact* Git commit and all original notices
    # are checked above, so bound the leaf-object count rather than equating
    # it to the 1970-entry GitHub tree total.
    if not 1200 <= len(entries) <= 1970 or any(row.startswith("160000 commit ") for row in entries):
        raise ValueError("Missing/injected upstream original N64 Gitlink")
    return verified


def capture(source, native, target, output):
    if (os.environ.get("AP_RELEASE_BUILD", "0") != "0"
            or os.environ.get("AP_V30_APPROVED_RELEASE", "0") != "0"):
        raise ValueError("Unapproved N64 source capture cannot run in a release workflow")
    source, native, output = Path(source), Path(native), Path(output)
    if (target not in EXTENSIONS or source.is_symlink() or not source.is_dir()
            or native.is_symlink() or not native.is_file()
            or output.is_symlink() or output.exists()):
        raise ValueError("Original N64 source/core/output missing or unsafe")
    index = json.loads(INDEX.read_text("utf-8"))
    notices = validate_source_and_notices(source, index)
    data = native.read_bytes()
    validate_native(native.name, data, target)
    archived = _git(source, "archive", "--format=tar", "HEAD")
    if not 1000000 < len(archived) < MAX_SOURCE:
        raise ValueError("Incomplete original N64 Git source TAR")
    original_name = f"parallel-n64-{SOURCE_REVISION}-ORIGINAL-SOURCE.tar"
    output.mkdir(parents=True)
    (output / native.name).write_bytes(data)
    (output / original_name).write_bytes(archived)
    manifest = {
        "schema_version": 1, "status": STATUS,
        "core": "parallel_n64", "target": target,
        "exact_upstream_source_revision": SOURCE_REVISION,
        "original_upstream_source_repository": SOURCE_REPOSITORY,
        "original_git_source_archive": original_name,
        "original_git_source_archive_sha256": sha(archived),
        "original_git_source_archive_bytes": len(archived),
        "actual_source_compiled_native_filename": native.name,
        "actual_source_compiled_native_sha256": sha(data),
        "actual_source_compiled_native_bytes": len(data),
        "source_tree_gitlinks": 0,
        "original_licenses": notices,
        "original_license_notice_count": 11,
        "original_tracked_source_unchanged": True,
        "reported_old_buildbot_source_equivalent": False,
        "native_source_build_and_playback_independently_reviewed": False,
        "mixed_gpl_combined_program_license_approved": False,
        "source_dependency_and_compiler_rights_reviewed": False,
        "corresponding_source_review_approved": False,
        "physical_game_audio_save_long_run_reviewed": False,
        "public_binary_redistribution_approved": False,
    }
    (output / "ORIGINAL_N64_SOURCE_NATIVE_UNAPPROVED.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", "utf-8")
    return manifest


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--target", choices=sorted(EXTENSIONS), required=True)
    p.add_argument("--output", type=Path, required=True)
    a=p.parse_args(argv)
    try:
        record=capture(a.source, a.native, a.target, a.output)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        p.exit(1, f"Original N64 source-built research BLOCKED: {exc}\n")
    print(json.dumps({k:record[k] for k in (
        "target", "exact_upstream_source_revision",
        "actual_source_compiled_native_sha256",
        "public_binary_redistribution_approved",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
