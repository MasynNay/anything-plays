"""Preserve all 11 original pinned emulator source trees for future 3.0 recipients.

No binaries/ROMs, no assertion of source-to-binary equivalence, license
compatibility or public 3.0 distribution rights. Source-only research archive.
Git checkout pinning, recursively initialized submodules, and source tar SHA256
are independently recorded for every core.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time

from anything_plays.v30_approved_core_map import ELEVEN_EXPECTED, ELEVEN_REPOSITORIES

SOURCE_SHA = re.compile(r"[0-9a-f]{40}\Z")
MAX_ARCHIVE = 1024 * 1024 * 1024


def run_git(*args, cwd=None, timeout=1200):
    return subprocess.check_output(
        ["git", *map(str, args)], cwd=cwd, text=True,
        stderr=subprocess.STDOUT, timeout=timeout,
    ).rstrip("\r\n")


def checkout_pinned_source(root: Path, name: str, repo: str, revision: str) -> None:
    if root.exists() or root.is_symlink():
        raise ValueError("Original source checkout destination must not exist")
    root.parent.mkdir(parents=True, exist_ok=True)
    run_git("init", "-q", root)
    run_git("remote", "add", "origin", repo, cwd=root)
    # Transient GitHub network failures are retried; source SHA never changes.
    for attempt in range(1, 5):
        try:
            run_git("fetch", "--depth=1", "--no-tags", "origin", revision,
                    cwd=root, timeout=600)
            break
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if attempt == 4:
                raise
            time.sleep(3 * attempt)
    run_git("checkout", "--detach", "--quiet", "FETCH_HEAD", cwd=root)
    run_git("submodule", "sync", "--recursive", cwd=root)
    for attempt in range(1, 5):
        try:
            run_git("-c", "advice.detachedHead=false", "submodule", "update",
                    "--init", "--recursive", "--jobs", "4", cwd=root, timeout=1800)
            break
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if attempt == 4:
                raise
            time.sleep(5 * attempt)
    verify_checkout(root, name, repo, revision)


def verify_checkout(root: Path, name: str, repo: str, revision: str) -> int:
    if (name not in ELEVEN_EXPECTED or repo != ELEVEN_REPOSITORIES[name]
            or revision != ELEVEN_EXPECTED[name]
            or not SOURCE_SHA.fullmatch(revision)):
        raise ValueError("Unrecognized original source repository or Git revision")
    if (run_git("rev-parse", "HEAD", cwd=root) != revision
            or run_git("remote", "get-url", "origin", cwd=root) != repo
            or run_git("status", "--porcelain", "--untracked-files=all", cwd=root)):
        raise ValueError(f"Original Git checkout is incomplete or modified: {name}")
    submods = run_git("submodule", "status", "--recursive", cwd=root).splitlines()
    if any(not line.startswith(" ") for line in submods):
        raise ValueError(f"Incomplete nested pinned Gitlink checkout: {name}")
    if name == "dolphin":
        from tools.verify_v30_dolphin_original_build import verify_original_source
        evidence = verify_original_source(root)
        if (evidence["direct_gitlinks_verified"] != 34
                or evidence["nested_gitlinks_verified"] != 3
                or len(submods) != 37):
            raise ValueError("Dolphin original 34 + 3 Gitlink source is incomplete")
    return len(submods)


def iter_source_files(root: Path):
    """A tar of Git content, including nested submodules, never Git credentials."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Missing or symlinked original source checkout")
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        if path.is_dir() and not path.is_symlink():
            continue
        if path.is_symlink():
            # Preserve only symlinks resolving inside the original source.
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError(f"External source symlink prohibited: {relative}")
        elif not path.is_file():
            raise ValueError(f"Unsupported source filesystem entry: {relative}")
        yield path, relative


def archive_checkout(root: Path, target: Path, name: str, revision: str):
    if target.exists() or target.is_symlink():
        raise ValueError("Immutable source TAR destination already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    prefix = f"{name}-source-{revision}"
    count = 0
    try:
        with target.open("wb") as stream:
            with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as gz:
                with tarfile.open(mode="w", fileobj=gz) as archive:
                    for source, relative in iter_source_files(root):
                        info = tarfile.TarInfo(f"{prefix}/{relative.as_posix()}")
                        stat = source.lstat()
                        info.mtime = 0
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        info.mode = 0o755 if stat.st_mode & 0o111 else 0o644
                        if source.is_symlink():
                            info.type = tarfile.SYMTYPE
                            info.linkname = os.readlink(source)
                            archive.addfile(info)
                        else:
                            info.size = stat.st_size
                            with source.open("rb") as handle:
                                archive.addfile(info, handle)
                        count += 1
        if count < 5 or not 200 < target.stat().st_size < MAX_ARCHIVE:
            raise ValueError(f"Source archive missing substantial original content: {name}")
        digest = hashlib.sha256()
        with target.open("rb") as stream:
            for part in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(part)
        return {"archive_file": target.name, "sha256": digest.hexdigest(),
                "size_bytes": target.stat().st_size, "source_files": count}
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def archive_all(checkouts: Path, output: Path, *, verify_git=True):
    if output.exists() or output.is_symlink():
        raise ValueError("Original source archive output must be new")
    if checkouts.resolve() == output.resolve() or checkouts.resolve() in output.resolve().parents:
        raise ValueError("Cannot overwrite source checkouts")
    output.mkdir(parents=True)
    entries = {}
    for name in sorted(ELEVEN_EXPECTED):
        revision = ELEVEN_EXPECTED[name]
        repository = ELEVEN_REPOSITORIES[name]
        root = checkouts / name
        count = verify_checkout(root, name, repository, revision) if verify_git else None
        archive = archive_checkout(
            root, output / f"source-{name}-{revision}.tar.gz", name, revision)
        entries[name] = {
            "source_repository": repository, "source_commit": revision,
            "nested_gitlink_source_count": count, **archive,
        }
    manifest = {
        "schema_version": 1,
        "status": "UNAPPROVED-ORIGINAL-SOURCE-TREE-ACCESS-CANDIDATE",
        "newly_compiled_libretro_core_outputs_included": False,
        "core_count": 11,
        "all_source_revisions_pinned": True,
        "source_to_bundled_binary_review_complete": False,
        "transitive_build_dependencies_review_complete": False,
        "combined_gpl_distribution_reviewed": False,
        "public_binary_distribution_approved": False,
        "sources": entries,
    }
    (output / "SOURCE_ACCESS_CANDIDATE_UNAPPROVED.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", "utf-8")
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{row['sha256']}  {row['archive_file']}\n"
                for row in entries.values()), "ascii")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    if args.fetch:
        args.workspace.mkdir(parents=True, exist_ok=True)
        for name in sorted(ELEVEN_EXPECTED):
            checkout_pinned_source(args.workspace / name, name,
                                   ELEVEN_REPOSITORIES[name], ELEVEN_EXPECTED[name])
    result = archive_all(args.workspace, args.output)
    print(f"Archived {len(result['sources'])} original source trees, source-only, rights NOT auto-approved.")


if __name__ == "__main__":
    main()
