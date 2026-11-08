"""Create an isolated 18-profile, 11-core test-only PCE replacement input set.

The other ten original Libretro core ZIPs and Dolphin Sys are copied byte-for-
byte from a preserved, hashed offline lab. Only PCE Fast is substituted with
the independently verified new GPL source-built candidate. Nothing touches
the existing preview's preserved archives or the official 3.0 release lock.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

from fetch_mgba_core import CORE_NAMES, OPTIONAL_V21_CORES
from tools.v30_pce_candidate import inspect_artifact, load_index, TARGETS

ALL_CORES = frozenset((*CORE_NAMES, *OPTIONAL_V21_CORES))


def stage_inputs(original_dir, candidate, output, evidence, target):
    if (os.environ.get("AP_RELEASE_BUILD", "0") != "0"
            or os.environ.get("AP_V30_APPROVED_RELEASE") == "1"
            or os.environ.get("AP_V30_TEST_CORES") != "1"):
        raise ValueError("Source-built PCE trial only permits unapproved 3.0 preview mode")
    if len(ALL_CORES) != 11 or target not in TARGETS:
        raise ValueError("Unexpected console/core target inventory")
    original = Path(original_dir).expanduser()
    destination = Path(output).expanduser()
    evidence_path = Path(evidence).expanduser()
    if original.is_symlink() or destination.is_symlink() or evidence_path.is_symlink():
        raise ValueError("Original inputs or output path cannot be symlinks")
    if not original.is_dir() or destination.exists() or evidence_path.exists():
        raise ValueError("Use existing original folder and NEW output/evidence locations")
    if destination.resolve() == original.resolve() or original.resolve() in destination.resolve().parents:
        raise ValueError("Trial inputs cannot overwrite or nest in preserved source")
    if evidence_path.resolve() == destination.resolve() or destination.resolve() in evidence_path.resolve().parents:
        raise ValueError("Evidence must not contaminate local core archive input folder")

    idx = load_index()
    binary = inspect_artifact(candidate, target, idx)
    extension = TARGETS[target][0]
    expected = {f"{name}_libretro{extension}.zip" for name in ALL_CORES}
    expected.add("Dolphin.zip")
    record_file = original / "PRESERVED_NATIVE_INPUTS.json"
    if not record_file.is_file() or record_file.is_symlink():
        raise ValueError("Original build archive identity record missing")
    record = json.loads(record_file.read_text("utf-8"))
    if (record.get("target") != target
            or record.get("status") != "UNAPPROVED-TEST-INPUTS"
            or record.get("public_distribution_approved") is not False
            or record.get("original_archive_count") != 12):
        raise ValueError("Expected exact unapproved 12-archive native lab record")
    archive_rows = record.get("files")
    if not isinstance(archive_rows, list) or len(archive_rows) != 12:
        raise ValueError("Expected fingerprints for every original native input")
    if {x.get("name") for x in archive_rows if isinstance(x, dict)} != expected:
        raise ValueError("Archived 11-core and Dolphin Sys set is incomplete")
    if set(p.name for p in original.iterdir()) != expected | {"PRESERVED_NATIVE_INPUTS.json"}:
        raise ValueError("Extra/missing files in the preserved original source folder")
    snapshots = {}
    for row in archive_rows:
        name = row["name"]
        path = original / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Refusing symlinked or missing original core input: {name}")
        data = path.read_bytes()
        if (hashlib.sha256(data).hexdigest() != row.get("sha256")
                or len(data) != row.get("size_bytes")):
            raise ValueError(f"Original native ZIP has changed: {name}")
        snapshots[name] = data
    pce_name = "mednafen_pce_fast_libretro" + extension
    candidate_zip_name = pce_name + ".zip"
    with io.BytesIO() as buffer:
        with zipfile.ZipFile(buffer, "w") as archive:
            member = zipfile.ZipInfo(pce_name, (1980, 1, 1, 0, 0, 0))
            member.compress_type = zipfile.ZIP_STORED
            archive.writestr(member, binary)
        substitute = buffer.getvalue()
    result = {
        "schema_version": 1,
        "status": "SOURCE-BUILT-PCE-INTEGRATION-PREVIEW-ONLY-UNAPPROVED",
        "target": target,
        "profiles": 18,
        "cores": len(ALL_CORES),
        "original_source_run_id": record.get("source_revision"),
        "original_other_cores_and_dolphin_archive_count": 11,
        "substituted_core": pce_name,
        "substituted_archive": candidate_zip_name,
        "native_sha256": idx["targets"][target]["native_sha256"],
        "staged_archive_sha256": hashlib.sha256(substitute).hexdigest(),
        "pce_git_commit": idx["pinned_source_commit"],
        "pce_source_archive_sha256": idx["targets"][target]["source_archive_sha256"],
        "base_original_input_provenance_sha256": hashlib.sha256(record_file.read_bytes()).hexdigest(),
        "public_release_approved": False,
        "mixed_license_review_complete": False,
        "gamecube_and_all_other_original_core_archives_unchanged": True,
    }
    # No writes happen before complete original-input and candidate integrity validation.
    destination.mkdir(parents=True)
    for name, data in snapshots.items():
        (destination / name).write_bytes(substitute if name == candidate_zip_name else data)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-dir", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--target", required=True, choices=sorted(TARGETS))
    a = p.parse_args(argv)
    try:
        data = stage_inputs(a.original_dir, a.candidate, a.output, a.evidence, a.target)
    except (ValueError, OSError, TypeError, KeyError, zipfile.BadZipFile) as err:
        p.exit(1, f"3.0 PCE TRIAL BLOCKED: {err}\n")
    print(f"Prepared {data['cores']} exact original/trial cores for {a.target}: "
          f"new PCE {data['native_sha256']}; public release still BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
