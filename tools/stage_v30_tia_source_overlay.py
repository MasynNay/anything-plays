"""Replace GPLv2-only Stella2014 with GPLv2-or-later Tia in a full offline TEST.

The resulting 11-native/18-profile 3.0 artifact is still UNAPPROVED, not
a public release. No extra console, external emulator download or missing
GameCube/N64 substitution is permitted. Every source SHA/notice and the real
Atari2600 GUI Libretro audio/video homebrew are verified before writing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile

from anything_plays.v30_gpl_trial import MARKER, validate_trial_core_directory
from tools.stage_v30_gpl_trial_inputs import TARGET_EXT, package_native_zip

TIA_REPOSITORY = "https://github.com/warmenhoven/tia"
TIA_COMMIT = "6ae5bf998fe7a7842294089db17fc86fd73db1f0"
TIA_INDEPENDENT_TEST_RUN = 42625769973
COPYING_NAME = "GPL-TRIAL-tia-ORIGINAL-COPYING.txt"
SOURCE_NOTICE_NAME = "GPL-TRIAL-tia-ORIGINAL-SPDX.txt"
EVIDENCE_STATUS = "UNAPPROVED-GPL2PLUS-TIA-REPLACES-STELLA2014-IN-11-ORIGINAL-SOURCE-CORES"
SOURCE_EXPECTED = b"SPDX-License-Identifier: GPL-2.0-or-later"


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _bytes(path: Path, *, max_bytes: int) -> bytes:
    if (path.is_symlink() or not path.is_file()
            or not 1 < path.stat().st_size <= max_bytes):
        raise ValueError(f"Missing original source or unsafe file: {path}")
    return path.read_bytes()


def _source(source: Path) -> tuple[bytes, bytes]:
    if not source.is_dir() or source.is_symlink():
        raise ValueError("Original Tia Git checkout is missing")
    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(source), *args], text=True, timeout=25,
        ).strip()
    if (git("rev-parse", "HEAD") != TIA_COMMIT
            or git("remote", "get-url", "origin") != TIA_REPOSITORY
            or git("status", "--porcelain", "--untracked-files=all")):
        raise ValueError("Tia source identity does not match pristine pinned original Git")
    readme = _bytes(source / "README.md", max_bytes=256 * 1024)
    spdx = _bytes(source / "src" / "libretro.c", max_bytes=2 * 1024 * 1024)
    copying = _bytes(source / "COPYING", max_bytes=256 * 1024)
    if (b"GPL-2.0-or-later" not in readme
            or SOURCE_EXPECTED not in spdx
            or b"GNU GENERAL PUBLIC LICENSE" not in copying
            or b"Version 2" not in copying):
        raise ValueError("Original Git-authored GPLv2-or-later grant cannot be verified")
    return copying, spdx


def stage_tia(*, baseline: Path, source: Path, native: Path,
              source_tar: Path, playback_report: Path,
              output: Path, evidence: Path, target: str):
    """Convert a proven ELEVEN-source lab installer into same-profile Tia test."""
    if target not in TARGET_EXT:
        raise ValueError("Unknown Tia OS architecture")
    if (os.environ.get("AP_V30_GPL_TRIAL") != "1"
            or os.environ.get("AP_V30_TEST_CORES") != "1"
            or os.environ.get("AP_V30_TIA_TRIAL") != "1"
            or os.environ.get("AP_RELEASE_BUILD", "0") != "0"
            or os.environ.get("AP_V30_APPROVED_RELEASE", "0") != "0"):
        raise ValueError("Tia alternative is research only, never approved public release")
    baseline, source, native, source_tar, playback_report, output, evidence = (
        Path(p) for p in (baseline, source, native, source_tar, playback_report, output, evidence)
    )
    if any(p.is_symlink() for p in (baseline, source, native, source_tar,
                                  playback_report, output, evidence)):
        raise ValueError("Refusing symlinked original sources or staging paths")
    if (not baseline.is_dir() or output.exists() or evidence.exists()
            or output.resolve() == baseline.resolve()
            or baseline.resolve() in output.resolve().parents
            or output.resolve() in baseline.resolve().parents
            or output.resolve() == source.resolve()
            or source.resolve() in output.resolve().parents):
        raise ValueError("Tia staging must not overwrite original 11-core source evidence")
    ext = TARGET_EXT[target]
    marker = validate_trial_core_directory(baseline, ext, verify_native=False)
    if (marker.get("total_source_built_core_families") != 11
            or marker.get("original_unchanged_core_archives") != 0
            or "stella2014" not in marker.get("source_built_remaining_five", {})
            or marker.get("source_built_tia") is not None
            or marker.get("target") != target):
        raise ValueError("Tia overlay requires authentic pristine 11-family baseline")
    old = baseline / f"stella2014_libretro{ext}.zip"
    if old.is_symlink() or not old.is_file():
        raise ValueError("Baseline original Stella compiled archive missing")
    with ZipFile(old) as z:
        if z.namelist() != [f"stella2014_libretro{ext}"]:
            raise ValueError("Unexpected original Stella archive")
    copying, spdx = _source(source)
    orig_tar = _bytes(source_tar, max_bytes=100 * 1024 * 1024)
    from io import BytesIO
    from tarfile import open as taropen
    with taropen(fileobj=BytesIO(orig_tar), mode="r:") as tar:
        names = set(tar.getnames())
        if not {"COPYING", "README.md", "src/libretro.c"} <= names:
            raise ValueError("Source archive not the full pinned Tia copyright tree")
        expected_source = {"COPYING": copying, "src/libretro.c": spdx,
                           "README.md": _bytes(source / "README.md", max_bytes=256*1024)}
        for filename, expected in expected_source.items():
            member = tar.getmember(filename)
            if (not member.isfile() or member.issym() or member.islnk()
                    or member.size != len(expected)
                    or tar.extractfile(member).read() != expected):
                raise ValueError(f"Tia original source TAR differs from pinned Git checkout: {filename}")
    expected_name = f"tia_libretro{ext}"
    if native.name != expected_name:
        raise ValueError("Wrong original Tia native target filename")
    raw = _bytes(native, max_bytes=60 * 1024 * 1024)
    headers = {".dll": (b"MZ",), ".so": (b"\x7fELF",), ".dylib": (
        b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe",
    )}
    if not raw.startswith(headers[ext]) or len(raw) < 10000:
        raise ValueError("Not a real compiled Tia platform native core")
    evidence_report = json.loads(_bytes(playback_report, max_bytes=512 * 1024))
    details = evidence_report.get("details")
    if (not isinstance(details, dict)
            or evidence_report.get("passed") is not True
            or evidence_report.get("native_exit_code") != 0
            or evidence_report.get("timed_out") is not False
            or details.get("passed") is not True
            or details.get("video_frames", 0) < 30
            or details.get("nonblank_frames_sampled", 0) < 2
            or details.get("unique_frame_hashes", 0) < 2
            or details.get("pcm_nonzero_samples", 0) < 100
            or details.get("pcm_sample_peak", 0) <= 0):
        raise ValueError("Original Tia Atari game did not render actual video and PCM")
    newzip = package_native_zip("tia", ext, raw)
    row = {
        "source_repository": TIA_REPOSITORY,
        "source_commit": TIA_COMMIT,
        "native_filename": expected_name,
        "native_sha256": digest(raw),
        "source_archive_sha256": digest(orig_tar),
        "native_archive_sha256": digest(newzip),
        "original_license_notice_sha256": digest(copying),
        "original_license_notice_copied": True,
        "old_unknown_source_buildbot_replaced": True,
        "source_build_run_id": TIA_INDEPENDENT_TEST_RUN,
        "native_playback_report_sha256": digest(_bytes(playback_report, max_bytes=512*1024)),
        "original_source_spdx_sha256": digest(spdx),
        "source_file_grants_gpl_2_or_later": True,
        "all_games_and_mappers_compatible": False,
        "public_binary_distribution_approved": False,
    }
    result = dict(marker)
    remaining = dict(result["source_built_remaining_five"])
    remaining.pop("stella2014")
    remaining["tia"] = row
    result["source_built_remaining_five"] = remaining
    result["source_built_tia"] = row
    result["original_stella2014_native_excluded"] = True
    result["stella2014_source_license_gpl2_only_replaced"] = True
    for flag in ("public_binary_distribution_approved", "combined_gpl_license_reviewed",
                 "physical_qa_approved", "production_core_substitution_approved"):
        result[flag] = False
    # Do not write anything until the full source and original gameplay proof
    # have been accepted. Copy all other original source-built cores bytewise.
    output.mkdir(parents=True)
    for item in baseline.iterdir():
        if item.is_symlink() or not item.is_file():
            raise ValueError("Invalid original eleven-source baseline")
        if item.name in {old.name, MARKER,
                         "GPL-TRIAL-stella2014-ORIGINAL-COPYING.txt"}:
            continue
        shutil.copyfile(item, output / item.name)
    (output / f"tia_libretro{ext}.zip").write_bytes(newzip)
    (output / COPYING_NAME).write_bytes(copying)
    (output / SOURCE_NOTICE_NAME).write_bytes(spdx)
    (output / MARKER).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", "utf-8")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({
        "status": EVIDENCE_STATUS, "target": target, "source_built_tia": row,
        "original_core_count": 11, "original_profile_count": 18,
        "original_stella2014_native_excluded": True,
        "public_binary_distribution_approved": False,
    }, sort_keys=True, indent=2) + "\n", "utf-8")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "source", "native", "source-tar",
                 "playback-report", "output", "evidence", "target"):
        p.add_argument("--" + name, required=True)
    a = p.parse_args()
    try:
        result = stage_tia(
            baseline=Path(a.baseline), source=Path(a.source),
            native=Path(a.native), source_tar=Path(a.source_tar),
            playback_report=Path(a.playback_report),
            output=Path(a.output), evidence=Path(a.evidence), target=a.target)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        p.exit(1, f"Original Tia 11-core trial BLOCKED: {exc}\n")
    print(f"{a.target}: true original GPL2+ Tia substituted; 18 profiles / 11 native cores; NOT publicly licensed by this test.")
    return 0 if result["source_built_tia"]["native_filename"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
