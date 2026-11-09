"""Assemble immutable, source-authentic, reviewed 3.0 production native inputs.

Unlike the developer-only GPL trial stager, this module accepts ONLY a
separately approved, exact 44-core/four-platform source/license lock and its
corresponding-source inventory. It will not approve anything. It independently
verifies all original inputs and Dolphin Sys against the exact original
full-offline archive, then replaces the reviewed core families with original
pinned native builds. The ten-source variant retains ONLY original Dolphin.

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
    selected_source_families, SOURCE_BUILT_EIGHT, SOURCE_BUILT_TEN, SOURCE_BUILT_FIVE,
    verify_core_archive, verify_core_payload, verify_dolphin_archive,
)
from tools.emit_v30_production_provenance import SOURCE_FILE, validate_source_inventory
from tools.stage_v30_approved_native_mapping import (
    EXT, approved_core_map_from_lock,
)
from tools.stage_v30_gpl_trial_inputs import package_native_zip
from tools.probe_v30_gpl_core_switch import validate_original_source_artifact
from tools.v30_pce_candidate import inspect_artifact, load_index
from anything_plays.v30_approved_core_map import (
    REPOSITORIES, EXPECTED, EIGHT_REPOSITORIES, EIGHT_EXPECTED,
    TEN_REPOSITORIES, TEN_EXPECTED, WINDOWS_RUNTIME,
)
from tools.stage_v30_eight_source_inputs import check_original_five_artifact
from tools.stage_v30_nine_source_inputs import inspect_original_mgba
from tools.stage_v30_ten_source_inputs import check_original_n64_artifact

UNAPPROVED_ORIGINAL = "PRESERVED_NATIVE_INPUTS.json"
FIVE_FAMILY_SOURCE_RUN = 42515151314
UNCHANGED_3 = frozenset(("mgba", "parallel_n64", "dolphin"))
UNCHANGED_1 = frozenset(("dolphin",))
assert len(UNCHANGED_3) == 3 and len(UNCHANGED_1) == 1
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
                             windows_runtime=None, five_dirs=None,
                             mgba_dir=None, n64_dir=None):
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
    families = selected_source_families(lock)
    eight = families in (SOURCE_BUILT_EIGHT, SOURCE_BUILT_TEN)
    ten = families == SOURCE_BUILT_TEN
    if eight != (five_dirs is not None):
        raise ValueError("Eight/ten reviewed sources require EXACT original five-family artifact inputs")
    if eight and (not isinstance(five_dirs,dict) or set(five_dirs)!=SOURCE_BUILT_FIVE):
        raise ValueError("Exactly five additional pinned original source builds required")
    if ten != (mgba_dir is not None and n64_dir is not None):
        raise ValueError("Ten-source production requires BOTH separately captured original mGBA and N64 artifacts")
    if not ten and (mgba_dir is not None or n64_dir is not None):
        raise ValueError("Unreviewed mGBA or N64 research artifacts in older production variant")
    retained = UNCHANGED_1 if ten else UNCHANGED_3 if eight else UNCHANGED_8
    expected = TEN_EXPECTED if ten else EIGHT_EXPECTED if eight else EXPECTED
    repositories = TEN_REPOSITORIES if ten else EIGHT_REPOSITORIES if eight else REPOSITORIES
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
    # All 12 old archived inputs MUST remain verified, but only the actual
    # 3 retained originals (8 source builds) or 8 retained originals
    # (3 source builds) and Dolphin Sys may enter approved production.
    original = _original_inputs(original_dir, original_target, ext)
    payload = {
        f"{name}_libretro{ext}.zip": original[f"{name}_libretro{ext}.zip"]
        for name in retained
    }
    payload["Dolphin.zip"] = original["Dolphin.zip"]
    # Verifies exact immutable core ZIP (and Dolphin) identities from LOCK.
    for name in retained:
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
    if eight:
        for name,path in sorted(five_dirs.items()):
            # Exact original Git TAR and original compiled binary plus real
            # original tracked GPLv2 source notice, with A/V evidence. The
            # matching source from OLD historical buildbot ZIP is UNKNOWN.
            native, original_notice, original_record = check_original_five_artifact(
                path, name, original_target, ext)
            if original_notice is None:
                raise ValueError(f"Unverified original GPL source notice: {name}")
            native_zip = package_native_zip(name, ext, native)
            verify_core_archive(lock,_sys_platform(target),_architecture(target),name,native_zip)
            verify_core_payload(lock,_sys_platform(target),_architecture(target),
                                name,f"{name}_libretro{ext}",native)
            if sha(original_notice) != reviewed_map["cores"][name]["license_notice_sha256"]:
                raise ValueError(f"Unreviewed actual original upstream license: {name}")
            source_row=inventory["targets"][target]["cores"][name]
            if (source_row.get("source_archive_sha256") != original_record["source_archive_sha256"]
                    or source_row.get("source_commit_sha") != expected[name]
                    or source_row.get("source_repository") != repositories[name]
                    or source_row.get("native_sha256") != sha(native)
                    or original_record.get("original_license_notice_copied") is not True):
                raise ValueError(f"Original 5-family source/archive differs from independent reviewed inventory: {name}")
            payload[f"{name}_libretro{ext}.zip"] = native_zip
            payload[f"GPL-TRIAL-{name}-ORIGINAL-COPYING.txt"] = original_notice
            sources[name] = {
                "source_revision": expected[name],
                "source_archive_sha256": original_record["source_archive_sha256"],
                "native_sha256": sha(native),
                "original_native_archive_sha256": sha(native_zip),
                "original_license_sha256": sha(original_notice),
                "original_owned_actions_run_id": FIVE_FAMILY_SOURCE_RUN,
            }
    if ten:
        # Source-native identity is authenticated by the ORIGINAL four-platform
        # capture validators, including real original mGBA video/audio, the
        # exact immutable Git source TAR, and N64's eleven source-tree notices.
        for name, folder in (("mgba", mgba_dir), ("parallel_n64", n64_dir)):
            original_target = {
                "windows-x86_64": "windows-x64", "linux-x86_64": "linux-x64",
                "macos-arm64": "macos-arm64", "macos-x86_64": "macos-x64",
            }[target]
            if name == "mgba":
                native, notice, proof = inspect_original_mgba(folder, original_target)
                notice_map = {"MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt": notice}
                source_archive_sha = proof["source_archive_sha256"]
                original_notice_sha = sha(notice)
            else:
                native, notice_map, proof = check_original_n64_artifact(folder, original_target)
                source_archive_sha = proof["original_source_sha256"]
                # Deterministic named/hashed eleven-notice aggregate; one
                # digest in the immutable lock cannot omit a required notice.
                original_notice_sha = sha(json.dumps(
                    {file: sha(data) for file,data in sorted(notice_map.items())},
                    sort_keys=True, separators=(",", ":")).encode("utf-8"))
                if len(notice_map) != 11:
                    raise ValueError("N64 production missing original source notices")
            archive = package_native_zip(name, ext, native)
            verify_core_archive(lock, _sys_platform(target), _architecture(target), name, archive)
            verify_core_payload(lock, _sys_platform(target), _architecture(target),
                                name, f"{name}_libretro{ext}", native)
            if original_notice_sha != reviewed_map["cores"][name]["license_notice_sha256"]:
                raise ValueError(f"Ten-source core {name} original notice identity differs from reviewed lock")
            reviewed = inventory["targets"][target]["cores"][name]
            if (reviewed.get("source_archive_sha256") != source_archive_sha
                    or reviewed.get("source_commit_sha") != expected[name]
                    or reviewed.get("source_repository") != repositories[name]
                    or reviewed.get("native_sha256") != sha(native)
                    or proof.get("source_commit") != expected[name]
                    or proof.get("native_sha256") != sha(native)
                    or proof.get("source_repository") != repositories[name]):
                raise ValueError(f"Ten-source original {name} binary/source does not match independent review")
            payload[f"{name}_libretro{ext}.zip"] = archive
            payload.update(notice_map)
            sources[name] = {
                "source_revision": expected[name],
                "source_archive_sha256": source_archive_sha,
                "native_sha256": sha(native),
                "original_native_archive_sha256": sha(archive),
                "original_license_sha256": original_notice_sha,
                "original_owned_actions_run_id": proof["source_build_run_id"],
            }
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
        "unchanged_original_core_count": len(retained),
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
    parser.add_argument("--mgba-dir", type=Path)
    parser.add_argument("--n64-dir", type=Path)
    for name in sorted(SOURCE_BUILT_FIVE):
        parser.add_argument("--"+name.replace("_","-")+"-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        lock = load_approved_lock()  # ALWAYS fails with current UNAPPROVED.
        inventory = json.loads(SOURCE_FILE.read_text("utf-8"))
        if not (ROOT / "docs/V3_LICENSE_COMPATIBILITY_APPROVED.md").is_file():
            raise ValueError("Independent reviewed copyright decision is missing")
        families = selected_source_families(lock)
        wants_eight = families in (SOURCE_BUILT_EIGHT, SOURCE_BUILT_TEN)
        five={name: getattr(args,name+"_dir") for name in SOURCE_BUILT_FIVE}
        if wants_eight and any(path is None for path in five.values()):
            raise ValueError("Independent 8-family source lock requires all 5 original artifacts")
        if not wants_eight and any(path is not None for path in five.values()):
            raise ValueError("Original 3-family source lock must not consume 5-family unreviewed inputs")
        result = assemble_approved_inputs(
            lock=lock, inventory=inventory, target=args.target,
            original_dir=args.original_dir, snes_dir=args.snes_dir,
            sega_dir=args.sega_dir, pce_artifact=args.pce_artifact,
            output_dir=args.output_dir, windows_runtime=args.windows_runtime,
            five_dirs=five if wants_eight else None,
            mgba_dir=args["mgba_dir"], n64_dir=args["n64_dir"],
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as err:
        parser.exit(1, f"3.0 SOURCE-BUILT PRODUCTION INPUTS BLOCKED: {err}\n")
    print(f"{result['target']}: EXACT reviewed 11 native core archives and Dolphin Sys staged; NOT PUBLISHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
