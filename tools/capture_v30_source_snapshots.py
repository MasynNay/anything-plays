"""Preserve upstream source snapshots for 3.0, with missing evidence explicit.

Download only immutable Libretro Git commits identified by the actual preview
binary's self-reported revision. These source trees are TECHNICAL CANDIDATES:
their presence does not prove which compiler or patches created a buildbot
binary, nor does it license in-process redistribution of mixed-license cores.
The PC Engine binary reports no revision and remains an explicit gap.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tarfile
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fetch_mgba_core import CORE_NAMES, OPTIONAL_V21_CORES, SOURCE_REPOSITORIES

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/v3.0-preview-candidate-integrity.json"
NAMES = frozenset((*CORE_NAMES, *OPTIONAL_V21_CORES))
FULL_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024


def source_plan(records):
    """Validate the frozen source-identity claims before network access."""
    if not isinstance(records, list) or len(records) != 11:
        raise ValueError("Expected source identity evidence for all eleven cores")
    identity = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid core source evidence")
        name = record.get("name")
        if name not in NAMES or name in identity:
            raise ValueError("Unknown or duplicate native core identity")
        repository = record.get("source_repository")
        if repository != SOURCE_REPOSITORIES[name]:
            raise ValueError(f"{name}: upstream source repository mismatch")
        sha = record.get("reported_source_commit")
        if sha is not None and not (isinstance(sha, str) and FULL_COMMIT.fullmatch(sha)):
            raise ValueError(f"{name}: incomplete upstream Git commit")
        identity[name] = sha
    if set(identity) != NAMES:
        raise ValueError("Missing core source identities")
    if identity["mednafen_pce_fast"] is not None:
        # Re-evaluate only with independently supported evidence; never guess
        # a source commit for an unversioned binary.
        raise ValueError("PCE Fast unexpectedly has a commit; review source evidence")
    return {name: {
        "repository": SOURCE_REPOSITORIES[name],
        "reported_commit": identity[name],
        "source_to_binary_independently_verified": False,
        "redistribution_reviewed": False,
    } for name in sorted(NAMES)}


def _copy_url_to_archive(url, path, *, limit=MAX_ARCHIVE_BYTES):
    """Bounded streaming capture; validate as tar.gz; never extract source."""
    path.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={
        "User-Agent": "AnythingPlays/3.0-release-source-audit",
        "Accept": "application/octet-stream",
    })
    digest = hashlib.sha256()
    count = 0
    with tempfile.NamedTemporaryFile(
        prefix=".source-", suffix=".tar.gz", dir=path.parent, delete=False
    ) as temporary:
        staged = Path(temporary.name)
        try:
            with urlopen(request, timeout=90) as response:
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > limit:
                        raise ValueError("Upstream source archive exceeds download limit")
                    digest.update(chunk)
                    temporary.write(chunk)
            with tarfile.open(staged, "r:gz") as tree:
                members = tree.getmembers()
                if not members or any(member.name.startswith("/")
                                      or ".." in Path(member.name).parts
                                      for member in members):
                    raise ValueError("Unexpected unsafe upstream source archive")
                submodules = [
                    member.name for member in members
                    if member.name.endswith("/.gitmodules") or member.name == ".gitmodules"
                ]
            os.replace(staged, path)
        except BaseException:
            staged.unlink(missing_ok=True)
            raise
    return {"sha256": digest.hexdigest(), "size_bytes": count,
            "gitmodules_manifest_paths": submodules,
            "submodules_and_build_dependencies_independently_archived": False}


def capture_sources(evidence, output):
    """Store ten source snapshots and report the unresolved eleventh."""
    candidates = source_plan(evidence.get("linux_native_cores"))
    root = Path(output).expanduser()
    if root.is_symlink() or (root.exists() and any(root.iterdir())):
        raise ValueError("Source snapshot output must be an empty non-symlink directory")
    root.mkdir(parents=True, exist_ok=True)
    provenance = {
        "schema_version": 1,
        "status": "UNAPPROVED-UPSTREAM-SOURCE-SNAPSHOT-EVIDENCE",
        "approved_for_binary_distribution": False,
        "independent_binary_to_source_match_proven": False,
        "source_evidence_source": "config/v3.0-preview-candidate-integrity.json",
        "cores": {},
    }
    for name, record in candidates.items():
        entry = dict(record)
        sha = record["reported_commit"]
        if sha is None:
            entry["status"] = "NO_REPORTED_SOURCE_REVISION"
            provenance["cores"][name] = entry
            print(f"{name}: unresolved binary revision; no source guessed", flush=True)
            continue
        repo = record["repository"].removeprefix("https://github.com/")
        dest = root / f"source-{name}-{sha}.tar.gz"
        url = f"https://codeload.github.com/{repo}/tar.gz/{sha}"
        entry["source_download_url"] = url
        for attempt in range(3):
            try:
                entry.update(_copy_url_to_archive(url, dest))
                break
            except (OSError, HTTPError, URLError) as exc:
                if attempt == 2:
                    raise
                print(f"{name}: retrying source capture: {exc}", flush=True)
                time.sleep(2 * (attempt + 1))
        entry["archive_file"] = dest.name
        entry["status"] = "REPORTED-COMMIT-SNAPSHOT-CAPTURED-NOT-APPROVED"
        provenance["cores"][name] = entry
        print(f"{name}: saved pinned archive {entry['sha256']}", flush=True)
    (root / "SOURCE_SNAPSHOTS_UNAPPROVED.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        evidence = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = capture_sources(evidence, args.output)
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.exit(1, f"Source snapshot capture failed: {error}\n")
    captured = sum(bool(x.get("archive_file")) for x in result["cores"].values())
    print(f"Preserved {captured}/11 exact reported Git source snapshots; "
          "source-to-binary correspondence, submodules and redistribution remain unapproved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
