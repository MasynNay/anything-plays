"""Hash SDL/pygame-ce frozen runtime evidence for *unreleased* 3.1 QA.

Inspect the actual staged or installed application, not the developer's venv.
This report does not establish LGPL compliance, resolve native linkage or
grant redistribution permission. It exists to make those reviews specific.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

TARGETS = ("linux-x64", "windows-x64", "macos-arm64", "macos-x64")
VERSION = "2.5.8"
MAX_NOTICE_SIZE = 4 * 1024 * 1024
# Verbatim upstream 2.5.8 docs/LGPL.txt, not inferred from wheel metadata.
UPSTREAM_LGPL_SHA256 = "a190dc9c8043755d90f8b0a75fa66b9e42d4af4c980bf5ddc633f0124db3cee7"
NATIVE_SUFFIXES = (".so", ".dylib", ".dll", ".pyd")


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_file(root, relative):
    """Verify a tracked notice stays inside the real, unsymlinked bundle."""
    if not isinstance(relative, str):
        raise ValueError("Notice path must be a string")
    posix = PurePosixPath(relative)
    if (not relative or relative.startswith("/") or "\\" in relative
            or any(part in ("..", ".") for part in relative.split("/"))):
        raise ValueError("Unsafe notice path: " + repr(relative))
    path = root.joinpath(*posix.parts)
    if not path.is_file() or path.is_symlink():
        raise ValueError("Missing or linked notice: " + relative)
    # Reject symlinked parent directories, including a linked license root.
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Notice outside bundle: " + relative)
    parent = path.parent
    while parent != root:
        if parent.is_symlink():
            raise ValueError("Symlinked notice directory: " + relative)
        parent = parent.parent
    size = path.stat().st_size
    if size < 1 or size > MAX_NOTICE_SIZE:
        raise ValueError("Missing or oversized notice: " + relative)
    return path


def _native_candidate(path):
    """Include pygame extensions and SDL shared objects; not all OS libraries."""
    name = path.name.lower()
    relevant = ("pygame" in str(path).lower() or "sdl" in name)
    return relevant and (
        name.endswith(NATIVE_SUFFIXES)
        or ".so." in name
    )


def inspect_bundle(bundle, target):
    if target not in TARGETS:
        raise ValueError("Unsupported 3.1 audit target")
    bundle = Path(bundle)
    if not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("Expected an unpacked application directory")
    license_root = (bundle / "Contents" / "Resources" / "licenses"
                    if target.startswith("macos-") else bundle / "licenses")
    inventory = _safe_file(license_root, "PYTHON_DISTRIBUTIONS.json")
    try:
        data = json.loads(inventory.read_text("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid frozen Python distribution inventory") from exc
    if not isinstance(data, dict) or not isinstance(data.get("distributions"), list):
        raise ValueError("Frozen distribution inventory schema mismatch")
    matches = [dist for dist in data["distributions"]
               if isinstance(dist, dict)
               and str(dist.get("name", "")).lower().replace("_", "-") == "pygame-ce"]
    if len(matches) != 1 or matches[0].get("version") != VERSION:
        raise ValueError("Exactly one pinned pygame-ce 2.5.8 runtime is required")
    dist = matches[0]
    recorded_notices = dist.get("license_files")
    if not isinstance(recorded_notices, list):
        raise ValueError("Malformed pygame-ce notice inventory")
    notices = []
    for record in recorded_notices:
        if not isinstance(record, dict):
            raise ValueError("Malformed pygame-ce notice record")
        relative = record.get("bundled_path")
        if not isinstance(relative, str) or not relative.startswith(
                "python-distribution-notices/"):
            raise ValueError("Missing bundled pygame-ce license path")
        path = _safe_file(license_root, relative)
        notices.append({"path": path.relative_to(bundle).as_posix(),
                        "sha256": file_hash(path), "size_bytes": path.stat().st_size})
    if len({entry["path"] for entry in notices}) != len(notices):
        raise ValueError("Duplicate license path in frozen manifest")

    # pygame-ce 2.5.8's installed wheel inventory sometimes exposes no
    # wheel-notice files. Preserve that gap honestly. The full 3.1 QA
    # assembly adds the *verbatim upstream tagged license* as an independent
    # corresponding notice; its exact bytes must match the pinned digest.
    upstream = None
    if not notices:
        upstream_path = _safe_file(license_root, "Pygame-CE-LGPL-2.1.txt")
        if file_hash(upstream_path) != UPSTREAM_LGPL_SHA256:
            raise ValueError("Pinned upstream pygame-ce LGPL license mismatch")
        upstream = {
            "path": upstream_path.relative_to(bundle).as_posix(),
            "sha256": UPSTREAM_LGPL_SHA256,
            "source": "https://github.com/pygame-community/pygame-ce/blob/2.5.8/docs/LGPL.txt",
            "wheel_provided": False,
        }
    binaries = []
    for path in sorted(bundle.rglob("*")):
        if not _native_candidate(path):
            continue
        # ELF libraries often use legitimate relative SONAME symlinks.
        # Accept those only when the target is inside the extracted app.
        # Never dereference a link into the CI host's system directories.
        link = path.is_symlink()
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError("Broken native runtime link: " + str(path)) from exc
        if (not resolved.is_file()
                or not resolved.is_relative_to(bundle.resolve())):
            raise ValueError("Native runtime link escapes bundle: " + str(path))
        entry = {"path": path.relative_to(bundle).as_posix(),
                 "sha256": file_hash(resolved),
                 "size_bytes": resolved.stat().st_size}
        if link:
            entry["symlink_target"] = resolved.relative_to(bundle.resolve()).as_posix()
        binaries.append(entry)
    if not binaries:
        raise ValueError("No pygame or SDL native runtime found in frozen application")
    return {
        "schema_version": 1,
        "status": "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY",
        "target": target,
        "pygame_distribution": "pygame-ce",
        "pygame_version": VERSION,
        "python_inventory_scope": "Build environment, not a final runtime SBOM",
        "native_candidates": binaries,
        "wheel_notices": sorted(notices, key=lambda item: item["path"]),
        "wheel_notice_files_missing": not bool(notices),
        "pinned_upstream_lgpl_notice": upstream,
        "sdl_linkage_reviewed": False,
        "original_sources_verified": False,
        "lgpl_relinking_reviewed": False,
        "redistribution_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bundle = args.bundle.resolve(strict=True)
    output = args.output.resolve()
    if output.is_relative_to(bundle):
        parser.error("Audit output must be outside the frozen application")
    report = inspect_bundle(bundle, args.target)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"SDL runtime evidence: {args.target}, "
          f"{len(report['native_candidates'])} native candidates, "
          f"{len(report['wheel_notices'])} wheel notices; "
          f"upstream fallback: {report['pinned_upstream_lgpl_notice'] is not None}; "
          "approval remains false")


if __name__ == "__main__":
    main()
