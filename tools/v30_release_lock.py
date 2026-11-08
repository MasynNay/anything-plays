"""Fail-closed immutable 11-core production gate for Anything Plays 3.0.

The official 2.0 core lock remains completely separate. This validator
rejects all release-mode binaries until every platform's native archive,
source correspondence and mixed-license rights are explicitly approved.

Cryptographic identity is necessary but NOT sufficient for license rights.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from tools.core_release_lock import release_target

LOCK_PATH = Path(__file__).resolve().parents[1] / "config/v3.0-core-lock.json"
CORE_NAMES = frozenset((
    "mgba", "snes9x", "fceumm", "genesis_plus_gx", "parallel_n64", "dolphin",
    "stella2014", "prosystem", "mednafen_pce_fast", "mednafen_ngp",
    "mednafen_wswan",
))
# The legacy original preview (Snes9x + Genesis Plus GX) stays readable for
# existing exact-lock regression tests. An independently reviewed production
# candidate MAY select the genuinely differently named, source-built GPL
# alternative once its full per-native licensing/source evidence exists.
# This does not itself approve any binary or convert the trial into release.
ALTERNATIVE_CORE_ORDER = (
    "mgba", "mednafen_supafaust", "fceumm", "blastem", "parallel_n64",
    "dolphin", "stella2014", "prosystem", "mednafen_pce_fast",
    "mednafen_ngp", "mednafen_wswan",
)
ALTERNATIVE_CORE_NAMES = frozenset(ALTERNATIVE_CORE_ORDER)
ORIGINAL_CORE_ORDER = (
    "mgba", "snes9x", "fceumm", "genesis_plus_gx", "parallel_n64",
    "dolphin", "stella2014", "prosystem", "mednafen_pce_fast",
    "mednafen_ngp", "mednafen_wswan",
)
assert frozenset(ORIGINAL_CORE_ORDER) == CORE_NAMES
assert len(ALTERNATIVE_CORE_ORDER) == len(ALTERNATIVE_CORE_NAMES) == 11

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_SHA = re.compile(r"[0-9a-f]{40}\Z")
TARGETS = frozenset((
    "windows-x86_64", "linux-x86_64", "macos-arm64", "macos-x86_64",
))


def selected_core_set(lock):
    """Know exactly which source-reviewed 11 core names a future lock approves.

    The current tracked lock has NO approvals and cannot pass load_approved_lock.
    A future alternative choice cannot be enabled by a build env flag or an
    unapproved research marker; the fully reviewed approval record must bind
    the exact source-built identities and document absent NC libraries.
    """
    if not isinstance(lock, dict):
        raise ValueError("Missing reviewed 3.0 native lock")
    mode = lock.get("core_set_id", "legacy-noncommercial")
    if mode == "legacy-noncommercial":
        return CORE_NAMES
    if mode != "gpl-source-built-alternative":
        raise ValueError("Unknown 3.0 release core set")
    if (lock.get("legacy_noncommercial_native_binaries_excluded") is not True
            or lock.get("source_built_alternative_binary_rights_reviewed") is not True):
        raise ValueError("GPL-alternative release rights/exclusion not approved")
    return ALTERNATIVE_CORE_NAMES


def ordered_core_names_for_lock(lock):
    names = selected_core_set(lock)
    if names == ALTERNATIVE_CORE_NAMES:
        return ALTERNATIVE_CORE_ORDER
    return ORIGINAL_CORE_ORDER


def load_approved_lock(path=LOCK_PATH):
    """Require complete rights approvals before touching native ZIP contents."""
    try:
        lock = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValueError("Cannot read 3.0 approved native core lock") from exc
    if not isinstance(lock, dict) or lock.get("schema_version") != 1:
        raise ValueError("Invalid 3.0 native lock schema")
    for name in (
        "approved_for_binary_distribution",
        "license_compatibility_reviewed",
        "corresponding_source_inventory_verified",
    ):
        if lock.get(name) is not True:
            raise ValueError(f"3.0 redistribution blocked: {name} not approved")
    if lock.get("native_core_count") != 11 or lock.get("system_profile_count") != 18:
        raise ValueError("3.0 native lock inventory mismatch")
    names = selected_core_set(lock)
    records = lock.get("targets")
    if not isinstance(records, dict) or set(records) != TARGETS:
        raise ValueError("Approved 3.0 lock must include all four architectures")
    for target, row in records.items():
        if not isinstance(row, dict) or row.get("approved_for_distribution") is not True:
            raise ValueError(f"{target}: native distribution unapproved")
        cores = row.get("cores")
        if not isinstance(cores, dict) or set(cores) != names:
            raise ValueError(f"{target}: approved core count mismatch")
        for name, core in cores.items():
            if not isinstance(core, dict):
                raise ValueError(f"{target}/{name}: bad core record")
            if (core.get("redistribution_approved") is not True or
                    core.get("corresponding_source_verified") is not True):
                raise ValueError(f"{target}/{name}: incomplete source/license approval")
            for digest_name in ("native_sha256", "original_archive_sha256"):
                if not isinstance(core.get(digest_name), str) or not SHA256.fullmatch(core[digest_name]):
                    raise ValueError(f"{target}/{name}: missing {digest_name}")
            for size_name in ("native_size_bytes", "original_archive_size_bytes"):
                if type(core.get(size_name)) is not int or core[size_name] <= 0:
                    raise ValueError(f"{target}/{name}: invalid {size_name}")
            name_ext = {
                "windows-x86_64": ".dll",
                "linux-x86_64": ".so",
                "macos-arm64": ".dylib",
                "macos-x86_64": ".dylib",
            }[target]
            if core.get("file") != f"{name}_libretro{name_ext}":
                raise ValueError(f"{target}/{name}: wrong core filename")
            if (not isinstance(core.get("upstream_source_repository"), str)
                    or not core["upstream_source_repository"].startswith("https://github.com/")):
                raise ValueError(f"{target}/{name}: source repository not reviewed")
            if (not isinstance(core.get("source_commit_sha"), str)
                    or not SOURCE_SHA.fullmatch(core["source_commit_sha"])):
                raise ValueError(f"{target}/{name}: corresponding source commit missing")
        sys = row.get("dolphin_sys")
        if not isinstance(sys, dict) or sys.get("source_correspondence_verified") is not True:
            raise ValueError(f"{target}: Dolphin Sys source is unverified")
        if sys.get("redistribution_approved") is not True:
            raise ValueError(f"{target}: Dolphin Sys redistribution not approved")
        if (not isinstance(sys.get("original_archive_sha256"), str)
                or not SHA256.fullmatch(sys["original_archive_sha256"])):
            raise ValueError(f"{target}: Dolphin Sys archive hash missing")
        if type(sys.get("original_archive_size_bytes")) is not int or sys["original_archive_size_bytes"] <= 0:
            raise ValueError(f"{target}: Dolphin Sys archive size missing")
    return lock


def native_for_target(lock, platform_name, architecture, name):
    target = release_target(platform_name, architecture)
    if name not in selected_core_set(lock):
        raise ValueError(f"Unknown 3.0 approved emulator core: {name}")
    return target, lock["targets"][target]["cores"][name]


def verify_core_archive(lock, platform_name, architecture, name, archive_bytes):
    target, record = native_for_target(lock, platform_name, architecture, name)
    digest = hashlib.sha256(archive_bytes).hexdigest()
    if digest != record["original_archive_sha256"] or len(archive_bytes) != record["original_archive_size_bytes"]:
        raise ValueError(f"3.0 preserved archive changed: {target}/{name}")
    return target


def verify_core_payload(lock, platform_name, architecture, name, filename, payload):
    target, record = native_for_target(lock, platform_name, architecture, name)
    if (filename != record["file"] or len(payload) != record["native_size_bytes"]
            or hashlib.sha256(payload).hexdigest() != record["native_sha256"]):
        raise ValueError(f"3.0 native core changed: {target}/{name}")
    return target


def verify_dolphin_archive(lock, platform_name, architecture, archive_bytes):
    target = release_target(platform_name, architecture)
    record = lock["targets"][target]["dolphin_sys"]
    if (hashlib.sha256(archive_bytes).hexdigest() != record["original_archive_sha256"]
            or len(archive_bytes) != record["original_archive_size_bytes"]):
        raise ValueError(f"3.0 Dolphin Sys archive changed: {target}")
    return target


def verify_native_bundle(lock, manifest):
    """Rehash installed payload provenance against the immutable lock."""
    target = release_target(manifest["build_platform"], manifest["build_architecture"])
    data = lock["targets"][target]["cores"]
    actual = manifest.get("cores")
    if not isinstance(actual, list) or len(actual) != 11:
        raise ValueError("3.0 native bundle must contain eleven cores")
    observed = {row.get("name"): row for row in actual}
    if set(observed) != selected_core_set(lock):
        raise ValueError("3.0 native bundle core set incomplete or wrong release lineup")
    for name, record in data.items():
        core = observed[name]
        checks = {
            "file": record["file"],
            "sha256": record["native_sha256"],
            "size_bytes": record["native_size_bytes"],
            "archive_sha256": record["original_archive_sha256"],
            "archive_size_bytes": record["original_archive_size_bytes"],
            "source_repository_url": record["upstream_source_repository"],
        }
        for field, expected in checks.items():
            if core.get(field) != expected:
                raise ValueError(f"3.0 bundle core mismatch: {target}/{name}/{field}")
    source = manifest.get("dolphin_system_assets")
    if not isinstance(source, dict):
        raise ValueError("3.0 release missing Dolphin Sys provenance")
    sys = lock["targets"][target]["dolphin_sys"]
    for field, pinned in (
        ("archive_sha256", sys["original_archive_sha256"]),
        ("archive_size_bytes", sys["original_archive_size_bytes"]),
    ):
        if source.get(field) != pinned:
            raise ValueError(f"3.0 bundle Dolphin Sys changed: {target}/{field}")
    return target

def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Print fully approved 3.0 frozen core identities")
    parser.add_argument("--print-approved-core-names", action="store_true")
    args = parser.parse_args(argv)
    if not args.print_approved_core_names:
        parser.error("Choose --print-approved-core-names")
    try:
        lock = load_approved_lock()
        names = ordered_core_names_for_lock(lock)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Unapproved 3.0 native core lineup: {exc}\n")
    print(" ".join(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
