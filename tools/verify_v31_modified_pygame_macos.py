"""Safely stage *genuinely C-source modified* pygame extension in a Mac RC1 copy.

Authenticated original signed DMG remains read-only. Only independent
external disposable copy is modified. The workflow then adjusts internal
rpaths, ad-hoc re-signs, imports the patched C-native method and boots
the original frozen 18-console GUI.

This test is technical evidence, not complete LGPL Section 6 compliance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from tools.build_v31_modified_pygame_probe import PYGAME_COMMIT, PROBE_VALUE
from tools.probe_v31_macos_lgpl_replacement import (
    validate_inputs, FROZEN_PATH, ARCHES,
)
from tools.inspect_v31_macos_text_provenance import executable_text_fingerprint
from tools.prepare_v31_sdl_source_review import RC_APP_COMMIT


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stage(original_app, installer, receipt, audit, wheel,
          compiled, source_receipt, target, destination):
    if target not in ARCHES:
        raise ValueError("Expected actual Mac ARM or Intel RC1")
    original, original_wheel_slice, _ = validate_inputs(
        original_app, installer, receipt, audit, wheel, target)
    if (source_receipt.get("original_source_revision") != PYGAME_COMMIT
            or source_receipt.get("expected_modified_native_method")
            != "_ap31_relink_probe"
            or source_receipt.get("expected_modified_native_result") != PROBE_VALUE
            or source_receipt.get("full_lgpl_compliance_approved") is not False
            or source_receipt.get("stable_3_1_release_approved") is not False
            or source_receipt.get("original_base_c_sha256")
            == source_receipt.get("patched_base_c_sha256")
            or source_receipt.get("not_official_unmodified_pygame_wheel") is not True):
        raise ValueError("No verified actual C-source modification manifest")
    compiled, destination, original_app = (
        Path(compiled), Path(destination), Path(original_app))
    if (not compiled.is_file() or compiled.is_symlink()
            or not compiled.name.startswith("base.cpython-313-")
            or not compiled.name.endswith(".so")
            or not 8_192 <= compiled.stat().st_size <= 20 * 1024 * 1024):
        raise ValueError("No actual compiled CPython 3.13 Mac native extension")
    compiled_data = compiled.read_bytes()
    compiled_text = executable_text_fingerprint(compiled_data, ARCHES[target])
    original_text = executable_text_fingerprint(original.read_bytes(), ARCHES[target])
    if (not compiled_text or not original_text
            or compiled_text == original_text
            or sha(compiled) == sha(original)
            or hashlib.sha256(original_wheel_slice).digest()
            == hashlib.sha256(compiled_data).digest()):
        raise ValueError("Source-compiled native not genuinely different from original")
    if (destination.exists() or destination.is_symlink()
            or destination.resolve().is_relative_to(original_app.resolve())
            or original_app.resolve().is_relative_to(destination.resolve())):
        raise ValueError("Must use new location outside original readonly DMG")
    destination.parent.mkdir(parents=True, exist_ok=True)
    original_hash = sha(original)
    shutil.copytree(original_app, destination, symlinks=True)
    copied = destination / FROZEN_PATH
    if (not copied.is_file() or copied.is_symlink()
            or sha(copied) != original_hash):
        raise ValueError("Copied Mac pygame extension did not match original")
    copied.write_bytes(compiled_data)
    copied.chmod(0o755)
    if sha(copied) != sha(compiled) or sha(original) != original_hash:
        raise ValueError("Original signed Mac RC1 modified or copied output corrupted")
    return {
        "schema_version": 1,
        "status": "PUBLIC_RC1_MACOS_SOURCE_MODIFIED_PYGAME_C_NATIVE_STAGED_ONLY",
        "target": target,
        "original_app_source_commit": RC_APP_COMMIT,
        "original_pygame_ce_source_commit": PYGAME_COMMIT,
        "modified_c_source_sha256": source_receipt["patched_base_c_sha256"],
        "compiled_extension_sha256": sha(compiled),
        "original_signed_extension_sha256": original_hash,
        "compiled_native_executable_text_sha256": compiled_text["sha256"],
        "original_signed_executable_text_sha256": original_text["sha256"],
        "source_modified_c_binary_verified_different": True,
        "source_modified_c_method": "_ap31_relink_probe",
        "actual_modified_method_invoked": False,
        "copied_app_ad_hoc_codesign_verified": False,
        "copied_original_frozen_rc1_tk_boot_verified": False,
        "unmodified_original_mac_rc1_verified": True,
        "real_physical_controller_tested": False,
        "complete_lgpl_section_6_source_and_relinking_approved": False,
        "stable_3_1_release_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", choices=sorted(ARCHES), required=True)
    for key in ("bundle","installer","receipt","audit","wheel",
                "compiled","source-receipt","destination","output"):
        p.add_argument("--"+key, type=Path, required=True)
    args=p.parse_args()
    r=stage(
        args.bundle, args.installer,
        json.loads(args.receipt.read_text("utf-8")),
        json.loads(args.audit.read_text("utf-8")),
        args.wheel, args.compiled,
        json.loads(args.source_receipt.read_text("utf-8")),
        args.target, args.destination,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(r,indent=2)+"\n","utf-8")
    print("Copied modified native C extension to Mac disposable app; original readonly.")


if __name__=="__main__":
    main()
