"""Capture three nested immutable Dolphin Gitlink source candidates for review.

The original 34 Dolphin Gitlinks contain TWO upstream .gitmodules files:
Cubeb and libadrenotools. Their pinned Git trees point to three more
Gitlinks. This tool checks the exact original 34-archive review hashes,
independently verifies pinned parent and child Git trees plus .gitmodules,
and captures the three source archives without extracting or running them.

No corresponding-source equivalence, runtime dependency inclusion or
GPL/noncommercial redistribution right is inferred by this research.
"""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
from urllib.request import Request, urlopen

from tools.capture_v30_dolphin_submodule_sources import immutable_archive_url
from tools.capture_v30_source_snapshots import _copy_url_to_archive
from tools.check_v30_dolphin_submodules import PINNED, validate_index

ROOT = Path(__file__).resolve().parents[1]
NESTED = ROOT / "config/v3.0-dolphin-nested-submodule-candidates.json"
STATUS = "UNAPPROVED-DOLPHIN-THREE-NESTED-SOURCE-ARCHIVES"
INDEX_STATUS = "UNAPPROVED-DOLPHIN-THREE-NESTED-GITLINK-SOURCE-CANDIDATES"
REVIEW_STATUS = "UNAPPROVED-DOLPHIN-34-SOURCE-ARCHIVE-REVIEW"
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
REPO = re.compile(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
LICENSE = re.compile(r"(?:LICENSE|LICENCE|COPYING|NOTICE)(?:[._-].*)?\Z", re.I)
MAX_ARCHIVE = 128 * 1024 * 1024
MAX_METADATA = 4 * 1024 * 1024


def _normal_repo(url):
    if not isinstance(url, str):
        raise ValueError("Gitlink submodule URL must be text")
    name = url.rstrip("/").removesuffix(".git")
    if not REPO.fullmatch(name):
        raise ValueError(f"Unsupported nested source URL: {url!r}")
    return name


def _relative_path(name):
    if not isinstance(name, str) or not name or "\\" in name or not name.isascii():
        raise ValueError("Invalid nested submodule path")
    p = PurePosixPath(name)
    if p.is_absolute() or any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError("Unsafe nested submodule path")
    return name


def validate_nested_map(record, direct_index, parent_review):
    """Tie all three rows to the independently rehashed original 34 archives."""
    direct = validate_index(direct_index)
    if (not isinstance(record, dict) or record.get("schema_version") != 1
            or record.get("status") != INDEX_STATUS
            or record.get("dolphin_parent_commit") != direct_index["parent_commit"]
            or record.get("original_direct_gitlinks") != 34
            or record.get("original_nested_parent_sources") != 2
            or record.get("exact_nested_gitlinks") != 3
            or record.get("original_34_review_run") != "42447184893"
            or not isinstance(parent_review, dict)
            or parent_review.get("status") != REVIEW_STATUS
            or parent_review.get("pinned_dolphin_parent_commit") != direct_index["parent_commit"]
            or parent_review.get("captured_source_archive_count") != 34
            or set(parent_review.get("submodules", {})) != set(direct)):
        raise ValueError("Nested sources are not pinned to original 34-source audit")
    for field in ("approved_for_binary_distribution",
                  "complete_source_to_shipped_binary_verified",
                  "independent_combined_license_reviewed",
                  "transitive_build_dependency_correspondence_reviewed"):
        if record.get(field) is not False:
            raise ValueError("Nested candidates may not assert distribution approvals")
    parents = record.get("parents")
    if not isinstance(parents, list) or len(parents) != 2:
        raise ValueError("Expected exactly two parent source repositories with Gitlinks")
    nested_reported = {name for name, row in parent_review["submodules"].items()
                       if row.get("nested_gitmodules_reported")}
    actual = {}
    count = 0
    for parent in parents:
        if not isinstance(parent, dict):
            raise ValueError("Malformed nested parent source")
        key = parent.get("parent_path")
        if key not in direct or key in actual:
            raise ValueError("Missing or duplicated original Dolphin parent")
        root = direct[key]
        review = parent_review["submodules"][key]
        if (parent.get("parent_gitlink_commit") != root["sha"]
                or _normal_repo(parent.get("parent_source_repository")) != _normal_repo(root["url"])
                or parent.get("parent_source_archive_sha256") != review.get("archive_sha256")
                or parent.get("parent_source_archive_size_bytes") != review.get("archive_size_bytes")
                or not SHA256.fullmatch(str(parent.get("parent_source_archive_sha256")))
                or not isinstance(parent.get("nested"), list)
                or not parent["nested"]):
            raise ValueError("Nested candidate detached from original parent archive")
        rows = {}
        for item in parent["nested"]:
            if not isinstance(item, dict):
                raise ValueError("Malformed nested source entry")
            name = _relative_path(item.get("path"))
            if name in rows or name in actual:
                raise ValueError("Duplicate nested child source")
            commit = item.get("gitlink_commit")
            if not isinstance(commit, str) or not COMMIT.fullmatch(commit):
                raise ValueError("Nested Gitlink must be a full immutable commit")
            repo = _normal_repo(item.get("source_repository"))
            if _normal_repo(item.get("declared_source_url")) != repo:
                raise ValueError("Declared nested Gitmodule source changed")
            rows[name] = item
            count += 1
        actual[key] = rows
    if set(actual) != nested_reported or count != 3:
        raise ValueError("Original source indicates missing/extra nested Gitmodules")
    return actual


def _get_bytes(url, *, limit=MAX_METADATA):
    if not (url.startswith("https://api.github.com/repos/")
            or url.startswith("https://raw.githubusercontent.com/")):
        raise ValueError("Source verifier URL is not an approved GitHub endpoint")
    headers = {"User-Agent": "AnythingPlays/3.0-nested-source-review",
               "Accept": "application/vnd.github+json"}
    if url.startswith("https://api.github.com/") and os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=45) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Pinned Git tree or .gitmodules response too large")
    return data


