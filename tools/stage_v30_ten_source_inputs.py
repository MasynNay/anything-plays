"""Stage full 18-console 3.0 offline research installer with TEN pinned source-built cores.

N64 is a newly compiled genuine pinned ParaLLEl-N64 native, not the older
source-unverified buildbot ZIP. Verify the exact 4-OS compilation artifact,
original Git source TAR, 11 source-tree GPL/LGPL/MIT notices and real
public-domain N64 CoreSession playback before replacing its offline ZIP.
No license or physical release approval is made. This only handles test-only
archives from the repository owner's private CI artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile

from anything_plays.v30_gpl_trial import MARKER
from tools.capture_v30_n64_original_source_build import (
    SOURCE_REPOSITORY, SOURCE_REVISION, STATUS as SOURCE_STATUS,
    validate_native,
)
from tools.stage_v30_nine_source_inputs import FAMILIES, stage_nine
from tools.stage_v30_gpl_trial_inputs import TARGET_EXT, package_native_zip

N64_SOURCE_RUN_ID = 42534736496
SOURCE_MARKER = "ORIGINAL_N64_SOURCE_NATIVE_UNAPPROVED.json"
SOURCE_PROBE = "ORIGINAL_N64_NATIVE_PLAYBACK_UNAPPROVED.json"
STATUS = "UNAPPROVED-TEN-SOURCE-FAMILIES-FULL-3.0-OFFLINE-TEST"
NOTICE_NAMES = tuple(f"GPL-TRIAL-N64-NOTICE-{i:02}.txt" for i in range(1, 12))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _original_bytes(folder, name, reported_sha, reported_length, max_size):
    file = Path(folder) / name
    if (not isinstance(reported_sha, str) or len(reported_sha) != 64
            or any(c not in "0123456789abcdef" for c in reported_sha)
            or type(reported_length) is not int or not 0 < reported_length <= max_size
            or file.is_symlink() or not file.is_file()
            or file.stat().st_size != reported_length):
        raise ValueError(f"Source-authentic N64 original file missing: {name}")
    raw = file.read_bytes()
    if digest(raw) != reported_sha:
        raise ValueError(f"Exact source-built N64 original SHA changed: {name}")
    return raw


def check_original_n64_artifact(folder, target):
    """Never equate this newly built library with a historical buildbot binary."""
    if target not in TARGET_EXT:
        raise ValueError("Unsupported original N64 target")
    root = Path(folder)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Missing original 4OS N64 source/native artifact")
    ext = TARGET_EXT[target]
    native_name = f"parallel_n64_libretro{ext}"
    source_name = f"parallel-n64-{SOURCE_REVISION}-ORIGINAL-SOURCE.tar"
    wanted = {SOURCE_MARKER, SOURCE_PROBE, native_name, source_name}
    files = list(root.iterdir())
    names = {p.name for p in files}
    if (len(files) > 6 or not wanted.issubset(names)
            or any(p.is_symlink() or not p.is_file() for p in files)
            or any(name not in wanted and name != "n64-homebrew-frame.png" for name in names)):
        raise ValueError("Unexpected files or missing N64 source/native playback evidence")
    metadata = root / SOURCE_MARKER
    if metadata.stat().st_size > 30000:
        raise ValueError("Unreviewed oversized N64 native identity manifest")
    m = json.loads(metadata.read_text("utf-8"))
    fields = {
        "schema_version": 1,
        "status": SOURCE_STATUS,
        "core": "parallel_n64",
        "target": target,
        "exact_upstream_source_revision": SOURCE_REVISION,
        "original_upstream_source_repository": SOURCE_REPOSITORY,
        "original_git_source_archive": source_name,
        "actual_source_compiled_native_filename": native_name,
        "source_tree_gitlinks": 0,
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
    if not isinstance(m, dict) or any(m.get(key) != value for key,value in fields.items()):
        raise ValueError("Forged original N64 source-native identity or distribution rights")
    native = _original_bytes(root, native_name, m.get("actual_source_compiled_native_sha256"),
                             m.get("actual_source_compiled_native_bytes"), 120*1024*1024)
    validate_native(native_name, native, target)
    source = _original_bytes(root, source_name, m.get("original_git_source_archive_sha256"),
                             m.get("original_git_source_archive_bytes"), 260*1024*1024)
    licenses = m.get("original_licenses")
    if not isinstance(licenses, dict) or len(licenses) != 11:
        raise ValueError("All eleven original N64 source notices are mandatory")
    copied = {}
    notice_sources = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(source), mode="r:") as tar:
            for i,path in enumerate(sorted(licenses)):
                identity = licenses[path]
                if (not isinstance(path, str) or path.startswith("/")
                        or ".." in Path(path).parts or "\\" in path
                        or not isinstance(identity, dict)
                        or type(identity.get("size_bytes")) is not int
                        or not 0 < identity["size_bytes"] <= 1024*1024):
                    raise ValueError("Unsafe original N64 license provenance path")
                member = tar.getmember(path)
                if not member.isfile() or member.issym() or member.islnk():
                    raise ValueError("Original N64 license is not a regular Git file")
                stream = tar.extractfile(member)
                if stream is None or member.size != identity["size_bytes"]:
                    raise ValueError("Original N64 license TAR member size changed")
                data = stream.read(identity["size_bytes"] + 1)
                if len(data) != identity["size_bytes"] or digest(data) != identity.get("sha256"):
                    raise ValueError(f"Original N64 GPL/LGPL/MIT notice mismatch: {path}")
                filename = NOTICE_NAMES[i]
                copied[filename] = data
                notice_sources[filename] = path
    except (tarfile.TarError, KeyError, OSError) as exc:
        raise ValueError("Original ParaLLEl N64 source TAR invalid") from exc
    probe = root / SOURCE_PROBE
    if not 0 < probe.stat().st_size < 1000000:
        raise ValueError("Missing authentic original N64 native homebrew probe")
    original_report = json.loads(probe.read_text("utf-8"))
    details = original_report.get("details")
    if (original_report.get("probe_passed") is not True
            or original_report.get("child_returncode") != 0
            or not isinstance(details, dict)
            or details.get("playback_probe_passed") is not True
            or details.get("nonblank_samples", 0) < 1):
        raise ValueError("Genuine pinned source-built N64 native playback failed")
    return native, copied, {
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_REVISION,
        "native_filename": native_name,
        "native_sha256": m["actual_source_compiled_native_sha256"],
        "original_source_sha256": m["original_git_source_archive_sha256"],
        "source_build_run_id": N64_SOURCE_RUN_ID,
        "original_native_av_sha256": digest(probe.read_bytes()),
        "old_unverified_buildbot_replaced": True,
        "native_archive_sha256": digest(package_native_zip("parallel_n64", ext, native)),
        "original_notice_sha256": {name: digest(data) for name,data in copied.items()},
        "original_notice_sources": notice_sources,
    }


def stage_ten(*, original_dir, snes_dir, sega_dir, pce_artifact, five_dirs,
              mgba_dir, n64_dir, target, output, evidence, windows_runtime=None):
    if (any(os.environ.get(flag) != "1" for flag in (
            "AP_V30_GPL_TRIAL","AP_V30_PINNED_PCE","AP_V30_PINNED_FIVE",
            "AP_V30_PINNED_MGBA","AP_V30_PINNED_N64"))
            or os.environ.get("AP_RELEASE_BUILD", "0") != "0"
            or os.environ.get("AP_V30_APPROVED_RELEASE", "0") != "0"):
        raise ValueError("Only genuine ten-family UNAPPROVED offline research permitted")
    output, evidence = Path(output), Path(evidence)
    if (output.exists() or output.is_symlink()
            or evidence.exists() or evidence.is_symlink()
            or output.resolve() == evidence.resolve()):
        raise ValueError("Original ten-family output and report must be newly created")
    native, notices, original = check_original_n64_artifact(n64_dir, target)
    extension = TARGET_EXT[target]
    with tempfile.TemporaryDirectory(prefix="anything-plays-ten-source-n64-") as temporary:
        tmp = Path(temporary)
        stage_nine(
            original_dir=original_dir, snes_dir=snes_dir,
            sega_dir=sega_dir, pce_artifact=pce_artifact,
            five_dirs=five_dirs, mgba_dir=mgba_dir,
            target=target, output=tmp/"nine", evidence=tmp/"nine-report.json",
            windows_runtime=windows_runtime,
        )
        previous = tmp/"nine"
        marker = json.loads((previous/MARKER).read_text("utf-8"))
        if (marker.get("total_source_built_core_families") != 9
                or marker.get("original_unchanged_core_archives") != 2
                or marker.get("source_built_n64") is not None):
            raise ValueError("Full original nine-family candidate was not authenticated")
        marker["source_built_n64"] = original
        marker["original_unchanged_core_archives"] = 1
        marker["total_source_built_core_families"] = 10
        for approval in ("public_binary_distribution_approved",
                         "combined_gpl_license_reviewed","physical_qa_approved",
                         "production_core_substitution_approved"):
            marker[approval] = False
        archive_name = f"parallel_n64_libretro{extension}.zip"
        if not (previous/archive_name).is_file():
            raise ValueError("Original ParaLLEl-N64 native archive slot missing")
        replacement = package_native_zip("parallel_n64", extension, native)
        output.mkdir(parents=True)
        for file in previous.iterdir():
            if file.is_symlink() or not file.is_file():
                raise ValueError("Unsafe original nine-source file")
            data = (json.dumps(marker,indent=2,sort_keys=True)+"\n").encode() if file.name==MARKER else (
                replacement if file.name==archive_name else file.read_bytes())
            (output/file.name).write_bytes(data)
        for name,data in sorted(notices.items()):
            (output/name).write_bytes(data)
        evidence.parent.mkdir(parents=True,exist_ok=True)
        evidence.write_text(json.dumps(marker,indent=2,sort_keys=True)+"\n","utf-8")
    return marker


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("original-dir","snes-dir","sega-dir","pce-artifact",
                 "target","output","evidence","mgba-dir","n64-dir"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--windows-runtime")
    for name in sorted(FAMILIES):
        p.add_argument("--"+name.replace("_","-")+"-dir",required=True)
    args=vars(p.parse_args(argv))
    try:
        row=stage_ten(
            original_dir=args["original_dir"],snes_dir=args["snes_dir"],
            sega_dir=args["sega_dir"],pce_artifact=args["pce_artifact"],
            five_dirs={name:args[name+"_dir"] for name in FAMILIES},
            mgba_dir=args["mgba_dir"],n64_dir=args["n64_dir"],
            target=args["target"],output=args["output"],evidence=args["evidence"],
            windows_runtime=args["windows_runtime"],
        )
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as exc:
        p.exit(1,f"Ten source-family N64 full offline research REFUSED: {exc}\n")
    print(f"{row['target']}: 18 profiles/11 cores, 10 original source builds, 1 original Dolphin; NO public rights")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
