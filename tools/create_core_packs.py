"""Create candidate, content-addressed in-app emulator update packs.

This tool is for maintainers / CI only. It does not publish unreviewed
nightly libraries or approve them for user installation. After each
platform's gameplay/controls/save/signature audit, explicitly upload the
candidate ZIPs to an official 2.1 GitHub release. GitHub's release API then
provides the asset SHA-256 digest used by the in-app updater.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from anything_plays.core_packs import (
    MAX_BINARY_BYTES, PACK_PREFIX, RELEASE_TAG_RE, target_identity,
)
from anything_plays.emulator_updates import UPSTREAM_REPOS


def create_candidate_packs(cores_dir: Path, output_dir: Path, tag: str,
                           *, selected=None, target=None, license_reviewed=False,
                           runtime_tested=False):
    if not RELEASE_TAG_RE.fullmatch(tag):
        raise ValueError("Refusing non-2.1 release identity")
    cores_dir, output_dir = Path(cores_dir), Path(output_dir)
    target = target or target_identity()[0]
    ext = {
        "windows-x64": ".dll", "macos-arm64": ".dylib",
        "macos-x64": ".dylib", "linux-x64": ".so",
    }.get(target)
    if ext is None:
        raise ValueError("Unrecognized build target")
    provenance = json.loads(
        (cores_dir / "CORE_PROVENANCE.json").read_text(encoding="utf-8")
    )
    if not isinstance(provenance.get("cores"), list):
        raise ValueError("Missing native core provenance list")
    records = {
        row["name"]: row
        for row in provenance["cores"]
        if isinstance(row, dict) and row.get("name") in UPSTREAM_REPOS
    }
    names = list(selected) if selected is not None else list(records)
    if not names or len(set(names)) != len(names):
        raise ValueError("Select distinct, vetted native cores")
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for name in names:
        if name not in UPSTREAM_REPOS or name not in records:
            raise ValueError(f"Unknown or absent native core: {name}")
        if name == "dolphin":
            raise ValueError(
                "Dolphin must be distributed with matching Sys files in "
                "a full signed application update until standalone core "
                "pack compatibility is reviewed"
            )
        row = records[name]
        filename = f"{name}_libretro{ext}"
        if row.get("file") != filename:
            raise ValueError(f"Wrong architecture or file name for {name}")
        core = cores_dir / filename
        if core.is_symlink() or not core.is_file():
            raise ValueError(f"Missing or symlinked binary: {filename}")
        if not 10_000 < core.stat().st_size < MAX_BINARY_BYTES:
            raise ValueError(f"Native core size is outside approved limits: {name}")
        data = core.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if row.get("sha256") != digest:
            raise ValueError(f"Core provenance checksum mismatch: {name}")
        manifest = {
            "schema": 1, "name": name, "target": target, "release": tag,
            "file": filename, "sha256": digest,
            "source_repository": "https://github.com/" + UPSTREAM_REPOS[name],
            "source_revision": row.get("reported_source_revision"),
            "libretro_library_version": row.get("libretro_library_version"),
            "third_party_license_reviewed": license_reviewed is True,
            "packaged_runtime_tested": runtime_tested is True,
        }
        # A CI packaging candidate isn't permission to silently publish.
        archive_path = output_dir / f"{PACK_PREFIX}{name}-{target}.zip"
        if archive_path.is_symlink():
            raise ValueError("Refusing a symlinked output archive")
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("core-pack.json", json.dumps(manifest, sort_keys=True) + "\n")
            archive.writestr(filename, data)
        summaries.append({
            "name": name, "target": target, "file": str(archive_path),
            "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
            "binary_sha256": digest, "release": tag,
            "status": "candidate-only; requires review and release approval",
        })
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cores", type=Path, default=ROOT / "cores")
    parser.add_argument("--output", type=Path, default=ROOT / "release" / "core-packs")
    parser.add_argument("--release", required=True)
    parser.add_argument("--name", action="append", dest="names")
    parser.add_argument(
        "--license-reviewed", action="store_true",
        help="Maintainer attests the specific core and source license was audited",
    )
    parser.add_argument(
        "--runtime-tested", action="store_true",
        help="Maintainer attests this core passed installed-app gameplay QA on this platform",
    )
    args = parser.parse_args()
    results = create_candidate_packs(
        args.cores, args.output, args.release,
        selected=args.names,
        license_reviewed=args.license_reviewed,
        runtime_tested=args.runtime_tested,
    )
    print(json.dumps(results, indent=2))
    print(
        "Reviewed pack candidates created" if args.license_reviewed and args.runtime_tested
        else "UNAPPROVED candidates created; updater will refuse them."
    )
    print("NOTHING was published or installed.")


if __name__ == "__main__":
    main()
