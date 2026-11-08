"""Safely collect four explicitly approved 3.0 production installers.

A passing developer-preview lab is NOT a release candidate: it uses mutable
upstream inputs and marks its payload TEST ONLY. This collector requires exact
production artifact directories with per-platform provenance. It never grants
redistribution rights; the separate strict release acceptance gate is required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

from tools.stage_v30_release_assets import expected_installers


TARGETS = ("windows-x64", "macos-arm64", "macos-x64", "linux-x64")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
MANIFEST = "PRODUCTION_PROVENANCE.json"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_production_assets(source_dir, destination, *, version, source_revision):
    """Validate every input, then copy exactly four approved files.

    Never treat checked-in flags or a manifest as sole legal authorization:
    callers must also pass the independent reviewed release acceptance gate.
    """
    filenames = dict(zip(TARGETS, expected_installers(version), strict=True))
    if not COMMIT_SHA.fullmatch(source_revision):
        raise ValueError("Expected a fully pinned 40-character source commit")
    origin = Path(source_dir).expanduser()
    output = Path(destination).expanduser()
    if origin.is_symlink() or output.is_symlink():
        raise ValueError("Candidate source/output must not be symlinks")
    origin, output = origin.resolve(), output.resolve()
    if not origin.is_dir():
        raise ValueError("Production candidate artifacts are missing")
    if origin == output or origin in output.parents or output in origin.parents:
        raise ValueError("Source and output directories must be separate")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Destination must be empty")

    if set(child.name for child in origin.iterdir()) != set(TARGETS):
        raise ValueError("Expected exactly four named production platform directories")

    approved = {}
    for target, filename in filenames.items():
        folder = origin / target
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError(f"{target}: expected real production artifact folder")
        if set(p.name for p in folder.iterdir()) != {filename, MANIFEST}:
            raise ValueError(f"{target}: unexpected or missing production artifact contents")
        installer = folder / filename
        record_file = folder / MANIFEST
        if any(p.is_symlink() or not p.is_file() for p in (installer, record_file)):
            raise ValueError(f"{target}: symlink/non-file in release candidate")
        if installer.stat().st_size < 1024 * 1024:
            raise ValueError(f"{target}: installer unexpectedly small")
        try:
            record = json.loads(record_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise ValueError(f"{target}: invalid provenance JSON") from exc
        expected = {
            "target": target,
            "source_revision": source_revision,
            "installer_name": filename,
            "release_mode": "APPROVED-IMMUTABLE-PRODUCTION",
            "public_binary_distribution_approved": True,
            "profiles_bundled": 18,
            "native_cores_bundled": 11,
        }
        for field, value in expected.items():
            if type(record.get(field)) is not type(value) or record.get(field) != value:
                raise ValueError(f"{target}: unapproved provenance field: {field}")
        for field in ("installer_sha256", "native_inputs_lock_sha256",
                      "corresponding_source_inventory_sha256"):
            if not isinstance(record.get(field), str) or not SHA256.fullmatch(record[field]):
                raise ValueError(f"{target}: missing pinned release evidence: {field}")
        if (not isinstance(record.get("license_review_record"), str)
                or not record["license_review_record"].startswith("docs/")):
            raise ValueError(f"{target}: missing linked license review")
        if record["installer_sha256"] != _hash_file(installer):
            raise ValueError(f"{target}: installer digest mismatch")
        approved[target] = installer

    output.mkdir(parents=True, exist_ok=True)
    for target, installer in approved.items():
        shutil.copyfile(installer, output / filenames[target])
        if _hash_file(output / filenames[target]) != _hash_file(installer):
            raise RuntimeError(f"{target}: staged installer checksum mismatch")
    return [filenames[target] for target in TARGETS]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="3.0.0")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        names = collect_production_assets(
            args.input, args.output, version=args.version,
            source_revision=args.source_commit,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"RELEASE ARTIFACTS REJECTED: {exc}\n")
    print("Validated exact approved production candidates (not yet published):")
    for name in names:
        print("  " + name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
