"""Prepare a disposable original-wheel pygame extension replacement in full 3.1 RC1.

The genuine mounted DMG remains read-only. Only a new independent app copy
is changed. An exact upstream pygame-ce wheel provides the donor native
extension; the CI workflow must re-sign and boot the copy separately.

A successful copy/sign/launch establishes a limited ability to swap an
ABI-compatible *unmodified upstream* extension, NOT a recompiled user
modification, full LGPL 2.1 section 6 compliance, complete corresponding
source, or stable 3.1.0 release approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from tools.inspect_v31_macos_text_provenance import (
    executable_text_fingerprint, thin_slice
)
from tools.prepare_v31_sdl_source_review import WHEELS, RC_APP_COMMIT
from tools.verify_v31_installed_ui_smoke import TARGETS

ARCHES = {"macos-arm64": "arm64", "macos-x64": "x86_64"}
FROZEN_PATH = "Contents/Frameworks/pygame/base.cpython-313-darwin.so"
WHEEL_MEMBER = "pygame/base.cpython-313-darwin.so"
MAX_DONOR_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_BYTES = 40 * 1024 * 1024


def digest(path):
    hash_object = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hash_object.update(chunk)
    return hash_object.hexdigest()


def validate_inputs(bundle, installer, receipt, audit, wheel, target):
    """Require genuinely pinned signed RC and official pygame wheel inputs."""
    if target not in ARCHES:
        raise ValueError("Unknown signed 3.1 macOS platform")
    bundle, installer, wheel = Path(bundle), Path(installer), Path(wheel)
    if (not bundle.is_dir() or bundle.is_symlink()
            or installer.is_symlink() or not installer.is_file()
            or wheel.is_symlink() or not wheel.is_file()):
        raise ValueError("Original RC installer, bundle or official wheel missing")
    state, expected_dmg = TARGETS[target]
    if (receipt.get("target") != target
            or receipt.get("status") != state
            or receipt.get("source_preview_revision") != RC_APP_COMMIT
            or receipt.get("installer") != expected_dmg
            or installer.name != expected_dmg
            or receipt.get("sha256") != digest(installer)
            or receipt.get("native_core_count") != 11
            or receipt.get("console_profiles") != 18
            or receipt.get("public_release_approved") is not False
            or receipt.get("final_release_approved") is not False):
        raise ValueError("Original installer is not the pinned QA RC1")
    if (audit.get("target") != target
            or audit.get("status") != "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY"
            or audit.get("pygame_version") != "2.5.8"
            or audit.get("pygame_distribution") != "pygame-ce"
            or audit.get("redistribution_approved") is not False
            or audit.get("lgpl_relinking_reviewed") is not False):
        raise ValueError("Not the original unapproved pygame SDL native inventory")
    originals = [v for v in audit.get("native_candidates", [])
                 if isinstance(v, dict) and v.get("path") == FROZEN_PATH]
    if len(originals) != 1:
        raise ValueError("Expected exactly one original frozen LGPL extension")
    original = bundle / FROZEN_PATH
    if (not original.is_file()
            or not original.resolve().is_relative_to(bundle.resolve())
            or digest(original) != originals[0].get("sha256")):
        raise ValueError("Installed pygame extension is not the original signed bytes")
    name, pinned_hash = WHEELS[target]
    if (wheel.name != name or wheel.stat().st_size < 1_000_000
            or wheel.stat().st_size > MAX_ARCHIVE_BYTES
            or digest(wheel) != pinned_hash):
        raise ValueError("Official tagged pygame-ce 2.5.8 wheel hash mismatch")
    with zipfile.ZipFile(wheel) as archive:
        members = archive.infolist()
        matches = [m for m in members if m.filename == WHEEL_MEMBER]
        if (len(matches) != 1 or matches[0].file_size < 10_000
                or matches[0].file_size > MAX_DONOR_BYTES):
            raise ValueError("Missing correct original wheel pygame.base extension")
        donor = thin_slice(archive.read(matches[0]), ARCHES[target])
    if not donor or len(donor) > MAX_DONOR_BYTES:
        raise ValueError("Missing official pygame native code for target CPU")
    donor_text = executable_text_fingerprint(donor, ARCHES[target])
    original_text = executable_text_fingerprint(original.read_bytes(), ARCHES[target])
    if (not donor_text or donor_text != original_text):
        raise ValueError("Donor not compatible with the exact installed RC1 source code")
    return original, donor, original_text


def stage_replacement(bundle, installer, receipt, audit, wheel, target, destination):
    """Make a new, isolated app copy, never mutate the mounted original."""
    original, donor, original_text = validate_inputs(
        bundle, installer, receipt, audit, wheel, target)
    destination, bundle = Path(destination), Path(bundle)
    if (destination.exists() or destination.is_symlink()
            or destination.resolve().is_relative_to(bundle.resolve())
            or bundle.resolve().is_relative_to(destination.resolve())):
        raise ValueError("Replacement must use a fresh external app-copy location")
    destination.parent.mkdir(parents=True, exist_ok=True)
    original_hash = digest(original)
    shutil.copytree(bundle, destination, symlinks=True)
    copy = destination / FROZEN_PATH
    if (not copy.is_file() or copy.is_symlink()
            or digest(copy) != original_hash):
        raise ValueError("Disposable copy did not preserve original signed native bytes")
    copy.write_bytes(donor)
    copy.chmod(0o755)
    if digest(copy) != hashlib.sha256(donor).hexdigest():
        raise ValueError("Copied extension does not equal exact official wheel slice")
    if digest(original) != original_hash:
        raise ValueError("Original readonly DMG was modified")
    return {
        "schema_version": 1,
        "status": "PUBLIC_3_1_RC1_DISPOSABLE_MACOS_UPSTREAM_PYGAME_EXTENSION_SWAP_STAGED",
        "target": target,
        "app_source_commit": RC_APP_COMMIT,
        "installer": Path(installer).name,
        "installer_sha256": digest(installer),
        "donor_official_pygame_wheel_sha256": WHEELS[target][1],
        "native_relative_path": FROZEN_PATH,
        "donor_wheel_member": WHEEL_MEMBER,
        "original_signed_extension_sha256": original_hash,
        "original_unmodified_after_staging": True,
        "upstream_wheel_slice_sha256": digest(copy),
        "original_and_upstream_text_section_equal": True,
        "executable_text_section": original_text,
        "re_signed_modified_app": False,
        "frozen_app_startup_after_swap_verified": False,
        "modified_pygame_source_compiled_and_tested": False,
        "lgpl_replacement_and_relinking_compliance_approved": False,
        "complete_corresponding_source_approved": False,
        "stable_3_1_release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "installer", "receipt", "audit",
                 "wheel", "destination", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--target", choices=sorted(ARCHES), required=True)
    a = parser.parse_args()
    r = json.loads(a.receipt.read_text("utf-8"))
    audit = json.loads(a.audit.read_text("utf-8"))
    result = stage_replacement(
        a.bundle, a.installer, r, audit, a.wheel, a.target, a.destination)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    print("Copy only: imported exactly pinned pygame base extension from official wheel.")
    print("Original app and DMG unchanged; signing and frozen startup NOT YET TESTED.")


if __name__ == "__main__":
    main()
