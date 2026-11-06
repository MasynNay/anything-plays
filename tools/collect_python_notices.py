"""Collect distributable Python package license files for frozen installers.

The inventory describes the *build environment*. Some packages are build-only,
and installed native libraries may have additional licensing obligations.
This is evidence for a review, not an automated redistribution approval.
"""

import argparse
from importlib import metadata
import json
from pathlib import Path
import re
import shutil

NOTICE_PREFIXES = ("license", "licence", "copying", "notice", "copyright")
MAX_NOTICE_BYTES = 4 * 1024 * 1024


def _safe_name(name):
    return re.sub(r"[^a-z0-9._-]", "_", name.lower())[:120]


def collect_python_notices(directory, distributions=None):
    """Copy wheel-provided notices and save an inventory of installed packages."""
    directory = Path(directory)
    notice_root = directory / "python-distribution-notices"
    if notice_root.is_symlink():
        raise ValueError("Refusing symlinked notice directory")
    if notice_root.exists():
        shutil.rmtree(notice_root)
    notice_root.mkdir(parents=True)
    packages = sorted(
        metadata.distributions() if distributions is None else distributions,
        key=lambda dist: (dist.metadata.get("Name") or "").casefold(),
    )
    inventory = []
    copied = 0
    for dist in packages:
        name = dist.metadata.get("Name") or "unknown"
        version = dist.version or "unknown"
        folder = _safe_name(name) + "-" + _safe_name(version)
        license_files = []
        for file in dist.files or ():
            relative = Path(str(file))
            if relative.is_absolute() or ".." in relative.parts:
                continue
            filename = relative.name.lower()
            if not filename.startswith(NOTICE_PREFIXES):
                continue
            source = Path(dist.locate_file(file))
            if not source.is_file() or source.is_symlink():
                continue
            if source.stat().st_size > MAX_NOTICE_BYTES:
                continue
            destination = notice_root / folder / f"{len(license_files):03d}_{_safe_name(relative.name)}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            copied += 1
            license_files.append({
                "original_path": str(relative),
                "bundled_path": destination.relative_to(directory).as_posix(),
            })
        license_expression = dist.metadata.get("License-Expression")
        fallback = (dist.metadata.get("License") or "").splitlines()
        inventory.append({
            "name": name,
            "version": version,
            "license_expression": license_expression or (fallback[0][:200] if fallback else None),
            "license_files": license_files,
        })

    if not inventory or not copied:
        raise ValueError("No Python distribution license files were found")
    manifest = {
        "schema_version": 1,
        "scope": "Installed Python build environment; may include build-only packages",
        "redistribution_approved": False,
        "distributions": inventory,
    }
    (directory / "PYTHON_DISTRIBUTIONS.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("license_directory", type=Path)
    args = parser.parse_args()
    manifest = collect_python_notices(args.license_directory)
    total = sum(len(entry["license_files"]) for entry in manifest["distributions"])
    print(f"Collected {total} Python notice files for "
          f"{len(manifest['distributions'])} installed distributions")


if __name__ == "__main__":
    main()
