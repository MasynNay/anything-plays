"""Assemble immutable, source-authentic, reviewed 3.0 production native inputs.

Unlike the developer-only GPL trial stager, this module accepts ONLY a
separately approved, exact 44-core/four-platform source/license lock and its
corresponding-source inventory. It will not approve anything. It independently
verifies the original eight unchanged cores and Dolphin Sys against their
original complete-offline research artifact, then replaces THREE core families
with validated original source-built Supafaust, BlastEm and Beetle PCE Fast.

Never publish the new ZIPs or call them license-cleared based on this script
alone: all third-party rights, source correspondence, and physical QA must be
reviewed independently. No ROM, BIOS, or external emulator downloads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fetch_mgba_core import CORE_NAMES, OPTIONAL_V21_CORES
from tools.v30_release_lock import (
    ALTERNATIVE_CORE_NAMES, TARGETS, load_approved_lock, selected_core_set,
    verify_core_archive, verify_core_payload, verify_dolphin_archive,
)
from tools.emit_v30_production_provenance import SOURCE_FILE, validate_source_inventory
from tools.stage_v30_approved_native_mapping import (
    EXT, approved_core_map_from_lock,
)
from tools.stage_v30_gpl_trial_inputs import package_native_zip
from tools.probe_v30_gpl_core_switch import validate_original_source_artifact
from tools.v30_pce_candidate import inspect_artifact, load_index
from anything_plays.v30_approved_core_map import REPOSITORIES, EXPECTED, WINDOWS_RUNTIME

UNAPPROVED_ORIGINAL = "PRESERVED_NATIVE_INPUTS.json"
RECEIPT = "V30_SOURCE_BUILT_INPUTS_MATCH_REVIEWED_LOCK.json"
# The old Snes9x / Genesis Plus GX must NOT be copied into production.
REPLACED_ORIGINAL = frozenset(("snes9x", "genesis_plus_gx", "mednafen_pce_fast"))
ORIGINAL_11 = frozenset((*CORE_NAMES, *OPTIONAL_V21_CORES))
UNCHANGED_8 = ORIGINAL_11 - REPLACED_ORIGINAL
assert len(ORIGINAL_11) == 11 and len(UNCHANGED_8) == 8
assert len(ALTERNATIVE_CORE_NAMES) == 11
NOTICES = {
    "mednafen_supafaust": ("SUPAFAUST_ORIGINAL_GPL2_LICENSE.txt",
                           "GPL-TRIAL-Supafaust-COPYING.txt"),
    "blastem": ("blastem-GPLv3-NOTICE.txt",
                "GPL-TRIAL-BlastEm-COPYING.txt"),
    "mednafen_pce_fast": ("PCE_COPYING_GPL-2.0.txt",
                          "GPL-TRIAL-PCE-COPYING.txt"),
}
SOURCE_ARTIFACT_RUNS = {
    "mednafen_supafaust": 42494297281,
    "blastem": 42496671418,
    "mednafen_pce_fast": 42444367068,
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _file_bytes(folder, name, *, max_size=30 * 1024 * 1024):
    """Require a single real local file; no network access, paths or symlinks."""
    if not isinstance(name, str) or name.startswith(".") or Path(name).name != name:
        raise ValueError("Unsafe reviewed native input filename")
    path = Path(folder) / name
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size < max_size:
        raise ValueError(f"Missing/unsafe reviewed native input: {name}")
    return path.read_bytes()


def _original_inputs(root, target, extension):
    """Check every original lab ZIP, not only the eight we plan to preserve."""
    folder = Path(root)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Original complete offline native input set missing or unsafe")
    originals = {f"{n}_libretro{extension}.zip" for n in ORIGINAL_11}
    originals.add("Dolphin.zip")
    expected = originals | {UNAPPROVED_ORIGINAL}
    observed = {p.name for p in folder.iterdir() if p.is_file() and not p.is_symlink()}
    if observed != expected or len(list(folder.iterdir())) != len(expected):
        raise ValueError("Original 12-native-input archive set has missing/extra/symlink entries")
    record = json.loads(_file_bytes(folder, UNAPPROVED_ORIGINAL))
    rows = record.get("files")
    if (record.get("target") != target
            or record.get("status") != "UNAPPROVED-TEST-INPUTS"
            or record.get("public_distribution_approved") is not False
            or record.get("original_archive_count") != 12
            or not isinstance(rows, list) or len(rows) != 12
            or {row.get("name") for row in rows if isinstance(row, dict)} != originals):
        raise ValueError("Original source input record is missing or rewritten")
    binaries = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid original source native record")
        name = row["name"]
        data = _file_bytes(folder, name)
        if sha(data) != row.get("sha256") or len(data) != row.get("size_bytes"):
            raise ValueError(f"Original preserved full offline artifact changed: {name}")
        binaries[name] = data
    return binaries


def _source_original_family(root, name, target, extension):
    """Return true verified compiled bytes and verbatim original GPL notice."""
    if name in ("mednafen_supafaust", "blastem"):
        mode = "snes" if name == "mednafen_supafaust" else "sega"
        native_path, digest = validate_original_source_artifact(root, mode, target)
        binary = native_path.read_bytes()
        if sha(binary) != digest or native_path.name != f"{name}_libretro{extension}":
            raise ValueError(f"{name} original compiled core differs from claimed source")
        notice = _file_bytes(root, NOTICES[name][0], max_size=1024 * 1024)
        metadata_name = ("SUPAFAUST_SOURCE_BUILD_UNAPPROVED.json" if mode == "snes"
                         else "PINNED_GPL_ALTERNATIVE_SOURCE_BUILD_UNAPPROVED.json")
        data = json.loads(_file_bytes(root, metadata_name, max_size=1024 * 1024))
        if (data.get("source_commit") != EXPECTED[name]
                or data.get("source_archive_sha256") is None
                or data.get("target") != target):
            raise ValueError("Source-built SNES/Sega original report changed")
        source_sha = data["source_archive_sha256"]
    else:
        index = load_index()
        binary = inspect_artifact(root, target, index)
        with ZipFile(root) as archive:
            notice = archive.read(NOTICES[name][0])
        source_sha = index["targets"][target]["source_archive_sha256"]
    if not 40000 < len(binary) < 60 * 1024 * 1024:
        raise ValueError(f"Invalid original compiled size: {name}")
    if not b"GNU GENERAL PUBLIC LICENSE" in notice:
        raise ValueError(f"Original upstream GPL text missing: {name}")
    return binary, notice, source_sha


def assemble_approved_inputs(*, lock, inventory, target, original_dir,
                             snes_dir, sega_dir, pce_artifact, output_dir,
                             windows_runtime=None):
    """Validate EVERYTHING, then create exactly one review-bound input folder.

    A caller-supplied JSON or environment variable cannot flip the real repo's
    unapproved lock: main() ALWAYS uses load_approved_lock(), the exact
    independently authored source inventory and checked-in license review.
    Unit tests may exercise this function with explicitly synthetic records.
    """
    if (os.environ.get("AP_V30_GPL_TRIAL", "0") != "0"
            or os.environ.get("AP_V30_TEST_CORES", "0") != "0"
            or os.environ.get("AP_RELEASE_BUILD") != "1"
            or os.environ.get("AP_V30_APPROVED_RELEASE") != "1"):
        raise ValueError("Only the independently reviewed production lane may stage approved inputs")
    if target not in TARGETS or selected_core_set(lock) != ALTERNATIVE_CORE_NAMES:
        raise ValueError("Only the reviewed source-built alternative set is supported")
    validate_source_inventory(lock, inventory)
    reviewed_map = approved_core_map_from_lock(lock, target)
    ext = EXT[target]
    original_target = {
        "windows-x86_64": "windows-x64",
        "linux-x86_64": "linux-x64",
        "macos-arm64": "macos-arm64",
        "macos-x86_64": "macos-x64",
    }[target]
    if ((target == "windows-x86_64") != (windows_runtime is not None)):
        raise ValueError("Exactly the original reviewed Windows runtime is mandatory on Windows only")
    output = Path(output_dir)
    for folder in (original_dir, snes_dir, sega_dir):
        p = Path(folder)
        if p.is_symlink() or not p.is_dir():
            raise ValueError("Missing original local source archive folder")
    if output.exists() or output.is_symlink():
        raise ValueError("Production immutable input folder must be new")
    if any(output.resolve() == Path(folder).resolve()
           or Path(folder).resolve() in output.resolve().parents
           for folder in (original_dir, snes_dir, sega_dir, pce_artifact)):
        raise ValueError("Cannot overwrite original source-built proof/archive files")
    # All 12 old archived inputs must be valid, but ONLY the eight unchanged
    # and Dolphin Sys may enter the approved alternative production candidate.
    original = _original_inputs(original_dir, original_target, ext)
    payload = {
        f"{name}_libretro{ext}.zip": original[f"{name}_libretro{ext}.zip"]
        for name in UNCHANGED_8
    }
    payload["Dolphin.zip"] = original["Dolphin.zip"]
    # Verifies exact immutable core ZIP (and Dolphin) identities from LOCK.
    for name in UNCHANGED_8:
        verify_core_archive(lock, _sys_platform(target), _architecture(target),
                            name, payload[f"{name}_libretro{ext}.zip"])
    verify_dolphin_archive(lock, _sys_platform(target), _architecture(target), payload["Dolphin.zip"])
    sources = {}
    archives = {}
    for name, location in (
            ("mednafen_supafaust", snes_dir),
            ("blastem", sega_dir),
            ("mednafen_pce_fast", pce_artifact)):
        native, license_text, source_sha = _source_original_family(
            location, name, original_target, ext)
        name_zip = f"{name}_libretro{ext}.zip"
        zipped = package_native_zip(name, ext, native)
        verify_core_archive(lock, _sys_platform(target), _architecture(target), name, zipped)
        verify_core_payload(lock, _sys_platform(target), _architecture(target),
                            name, f"{name}_libretro{ext}", native)
        if sha(license_text) != reviewed_map["cores"][name]["license_notice_sha256"]:
            raise ValueError(f"Unreviewed original upstream GPL notice: {name}")
        required = inventory["targets"][target]["cores"][name]
        if (required.get("source_archive_sha256") != source_sha
                or required.get("source_commit_sha") != EXPECTED[name]
                or required.get("source_repository") != REPOSITORIES[name]
                or required.get("native_sha256") != sha(native)):
            raise ValueError(f"Original source archive differs from independent source inventory: {name}")
        payload[name_zip] = zipped
        payload[NOTICES[name][1]] = license_text
        sources[name] = {
            "source_revision": EXPECTED[name],
            "source_archive_sha256": source_sha,
            "native_sha256": sha(native),
            "original_native_archive_sha256": sha(zipped),
            "original_license_sha256": sha(license_text),
            "original_owned_actions_run_id": SOURCE_ARTIFACT_RUNS[name],
        }
        archives[name] = sha(zipped)
    if target == "windows-x86_64":
        binary = _file_bytes(Path(windows_runtime).parent, Path(windows_runtime).name,
                             max_size=8 * 1024 * 1024)
        if not binary.startswith(b"MZ") or len(binary) < 10000:
            raise ValueError("Windows native DLL is not the actual compiled runtime")
        if sha(binary) != reviewed_map["runtime_dependencies"][WINDOWS_RUNTIME]:
            raise ValueError("Source-reviewed Windows DLL native hash changed")
        payload[WINDOWS_RUNTIME] = binary
    final_zip_names = {f"{n}_libretro{ext}.zip" for n in ALTERNATIVE_CORE_NAMES}
    if ({n for n in payload if n.endswith(".zip")} != final_zip_names | {"Dolphin.zip"}
            or len(final_zip_names) != 11):
        raise ValueError("Approved full 11-core offline native inventory incomplete")
    if any(f"{nc}_libretro{ext}.zip" in payload for nc in ("snes9x", "genesis_plus_gx")):
        raise ValueError("Original NC libraries remain in production payload")
    manifest = {
        "schema_version": 1,
        "status": "MATCHED-INDEPENDENTLY-APPROVED-3.0-SOURCE-LOCK",
        "target": target,
        "native_core_count": 11, "system_profile_count": 18,
        "unchanged_original_core_count": 8,
        "all_native_archive_sha256": {
            name: sha(data) for name, data in sorted(payload.items())
            if name.endswith(".zip")
        },
        "source_built_families": sources,
        "original_dolphin_sys_sha256": sha(payload["Dolphin.zip"]),
        "native_approval_comes_from_separately_reviewed_lock": True,
        "auto_granted_license_rights": False,
        "generated_by": "tools.stage_v30_approved_source_inputs",
    }
    output.mkdir(parents=True)
    for name, data in sorted(payload.items()):
        (output / name).write_bytes(data)
    (output / RECEIPT).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", "utf-8")
    return manifest


def _sys_platform(target):
    return "win32" if target.startswith("windows") else "darwin" if target.startswith("macos") else "linux"


def _architecture(target):
    return "arm64" if target.endswith("arm64") else "x86_64"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=sorted(TARGETS))
    parser.add_argument("--original-dir", type=Path, required=True)
    parser.add_argument("--snes-dir", type=Path, required=True)
    parser.add_argument("--sega-dir", type=Path, required=True)
    parser.add_argument("--pce-artifact", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--windows-runtime", type=Path)
    args = parser.parse_args(argv)
    try:
        lock = load_approved_lock()  # ALWAYS fails with current UNAPPROVED.
        inventory = json.loads(SOURCE_FILE.read_text("utf-8"))
        if not (ROOT / "docs/V3_LICENSE_COMPATIBILITY_APPROVED.md").is_file():
            raise ValueError("Independent reviewed copyright decision is missing")
        result = assemble_approved_inputs(
            lock=lock, inventory=inventory, target=args.target,
            original_dir=args.original_dir, snes_dir=args.snes_dir,
            sega_dir=args.sega_dir, pce_artifact=args.pce_artifact,
            output_dir=args.output_dir, windows_runtime=args.windows_runtime,
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as err:
        parser.exit(1, f"3.0 SOURCE-BUILT PRODUCTION INPUTS BLOCKED: {err}\n")
    print(f"{result['target']}: EXACT reviewed 11 native core archives and Dolphin Sys staged; NOT PUBLISHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
