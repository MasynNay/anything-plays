"""Independently audit the reported ParaLLEl-N64 revision and embedded notices.

The *actual* original source tree has a zero-byte .gitmodules and zero
Gitlink objects. Preserve its exact original source snapshot SHA, all
source-embedded license/notice blob SHAs and four existing native fingerprints,
without claiming source-to-binary correspondence or redistribution permission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
from urllib.request import Request, urlopen

from tools.v30_release_lock import TARGETS

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "config/v3.0-parallel-n64-source-notice-candidates.json"
STATUS = "UNAPPROVED-PARALLEL-N64-EXACT-ARCHIVE-NOTICE-REVIEW"
SOURCE_REVIEW_STATUS = "UNAPPROVED-SOURCE-REVIEW-CANDIDATE"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
NOTICE = re.compile(
    r"(?:COPYING(?:\.[A-Za-z0-9_-]+)?|LICENSES?|LICENSE\.[A-Za-z0-9_-]+"
    r"|NOTICE(?:\.[A-Za-z0-9_-]+)?)\Z", re.I
)


def _git_blob(content: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    ).hexdigest()


def _hash_file(path):
    h = hashlib.sha256()
    count = 0
    with Path(path).open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            h.update(chunk)
            count += len(chunk)
    return h.hexdigest(), count


def valid_index(index):
    if (not isinstance(index, dict) or index.get("schema_version") != 1
            or index.get("status") !=
            "UNAPPROVED-PARALLEL-N64-REPORTED-SOURCE-AND-EMBEDDED-NOTICE-CANDIDATES"
            or index.get("source_repository") != "https://github.com/libretro/parallel-n64"
            or not isinstance(index.get("reported_source_commit"), str)
            or not COMMIT.fullmatch(index["reported_source_commit"])
            or index.get("actual_source_tree_sha") != index["reported_source_commit"]
            or index.get("source_tree_entry_count") != 1970
            or index.get("gitmodules_blob_sha1") !=
            "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
            or index.get("gitmodules_size_bytes") != 0
            or index.get("gitlink_count") != 0
            or index.get("license_notice_file_count") != 11
            or not SHA256.fullmatch(str(index.get("archived_source_snapshot_sha256")))
            or index.get("archived_source_snapshot_size_bytes") != 6877459
            or index.get("original_source_capture_run_id") != 42441448884):
        raise ValueError("Pinned N64 source/notice map does not match audited revision")
    for flag in (
        "source_to_native_binary_independently_verified",
        "compiled_dependency_selection_reviewed", "notices_and_copyleft_reviewed",
        "in_process_mixed_license_compatibility_reviewed",
        "public_binary_redistribution_approved",
    ):
        if index.get(flag) is not False:
            raise ValueError(f"N64 rights/source approval was asserted without evidence: {flag}")
    notes = index.get("notices")
    if not isinstance(notes, list) or len(notes) != 11:
        raise ValueError("Original ParaLLEl-N64 notice candidates must be exactly 11")
    out = {}
    for entry in notes:
        if not isinstance(entry, dict) or entry.get("notice_reviewed") is not False:
            raise ValueError("Missing or already-approved embedded notice")
        path, git_sha, n = (
            entry.get("path"), entry.get("git_blob_sha1"),
            entry.get("size_bytes"),
        )
        if (not isinstance(path, str) or "\\" in path
                or PurePosixPath(path).is_absolute()
                or any(x in ("", ".", "..") for x in path.split("/"))
                or not NOTICE.fullmatch(PurePosixPath(path).name)
                or not isinstance(git_sha, str) or not COMMIT.fullmatch(git_sha)
                or type(n) is not int or not 0 < n < 512 * 1024
                or path in out):
            raise ValueError("Unsafe, duplicated or unpinned embedded N64 license")
        out[path] = entry
    cores = index.get("core_sha256_per_target")
    if (not isinstance(cores, dict) or set(cores) != TARGETS
            or not all(isinstance(v, str) and SHA256.fullmatch(v)
                       for v in cores.values())):
        raise ValueError("Original four-platform N64 native hashes incomplete")
    return out


def verify_tree(index, tree):
    expected = valid_index(index)
    if (not isinstance(tree, dict)
            or tree.get("sha") != index["reported_source_commit"]
            or tree.get("truncated") is not False
            or not isinstance(tree.get("tree"), list)
            or len(tree["tree"]) != index["source_tree_entry_count"]):
        raise ValueError("Pinned N64 upstream Git tree changed or is truncated")
    if any(not isinstance(row, dict) or row.get("type") == "commit"
           or row.get("mode") == "160000" for row in tree["tree"]):
        raise ValueError("Unexpected source Gitlinks; cannot claim zero submodules")
    modules = [x for x in tree["tree"] if x.get("path") == ".gitmodules"]
    if (len(modules) != 1 or modules[0].get("type") != "blob"
            or modules[0].get("size") != 0
            or modules[0].get("sha") != index["gitmodules_blob_sha1"]):
        raise ValueError("N64 source .gitmodules is not the empty Git blob")
    found = {
        x["path"]: x for x in tree["tree"]
        if x.get("type") == "blob"
        and NOTICE.fullmatch(PurePosixPath(x.get("path", "")).name)
    }
    if set(found) != set(expected):
        raise ValueError("Incomplete source-embedded licenses/notices")
    for path, item in expected.items():
        if (found[path].get("sha") != item["git_blob_sha1"]
                or found[path].get("size") != item["size_bytes"]):
            raise ValueError(f"Source notice is not the exact pinned Git blob: {path}")
    return expected


def verify_old_review(index, source_review):
    valid_index(index)
    if (not isinstance(source_review, dict)
            or source_review.get("status") != SOURCE_REVIEW_STATUS
            or source_review.get("approved_for_public_binary_distribution") is not False
            or source_review.get("independent_binary_to_source_match_proven") is not False
            or set(source_review.get("targets", {})) != TARGETS):
        raise ValueError("Missing complete original, unapproved four-target source review")
    for target in TARGETS:
        core = source_review["targets"][target]["cores"]["parallel_n64"]
        checks = {
            "native_sha256": index["core_sha256_per_target"][target],
            "source_repository": index["source_repository"],
            "source_commit_sha": index["reported_source_commit"],
            "source_archive_sha256": index["archived_source_snapshot_sha256"],
            "source_archive_size_bytes": index["archived_source_snapshot_size_bytes"],
            "source_to_binary_verified": False,
            "redistribution_license_reviewed": False,
            "source_build_dependencies_reviewed": False,
        }
        for name, value in checks.items():
            if core.get(name) != value:
                raise ValueError(f"{target}: original N64 candidate source/native field changed: {name}")
    return True


def audit_original_tar(index, source_tar):
    expected = valid_index(index)
    source_tar = Path(source_tar)
    if not source_tar.is_file() or source_tar.is_symlink():
        raise ValueError("Original archived GitHub source TAR is missing or unsafe")
    digest, size = _hash_file(source_tar)
    if (digest != index["archived_source_snapshot_sha256"]
            or size != index["archived_source_snapshot_size_bytes"]):
        raise ValueError("Original pinned N64 source TAR bytes do not match prior audit")
    collected = {}
    modules_found = False
    seen = set()
    with tarfile.open(source_tar, "r:gz") as archive:
        for member in archive:
            name = member.name.rstrip("/")
            path = PurePosixPath(name)
            if (path.is_absolute() or ".." in path.parts
                    or len(path.parts) == 0
                    or not path.parts[0].startswith("parallel-n64-")
                    or name in seen):
                raise ValueError("Unsafe/duplicate member in N64 archived source tree")
            seen.add(name)
            if not member.isfile():
                continue
            rel = "/".join(path.parts[1:])
            if rel not in expected and rel != ".gitmodules":
                continue
            if member.size > 512 * 1024:
                raise ValueError("Unexpectedly large N64 source notice")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Missing original N64 source notice bytes")
            data = stream.read(member.size + 1)
            if len(data) != member.size:
                raise ValueError("Truncated source notice in original N64 archive")
            if rel == ".gitmodules":
                if len(data) != 0 or _git_blob(data) != index["gitmodules_blob_sha1"]:
                    raise ValueError("Original N64 .gitmodules is not genuinely empty")
                modules_found = True
            else:
                item = expected[rel]
                if (len(data) != item["size_bytes"]
                        or _git_blob(data) != item["git_blob_sha1"]):
                    raise ValueError(f"Original archived source notice disagrees with pinned Git: {rel}")
                if rel in collected:
                    raise ValueError("Duplicate pinned notice")
                collected[rel] = {
                    "git_blob_sha1": _git_blob(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size_bytes": len(data),
                    "license_text_independently_reviewed": False,
                    "compiled_into_native_binary_independently_verified": False,
                }
    if not modules_found or set(collected) != set(expected):
        raise ValueError("Original N64 source TAR missing empty .gitmodules or eleven notices")
    return digest, size, collected


def audit(index, review, tree, source_tar):
    verify_tree(index, tree)
    verify_old_review(index, review)
    digest, size, notices = audit_original_tar(index, source_tar)
    return {
        "schema_version": 1,
        "status": STATUS,
        "reported_source_commit": index["reported_source_commit"],
        "source_repository": index["source_repository"],
        "original_4_architecture_native_sha256": index["core_sha256_per_target"],
        "source_archive_sha256": digest,
        "source_archive_size_bytes": size,
        "original_git_tree_members": 1970,
        "actual_gitlink_count": 0,
        "empty_gitmodules_verified": True,
        "embedded_source_notice_candidates": notices,
        "embedded_notice_count": len(notices),
        "source_to_native_binary_independently_verified": False,
        "compiled_notice_selection_independently_verified": False,
        "upstream_license_and_transitive_copyleft_reviewed": False,
        "in_process_gpl_noncommercial_license_decision_complete": False,
        "public_distribution_approved": False,
        "production_release_approved": False,
        "source_rom_bios_or_executable_in_evidence": False,
    }


def fetch_upstream_tree(commit):
    url = f"https://api.github.com/repos/libretro/parallel-n64/git/trees/{commit}?recursive=1"
    headers = {
        "User-Agent": "AnythingPlays/3.0-reproducible-N64-source-review",
        "Accept": "application/vnd.github+json",
    }
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=50) as source:
        payload = source.read(4 * 1024 * 1024 + 1)
    if len(payload) > 4 * 1024 * 1024:
        raise ValueError("Original N64 Git tree API response too large")
    return json.loads(payload)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=INDEX)
    parser.add_argument("--source-review", required=True, type=Path)
    parser.add_argument("--source-tar", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    a = parser.parse_args(argv)
    try:
        index = json.loads(a.index.read_text(encoding="utf-8"))
        old_review = json.loads(a.source_review.read_text(encoding="utf-8"))
        tree = fetch_upstream_tree(index["reported_source_commit"])
        report = audit(index, old_review, tree, a.source_tar)
        output = a.output
        if (output.is_symlink() or
                (output.exists() and (not output.is_dir() or any(output.iterdir())))):
            raise ValueError("N64 review destination must be new or empty")
        output.mkdir(parents=True, exist_ok=True)
        file = output / "PARALLEL_N64_PINNED_SOURCE_NOTICES_UNAPPROVED.json"
        file.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        (output / "SHA256SUMS.txt").write_bytes(
            f"{_hash_file(file)[0]}  {file.name}\n".encode("ascii"))
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError,
            json.JSONDecodeError) as error:
        parser.exit(1, f"PINNED PARALLEL N64 SOURCE AUDIT BLOCKED: {error}\n")
    print("Verified reported N64 source revision, exact 4-target native hash map, "
          "source TAR, 0 actual Gitlinks and 11 actual archived notice blobs; "
          "binary/source and GPL/noncommercial approvals remain FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
