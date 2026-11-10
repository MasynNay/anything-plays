"""Owner-only 3.1 full macOS preview, with original released 3.0 native cores.

Verify the public 3.0 DMG SHA256, the 3.1 SDL-enabled preview receipt, then
copy original byte-for-byte source-reviewed eleven-core payload and notices.
Never sign, tag, or publish a stable GitHub Release with this QA candidate.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import time

from anything_plays.v30_gpl_trial import validate_trial_core_directory
from verify_bundle import verify_bundle

PREVIEW_RUN_SHA = "ffee5dcdf0415440c9f5bffc7f9049a07c094ff3"


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as src:
        for chunk in iter(lambda: src.read(4 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def command(*args):
    subprocess.run([str(x) for x in args], check=True)


@contextmanager
def mount(dmg, location):
    location.mkdir(parents=True, exist_ok=True)
    command("hdiutil", "attach", "-readonly", "-nobrowse",
            "-mountpoint", location, dmg)
    try:
        yield location
    finally:
        command("hdiutil", "detach", location)


def verify_inputs(arch, stable, preview, checksums, receipt):
    if arch not in ("arm64", "x64"):
        raise ValueError("Only reviewed Apple Silicon or Intel architecture")
    stable_name = "AnythingPlays-3.0.0-macos-" + arch + ".dmg"
    preview_name = "AnythingPlays-3.1.0-preview1-macos-" + arch + ".dmg"
    if (stable.name != stable_name or preview.name != preview_name
            or not stable.is_file() or not preview.is_file()):
        raise ValueError("Missing exact named original/3.1 preview disk image")
    stable_sha = digest(stable)
    if stable_sha + "  " + stable_name not in checksums.read_text("utf-8").splitlines():
        raise ValueError("3.0 public DMG hash mismatch")
    meta = json.loads(receipt.read_text("utf-8"))
    if (meta.get("target") != "macos-" + arch or meta.get("installer") != preview_name
            or meta.get("source_revision") != PREVIEW_RUN_SHA
            or meta.get("sha256") != digest(preview)):
        raise ValueError("3.1 app does not match independently verified Preview 1")
    return stable_sha


def build(arch, stable, preview, checksums, receipt, output):
    if os.getenv("AP_V31_PREVIEW") != "1" or os.getenv("AP_V31_FULL_TEST_CORES") != "1":
        raise ValueError("Private QA flags not set")
    if os.getenv("AP_RELEASE_BUILD") == "1" or os.getenv("AP_V30_APPROVED_RELEASE") == "1":
        raise ValueError("Cannot treat preview as approved stable release")
    stable_sha = verify_inputs(arch, stable, preview, checksums, receipt)
    with tempfile.TemporaryDirectory(prefix="ap31-mac-full-") as temp:
        tmp = Path(temp)
        with mount(stable, tmp/"stable"), mount(preview, tmp/"preview"):
            old = tmp/"stable/AnythingPlays.app/Contents/Resources"
            src = tmp/"preview/AnythingPlays31Preview.app"
            app = tmp/"AnythingPlays31Preview.app"
            shutil.copytree(src, app, symlinks=True)
            resources = app/"Contents/Resources"
            orig_core = old/"cores"
            new_core = resources/"cores"
            original = validate_trial_core_directory(orig_core, ".dylib")
            if (original.get("total_source_built_core_families") != 11
                    or original.get("source_built_dolphin") is None
                    or original.get("source_built_tia") is None):
                raise ValueError("Expected verified 3.0 eleven original-source core families")
            shutil.rmtree(new_core)
            shutil.copytree(orig_core, new_core, symlinks=True)
            if validate_trial_core_directory(new_core, ".dylib") != original:
                raise ValueError("3.0 released native core bytes were changed")
            source_licenses = old/"licenses"
            current_licenses = resources/"licenses"
            for item in source_licenses.iterdir():
                if item.is_symlink():
                    raise ValueError("Unexpected symlinked source notice")
                if item.is_file() and item.name not in {
                    "PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
                    "THIRD_PARTY_COMPONENTS.md",
                }:
                    shutil.copy2(item, current_licenses/item.name)
            if not (current_licenses/"python-distribution-notices").is_dir():
                raise ValueError("Preview runtime license receipts missing")
        info = app/"Contents/Info.plist"
        with info.open("rb") as stream:
            plist = plistlib.load(stream)
        if plist.get("CFBundleIdentifier") != "com.anythingplays.preview31":
            raise ValueError("3.1 candidate could overwrite stable 3.0 app")
        verify_bundle(app, "macos", check_native=True)
        command("codesign", "--force", "--sign", "-", app)
        command("codesign", "--verify", "--verbose=2", app)
        verify_bundle(app, "macos", check_native=True)

        output.mkdir(parents=True, exist_ok=True)
        filename = "AnythingPlays-3.1.0-preview2-macos-" + arch + ".dmg"
        dmg = output/filename
        command("hdiutil", "create", "-volname", "Anything Plays 3.1 Full QA",
                "-srcfolder", app, "-ov", "-format", "UDZO", dmg)
        with mount(dmg, tmp/"final-dmg"):
            final = tmp/"final-dmg/AnythingPlays31Preview.app"
            verify_bundle(final, "macos", check_native=True)
            if validate_trial_core_directory(final/"Contents/Resources/cores", ".dylib") != original:
                raise ValueError("Final macOS DMG changed original source binaries")
        report = {
            "status": "UNRELEASED_3_1_FULL_MACOS_QA",
            "public_release_approved": False,
            "target": "macos-" + arch,
            "original_stable_sha256": stable_sha,
            "original_preview_sha256": digest(preview),
            "installer": filename, "sha256": digest(dmg),
            "size_bytes": dmg.stat().st_size,
            "original_source_core_families": original["total_source_built_core_families"],
            "native_core_count": 11,
            "console_profiles": 18,
            "notarized": False,
            "physical_controller_accepted": False,
        }
        (output/"FULL_MACOS_QA_RECEIPT.json").write_text(
            json.dumps(report, indent=2)+"\n", "utf-8")
        print(json.dumps(report, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arch", choices=("arm64", "x64"), required=True)
    for name in ("stable", "preview", "checksums", "receipt", "output"):
        p.add_argument("--"+name, type=Path, required=True)
    a = p.parse_args()
    build(a.arch, *(getattr(a, x).resolve() for x in (
        "stable", "preview", "checksums", "receipt", "output")))


if __name__ == "__main__":
    main()
