"""Safely stage genuinely source-modified pygame in the final clean 3.1 Mac app.

The exact source-built final 3.1 original signed DMG remains read-only. Only independent
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
from tools.probe_v31_macos_lgpl_replacement import FROZEN_PATH, ARCHES
from tools.inspect_v31_macos_text_provenance import (
    executable_text_fingerprint, thin_slice,
)
import zipfile

APP_SOURCE_SHA = "104b96621ec4cb8dc39fde8c3fe96fc854c406ed"
WHEEL_NAME = "pygame_ce-2.5.8-cp313-cp313-macosx_10_13_universal2.whl"
WHEEL_SHA256 = "56441a9bb75c2461750dc0e6e4a46e3833b3cf6339bfbaf16f93ecac037510f3"
EXPECTED = {
    "macos-arm64": "AnythingPlays-3.1.0-macos-arm64.dmg",
    "macos-x64": "AnythingPlays-3.1.0-macos-x64.dmg",
}


def validate_inputs(bundle, installer, receipt, audit, wheel, target):
    if target not in EXPECTED:
        raise ValueError("Unknown clean final Mac target")
    bundle, installer, wheel = map(Path, (bundle, installer, wheel))
    if (not bundle.is_dir() or bundle.is_symlink()
            or not installer.is_file() or installer.is_symlink()
            or not wheel.is_file() or wheel.is_symlink()):
        raise ValueError("Missing or linked original Mac final inputs")
    expected = {
        "target": target,
        "installer": EXPECTED[target],
        "sha256": sha(installer),
        "source_preview_revision": APP_SOURCE_SHA,
        "identity_channel": "final_candidate",
        "settings_namespace": "anything-plays-31",
        "native_core_count": 11,
        "console_profiles": 18,
        "status": "PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA",
        "public_release_approved": False,
        "final_release_approved": False,
    }
    if installer.name != EXPECTED[target]:
        raise ValueError("Wrong clean final Mac DMG filename")
    for key, value in expected.items():
        if type(receipt.get(key)) is not type(value) or receipt[key] != value:
            raise ValueError("Not exact original clean final Mac receipt: " + key)
    frozen = bundle / FROZEN_PATH
    if (not frozen.is_file() or frozen.is_symlink()
            or not frozen.resolve().is_relative_to(bundle.resolve())):
        raise ValueError("Missing original frozen pygame native extension")
    if audit.get("source_revision") != APP_SOURCE_SHA or audit.get("target") != target:
        raise ValueError("Wrong exact clean final Mac inventory source")
    matches = [x for x in audit.get("native_files", [])
               if isinstance(x, dict) and x.get("path") == FROZEN_PATH]
    if len(matches) != 1 or matches[0].get("sha256") != sha(frozen):
        raise ValueError("Not the original SHA-audited Mac pygame native extension")
    if (wheel.name != WHEEL_NAME or wheel.stat().st_size < 1_000_000
            or wheel.stat().st_size > 40 * 1024 * 1024
            or sha(wheel) != WHEEL_SHA256):
        raise ValueError("Official tagged pygame CE Mac wheel mismatched")
    with zipfile.ZipFile(wheel) as archive:
        matches = [x for x in archive.infolist()
                   if x.filename == "pygame/base.cpython-313-darwin.so"]
        if len(matches) != 1 or not 64 <= matches[0].file_size <= 20 * 1024**2:
            raise ValueError("Missing official pygame CE native Mac wheel member")
        upstream = thin_slice(archive.read(matches[0]), ARCHES[target])
    original_text = executable_text_fingerprint(frozen.read_bytes(), ARCHES[target])
    official_text = executable_text_fingerprint(upstream, ARCHES[target])
    if not original_text or original_text != official_text:
        raise ValueError("Exact final Mac pygame code sections do not match original source wheel")
    return frozen, upstream, original_text


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stage(original_app, installer, receipt, audit, wheel,
          compiled, source_receipt, target, destination):
    if target not in ARCHES:
        raise ValueError("Expected actual final Mac ARM or Intel")
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
        raise ValueError("Original signed Mac final modified or copied output corrupted")
    return {
        "schema_version": 1,
        "status": "CLEAN_FINAL_MACOS_SOURCE_MODIFIED_PYGAME_C_NATIVE_STAGED_ONLY",
        "target": target,
        "original_app_source_commit": APP_SOURCE_SHA,
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
        "copied_final_frozen_tk_boot_verified": False,
        "unmodified_original_mac_final_verified": True,
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
