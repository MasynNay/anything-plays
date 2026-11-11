"""Audit a safe upstream pygame native-extension replacement on original RC1.

Supports Linux/Windows frozen onedir applications. Only a NEW disposable
copy may be modified. Original upstream wheel and installed frozen app must
match pinned original SHA-256 receipts. Replacing an identical byte-for-byte
extension is NOT proof of replacing a modified LGPL library or compliance
with LGPL 2.1 section 6. Run the separately copied app to test boot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from tools.prepare_v31_sdl_source_review import (
    WHEELS, RC_APP_COMMIT, EXPECTED_RECEIPT_STATUS, MAX_WHEEL_BYTES,
)
from tools.verify_v31_installed_ui_smoke import TARGETS

PLATFORMS = {"linux-x64": ".so", "windows-x64": ".pyd"}
COUNTS = {"linux-x64": 74, "windows-x64": 62}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_base(audit, suffix):
    """Pick only authentic audited pygame.base, not unrelated native libs."""
    entries = audit.get("native_candidates")
    if not isinstance(entries, list) or len(entries) < 10:
        raise ValueError("Incomplete frozen pygame/SDL inventory")
    matches = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Malformed native library entry")
        path = entry.get("path")
        if not isinstance(path, str):
            raise ValueError("Malformed native path")
        parts = path.split("/")
        if (path.startswith("/") or "\\" in path
                or any(p in ("", ".", "..") for p in parts)):
            raise ValueError("Unsafe native path")
        if len(parts) >= 2 and parts[-2] == "pygame" and parts[-1].startswith("base.") and parts[-1].endswith(suffix):
            matches.append(entry)
    if len(matches) != 1:
        raise ValueError("Expected exactly one audited pygame.base extension")
    return matches[0]


def validate(bundle, installer, receipt, audit, wheel, target):
    if target not in PLATFORMS:
        raise ValueError("Target must be Linux x64 or Windows x64")
    bundle, installer, wheel = Path(bundle), Path(installer), Path(wheel)
    if (not bundle.is_dir() or bundle.is_symlink()
            or not installer.is_file() or installer.is_symlink()
            or not wheel.is_file() or wheel.is_symlink()):
        raise ValueError("Missing or linked original RC1 or wheel")
    status, expected_name = TARGETS[target]
    if (receipt.get("target", target) != target
            or receipt.get("status") != status
            or receipt.get("source_preview_revision") != RC_APP_COMMIT
            or receipt.get("installer") != expected_name
            or installer.name != expected_name
            or receipt.get("sha256") != digest(installer)
            or receipt.get("console_profiles") != 18
            or receipt.get("native_core_count") != 11
            or receipt.get("public_release_approved") is not False
            or receipt.get("final_release_approved") is not False):
        raise ValueError("Incorrect frozen RC1 native installer receipt")
    if (audit.get("status") != "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY"
            or audit.get("target") != target
            or audit.get("pygame_version") != "2.5.8"
            or audit.get("pygame_distribution") != "pygame-ce"
            or audit.get("redistribution_approved") is not False
            or audit.get("lgpl_relinking_reviewed") is not False
            or len(audit.get("native_candidates", [])) != COUNTS[target]):
        raise ValueError("Incorrect or approved frozen SDL native audit")
    entry = find_base(audit, PLATFORMS[target])
    native = bundle / entry["path"]
    if (not native.is_file() or native.is_symlink()
            or not native.resolve().is_relative_to(bundle.resolve())
            or digest(native) != entry.get("sha256")):
        raise ValueError("Original frozen pygame.base not the audited bytes")
    filename, pinned_sha = WHEELS[target]
    if (wheel.name != filename or not 1_000_000 <= wheel.stat().st_size <= MAX_WHEEL_BYTES
            or digest(wheel) != pinned_sha):
        raise ValueError("Pinned official pygame wheel mismatch")
    with zipfile.ZipFile(wheel) as archive:
        entries = [e for e in archive.infolist()
                   if e.filename.startswith("pygame/base.")
                   and e.filename.endswith(PLATFORMS[target])]
        if (len(entries) != 1 or not 64 <= entries[0].file_size <= 30 * 1024 * 1024):
            raise ValueError("Missing exact upstream pygame.base wheel member")
        donor = archive.read(entries[0])
    return native, donor, entries[0].filename


def stage(bundle, installer, receipt, audit, wheel, target, destination):
    native, donor, member = validate(
        bundle, installer, receipt, audit, wheel, target)
    bundle, destination = Path(bundle), Path(destination)
    if (destination.exists() or destination.is_symlink()
            or destination.resolve().is_relative_to(bundle.resolve())
            or bundle.resolve().is_relative_to(destination.resolve())):
        raise ValueError("Only fresh out-of-tree disposable QA copies are permitted")
    destination.parent.mkdir(parents=True, exist_ok=True)
    original_sha = digest(native)
    shutil.copytree(bundle, destination, symlinks=True)
    relative = native.relative_to(bundle)
    target_native = destination / relative
    if (not target_native.is_file() or target_native.is_symlink()
            or digest(target_native) != original_sha):
        raise ValueError("Original native bytes changed while copying")
    target_native.write_bytes(donor)
    if digest(target_native) != hashlib.sha256(donor).hexdigest():
        raise ValueError("Native donor was corrupted while writing")
    if digest(native) != original_sha:
        raise ValueError("Original installed RC was modified")
    return {
        "schema_version": 1,
        "status": "PUBLIC_3_1_RC1_DISPOSABLE_LINUX_WINDOWS_ORIGINAL_WHEEL_SWAP_STAGED",
        "platform": target,
        "original_installer": Path(installer).name,
        "original_installer_sha256": digest(installer),
        "original_source_app_commit": RC_APP_COMMIT,
        "upstream_official_wheel": Path(wheel).name,
        "upstream_official_wheel_sha256": WHEELS[target][1],
        "upstream_wheel_member": member,
        "frozen_native_relative_path": relative.as_posix(),
        "original_frozen_extension_sha256": original_sha,
        "replacement_extension_sha256": digest(target_native),
        "extension_bytes_differ_from_original": digest(target_native) != original_sha,
        "original_installed_native_unchanged": True,
        "copied_frozen_app_gui_started": False,
        "user_compiled_modified_library_tested": False,
        "full_lgpl_2_1_section_6_compliance_approved": False,
        "corresponding_source_complete": False,
        "stable_3_1_release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=sorted(PLATFORMS))
    for param in ("bundle", "installer", "receipt", "audit", "wheel", "destination", "output"):
        parser.add_argument("--" + param, type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text("utf-8"))
    audit = json.loads(args.audit.read_text("utf-8"))
    report = stage(args.bundle, args.installer, receipt, audit, args.wheel,
                   args.target, args.destination)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print("Copied official wheel native extension into disposable", args.target,
          "app; original untouched; UI and LGPL compliance NOT YET approved.")


if __name__ == "__main__":
    main()
