"""Stage a strictly unapproved, full-offline 18-profile GPL alternative lab.

Replaces the TWO noncommercial 3.0 preview core ZIPs with genuinely
source-built, hash-verified, differently NAMED GPL alternative libraries:
  Snes9x -> Beetle Supafaust (GPL-2.0-or-later, SNES)
  Genesis Plus GX -> BlastEm (GPLv3, Genesis/SMS/GG/SG1000)
All other NINE cores and original Dolphin Sys are byte-for-byte identical to
the existing preserved four-platform 3.0 trial inputs. No game images, BIOS,
downloads at app startup, or public artifacts. Not a licensing signoff.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from zipfile import ZipFile, ZipInfo, ZIP_STORED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fetch_mgba_core import CORE_NAMES, OPTIONAL_V21_CORES, V30_GPL_TRIAL_CORES
from anything_plays.v30_gpl_trial import (
    MARKER, STATUS, EXPECTED_SOURCE_COMMITS, validate_trial_core_directory,
)
from tools.probe_v30_gpl_core_switch import validate_original_source_artifact

TARGET_EXT = {
    "windows-x64": ".dll",
    "linux-x64": ".so",
    "macos-arm64": ".dylib",
    "macos-x64": ".dylib",
}
NOTICES = {
    "mednafen_supafaust": (
        "SUPAFAUST_ORIGINAL_GPL2_LICENSE.txt",
        "GPL-TRIAL-Supafaust-COPYING.txt",
    ),
    "blastem": (
        "blastem-GPLv3-NOTICE.txt",
        "GPL-TRIAL-BlastEm-COPYING.txt",
    ),
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def package_native_zip(name, ext, data):
    """One genuine original compiled image with its OWN core filename."""
    filename = f"{name}_libretro{ext}"
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_STORED) as archive:
        member = ZipInfo(filename, (1980, 1, 1, 0, 0, 0))
        member.compress_type = ZIP_STORED
        archive.writestr(member, data)
    return buffer.getvalue()


def stage_inputs(original_dir, snes_dir, sega_dir, output, evidence, target):
    if (os.environ.get("AP_V30_GPL_TRIAL") != "1"
            or os.environ.get("AP_V30_TEST_CORES") != "1"
            or os.environ.get("AP_RELEASE_BUILD", "0") != "0"
            or os.environ.get("AP_V30_APPROVED_RELEASE", "0") != "0"):
        raise ValueError("Unapproved offline 3.0 GPL trial mode is required")
    if target not in TARGET_EXT:
        raise ValueError("Unsupported trial target")
    if len(V30_GPL_TRIAL_CORES) != 11 or len(set(V30_GPL_TRIAL_CORES)) != 11:
        raise ValueError("Trial must keep all 11 native core slots")
    ext = TARGET_EXT[target]
    if ((sys.platform == "win32" and ext != ".dll")
            or (sys.platform == "darwin" and ext != ".dylib")
            or (sys.platform.startswith("linux") and ext != ".so")):
        raise ValueError("Real native OS does not match target")
    src, dst, proof = map(lambda p: Path(p).expanduser(),
                          (original_dir, output, evidence))
    if any(p.is_symlink() for p in (src, dst, proof)):
        raise ValueError("Symlinked stage input/output")
    if not src.is_dir() or dst.exists() or proof.exists():
        raise ValueError("Expected preserved inputs and a NEW output/report")
    if src.resolve() == dst.resolve() or src.resolve() in dst.resolve().parents:
        raise ValueError("Do not overwrite or nest inside preserved native inputs")
    if dst.resolve() == proof.resolve() or dst.resolve() in proof.resolve().parents:
        raise ValueError("Report destination must be separate from offline core inputs")
    original_names = set((*CORE_NAMES, *OPTIONAL_V21_CORES))
    if len(original_names) != 11:
        raise ValueError("Original 3.0 core inventory changed")
    originals = {f"{name}_libretro{ext}.zip" for name in original_names}
    originals.add("Dolphin.zip")
    record_path = src / "PRESERVED_NATIVE_INPUTS.json"
    if record_path.is_symlink() or not record_path.is_file():
        raise ValueError("Original 3.0 native input manifest missing")
    record = json.loads(record_path.read_text("utf-8"))
    rows = record.get("files")
    if (record.get("target") != target
            or record.get("status") != "UNAPPROVED-TEST-INPUTS"
            or record.get("public_distribution_approved") is not False
            or record.get("original_archive_count") != 12
            or not isinstance(rows, list) or len(rows) != 12
            or {row.get("name") for row in rows if isinstance(row, dict)} != originals):
        raise ValueError("Original original-natives set is not the unchanged 3.0 trial")
    if {p.name for p in src.iterdir()} != originals | {record_path.name}:
        raise ValueError("Unexpected original input member")
    preserved = {}
    for row in rows:
        name = row["name"]
        path = src / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 30 * 1024 * 1024:
            raise ValueError("Missing/unsafe original input ZIP")
        data = path.read_bytes()
        if sha256(data) != row.get("sha256") or len(data) != row.get("size_bytes"):
            raise ValueError(f"Unmodified original core archive checksum mismatch: {name}")
        preserved[name] = data
    replacements = {}
    notices = {}
    for core, artifact, mode in (
            ("mednafen_supafaust", snes_dir, "snes"),
            ("blastem", sega_dir, "sega")):
        native, digest = validate_original_source_artifact(artifact, mode, target)
        data = native.read_bytes()
        if len(data) <= 40000 or sha256(data) != digest:
            raise ValueError("Source-built alternative native fingerprint mismatch")
        zipped = package_native_zip(core, ext, data)
        notice_name, copied_name = NOTICES[core]
        notice = Path(artifact) / notice_name
        if notice.is_symlink() or not notice.is_file() or not notice.read_bytes().strip():
            raise ValueError(f"Missing original GPL source license notice for {core}")
        notices[copied_name] = notice.read_bytes()
        original_manifest_name = ("SUPAFAUST_SOURCE_BUILD_UNAPPROVED.json" if mode == "snes"
                                  else "PINNED_GPL_ALTERNATIVE_SOURCE_BUILD_UNAPPROVED.json")
        original = json.loads((Path(artifact) / original_manifest_name).read_text("utf-8"))
        replacements[core] = {
            "source_repository": ("https://github.com/libretro/supafaust" if mode == "snes"
                                  else "https://github.com/libretro/blastem"),
            "source_commit": EXPECTED_SOURCE_COMMITS[core],
            "source_archive_sha256": original["source_archive_sha256"],
            "native_filename": native.name,
            "native_sha256": digest,
            "archive_sha256": sha256(zipped),
            "original_source_notice_sha256": sha256(notice.read_bytes()),
            "notice_filename": copied_name,
        }
        # Do not retain an unapproved original commercial-terms core disguised
        # as a source-built alternative; archive members use their true names.
        preserved[f"{core}_libretro{ext}.zip"] = zipped
    for forbidden in ("snes9x", "genesis_plus_gx"):
        del preserved[f"{forbidden}_libretro{ext}.zip"]
    expected = {f"{name}_libretro{ext}.zip" for name in V30_GPL_TRIAL_CORES}
    expected.add("Dolphin.zip")
    if set(preserved) != expected or len(preserved) != 12:
        raise ValueError("GPL alternatives must preserve 11 cores, 18 profiles and Sys")
    marker = {
        "schema_version": 1,
        "status": STATUS,
        "target": target,
        "all_console_profiles": 18,
        "native_core_count": 11,
        "alternatives": replacements,
        "original_unchanged_core_archives": 9,
        "original_dolphin_sys_archive_unchanged": True,
        "original_native_inputs_sha256": sha256(record_path.read_bytes()),
        "public_binary_distribution_approved": False,
        "combined_gpl_license_reviewed": False,
        "physical_qa_approved": False,
        "production_core_substitution_approved": False,
    }
    # No output is created before every input has passed integrity validation.
    dst.mkdir(parents=True)
    for name, data in preserved.items():
        (dst / name).write_bytes(data)
    (dst / MARKER).write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n", "utf-8")
    for name, data in notices.items():
        (dst / name).write_bytes(data)
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n", "utf-8")
    return marker


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--original-dir", required=True, type=Path)
    ap.add_argument("--snes-dir", required=True, type=Path)
    ap.add_argument("--sega-dir", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--evidence", required=True, type=Path)
    ap.add_argument("--target", required=True, choices=tuple(TARGET_EXT))
    args = ap.parse_args(argv)
    try:
        result = stage_inputs(args.original_dir, args.snes_dir, args.sega_dir,
                              args.output, args.evidence, args.target)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        ap.exit(1, f"GPL alternative offline installer trial BLOCKED: {exc}\n")
    print(f"{result['target']}: exact 18-profile/11-core GPL alternative input set staged, NOT approved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
