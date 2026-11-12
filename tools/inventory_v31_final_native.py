"""Inventory exact frozen 3.1.0 native dependencies and bundled notices.

This is a read-only, byte-pinned *technical inventory* for independent
redistribution/source review. It does not infer corresponding source,
relinkability, legal obligations or approval from filenames or notices.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re

EXPECTED = {
    "linux-x64": ("anything-plays-31_3.1.0_amd64.deb", "FULL_LIBRARY_QA_RECEIPT.json"),
    "windows-x64": ("AnythingPlaysSetup-3.1.0.exe", "FULL_WINDOWS_QA_RECEIPT.json"),
    "macos-arm64": ("AnythingPlays-3.1.0-macos-arm64.dmg", "FULL_MACOS_QA_RECEIPT.json"),
    "macos-x64": ("AnythingPlays-3.1.0-macos-x64.dmg", "FULL_MACOS_QA_RECEIPT.json"),
}
STATUS = "UNAPPROVED_EXACT_FINAL_3_1_NATIVE_AND_NOTICE_INVENTORY"
NATIVE_EXT = (".pyd", ".dll", ".dylib", ".so", ".bundle", ".exe")
NOTICE_NAMES = ("license", "licence", "copying", "notice", "copyright", "authors")
CODEC_NAMES = ("ffmpeg", "avcodec", "avformat", "avutil", "swscale",
               "x264", "x265", "gstreamer", "libvpx", "aom", "dav1d")
MAX_NOTICE_BYTES = 4 * 1024 * 1024


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(2 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def native(name: str) -> bool:
    n = name.lower()
    # Accept ELF sonames such as libSDL2.so.0.3200.10, but never let
    # metadata files like copying.cpython-313-darwin.so.yml masquerade
    # as binary objects merely because ".so." appears in the name.
    return (n.endswith(NATIVE_EXT)
            or re.search(r"\\.so(?:\\.[0-9]+)+$", n) is not None
            or n.endswith(".dylib.tbd"))


def family(relative: str) -> str:
    value = relative.lower()
    name = value.rsplit("/", 1)[-1]
    if "cores/" in value and ("libretro" in name or name.endswith((".dll",".so",".dylib"))):
        return "libretro_core"
    if any(part in name for part in CODEC_NAMES):
        return "codec_candidate"
    if "sdl" in name:
        return "sdl"
    if "pygame" in value:
        return "pygame"
    if "cv2" in value or "opencv" in name:
        return "opencv"
    if "portaudio" in name or "openal" in name:
        return "audio"
    return "other_native"


def notice(relative: str) -> bool:
    p = relative.lower().split("/")
    name = p[-1]
    if name in ("python_distributions.json", "third_party_components.md",
                "third_party_notices.md", "pygame-ce-lgpl-2.1.txt"):
        return True
    if any(part == "licenses" or part.endswith(".dist-info") for part in p[:-1]):
        return (any(marker in name for marker in NOTICE_NAMES)
                or name.endswith((".txt", ".md")) and "licenses" in p)
    return False


def _walk(root: Path):
    for base, directories, files in os.walk(root, topdown=True, followlinks=False):
        here = Path(base)
        directories[:] = sorted(d for d in directories
                                if not (here / d).is_symlink())
        for name in sorted(files):
            item = here / name
            if not item.is_file() or item.is_symlink():
                continue
            relative = item.relative_to(root).as_posix()
            yield relative, item


def inspect(*, target: str, bundle: Path, installer: Path, receipt: Path,
            source_sha: str):
    if target not in EXPECTED:
        raise ValueError("Unknown 3.1 native QA target")
    if not isinstance(source_sha, str) or not re.fullmatch(r"[a-f0-9]{40}", source_sha):
        raise ValueError("Exact final source SHA required")
    bundle, installer, receipt = map(Path, (bundle, installer, receipt))
    if not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("Missing or symlinked extracted final bundle")
    correct, _ = EXPECTED[target]
    if (installer.name != correct or not installer.is_file()
            or installer.is_symlink() or installer.stat().st_size < 1024 * 1024):
        raise ValueError("Full original-core 3.1.0 installer missing or renamed")
    if (receipt.is_symlink() or not receipt.is_file() or
            receipt.stat().st_size > MAX_NOTICE_BYTES):
        raise ValueError("Original verified full-source receipt missing or invalid")
    try:
        report = json.loads(receipt.read_text("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Bad original full installer receipt") from exc
    expected = {
        "target": target, "installer": correct, "sha256": digest(installer),
        "source_preview_revision": source_sha,
        "identity_channel": "final_candidate",
        "settings_namespace": "anything-plays-31",
        "native_core_count": 11, "console_profiles": 18,
        "status": "PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA",
        "public_release_approved": False, "final_release_approved": False,
    }
    for key, value in expected.items():
        if type(report.get(key)) is not type(value) or report[key] != value:
            raise ValueError("Not exact verified full 3.1.0 final installer: " + key)

    binaries, notices, duplicates = [], [], defaultdict(list)
    license_roots = set()
    for relative, file in _walk(bundle):
        lower = relative.lower()
        if "/licenses/" in "/" + lower + "/" or lower.startswith("licenses/"):
            license_roots.add(relative.split("/licenses/")[0]
                              if "/licenses/" in relative else ".")
        if native(file.name) or (target.startswith("macos") and
                                  relative.endswith("Contents/MacOS/AnythingPlays")):
            d = digest(file)
            item = {"path": relative, "sha256": d,
                    "size_bytes": file.stat().st_size, "family": family(relative)}
            binaries.append(item)
            duplicates[file.name.lower()].append(item)
        if notice(relative):
            size = file.stat().st_size
            if 0 < size <= MAX_NOTICE_BYTES:
                notices.append({"path": relative, "sha256": digest(file),
                                "size_bytes": size})
    if not binaries:
        raise ValueError("Frozen final app has no inspected native files")
    if not notices:
        raise ValueError("Frozen final app has no observed notice files")
    groups = Counter(item["family"] for item in binaries)
    candidate_names = sorted({x["path"] for x in binaries
                              if x["family"] == "codec_candidate"})
    repeated = []
    for name, files in sorted(duplicates.items()):
        if len({x["sha256"] for x in files}) > 1:
            repeated.append({"basename": name, "distinct_hashes":
                             sorted({x["sha256"] for x in files}),
                             "paths": [x["path"] for x in files]})
    notices_lower = "\n".join(x["path"].lower() for x in notices)
    signals = {
        "pygame_ce_lgpl_notice_seen": "pygame-ce-lgpl-2.1" in notices_lower,
        "pygame_sdl_notice_candidate_seen": "sdl" in notices_lower,
        "opencv_notice_candidate_seen": "opencv" in notices_lower,
        "python_distribution_inventory_seen": "python_distributions.json" in notices_lower,
    }
    return {
        "schema_version": 1, "status": STATUS,
        "target": target, "source_revision": source_sha,
        "installer": correct, "installer_sha256": expected["sha256"],
        "native_file_count": len(binaries), "notice_file_count": len(notices),
        "native_family_counts": dict(sorted(groups.items())),
        "native_files": binaries, "notice_files": notices,
        "duplicate_native_basenames_with_different_hashes": repeated,
        "codec_candidates": candidate_names,
        "notice_presence_signals_not_legal_conclusions": signals,
        "license_roots_observed": sorted(license_roots),
        "source_to_binary_correspondence_verified": False,
        "all_native_library_replacement_paths_verified": False,
        "all_redistribution_rights_reviewed": False,
        "physical_controller_or_camera_tested": False,
        "public_release_approved": False,
        "review_note": "Native files and notices were hashed from exact final installer; "
                       "build options, binary source match, dependency loader choices, "
                       "license obligations and replacement/relinking require review.",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", choices=sorted(EXPECTED), required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--installer", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(argv)
    report = inspect(target=a.target, bundle=a.bundle, installer=a.installer,
                     receipt=a.receipt, source_sha=a.source_sha)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print(a.target, "unapproved native files", report["native_file_count"],
          "notice files", report["notice_file_count"],
          "candidate codec files", len(report["codec_candidates"]))
    print("This technical inventory DOES NOT clear any public release or LGPL gate.")


if __name__ == "__main__":
    main()
