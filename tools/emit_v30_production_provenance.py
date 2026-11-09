"""Emit exact approved 3.0 production installer artifacts for GitHub Releases.

This is not a legal approval tool. CI must independently pass the complete
release acceptance gate and human-reviewed GPL/noncommercial source records.
All native assets are checked against the *approved* 11-core immutable lock.
The output has exactly one installer and one production-provenance manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

from tools.collect_v30_production_assets import TARGETS
from tools.stage_v30_release_assets import expected_installers
from tools.v30_release_lock import TARGETS as NATIVE_TARGETS, load_approved_lock, selected_core_set, verify_native_bundle
from tools.check_v30_release import ACCEPTANCE_FILE, release_blockers
from tools.verify_v30_reviewed_runtime_code import verify_runtime_code_unchanged

ROOT = Path(__file__).resolve().parents[1]
LOCK_FILE = ROOT / "config/v3.0-core-lock.json"
SOURCE_FILE = ROOT / "config/v3.0-corresponding-source-inventory.json"
LICENSE_REVIEW_FILE = ROOT / "docs/V3_LICENSE_COMPATIBILITY_APPROVED.md"
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
NATIVE_MAP = {
    "windows-x64": "windows-x86_64",
    "linux-x64": "linux-x86_64",
    "macos-arm64": "macos-arm64",
    "macos-x64": "macos-x86_64",
}


def digest_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_source_inventory(lock, inventory):
    """Require full exact-platform source/archive identities before staging."""
    if (not isinstance(inventory, dict) or inventory.get("schema_version") != 1
            or inventory.get("approved_for_public_binary_distribution") is not True
            or inventory.get("corresponding_source_inventory_verified") is not True):
        raise ValueError("Missing approved 3.0 corresponding-source inventory")
    if inventory.get("native_core_count") != 11:
        raise ValueError("Source inventory does not cover eleven native cores")
    # A filename, Git commit and SHA-256 digest alone do NOT establish that
    # the source supplied is the code used to create an existing buildbot
    # binary. Require an explicitly reviewed binary-to-source decision for
    # the complete 44-binary set, in addition to per-core verified evidence.
    if inventory.get("independent_binary_to_source_match_proven") is not True:
        raise ValueError("Independent 11-core/four-platform source-to-binary audit missing")
    revision = lock.get("source_commit")
    if (not isinstance(revision, str) or not COMMIT.fullmatch(revision)
            or inventory.get("source_commit") != revision):
        raise ValueError("Corresponding-source inventory is not for the locked build commit")
    expected_cores = selected_core_set(lock)
    rows = inventory.get("targets")
    if not isinstance(rows, dict) or set(rows) != NATIVE_TARGETS:
        raise ValueError("Source inventory must cover all four target architectures")
    for target in NATIVE_TARGETS:
        cores = rows[target].get("cores") if isinstance(rows[target], dict) else None
        if not isinstance(cores, dict) or set(cores) != expected_cores:
            raise ValueError(f"Missing source inventory cores: {target}")
        approved = lock["targets"][target]["cores"]
        for name in expected_cores:
            evidence = cores[name]
            if not isinstance(evidence, dict):
                raise ValueError(f"Missing verified corresponding source: {target}/{name}")
            # Check BOTH native library bytes and the exact original
            # distributed Libretro ZIP identity. Archive-only evidence can
            # otherwise be combined with a different payload at release time.
            for field, expected in (
                ("source_commit_sha", approved[name]["source_commit_sha"]),
                ("native_sha256", approved[name]["native_sha256"]),
                ("original_native_archive_sha256", approved[name]["original_archive_sha256"]),
                ("source_repository", approved[name]["upstream_source_repository"]),
            ):
                if evidence.get(field) != expected:
                    raise ValueError(f"Source inventory does not match pinned core: {target}/{name}/{field}")
            if (not isinstance(evidence.get("source_archive_sha256"), str)
                    or not SHA256.fullmatch(evidence["source_archive_sha256"])):
                raise ValueError(f"Missing source archive hash: {target}/{name}")
            if (type(evidence.get("source_archive_size_bytes")) is not int
                    or evidence["source_archive_size_bytes"] <= 0):
                raise ValueError(f"Missing source archive size: {target}/{name}")
            # Critically, existing research manifests mark ALL THREE false.
            # A reviewer must examine binary/source equivalence and actual
            # redistribution restrictions, not just attest that an upstream
            # source archive exists. These are not set by CI automatically.
            for field in (
                "source_build_dependencies_reviewed",
                "source_to_binary_verified",
                "redistribution_license_reviewed",
            ):
                if evidence.get(field) is not True:
                    raise ValueError(f"Unapproved per-core source/rights field: {target}/{name}/{field}")
        sys_record = rows[target].get("dolphin_sys")
        sys_locked = lock["targets"][target]["dolphin_sys"]
        if (not isinstance(sys_record, dict)
                or sys_record.get("original_archive_sha256") != sys_locked["original_archive_sha256"]
                or sys_record.get("original_archive_size_bytes") != sys_locked["original_archive_size_bytes"]
                or sys_record.get("source_and_license_reviewed") is not True
                or sys_record.get("source_correspondence_verified") is not True
                or sys_record.get("redistribution_approved") is not True):
            raise ValueError(f"Unreviewed Dolphin system source/rights or archive mismatch: {target}")
    return True


def prepare_production_artifact(*, target, version, source_commit, installer,
                                bundle_manifest, lock, inventory, review_text,
                                output, lock_digest, source_digest):
    """Pure validation first; only create output once every input is approved."""
    names = dict(zip(TARGETS, expected_installers(version), strict=True))
    if target not in names or not COMMIT.fullmatch(source_commit):
        raise ValueError("Invalid 3.0 target or unpinned source revision")
    if not isinstance(review_text, str) or len(review_text) < 200 or "APPROVED-3.0-DISTRIBUTION" not in review_text:
        raise ValueError("Missing reviewed 3.0 redistribution decision")
    for name, value in (("native lock", lock_digest), ("source inventory", source_digest)):
        if not isinstance(value, str) or not SHA256.fullmatch(value):
            raise ValueError(f"Missing signed-off {name} digest")
    validate_source_inventory(lock, inventory)
    # An approval manifest cannot embed the SHA of its own Git commit:
    # changing that manifest changes the SHA (cryptographic self-reference).
    # Pin a BEFORE-approval application source commit, and verify that the
    # actual production checkout differs ONLY in exact approval files.
    # This is a real Git comparison, never a self-reported JSON boolean.
    reviewed_code_commit = lock["source_commit"]
    if source_commit != reviewed_code_commit:
        verify_runtime_code_unchanged(reviewed_code_commit, source_commit)
    installed = verify_native_bundle(lock, bundle_manifest)
    if installed != NATIVE_MAP[target]:
        raise ValueError("Installed native core bundle belongs to another target")
    input_file = Path(installer).expanduser()
    output_file = Path(output).expanduser()
    if input_file.is_symlink() or output_file.is_symlink():
        raise ValueError("Production input/output cannot be symlinks")
    input_file, output_file = input_file.resolve(), output_file.resolve()
    if not input_file.is_file() or input_file.name != names[target] or input_file.stat().st_size < 1024 * 1024:
        raise ValueError("Installer missing or not canonical reviewed 3.0 production file")
    if output_file.exists():
        if not output_file.is_dir() or any(output_file.iterdir()):
            raise ValueError("Production output directory must be new or empty")
    if output_file == input_file.parent or output_file in input_file.parents or input_file in output_file.parents:
        raise ValueError("Production artifact input/output directories must be distinct")
    installer_sha = digest_file(input_file)
    record = {
        "target": target,
        "source_revision": source_commit,
        "reviewed_application_source_commit": reviewed_code_commit,
        "runtime_build_inputs_unchanged_since_approved_source": True,
        "installer_name": names[target],
        "installer_sha256": installer_sha,
        "release_mode": "APPROVED-IMMUTABLE-PRODUCTION",
        "public_binary_distribution_approved": True,
        "profiles_bundled": 18,
        "native_cores_bundled": 11,
        "native_inputs_lock_sha256": lock_digest,
        "corresponding_source_inventory_sha256": source_digest,
        "license_review_record": "docs/V3_LICENSE_COMPATIBILITY_APPROVED.md",
    }
    # Never leave a plausible installer without its verified provenance, or
    # a partial provenance file, if copy, hashing or JSON writing fails.
    # Preflight above guarantees the directory is absent or empty.
    output_file.mkdir(parents=True, exist_ok=True)
    dest = output_file / input_file.name
    provenance = output_file / "PRODUCTION_PROVENANCE.json"
    completed = False
    try:
        shutil.copyfile(input_file, dest)
        if digest_file(dest) != installer_sha:
            raise RuntimeError("Staged production installer checksum changed")
        provenance.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        completed = True
    finally:
        if not completed:
            dest.unlink(missing_ok=True)
            provenance.unlink(missing_ok=True)
    return record


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", required=True, choices=TARGETS)
    p.add_argument("--version", default="3.0.0")
    p.add_argument("--source-commit", required=True)
    p.add_argument("--installer", required=True, type=Path)
    p.add_argument("--core-provenance", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        approval = json.loads(ACCEPTANCE_FILE.read_text(encoding="utf-8"))
        blockers = release_blockers(approval)
        if blockers:
            raise ValueError(f"Strict 3.0 acceptance failed: {len(blockers)} blockers")
        lock = load_approved_lock()
        source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
        review = LICENSE_REVIEW_FILE.read_text(encoding="utf-8")
        manifest = json.loads(args.core_provenance.read_text(encoding="utf-8"))
        record = prepare_production_artifact(
            target=args.target, version=args.version, source_commit=args.source_commit,
            installer=args.installer, bundle_manifest=manifest, lock=lock,
            inventory=source, review_text=review, output=args.output,
            lock_digest=digest_file(LOCK_FILE), source_digest=digest_file(SOURCE_FILE),
        )
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as err:
        p.exit(1, f"PRODUCTION ARTIFACT BLOCKED: {err}\n")
    print(f"Prepared reviewed {record['target']} immutable installer {record['installer_sha256']}; NOT PUBLISHED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
