"""Build-time candidate fingerprints and fail-closed release core verification.

The release lock is an approval control, not proof of legal redistribution
rights or independent binary-to-source reproducibility.
"""

import argparse
import json
from pathlib import Path
import re

CORE_NAMES = ("mgba", "snes9x")
FINGERPRINT_FIELDS = (
    "sha256", "size_bytes", "file", "source_url",
    "libretro_library_version", "reported_source_revision",
    "source_repository_url",
)
LOCK_PATH = Path(__file__).resolve().parents[1] / "config" / "v2.0-core-lock.json"


def release_target(platform_name, architecture):
    """Return one of the four supported v2.0 binary release target IDs."""
    arch = architecture.lower()
    if platform_name == "win32" and arch in ("amd64", "x86_64"):
        return "windows-x86_64"
    if platform_name == "darwin" and arch in ("arm64", "aarch64"):
        return "macos-arm64"
    if platform_name == "darwin" and arch in ("x86_64", "amd64"):
        return "macos-x86_64"
    if platform_name.startswith("linux") and arch in ("x86_64", "amd64"):
        return "linux-x86_64"
    raise ValueError(f"Unsupported v2.0 release target: {platform_name}/{architecture}")


def candidate_fingerprint(manifest):
    """Produce a candidate record; never mark it as approved automatically."""
    target = release_target(manifest["build_platform"], manifest["build_architecture"])
    entries = manifest.get("cores")
    if not isinstance(entries, list) or len(entries) != len(CORE_NAMES):
        raise ValueError("Candidate manifest must contain exactly two cores")
    cores = {}
    for record in entries:
        name = record.get("name")
        if name not in CORE_NAMES or name in cores:
            raise ValueError(f"Unexpected or duplicate emulator core: {name}")
        for field in FINGERPRINT_FIELDS:
            if field not in record:
                raise ValueError(f"Missing core identity field: {name}.{field}")
        cores[name] = {field: record[field] for field in FINGERPRINT_FIELDS}
    return {"target": target, "cores": cores}


def verify_release_lock(manifest, lock):
    """Fail if the requested binary release is unapproved or any core changed.

    The lock contains immutable expected hashes and verified *source commit
    identities*, but the build inputs still need an independent source audit.
    """
    if lock.get("schema_version") != 1:
        raise ValueError("Invalid or missing core release lock schema")
    if lock.get("approved_for_binary_distribution") is not True:
        raise ValueError("Binary distribution is not approved in the core lock")
    candidate = candidate_fingerprint(manifest)
    target = candidate["target"]
    expected_targets = lock.get("targets")
    if not isinstance(expected_targets, dict) or target not in expected_targets:
        raise ValueError(f"No approved release core fingerprints for {target}")
    expected = expected_targets[target]
    if not isinstance(expected, dict) or set(expected) != set(CORE_NAMES):
        raise ValueError(f"Incomplete approved core set for {target}")
    for name in CORE_NAMES:
        actual = candidate["cores"][name]
        pinned = expected[name]
        if not isinstance(pinned, dict):
            raise ValueError(f"Invalid lock record for {target}/{name}")
        for field in FINGERPRINT_FIELDS:
            if pinned.get(field) != actual[field]:
                raise ValueError(
                    f"Release core mismatch: {target}/{name}/{field}; "
                    "the downloaded nightly may have changed"
                )
        revision = actual.get("reported_source_revision")
        commit = pinned.get("source_commit_sha")
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{7,40}", revision):
            raise ValueError(f"Core revision missing or invalid: {target}/{name}")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError(f"Full corresponding source commit missing: {target}/{name}")
        if not commit.startswith(revision):
            raise ValueError(f"Source revision mismatch: {target}/{name}")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("candidate", "verify"))
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--lock", type=Path, default=LOCK_PATH)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.command == "candidate":
        print("RELEASE_CORE_CANDIDATE_BEGIN")
        print(json.dumps(candidate_fingerprint(manifest), sort_keys=True))
        print("RELEASE_CORE_CANDIDATE_END")
    else:
        lock = json.loads(args.lock.read_text(encoding="utf-8"))
        print(f"Approved locked release cores: {verify_release_lock(manifest, lock)}")


if __name__ == "__main__":
    main()
