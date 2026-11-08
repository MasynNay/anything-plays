"""Capture immutable Dolphin submodule source *candidates*, never release rights.

GitHub's top-level source archive omits Gitlink contents. This tool preserves
the exact Git commits in the previously verified 34-entry source map, split
across bounded CI shards. It never extracts untrusted tarballs, builds cores,
changes the shipped Dolphin binary, or claims corresponding-source compliance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError

from tools.capture_v30_source_snapshots import _copy_url_to_archive
from tools.check_v30_dolphin_submodules import PINNED, validate_index

MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
STATUS = "UNAPPROVED-DOLPHIN-PINNED-SUBMODULE-SOURCE-CANDIDATES"


def immutable_archive_url(repository: str, revision: str) -> str:
    """Only allow the two previously audited Git-host archive endpoints."""
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Dolphin submodule revision must be a full Git SHA")
    if repository.startswith("https://github.com/"):
        name = repository.removeprefix("https://github.com/").removesuffix(".git")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
            raise ValueError("Unsupported GitHub source repository")
        return f"https://codeload.github.com/{name}/tar.gz/{revision}"
    if repository.startswith("https://gitlab.com/"):
        name = repository.removeprefix("https://gitlab.com/").removesuffix(".git")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
            raise ValueError("Unsupported GitLab source repository")
        project = name.rsplit("/", 1)[1]
        return f"https://gitlab.com/{name}/-/archive/{revision}/{project}-{revision}.tar.gz"
    raise ValueError("Unsupported Dolphin source host")


def capture_shard(index_record: dict, output: Path, *, shard_index: int,
                  shard_count: int, fetcher=_copy_url_to_archive,
                  retry_sleep=time.sleep) -> dict:
    """Capture one deterministic shard of the exact validated upstream map.

    Metadata is explicitly unapproved, regardless of how many archives exist.
    A reported URL and a downloaded tarball do not independently demonstrate
    which source, patches, and build dependencies produced any shipped binary.
    """
    if (type(shard_index) is not int or type(shard_count) is not int
            or not 1 <= shard_count <= 34 or not 0 <= shard_index < shard_count):
        raise ValueError("Invalid Dolphin source capture shard")
    frozen = validate_index(index_record)
    output = Path(output)
    if output.is_symlink() or (output.exists() and
                              (not output.is_dir() or any(output.iterdir()))):
        raise ValueError("Dolphin source output must be an empty non-symlink directory")
    paths = sorted(frozen)
    chosen = [(i, path) for i, path in enumerate(paths)
              if i % shard_count == shard_index]
    if not chosen:
        raise ValueError("Dolphin source shard cannot be empty")
    output.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": 1,
        "status": STATUS,
        "parent_commit": index_record["parent_commit"],
        "pinned_index_path": "config/v3.0-dolphin-submodule-candidates.json",
        "shard_index": shard_index,
        "shard_count": shard_count,
        "total_pinned_gitlinks": 34,
        "expected_archive_count_this_shard": len(chosen),
        "complete_shard": False,
        "approved_for_binary_distribution": False,
        "source_to_shipped_binary_correspondence_verified": False,
        "complete_corresponding_source_and_build_dependencies_verified": False,
        "independent_license_review_complete": False,
        "submodules": {},
    }
    checksum_lines = []
    for number, path in chosen:
        item = frozen[path]
        url = immutable_archive_url(item["url"], item["sha"])
        filename = f"dolphin-submodule-{number:02d}-{item['sha']}.tar.gz"
        destination = output / filename
        details = None
        for attempt in range(3):
            try:
                details = fetcher(url, destination, limit=MAX_ARCHIVE_BYTES)
                break
            except (OSError, HTTPError, URLError) as error:
                if attempt == 2:
                    raise
                print(f"{path}: retrying pinned source archive ({error})", flush=True)
                retry_sleep(2 * (attempt + 1))
        if not destination.is_file() or destination.is_symlink():
            raise ValueError(f"{path}: source archive not created as a regular file")
        digest = hashlib.sha256()
        size = 0
        with destination.open("rb") as reader:
            for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                size += len(chunk)
                if size > MAX_ARCHIVE_BYTES:
                    raise ValueError(f"{path}: source archive over size limit")
                digest.update(chunk)
        if (not isinstance(details, dict) or size == 0
                or details.get("sha256") != digest.hexdigest()
                or details.get("size_bytes") != size):
            raise ValueError(f"{path}: downloaded archive hash/size mismatch")
        record["submodules"][path] = {
            "source_repository": item["url"],
            "pinned_gitlink_commit": item["sha"],
            "archive_url": url,
            "archive_file": filename,
            "archive_sha256": digest.hexdigest(),
            "archive_size_bytes": size,
            "nested_gitmodules_in_archive": details.get("gitmodules_manifest_paths", []),
            "source_archive_captured": True,
            "corresponding_shipped_binary_verified": False,
            "recursive_dependencies_verified": False,
            "license_reviewed": False,
        }
        checksum_lines.append(f"{digest.hexdigest()}  {filename}")
        print(f"{path}: captured exact-revision source candidate {digest.hexdigest()}", flush=True)
    record["complete_shard"] = True
    manifest = output / "DOLPHIN_SUBMODULE_SOURCE_CANDIDATES_UNAPPROVED.json"
    manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    checksum_lines.append(f"{manifest_digest}  {manifest.name}")
    (output / "SHA256SUMS.txt").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=PINNED)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, default=6)
    args = parser.parse_args(argv)
    try:
        original = json.loads(args.index.read_text("utf-8"))
        result = capture_shard(original, args.output, shard_index=args.shard_index,
                               shard_count=args.shard_count)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        parser.exit(1, f"Pinned Dolphin source capture failed: {error}\n")
    print(f"Captured {len(result['submodules'])} original Dolphin Gitlink archive candidates "
          f"(shard {args.shard_index + 1}/{args.shard_count}); ALL rights/source-to-binary "
          "release approvals remain FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
