"""Restore a frozen candidate's exact Libretro archives before any core is loaded.

Inputs come from an earlier private candidate, not mutable buildbot URLs.
Cryptographic verification uses the still-unapproved fingerprint lock.
"""

import argparse
import json
from pathlib import Path
import shutil

from tools.core_release_lock import LOCK_PATH
from tools.verify_candidate_archives import verify_candidate_archives


def prepare_candidate_inputs(target, source_dir, archive_dir, lock_path=LOCK_PATH):
    source_dir = Path(source_dir).resolve(strict=True)
    archive_dir = Path(archive_dir).resolve()
    manifest_path = source_dir / f"CORE_PROVENANCE-{target}.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError(f"Missing regular source manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(manifest.get("cores", [])) != 2:
        raise ValueError("Expected exactly two candidate cores")
    if archive_dir == source_dir:
        raise ValueError("Input and staging directories must differ")
    archive_dir.mkdir(parents=True, exist_ok=True)
    for record in manifest["cores"]:
        source = source_dir / f"{target}-{record['file']}.zip"
        destination = archive_dir / f"{record['file']}.zip"
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"Missing regular preserved core ZIP: {source}")
        if destination.is_symlink():
            raise ValueError(f"Refusing symlinked staged ZIP: {destination}")
        shutil.copyfile(source, destination)
    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    result = verify_candidate_archives(manifest, lock, archive_dir)
    if result["target"] != target:
        raise ValueError(f"Core manifest belongs to {result['target']}, expected {target}")
    print(f"Verified two immutable Libretro candidate inputs for {target}; "
          "neither approved for public distribution nor sourced from mutable nightlies")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target")
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("archive_dir", type=Path)
    parser.add_argument("--lock", type=Path, default=LOCK_PATH)
    args = parser.parse_args()
    prepare_candidate_inputs(args.target, args.source_dir, args.archive_dir, args.lock)


if __name__ == "__main__":
    main()
