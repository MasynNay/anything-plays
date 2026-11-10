"""Stage genuine verified 3.1 RC1 installers into an UNPUBLISHED release draft.

A source companion is included for owner audit, but pygame/SDL source
correspondence, LGPL relinking and physical hardware acceptance are OPEN.
Never rename an RC1 installer as stable or assert binary distribution approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import zipfile

QA_RUN = 42905694504
QA_HEAD = "c67fab048d7e44f371f2589a6d73b9d556de84d0"
APP_SOURCE = "26de1e1ad1b701d0735e085158347f8c213ce437"
SOURCE_RUN = 42909893531
SOURCE_HEAD = "8f39b19300394ff3585c8968e3178c3ae70a4bfb"
TARGETS = {
    "windows-x64": ("AnythingPlaysSetup-3.1.0-rc1-full.exe",
                    "FULL_WINDOWS_QA_RECEIPT.json",
                    "UNRELEASED_3_1_FULL_WINDOWS_RC1_QA"),
    "linux-x64": ("anything-plays-31-rc1_3.1.0~rc1full_amd64.deb",
                  "FULL_LIBRARY_QA_RECEIPT.json",
                  "UNRELEASED_3_1_FULL_LINUX_RC1_QA"),
    "macos-arm64": ("AnythingPlays-3.1.0-rc1-full-macos-arm64.dmg",
                    "FULL_MACOS_QA_RECEIPT.json",
                    "UNRELEASED_3_1_FULL_MACOS_RC1_QA"),
    "macos-x64": ("AnythingPlays-3.1.0-rc1-full-macos-x64.dmg",
                  "FULL_MACOS_QA_RECEIPT.json",
                  "UNRELEASED_3_1_FULL_MACOS_RC1_QA"),
}
SOURCE_FILES = (
    "pygame-ce-2.5.8-tagged-upstream-source.tar.gz",
    "SDL_SOURCE_REVIEW.json",
    "SIX_ORIGINAL_SOURCE_CANDIDATE_SHA256SUMS.txt",
    "SIX_SOURCE_COMPANION_READINESS.json",
    "README_SOURCE_CANDIDATES.txt",
)
SDL_NAMES = ("sdl2-2.32.8", "sdl2-2.32.10", "sdl2-image-2.8.12",
             "sdl2-mixer-2.8.2", "sdl2-ttf-2.24.0")
SOURCE_ASSET = "AnythingPlays-3.1.0-RC1-ORIGINAL-SOURCE-CANDIDATES-UNAPPROVED.zip"
SHA = re.compile(r"^[0-9a-f]{64}$")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_file(path, minimum=1):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size < minimum:
        raise ValueError("Missing, tiny or symlinked release-draft input: " + path.name)
    return path


def read_json(path):
    path = safe_file(path)
    if path.stat().st_size > 8_000_000:
        raise ValueError("Unbounded JSON audit input")
    value = json.loads(path.read_text("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Invalid JSON audit object")
    return value


def verify_installers(folder, minimum=1_000_000):
    folder = Path(folder)
    staged = {}
    for target, (filename, record_name, status) in TARGETS.items():
        base = folder / target
        binary = safe_file(base / filename, minimum)
        receipt = read_json(base / record_name)
        audit = read_json(base / "SDL_RUNTIME_AUDIT.json")
        if (receipt.get("status") != status
                or receipt.get("target") != target
                or receipt.get("installer") != filename
                or receipt.get("source_preview_revision") != APP_SOURCE
                or receipt.get("native_core_count") != 11
                or receipt.get("console_profiles") != 18
                or receipt.get("sdl_runtime_audit") != "SDL_RUNTIME_AUDIT.json"
                or receipt.get("public_release_approved") is not False
                or receipt.get("final_release_approved") is not False
                or receipt.get("sha256") != digest(binary)):
            raise ValueError("RC1 original-source native build receipt mismatch: " + target)
        if (audit.get("target") != target
                or audit.get("status") != "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY"
                or audit.get("pygame_version") != "2.5.8"
                or audit.get("redistribution_approved") is not False):
            raise ValueError("Missing or overstated SDL audit: " + target)
        staged[target] = {
            "filename": filename, "sha256": digest(binary),
            "bytes": binary.stat().st_size, "path": binary,
        }
    if len({entry["sha256"] for entry in staged.values()}) != 4:
        raise ValueError("Reused unrelated installer bytes across targets")
    return staged


def verify_sources(source):
    source = Path(source)
    report = read_json(source / "SIX_SOURCE_COMPANION_READINESS.json")
    audit = read_json(source / "SDL_SOURCE_REVIEW.json")
    if (report.get("status") != "UNRELEASED_3_1_ORIGINAL_SOURCE_CANDIDATES_ONLY"
            or report.get("full_rc_qa_run") != QA_RUN
            or report.get("source_app_commit") != APP_SOURCE
            or report.get("original_source_archive_count") != 6
            or report.get("exact_binary_to_source_correspondence_verified") is not False
            or report.get("complete_transitive_source_verified") is not False
            or report.get("lgpl_relinking_reviewed") is not False
            or report.get("redistribution_approved") is not False
            or report.get("public_release_approved") is not False):
        raise ValueError("Source candidate report missing or falsely approved")
    if (audit.get("full_rc_qa_run") != QA_RUN
            or audit.get("source_app_commit") != APP_SOURCE
            or audit.get("corresponding_source_complete") is not False
            or audit.get("redistribution_approved") is not False):
        raise ValueError("Source candidate audit not pinned to exact RC1")
    required = set(SOURCE_FILES)
    required.add("SDL-original-tagged-source-candidates/SDL_CANDIDATE_SOURCE_MANIFEST.json")
    required.add("SDL-original-tagged-source-candidates/Pygame-CE-LGPL-2.1.txt")
    for name in SDL_NAMES:
        required.add("SDL-original-tagged-source-candidates/" + name + ".tar.gz")
        required.add("SDL-original-tagged-source-candidates/" + name + "-ORIGINAL-LICENSE.txt")
    checksum_file = safe_file(source / "SIX_ORIGINAL_SOURCE_CANDIDATE_SHA256SUMS.txt")
    checksums = {}
    for line in checksum_file.read_text("utf-8").splitlines():
        try:
            checksum, rel = line.split("  ", 1)
        except ValueError as exc:
            raise ValueError("Invalid source checksum record") from exc
        posix = PurePosixPath(rel)
        if (not SHA.fullmatch(checksum) or posix.is_absolute()
                or ".." in posix.parts or "\\" in rel or rel in checksums):
            raise ValueError("Unsafe or duplicated source archive entry")
        checksums[rel] = checksum
    expected_checks = required - {
        "SIX_ORIGINAL_SOURCE_CANDIDATE_SHA256SUMS.txt",
        "README_SOURCE_CANDIDATES.txt",
    }
    # The source manifest covers archives, licenses and pygame; two reports
    # are additionally packed and authenticated by the outer draft SHA list.
    if not expected_checks.issubset(set(checksums)):
        raise ValueError("Source verification missing upstream archives or notices")
    for name in sorted(required):
        path = safe_file(source / name)
        if name in checksums and digest(path) != checksums[name]:
            raise ValueError("Source-companion SHA-256 mismatch: " + name)
    return [source / name for name in sorted(required)]


def stage(installers, source, output, minimum=1_000_000):
    installers, source, output = map(Path, (installers, source, output))
    destination = output.resolve()
    for inp in (installers.resolve(), source.resolve()):
        if destination == inp or destination.is_relative_to(inp) or inp.is_relative_to(destination):
            raise ValueError("Staging output cannot overlap original input")
    if output.is_symlink() or (output.exists() and any(output.iterdir())):
        raise ValueError("Draft staging output must be new or empty")
    checked = verify_installers(installers, minimum)
    sources = verify_sources(source)
    output.mkdir(parents=True, exist_ok=True)
    assets = []
    for target, record in checked.items():
        dest = output / record["filename"]
        shutil.copyfile(record["path"], dest)
        if digest(dest) != record["sha256"]:
            raise ValueError("Copied installer does not match authenticated QA bytes")
        assets.append(dest)
    source_asset = output / SOURCE_ASSET
    with zipfile.ZipFile(source_asset, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as archive:
        for src in sources:
            archive.write(src, arcname=src.relative_to(source).as_posix())
    assets.append(source_asset)
    manifest = {
        "schema_version": 1,
        "status": "UNPUBLISHED_3_1_RC1_RELEASE_DRAFT_QA_ONLY",
        "tag": "v3.1.0-rc1",
        "app_source_commit": APP_SOURCE,
        "full_installer_qa_run": QA_RUN, "qa_commit": QA_HEAD,
        "source_audit_run": SOURCE_RUN, "source_audit_commit": SOURCE_HEAD,
        "original_emulator_source_release": "https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources",
        "installers": {key: {field: value for field, value in entry.items() if field != "path"}
                       for key, entry in checked.items()},
        "source_archive": {"filename": SOURCE_ASSET, "sha256": digest(source_asset)},
        "physical_controller_or_camera_tested": False,
        "retail_gameplay_save_audio_endurance_verified": False,
        "complete_native_corresponding_source_verified": False,
        "lgpl_relinking_reviewed": False,
        "redistribution_approved": False, "public_release_approved": False,
    }
    ledger = output / "RC1_DRAFT_QA_RECEIPT.json"
    ledger.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", "utf-8")
    assets.append(ledger)
    sums = output / "SHA256SUMS.txt"
    sums.write_text("".join(f"{digest(item)}  {item.name}\n"
                            for item in sorted(assets, key=lambda p: p.name)), "ascii")
    # Never emit a public 3.1.0 stable asset or reuse one of the stable tags.
    assert len(assets) == 6 and all("3.0.0" not in item.name for item in assets)
    return manifest


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--installers", type=Path, required=True)
    cli.add_argument("--source", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    status = stage(args.installers, args.source, args.output)
    print(status["status"], ": four 18-console RC1 installers and original "
          "source candidates staged; all public distribution gates remain open")


if __name__ == "__main__":
    main()
