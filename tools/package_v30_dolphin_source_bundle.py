"""Package all 37 exact Dolphin Gitlink source candidates plus pinned parent.

Only an **unapproved source-review bundle**. A tarball from a commit URL
does not prove correspondence with an older packaged Dolphin binary, license
compatibility, or complete compiler/build dependencies. Never set rights flags.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile

from tools.check_v30_dolphin_submodules import PINNED, validate_index
from tools.capture_v30_dolphin_nested_sources import (
    NESTED, validate_nested_map, STATUS as NESTED_STATUS,
)
from tools.reconcile_v30_dolphin_source_archives import reconcile, SOURCE_STATUS

PARENT_COMMIT = "32c61f9d0e933331bb7087ba57e96883241b4960"
REPORT = "DOLPHIN_37_GITLINK_SOURCE_BUNDLE_UNAPPROVED.json"
MANIFEST_34 = "DOLPHIN_34_SOURCE_ARCHIVE_REVIEW_UNAPPROVED.json"
MANIFEST_3 = "DOLPHIN_THREE_NESTED_SOURCE_CANDIDATES_UNAPPROVED.json"
SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_ARCHIVE = 512 * 1024 * 1024


def digest(path, *, cap=MAX_ARCHIVE):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Source file missing/unsafe: {path}")
    size = 0
    check = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            if size > cap:
                raise ValueError(f"Source file too large: {path}")
            check.update(chunk)
    if size == 0:
        raise ValueError(f"Empty source artifact: {path}")
    return check.hexdigest(), size


def json_file(path):
    checksum, size = digest(path, cap=5 * 1024 * 1024)
    result = json.loads(Path(path).read_text("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Source metadata must be a JSON object")
    return result, checksum


def checksum_lines(path, expected):
    if Path(path).is_symlink() or not Path(path).is_file():
        raise ValueError("Original nested checksums missing")
    actual = Path(path).read_text("ascii").splitlines()
    if len(actual) != len(expected) or sorted(actual) != sorted(
            f"{value}  {name}" for name, value in expected.items()):
        raise ValueError("Original nested SHA256SUMS mismatch")


def copy_verified(source, output, expected_sha, expected_bytes):
    value, size = digest(source)
    if (not isinstance(expected_sha, str) or not SHA.fullmatch(expected_sha)
            or expected_sha != value or size != expected_bytes):
        raise ValueError(f"Source bytes differ from immutable audit: {source}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        raise ValueError("Refusing to overwrite a source file")
    shutil.copyfile(source, output)
    if digest(output) != (expected_sha, expected_bytes):
        raise ValueError("Source bytes changed while preserving")
    return value, size


def validate_parent_archive(archive):
    """Pinned Dolphin source candidate only: does not verify buildbot provenance."""
    value, size = digest(archive)
    if size < 100_000:
        raise ValueError("Dolphin source archive implausibly small")
    prefix = f"dolphin-{PARENT_COMMIT}/"
    expected = {
        prefix + "CMakeLists.txt",
        prefix + ".gitmodules",
        prefix + "Source/Core/DolphinLibretro/CMakeLists.txt",
    }
    present = set()
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            # GitHub archives contain directory entries with a trailing slash.
            name = member.name.rstrip("/")
            if (name.startswith("/") or "\\" in name or
                    any(segment in ("", ".", "..") for segment in name.split("/"))):
                raise ValueError("Unsafe Dolphin source TAR entry")
            if name in expected:
                if not member.isfile() or member.issym() or member.islnk():
                    raise ValueError("Dolphin pinned source anchor not a regular file")
                present.add(name)
    if present != expected:
        raise ValueError("Dolphin original parent source anchors absent")
    return value, size


def collect(*, shards, nested, review, parent, output,
            direct_index=PINNED, nested_index=NESTED):
    """Rehash 34 direct and 3 nested, then stage 38 source TAR candidates.

    No original CI archive input is changed and no test-only emulator binary
    is deliberately included. All sources remain unapproved for public release.
    """
    shards, nested, review, parent, output = map(
        Path, (shards, nested, review, parent, output))
    if (not shards.is_dir() or shards.is_symlink() or
            not nested.is_dir() or nested.is_symlink() or
            output.is_symlink() or output.exists()):
        raise ValueError("Expected source folders and a NEW, safe bundle output")
    inputs = (shards, nested, review, parent)
    if any(output.resolve() == item.resolve() or
           item.resolve() in output.resolve().parents for item in inputs):
        raise ValueError("Source output cannot overwrite a source input")
    frozen, _ = json_file(direct_index)
    nested_lock, _ = json_file(nested_index)
    direct = validate_index(frozen)
    if frozen["parent_commit"] != PARENT_COMMIT or len(direct) != 34:
        raise ValueError("Dolphin exact source parent revision changed")
    old, old_digest = json_file(review)
    if old.get("status") != SOURCE_STATUS:
        raise ValueError("Original independent 34-source audit missing")
    # Actually read the 34 archives again, rather than trusting a JSON summary.
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix="dolphin-source-candidate-audit-") as temp:
        checked = reconcile(frozen, shards, Path(temp) / "fresh")
    if checked != old:
        raise ValueError("Direct source archives differ from original 34-source review")
    nested_rows = validate_nested_map(nested_lock, frozen, old)
    if sum(len(rows) for rows in nested_rows.values()) != 3:
        raise ValueError("Dolphin nested sources no longer match the pinned Gitlink graph")
    recent, recent_digest = json_file(nested / MANIFEST_3)
    if (recent.get("schema_version") != 1
            or recent.get("status") != NESTED_STATUS
            or recent.get("dolphin_parent_commit") != PARENT_COMMIT
            or recent.get("source_candidates_captured") != 3
            or recent.get("pinned_nested_gitlink_count") != 3
            or recent.get("pinned_nested_gitlink_tree_closure_verified") is not True
            or recent.get("original_34_source_review_manifest_sha256") != old_digest
            or not isinstance(recent.get("archives"), dict)
            or len(recent["archives"]) != 3):
        raise ValueError("Nested archive evidence does not match original source review")
    for field in (
            "complete_corresponding_source_verified",
            "source_to_dolphin_binary_verified",
            "transitive_build_deps_and_notices_reviewed",
            "independent_license_review_complete",
            "public_binary_distribution_approved"):
        if recent.get(field) is not False:
            raise ValueError(f"Nested source evidence falsely claims {field}")
    expected_nested = {
        f"{parent_path}/{entry['path']}": entry
        for parent_path, entries in nested_rows.items()
        for entry in entries.values()
    }
    if set(recent["archives"]) != set(expected_nested):
        raise ValueError("Nested source Gitlink set mismatch")
    nested_expected = {MANIFEST_3: recent_digest}
    for full, row in recent["archives"].items():
        pinned = expected_nested[full]
        if (row.get("source_repository") != pinned["source_repository"]
                or row.get("pinned_source_commit") != pinned["gitlink_commit"]
                or row.get("compiled_into_original_dolphin_binary_verified") is not False
                or row.get("source_rights_independently_reviewed") is not False):
            raise ValueError("Nested source evidence claims changed source or rights")
        name = row.get("archive_filename")
        if (not isinstance(name, str) or
                not re.fullmatch(r"dolphin-nested-\d\d-[0-9a-f]{40}\.tar\.gz", name)):
            raise ValueError("Unexpected nested immutable archive name")
        nested_expected[name] = row.get("archive_sha256")
    if ({p.name for p in nested.iterdir()} != set(nested_expected) | {"SHA256SUMS.txt"}):
        raise ValueError("Missing/extra nested original source assets")
    checksum_lines(nested / "SHA256SUMS.txt", nested_expected)

    parent_sha, parent_bytes = validate_parent_archive(parent)
    if parent.is_symlink():
        raise ValueError("Unsafe original Dolphin parent source TAR")
    record = {
        "schema_version": 1,
        "status": "UNAPPROVED-DOLPHIN-38-EXACT-SOURCE-CANDIDATES",
        "pinned_parent_commit": PARENT_COMMIT,
        "parent_source_repo": "https://github.com/libretro/dolphin",
        "parent_source_acquired_from_pinned_commit_url": True,
        "verified_direct_gitlink_count": 34,
        "verified_nested_gitlink_count": 3,
        "original_34_review_manifest_sha256": old_digest,
        "original_3_review_manifest_sha256": recent_digest,
        "source_candidate_count_including_parent": 38,
        "independent_binary_to_source_match_proven": False,
        "complete_corresponding_source_and_build_dependencies_verified": False,
        "license_combination_approved": False,
        "dolphin_sys_source_and_rights_verified": False,
        "public_binary_distribution_approved": False,
        "sources": {},
    }
    output.mkdir(parents=True)
    names = {}
    def add(key, source, output_name, sha, size, commit, repo):
        if key in record["sources"] or output_name in names:
            raise ValueError("Duplicate source provenance or archive destination")
        copy_verified(source, output / output_name, sha, size)
        names[output_name] = sha
        record["sources"][key] = {
            "filename": output_name, "sha256": sha, "size_bytes": size,
            "pinned_source_revision": commit, "source_repository": repo,
            "correspondence_to_packaged_dolphin_binary_proven": False,
            "license_review_complete": False,
        }
    add("dolphin", parent, f"dolphin-parent-{PARENT_COMMIT}.tar.gz",
        parent_sha, parent_bytes, PARENT_COMMIT, "https://github.com/libretro/dolphin")
    direct_names = sorted(direct)
    for index, path in enumerate(direct_names):
        entry = old["submodules"][path]
        filename = f"dolphin-submodule-{index:02d}-{direct[path]['sha']}.tar.gz"
        original_file = shards / f"shard-{index % 6}" / filename
        add(path, original_file, filename,
            entry["archive_sha256"], entry["archive_size_bytes"],
            direct[path]["sha"], direct[path]["url"])
    for full in sorted(expected_nested):
        row = recent["archives"][full]
        add(full, nested / row["archive_filename"], row["archive_filename"],
            row["archive_sha256"], row["archive_size_bytes"],
            row["pinned_source_commit"], row["source_repository"])
    if len(names) != 38 or len(record["sources"]) != 38:
        raise ValueError("Dolphin source inventory incomplete")
    manifest = output / REPORT
    manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", "utf-8")
    names[REPORT] = digest(manifest)[0]
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{checksum}  {name}\n" for name, checksum in sorted(names.items())),
        encoding="ascii")
    return record


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--shards", type=Path, required=True)
    p.add_argument("--nested", type=Path, required=True)
    p.add_argument("--review", type=Path, required=True)
    p.add_argument("--parent", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        record = collect(shards=a.shards, nested=a.nested, review=a.review,
                         parent=a.parent, output=a.output)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError,
            tarfile.TarError) as exc:
        p.exit(1, f"Dolphin source candidate bundle REFUSED: {exc}\n")
    print("Dolphin original parent + 37 source Gitlinks preserved. No binary "
          "correspondence, full dependency rights or public approval asserted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