def _github_repo(url):
    return _normal_repo(url).removeprefix("https://github.com/")


def _submodule_ini(content):
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.read_string(content)
    result = {}
    for section in parser.sections():
        if not re.fullmatch(r'submodule "[^"]+"', section):
            raise ValueError("Unexpected .gitmodules section")
        path = _relative_path(parser.get(section, "path"))
        url = parser.get(section, "url")
        if path in result:
            raise ValueError("Duplicate nested .gitmodules path")
        result[path] = _normal_repo(url)
    return result


def verify_upstream(record, indexed, *, tree_fetcher=None, modules_fetcher=None):
    """Recheck actual parent/child commit trees; no child may hide a Gitlink."""
    if tree_fetcher is None:
        tree_fetcher = lambda repo, commit: json.loads(_get_bytes(
            f"https://api.github.com/repos/{_github_repo(repo)}/git/trees/{commit}?recursive=1"))
    if modules_fetcher is None:
        modules_fetcher = lambda repo, commit: _get_bytes(
            f"https://raw.githubusercontent.com/{_github_repo(repo)}/{commit}/.gitmodules"
        ).decode("utf-8")
    checked = []
    for parent in record["parents"]:
        parent_path = parent["parent_path"]
        parent_sha = parent["parent_gitlink_commit"]
        repo = parent["parent_source_repository"]
        tree = tree_fetcher(repo, parent_sha)
        if (not isinstance(tree, dict) or tree.get("truncated") is not False
                or tree.get("sha") != parent_sha
                or not isinstance(tree.get("tree"), list)):
            raise ValueError(f"{parent_path}: wrong pinned parent Git tree")
        gitlinks = {x["path"]: x["sha"] for x in tree["tree"]
                    if x.get("type") == "commit" and x.get("mode") == "160000"}
        ini = _submodule_ini(modules_fetcher(repo, parent_sha))
        expected = indexed[parent_path]
        if set(gitlinks) != set(expected) or set(ini) != set(expected):
            raise ValueError(f"{parent_path}: missing/extra actual nested Gitlink")
        for name, child in expected.items():
            if (gitlinks[name] != child["gitlink_commit"]
                    or ini[name] != _normal_repo(child["declared_source_url"])):
                raise ValueError(f"{parent_path}/{name}: upstream Gitlink source changed")
            child_tree = tree_fetcher(child["source_repository"], child["gitlink_commit"])
            if (not isinstance(child_tree, dict)
                    or child_tree.get("truncated") is not False
                    or child_tree.get("sha") != child["gitlink_commit"]
                    or not isinstance(child_tree.get("tree"), list)):
                raise ValueError(f"{parent_path}/{name}: child Git tree is unverifiable")
            if any(x.get("type") == "commit" or x.get("mode") == "160000"
                   for x in child_tree["tree"]):
                raise ValueError(f"{parent_path}/{name}: another nested Gitlink needs capture")
            checked.append(f"{parent_path}/{name}")
    if len(checked) != 3:
        raise ValueError("Incomplete three-repository Gitlink closure")
    return sorted(checked)


def _license_candidates(archive):
    """Scan, never extract or execute, original source TAR for root notices."""
    notices = []
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            path = PurePosixPath(member.name)
            if (path.is_absolute() or ".." in path.parts):
                raise ValueError("Unsafe source member in original nested TAR")
            if len(path.parts) != 2 or not LICENSE.fullmatch(path.name):
                continue
            if member.size > 2 * 1024 * 1024:
                raise ValueError("Unusually large root license file")
            stream = tar.extractfile(member)
            if stream is None:
                raise ValueError("Missing license member bytes")
            contents = stream.read(member.size + 1)
            if len(contents) != member.size:
                raise ValueError("Truncated source notice")
            notices.append({"filename": path.name, "sha256": hashlib.sha256(contents).hexdigest(),
                            "size_bytes": len(contents)})
            if len(notices) > 20:
                raise ValueError("Unexpectedly many top-level license files")
    return sorted(notices, key=lambda row: row["filename"])


