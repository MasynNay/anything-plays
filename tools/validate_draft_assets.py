"""Check all files in a private v2.0 draft release before any publication.

Expected artifacts: four platform installers, eight preserved native ZIPs,
and four core provenance manifests. This never approves redistribution.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from tools.core_release_lock import LOCK_PATH
from tools.stage_candidate_assets import INSTALLERS, sha256_file
from tools.verify_candidate_archives import verify_candidate_archives


def validate_draft_assets(directory, lock_path=LOCK_PATH):
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError("Draft assets directory missing")
    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    if lock.get("approved_for_binary_distribution") is True:
        raise ValueError("Not a candidate-only release lock")
    expected = set(INSTALLERS.values())
    for target, installer_name in INSTALLERS.items():
        manifest_name = f"CORE_PROVENANCE-{target}.json"
        expected.add(manifest_name)
        manifest = json.loads((directory / manifest_name).read_text(encoding="utf-8"))
        if not manifest["cores"] or len(manifest["cores"]) != 2:
            raise ValueError(f"Invalid core manifest for {target}")
        with TemporaryDirectory() as temp:
            work = Path(temp)
            for record in manifest["cores"]:
                archived_name = f"{target}-{record['file']}.zip"
                expected.add(archived_name)
                shutil.copyfile(directory / archived_name,
                                work / f"{record['file']}.zip")
            report = verify_candidate_archives(manifest, lock, work)
            if report["target"] != target:
                raise ValueError("Manifest/target mismatch")
        installer = directory / installer_name
        if not installer.is_file() or installer.stat().st_size < 100000:
            raise ValueError(f"Installer is missing or unexpectedly small: {installer_name}")
        with installer.open("rb") as handle:
            magic = handle.read(8)
        if installer.suffix == ".exe" and not magic.startswith(b"MZ"):
            raise ValueError(f"Invalid Windows EXE magic: {installer_name}")
        if installer.suffix == ".deb" and not magic.startswith(b"!<arch>\n"):
            raise ValueError(f"Invalid DEB archive magic: {installer_name}")
    actual = {p.name for p in directory.iterdir() if p.is_file()}
    if actual != expected:
        raise ValueError(f"Unexpected draft assets: missing={sorted(expected - actual)}, "
                         f"extra={sorted(actual - expected)}")

    lines = [f"{sha256_file(directory / name)}  {name}" for name in sorted(expected)]
    checksums = directory / "SHA256SUMS.txt"
    checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {
        "schema_version": 1,
        "candidate_draft": True,
        "redistribution_approved": False,
        "independent_source_to_binary_verification": False,
        "platforms": list(INSTALLERS),
        "asset_count": len(expected),
        "checksums": checksums.name,
    }
    (directory / "DRAFT_REVIEW_STATUS.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--lock", type=Path, default=LOCK_PATH)
    args = parser.parse_args()
    print(json.dumps(validate_draft_assets(args.directory, args.lock), indent=2))
    print("Unapproved draft reviewed for archive integrity ONLY")


if __name__ == "__main__":
    main()
