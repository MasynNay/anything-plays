"""Verify genuine changed-source pygame.base in exact clean final Windows 3.1.

This stages only a disposable copy of the source-verified complete 18-console
final installer. The original EXE and installed native files remain unchanged.
One extension replacement is NOT full LGPL/relinking or distribution approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from tools.build_v31_modified_pygame_probe import PYGAME_COMMIT, PROBE_VALUE
from tools.build_v31_modified_pygame_windows import (
    OUTPUT_NAME, PINNED_CHANGED_C_SHA256, validate_pe_amd64,
)
from tools.inventory_v31_final_native import digest

APP_SOURCE_SHA = "104b96621ec4cb8dc39fde8c3fe96fc854c406ed"
INSTALLER_NAME = "AnythingPlaysSetup-3.1.0.exe"
TARGET = "windows-x64"
ORIGINAL_WHEEL = "pygame_ce-2.5.8-cp313-cp313-win_amd64.whl"
ORIGINAL_WHEEL_SHA = "f495b0eb7a5c54c59da58e964bc7f68073c3f43cf307729fd48309104a04c190"
RELATIVE = Path("_internal/pygame/base.cp313-win_amd64.pyd")
STATUS = "CLEAN_FINAL_WINDOWS_PYGAME_CHANGED_SOURCE_STAGED_ONLY"


def _regular(path, minimum=1, maximum=2 * 1024 ** 3):
    path = Path(path)
    if (not path.is_file() or path.is_symlink()
            or not minimum <= path.stat().st_size <= maximum):
        raise ValueError("Missing, linked or incorrectly sized exact native input: " + str(path))


def stage(*, bundle, installer, receipt, audit, original_wheel,
          source_receipt, compiled, destination):
    bundle, installer, original_wheel, compiled, destination = map(
        Path, (bundle, installer, original_wheel, compiled, destination))
    if not bundle.is_dir() or bundle.is_symlink():
        raise ValueError("Expected extracted original full Windows app")
    _regular(installer, 1024 * 1024)
    _regular(original_wheel, 1_000_000, 70 * 1024 * 1024)
    _regular(compiled, 25_000, 25 * 1024 * 1024)
    if installer.name != INSTALLER_NAME:
        raise ValueError("Not original clean final Windows 3.1 setup")
    original = bundle / RELATIVE
    _regular(original, 25_000, 25 * 1024 * 1024)
    expected = {
        "target": TARGET,
        "installer": INSTALLER_NAME,
        "sha256": digest(installer),
        "source_preview_revision": APP_SOURCE_SHA,
        "identity_channel": "final_candidate",
        "settings_namespace": "anything-plays-31",
        "native_core_count": 11,
        "console_profiles": 18,
        "status": "PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA",
        "public_release_approved": False,
        "final_release_approved": False,
    }
    for key, val in expected.items():
        if type(receipt.get(key)) is not type(val) or receipt[key] != val:
            raise ValueError("Not exact clean-source final Windows receipt: " + key)
    if (audit.get("target") != TARGET
            or audit.get("source_revision") != APP_SOURCE_SHA
            or audit.get("status") !=
            "UNAPPROVED_EXACT_FINAL_3_1_NATIVE_AND_NOTICE_INVENTORY"
            or audit.get("public_release_approved") is not False):
        raise ValueError("Missing exact final Windows original native inventory")
    found = [e for e in audit.get("native_files", [])
             if isinstance(e, dict) and e.get("path") == RELATIVE.as_posix()]
    if len(found) != 1 or found[0].get("sha256") != digest(original):
        raise ValueError("Not SHA-audited frozen final pygame native")
    if (original_wheel.name != ORIGINAL_WHEEL
            or digest(original_wheel) != ORIGINAL_WHEEL_SHA):
        raise ValueError("Not checksum-pinned genuine upstream pygame wheel")
    with zipfile.ZipFile(original_wheel) as archive:
        members = [e for e in archive.infolist()
                   if e.filename == "pygame/base.cp313-win_amd64.pyd"
                   and not e.is_dir()]
        if len(members) != 1:
            raise ValueError("Original upstream pygame.base is not unique")
        upstream = archive.read(members[0])
    original_sha = digest(original)
    if hashlib.sha256(upstream).hexdigest() != original_sha:
        raise ValueError("Final frozen pygame native not the actual upstream wheel")
    if (source_receipt.get("original_source_revision") != PYGAME_COMMIT
            or source_receipt.get("patched_base_c_sha256") != PINNED_CHANGED_C_SHA256
            or source_receipt.get("patched_base_c_sha256") ==
               source_receipt.get("original_base_c_sha256")
            or source_receipt.get("expected_modified_native_method") != "_ap31_relink_probe"
            or source_receipt.get("expected_modified_native_result") != PROBE_VALUE
            or source_receipt.get("not_official_unmodified_pygame_wheel") is not True
            or source_receipt.get("full_lgpl_compliance_approved") is not False
            or source_receipt.get("stable_3_1_release_approved") is not False):
        raise ValueError("Unverified changed original pygame C source")
    if compiled.name != OUTPUT_NAME:
        raise ValueError("Wrong compiled CPython Windows ABI")
    validate_pe_amd64(compiled)
    modified_sha = digest(compiled)
    if modified_sha == original_sha:
        raise ValueError("No actual C-native source replacement")
    if (destination.exists() or destination.is_symlink()
            or destination.resolve().is_relative_to(bundle.resolve())
            or bundle.resolve().is_relative_to(destination.resolve())
            or compiled.resolve().is_relative_to(bundle.resolve())):
        raise ValueError("Only new out-of-tree disposable Windows app copies")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, destination, symlinks=True)
    copy = destination / RELATIVE
    if not copy.is_file() or copy.is_symlink() or digest(copy) != original_sha:
        raise ValueError("Original copied native mismatch")
    shutil.copyfile(compiled, copy)
    if digest(copy) != modified_sha or digest(original) != original_sha:
        raise ValueError("Changed native corrupted or original app touched")
    return {
        "schema_version": 1,
        "status": STATUS,
        "target": TARGET,
        "source_app_commit": APP_SOURCE_SHA,
        "installer": INSTALLER_NAME,
        "installer_sha256": expected["sha256"],
        "original_pygame_source_commit": PYGAME_COMMIT,
        "original_wheel_sha256": ORIGINAL_WHEEL_SHA,
        "source_c_sha256": PINNED_CHANGED_C_SHA256,
        "native_replacement_path": RELATIVE.as_posix(),
        "original_native_sha256": original_sha,
        "compiled_changed_native_sha256": modified_sha,
        "source_modified_native_distinct_pe_amd64": True,
        "original_installer_and_frozen_app_unchanged": True,
        "real_modified_c_method_executed": False,
        "actual_full_final_frozen_tk_booted": False,
        "real_controller_or_camera_tested": False,
        "all_lgpl_native_relinking_verified": False,
        "corresponding_source_review_complete": False,
        "public_release_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("bundle", "installer", "receipt", "audit", "original-wheel",
                "source-receipt", "compiled", "destination", "output"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    report = stage(bundle=a.bundle, installer=a.installer,
                   receipt=json.loads(a.receipt.read_text("utf-8")),
                   audit=json.loads(a.audit.read_text("utf-8")),
                   original_wheel=a.original_wheel,
                   source_receipt=json.loads(a.source_receipt.read_text("utf-8")),
                   compiled=a.compiled, destination=a.destination)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print("Original complete final Windows installer unchanged; modified C native staged in separate copy.")


if __name__ == "__main__":
    main()