def capture_nested_sources(record, indexed, output, *, fetcher=_copy_url_to_archive,
                           tree_fetcher=None, modules_fetcher=None, review_sha256=None):
    """Fetch ONLY verified, immutable source TARs and preserve archive checksums."""
    verified = verify_upstream(record, indexed, tree_fetcher=tree_fetcher,
                               modules_fetcher=modules_fetcher)
    output = Path(output)
    if (output.is_symlink() or
            (output.exists() and (not output.is_dir() or any(output.iterdir())))):
        raise ValueError("Nested source output must be an empty non-symlink directory")
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "status": STATUS,
        "original_34_source_review_run": record["original_34_review_run"],
        "original_34_review_manifest_sha256": review_sha256,
        "dolphin_parent_commit": record["dolphin_parent_commit"],
        "source_candidates_captured": 0,
        "pinned_nested_gitlink_tree_closure_verified": True,
        "pinned_nested_gitlink_count": 3,
        "complete_corresponding_source_verified": False,
        "source_to_dolphin_binary_verified": False,
        "transitive_build_deps_and_notices_reviewed": False,
        "independent_license_review_complete": False,
        "public_binary_distribution_approved": False,
        "archives": {},
    }
    lines = []
    for i, full in enumerate(verified):
        parent_path, child_name = None, None
        for parent, rows in indexed.items():
            for nested, entry in rows.items():
                if f"{parent}/{nested}" == full:
                    parent_path, child_name = parent, nested
                    item = entry
                    break
        if parent_path is None:
            raise ValueError(f"Missing pinned nested source: {full}")
        archive_name = f"dolphin-nested-{i:02d}-{item['gitlink_commit']}.tar.gz"
        destination = output / archive_name
        details = fetcher(immutable_archive_url(item["source_repository"],
                                                  item["gitlink_commit"]),
                          destination, limit=MAX_ARCHIVE)
        if destination.is_symlink() or not destination.is_file():
            raise ValueError("Original nested source download did not create safe file")
        size = destination.stat().st_size
        if not 0 < size <= MAX_ARCHIVE:
            raise ValueError("Original nested source archive outside limit")
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if (not isinstance(details, dict) or details.get("sha256") != digest
                or details.get("size_bytes") != size):
            raise ValueError("Source archive changed after original pinned fetch")
        notices = _license_candidates(destination)
        report["archives"][full] = {
            "parent_gitlink_commit": next(p["parent_gitlink_commit"]
                                          for p in record["parents"]
                                          if p["parent_path"] == parent_path),
            "source_repository": item["source_repository"],
            "pinned_source_commit": item["gitlink_commit"],
            "archive_filename": archive_name,
            "archive_sha256": digest,
            "archive_size_bytes": size,
            "root_license_notice_candidates": notices,
            "compiled_into_original_dolphin_binary_verified": False,
            "source_rights_independently_reviewed": False,
        }
        lines.append(f"{digest}  {archive_name}")
        report["source_candidates_captured"] += 1
    if len(report["archives"]) != 3:
        raise ValueError("Not all nested source repositories captured")
    manifest = output / "DOLPHIN_THREE_NESTED_SOURCE_CANDIDATES_UNAPPROVED.json"
    manifest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    lines.append(f"{digest}  {manifest.name}")
    (output / "SHA256SUMS.txt").write_bytes(("\n".join(lines) + "\n").encode("ascii"))
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nested-index", type=Path, default=NESTED)
    p.add_argument("--direct-index", type=Path, default=PINNED)
    p.add_argument("--original-review", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        index = json.loads(a.nested_index.read_text("utf-8"))
        direct = json.loads(a.direct_index.read_text("utf-8"))
        original_bytes = a.original_review.read_bytes()
        old = json.loads(original_bytes)
        nested = validate_nested_map(index, direct, old)
        report = capture_nested_sources(index, nested, a.output,
                                        review_sha256=hashlib.sha256(original_bytes).hexdigest())
    except (OSError, ValueError, TypeError, KeyError, tarfile.TarError,
            configparser.Error, json.JSONDecodeError) as exc:
        p.exit(1, f"PINNED DOLPHIN NESTED SOURCE CAPTURE FAILED: {exc}\n")
    print(f"Captured {report['source_candidates_captured']}/3 nested pinned "
          "Dolphin source TARs; verified no further *Gitlinks* in these three "
          "upstream trees. Runtime build correspondence and licenses remain UNAPPROVED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
