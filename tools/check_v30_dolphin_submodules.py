"""Audit exact Dolphin submodule Gitlinks without claiming distribution rights.

GitHub's source tarballs omit content of Git submodules. The exact upstream
Dolphin revision exposes Gitlink *commit objects* for 34 dependencies. Keep
the identity map reviewable in Git; never fetch unpinned dependency branches,
resolve revisions by name, or mark binaries source-matched through this tool.
"""
from __future__ import annotations

import argparse
import configparser
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "config/v3.0-dolphin-submodule-candidates.json"
PARENT_COMMIT = "32c61f9d0e933331bb7087ba57e96883241b4960"
PARENT_REPOSITORY = "https://github.com/libretro/dolphin"
SHA = re.compile(r"[0-9a-f]{40}\Z")
HOST = re.compile(
    r"https://(?:github\.com|gitlab\.com)/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?\Z"
)


def _path(name):
    if (not isinstance(name, str) or not name.startswith("Externals/")
            or "\\" in name or not name.isascii()):
        raise ValueError(f"Unsafe submodule path: {name!r}")
    parsed = PurePosixPath(name)
    if any(p in ("", ".", "..") for p in name.split("/")) or parsed.is_absolute():
        raise ValueError(f"Unsafe submodule path: {name!r}")
    return parsed.as_posix()


def gitmodules(text):
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.read_string(text)
    result = {}
    for section in parser.sections():
        if not section.startswith('submodule "'):
            raise ValueError("Unexpected Git submodule config section")
        path, url = parser.get(section, "path"), parser.get(section, "url")
        key = _path(path)
        if key in result or not HOST.fullmatch(url):
            raise ValueError(f"Duplicate/unsupported Git submodule source: {key}")
        result[key] = url
    return result


def validate_index(record):
    if (not isinstance(record, dict)
            or record.get("schema_version") != 1
            or record.get("status") != "UNAPPROVED-PINNED-SUBMODULE-GITLINK-EVIDENCE"
            or record.get("parent_repository") != PARENT_REPOSITORY
            or record.get("parent_commit") != PARENT_COMMIT
            or not isinstance(record.get("parent_git_tree_sha"), str)
            or not SHA.fullmatch(record["parent_git_tree_sha"])):
        raise ValueError("Dolphin candidate parent identity invalid")
    fields = (
        "nested_source_dependencies_verified",
        "source_to_shipped_binary_correspondence_verified",
        "public_binary_redistribution_approved",
    )
    if any(record.get(field) is not False for field in fields):
        raise ValueError("Submodule index must not claim unreviewed approvals")
    rows = record.get("submodules")
    if (not isinstance(rows, list) or len(rows) != 34
            or type(record.get("submodule_count")) is not int
            or record["submodule_count"] != len(rows)):
        raise ValueError("Expected all 34 pinned Dolphin submodule Gitlinks")
    found = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed submodule candidate")
        name = _path(row.get("path"))
        if name in found:
            raise ValueError(f"Duplicate Dolphin dependency: {name}")
        commit, url = row.get("gitlink_commit"), row.get("source_repository")
        if (not isinstance(commit, str) or not SHA.fullmatch(commit)
                or not isinstance(url, str) or not HOST.fullmatch(url)
                or row.get("git_object_type") != "commit"):
            raise ValueError(f"Invalid pinned gitlink or URL: {name}")
        for approval in (
            "corresponding_binary_verified",
            "submodule_archive_captured",
            "license_reviewed",
        ):
            if row.get(approval) is not False:
                raise ValueError(f"Unverified gitlink cannot be declared cleared: {name}")
        found[name] = {"sha": commit, "url": url}
    return found


def verify_upstream(record, remote_tree, modules_text):
    local = validate_index(record)
    if (not isinstance(remote_tree, dict)
            or remote_tree.get("truncated") is True
            or remote_tree.get("sha") != record["parent_git_tree_sha"]
            or not isinstance(remote_tree.get("tree"), list)):
        raise ValueError("Unexpected upstream Dolphin Git tree identity")
    original = {}
    for entry in remote_tree["tree"]:
        if not isinstance(entry, dict) or entry.get("type") != "commit":
            continue
        name, sha = _path(entry.get("path")), entry.get("sha")
        if name in original or not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise ValueError("Duplicate or incomplete upstream Dolphin Gitlink")
        original[name] = sha
    urls = gitmodules(modules_text)
    if len(original) != 34 or set(original) != set(local) or set(urls) != set(local):
        raise ValueError("Frozen Dolphin gitlink set differs from upstream source")
    for path in original:
        if original[path] != local[path]["sha"] or urls[path] != local[path]["url"]:
            raise ValueError(f"Upstream Dolphin gitlink or URL mismatch: {path}")
    return len(original)


def fetch_text(url):
    request = Request(url, headers={"User-Agent": "AnythingPlays-3.0-source-audit"})
    with urlopen(request, timeout=35) as response:
        result = response.read(8 * 1024 * 1024 + 1)
    if len(result) > 8 * 1024 * 1024:
        raise ValueError("Upstream source audit response is unexpectedly large")
    return result.decode("utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=PINNED)
    parser.add_argument("--verify-upstream", action="store_true")
    args = parser.parse_args(argv)
    try:
        record = json.loads(args.index.read_text("utf-8"))
        count = len(validate_index(record))
        if args.verify_upstream:
            api = (f"https://api.github.com/repos/libretro/dolphin/git/trees/"
                   f"{PARENT_COMMIT}?recursive=1")
            modules = (f"https://raw.githubusercontent.com/libretro/dolphin/"
                       f"{PARENT_COMMIT}/.gitmodules")
            count = verify_upstream(record, json.loads(fetch_text(api)), fetch_text(modules))
    except (OSError, ValueError, TypeError, configparser.Error) as error:
        parser.exit(1, f"Dolphin source index rejected: {error}\n")
    print(f"Verified {count} immutable Dolphin gitlink identities; "
          "source archives, nested dependencies, binary correspondence "
          "and redistribution rights remain UNAPPROVED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
