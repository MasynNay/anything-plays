"""Prepare release-candidate assets from verified local core archives.

Used only for a private, explicitly unapproved draft release. Never changes
the native ZIP bytes or authorizes publishing a final installer.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from tools.core_release_lock import LOCK_PATH
from tools.verify_candidate_archives import verify_candidate_archives

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


INSTALLERS = {
    "windows-x86_64": "AnythingPlaysSetup-2.0.0.exe",
    "macos-arm64": "AnythingPlays-2.0.0-macos-arm64.dmg",
    "macos-x86_64": "AnythingPlays-2.0.0-macos-x86_64.dmg",
    "linux-x86_64": "anything-plays_2.0.0_amd64.deb",
}


def stage_assets(target, installer, manifest_path, archive_dir, output, lock_path=LOCK_PATH):
    if target not in INSTALLERS:
        raise ValueError(f"Unsupported candidate target: {target}")
    installer, manifest_path, archive_dir, output = map(
        Path, (installer, manifest_path, archive_dir, output)
    )
    if installer.name != INSTALLERS[target] or not installer.is_file():
        raise ValueError(f"Unexpected or missing installer for {target}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    if lock.get("approved_for_binary_distribution") is True:
        raise ValueError("This candidate workflow is not the approved release pipeline")
    result = verify_candidate_archives(manifest, lock, archive_dir)
    if result["target"] != target:
        raise ValueError("Candidate platform/architecture mismatch")
    output.mkdir(parents=True, exist_ok=True)
    copied = []
    destination = output / installer.name
    shutil.copyfile(installer, destination)
    copied.append(destination)
    provenance_file = output / f"CORE_PROVENANCE-{target}.json"
    shutil.copyfile(manifest_path, provenance_file)
    copied.append(provenance_file)
    for record in manifest["cores"]:
        source = archive_dir / f"{record['file']}.zip"
        destination = output / f"{target}-{record['file']}.zip"
        shutil.copyfile(source, destination)
        copied.append(destination)
    for path in copied:
        print(f"Candidate draft asset: {path.name} "
              f"{path.stat().st_size} bytes "
              f"sha256={sha256_file(path)}")
    return copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=tuple(INSTALLERS))
    parser.add_argument("installer", type=Path)
    parser.add_argument("--manifest", type=Path,
                        default=Path("cores/CORE_PROVENANCE.json"))
    parser.add_argument("--archive-dir", type=Path, default=Path("release-inputs"))
    parser.add_argument("--output", type=Path, default=Path("candidate-assets"))
    args = parser.parse_args()
    stage_assets(args.target, args.installer, args.manifest,
                 args.archive_dir, args.output)


if __name__ == "__main__":
    main()
