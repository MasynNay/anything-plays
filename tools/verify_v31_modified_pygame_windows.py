"""Validate and stage genuine modified LGPL C native extension into Windows RC1 copy.

Original full Windows 3.1 RC1 Inno installer and original extracted
app remain unchanged. The exact official pygame-ce wheel proves original
native identity; the source-compiled DLL must be distinct PE x64 bytes.
The Windows workflow separately imports and invokes the modified method,
then launches the complete copied 18-console frozen desktop.

No LGPL legal-compliance or final stable-release approval is inferred.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from tools.build_v31_modified_pygame_probe import PYGAME_COMMIT, PROBE_VALUE
from tools.build_v31_modified_pygame_windows import (
    OUTPUT_NAME, PINNED_CHANGED_C_SHA256, validate_pe_amd64,
)
from tools.probe_v31_linux_windows_pygame_replacement import (
    validate as validate_original, digest,
)
from tools.prepare_v31_sdl_source_review import RC_APP_COMMIT

PLATFORM = "windows-x64"


def stage(bundle, installer, receipt, audit, original_wheel,
          source_manifest, compiled, destination):
    """Fail closed before modifying an isolated directory."""
    original_native, official_wheel_bytes, wheel_member = validate_original(
        bundle, installer, receipt, audit, original_wheel, PLATFORM)
    if (source_manifest.get("original_source_revision") != PYGAME_COMMIT
            or source_manifest.get("patched_base_c_sha256") != PINNED_CHANGED_C_SHA256
            or source_manifest.get("expected_modified_native_method")
            != "_ap31_relink_probe"
            or source_manifest.get("expected_modified_native_result") != PROBE_VALUE
            or source_manifest.get("not_official_unmodified_pygame_wheel") is not True
            or source_manifest.get("full_lgpl_compliance_approved") is not False
            or source_manifest.get("stable_3_1_release_approved") is not False):
        raise ValueError("Cannot prove exact modified upstream pygame source")
    if (source_manifest.get("patched_base_c_sha256") ==
            source_manifest.get("original_base_c_sha256")):
        raise ValueError("No actual modification of LGPL C source")
    bundle, compiled, destination = Path(bundle), Path(compiled), Path(destination)
    if (compiled.is_symlink() or not compiled.is_file()
            or compiled.name != OUTPUT_NAME
            or not 25_000 <= compiled.stat().st_size <= 25 * 1024 * 1024):
        raise ValueError("Missing or unexpected source-compiled Windows native extension")
    validate_pe_amd64(compiled)
    original_sha = digest(original_native)
    compiled_sha = digest(compiled)
    import hashlib
    official_sha = hashlib.sha256(official_wheel_bytes).hexdigest()
    if original_sha != official_sha:
        raise ValueError("Original frozen Windows native does not match official wheel")
    if compiled_sha == original_sha:
        raise ValueError("Compiled C output was merely the original wheel binary")
    if (destination.exists() or destination.is_symlink()
            or destination.resolve().is_relative_to(bundle.resolve())
            or bundle.resolve().is_relative_to(destination.resolve())):
        raise ValueError("Only a new disposable location outside original RC1 is allowed")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, destination, symlinks=True)
    relative = original_native.relative_to(bundle)
    copy = destination / relative
    if copy.is_symlink() or not copy.is_file() or digest(copy) != original_sha:
        raise ValueError("Copied native is not the original verified frozen one")
    copy.write_bytes(compiled.read_bytes())
    if (digest(copy) != compiled_sha or digest(original_native) != original_sha):
        raise ValueError("Original RC1 or source-compiled replacement was corrupted")
    return {
        "schema_version": 1,
        "status": "AUTHENTIC_RC1_WINDOWS_SOURCE_MODIFIED_PYGAME_EXTENSION_STAGED_ONLY",
        "platform": PLATFORM,
        "original_source_commit": RC_APP_COMMIT,
        "original_pygame_source_commit": PYGAME_COMMIT,
        "modified_source_sha256": PINNED_CHANGED_C_SHA256,
        "source_modified_c_extension_name": OUTPUT_NAME,
        "modified_native_method": "_ap31_relink_probe",
        "original_wheel_member": wheel_member,
        "original_native_sha256": original_sha,
        "modified_compiled_native_sha256": compiled_sha,
        "native_replacement_path": relative.as_posix(),
        "source_modified_native_is_distinct_pe_amd64": True,
        "original_signed_installer_and_frozen_app_untouched": True,
        "modified_native_method_executed_from_copied_app": False,
        "copied_original_rc1_frozen_tk_gui_started": False,
        "real_physical_controller_tested": False,
        "all_lgpl_relinking_requirements_approved": False,
        "full_corresponding_source_approved": False,
        "stable_3_1_release_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("bundle", "installer", "receipt", "audit", "original-wheel",
                "source-receipt", "compiled", "destination", "output"):
        p.add_argument("--"+arg, type=Path, required=True)
    args=p.parse_args()
    report=stage(
        args.bundle,args.installer,
        json.loads(args.receipt.read_text("utf-8")),
        json.loads(args.audit.read_text("utf-8")),
        args.original_wheel,
        json.loads(args.source_receipt.read_text("utf-8")),
        args.compiled,args.destination)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n","utf-8")
    print("Exact original frozen RC1 unchanged; modified PE native staged ONLY in copy.")


if __name__ == "__main__":
    main()
