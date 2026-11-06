"""Verify exact, unapproved core ZIP candidates against the recorded lock.

This is a technical evidence check, NOT distribution approval. A matching
upstream-reported commit does not by itself prove build-to-source identity.
"""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from tools.core_release_lock import (
    CORE_NAMES, FINGERPRINT_FIELDS, LOCK_PATH, candidate_fingerprint,
)


def verify_candidate_archives(manifest, lock, archive_dir):
    """Require every candidate ZIP to contain the locked binary bytes."""
    archive_dir = Path(archive_dir)
    candidate = candidate_fingerprint(manifest)
    target = candidate["target"]
    expected_target = lock.get("targets", {}).get(target)
    if not isinstance(expected_target, dict) or set(expected_target) != set(CORE_NAMES):
        raise ValueError(f"No complete candidate lock for {target}")
    if lock.get("schema_version") != 1:
        raise ValueError("Unknown core lock schema")
    observed_records = {r["name"]: r for r in manifest["cores"]}
    verified = []
    for name in CORE_NAMES:
        expected = expected_target[name]
        actual = candidate["cores"][name]
        for field in FINGERPRINT_FIELDS:
            if actual.get(field) != expected.get(field):
                raise ValueError(f"Candidate core mismatch: {target}/{name}/{field}")
        revision = actual["reported_source_revision"]
        commit = expected.get("source_commit_sha")
        if not isinstance(commit, str) or len(commit) != 40 or not commit.startswith(revision):
            raise ValueError(f"Invalid source commit reference: {target}/{name}")
        filename = actual["file"]
        path = archive_dir / f"{filename}.zip"
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing regular core archive: {path}")
        archive_bytes = path.read_bytes()
        manifest_record = observed_records[name]
        if (hashlib.sha256(archive_bytes).hexdigest()
                != manifest_record.get("archive_sha256")
                or len(archive_bytes) != manifest_record.get("archive_size_bytes")):
            raise ValueError(f"Preserved ZIP differs from source archive: {name}")
        with zipfile.ZipFile(path) as archive:
            members = [item for item in archive.infolist()
                       if Path(item.filename).name == filename and not item.is_dir()]
            if len(members) != 1 or members[0].file_size > 60 * 1024 * 1024:
                raise ValueError(f"Bad candidate archive contents: {name}")
            payload = archive.read(members[0])
        if (hashlib.sha256(payload).hexdigest() != actual["sha256"]
                or len(payload) != actual["size_bytes"]):
            raise ValueError(f"Candidate core archive payload mismatch: {name}")
        verified.append({
            "name": name, "file": filename, "sha256": actual["sha256"],
            "archive_sha256": manifest_record["archive_sha256"],
            "source_commit_sha": commit,
        })
    return {
        "target": target,
        "redistribution_approved": False,
        "source_binary_correspondence_independently_verified": False,
        "cores": verified,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("archive_dir", type=Path)
    parser.add_argument("--lock", type=Path, default=LOCK_PATH)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    report = verify_candidate_archives(manifest, lock, args.archive_dir)
    print(json.dumps(report, indent=2))
    print("Candidate ZIP bytes verified (NOT approved for public distribution)")


if __name__ == "__main__":
    main()
