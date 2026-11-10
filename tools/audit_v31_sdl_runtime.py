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
    if not isinstance(recorded_notices, list) or not recorded_notices:
        raise ValueError("No wheel-provided pygame-ce notices in packaged inventory")
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
    binaries = []
    for path in sorted(bundle.rglob("*")):
        if not _native_candidate(path):
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError("Unexpected linked/invalid pygame or SDL runtime file")
        binaries.append({"path": path.relative_to(bundle).as_posix(),
                         "sha256": file_hash(path), "size_bytes": path.stat().st_size})
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
          f"{len(report['wheel_notices'])} notice files; approval remains false")


if __name__ == "__main__":
    main()
