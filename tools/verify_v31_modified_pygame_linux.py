"""Stage a *compiled from deliberately modified LGPL source* pygame.base in RC1.

Unlike the original upstream wheel replacement tests this must demonstrate
that generated native bytes differ from original RC1 and official pygame
wheel, while preserving original QA identities and never modifying
the original installed or published program.

The paired workflow invokes the new native method with the interpreter,
and separately boots the copied full frozen RC1 desktop. This demonstrates
limited user-source replacement, not complete LGPL 2.1 compliance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from tools.build_v31_modified_pygame_probe import PYGAME_COMMIT, PROBE_VALUE
from tools.probe_v31_linux_windows_pygame_replacement import validate, digest
from tools.prepare_v31_sdl_source_review import RC_APP_COMMIT

TARGET = "linux-x64"


def stage(bundle, installer, receipt, audit, original_wheel,
          source_patch_receipt, compiled, destination):
    """Return a receipt before executable runtime checks, never legal approval."""
    native, unmodified_wheel_bytes, original_wheel_member = validate(
        bundle, installer, receipt, audit, original_wheel, TARGET)
    if (source_patch_receipt.get("original_source_revision") != PYGAME_COMMIT
            or source_patch_receipt.get("expected_modified_native_method")
            != "_ap31_relink_probe"
            or source_patch_receipt.get("expected_modified_native_result") != PROBE_VALUE
            or source_patch_receipt.get("full_lgpl_compliance_approved") is not False
            or source_patch_receipt.get("stable_3_1_release_approved") is not False
            or not source_patch_receipt.get("not_official_unmodified_pygame_wheel")):
        raise ValueError("Missing exact source-modification manifest")
    if (source_patch_receipt.get("original_base_c_sha256")
            == source_patch_receipt.get("patched_base_c_sha256")):
        raise ValueError("Not actually modified source")
    compiled, destination, bundle = Path(compiled), Path(destination), Path(bundle)
    if (not compiled.is_file() or compiled.is_symlink()
            or compiled.stat().st_size < 100_000
            or compiled.stat().st_size > 20 * 1024 * 1024
            or not compiled.name.startswith("base.cpython-313-")
            or not compiled.name.endswith(".so")):
        raise ValueError("Expected real source-compiled CPython 3.13 native extension")
    original_hash = digest(native)
    compiled_hash = digest(compiled)
    upstream_hash = hashlib.sha256(unmodified_wheel_bytes).hexdigest()
    if original_hash != upstream_hash:
        raise ValueError("Original Linux RC extension must match pinned official wheel")
    if compiled_hash == original_hash:
        raise ValueError("Compiled source has exactly original unmodified wheel bytes")
    if (destination.exists() or destination.is_symlink()
            or destination.resolve().is_relative_to(bundle.resolve())
            or bundle.resolve().is_relative_to(destination.resolve())):
        raise ValueError("Only a fresh disposable RC1 app location is permitted")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, destination, symlinks=True)
    replaced = destination / native.relative_to(bundle)
    if (not replaced.is_file() or replaced.is_symlink()
            or digest(replaced) != original_hash):
        raise ValueError("Disposable install did not retain original native extension")
    replaced.write_bytes(compiled.read_bytes())
    replaced.chmod(0o755)
    if (digest(replaced) != compiled_hash or digest(native) != original_hash):
        raise ValueError("Copied source-compiled bytes lost or original was modified")
    return {
        "schema_version": 1,
        "status": "PUBLIC_3_1_RC1_LINUX_SOURCE_MODIFIED_PYGAME_NATIVE_STAGED_ONLY",
        "original_source_commit": PYGAME_COMMIT,
        "source_app_commit": RC_APP_COMMIT,
        "source_file_modified": "src_c/base.c",
        "modified_source_sha256": source_patch_receipt["patched_base_c_sha256"],
        "original_upstream_wheel_member": original_wheel_member,
        "original_native_sha256": original_hash,
        "compiled_modified_native_sha256": compiled_hash,
        "native_replacement_path": native.relative_to(bundle).as_posix(),
        "compiled_binary_is_not_original_wheel_binary": True,
        "original_installer_untouched": True,
        "source_modified_method_observed_by_native_python": False,
        "real_frozen_app_gui_boot_after_source_swap": False,
        "real_controller_tested": False,
        "full_corresponding_source_available": False,
        "full_lgpl_2_1_relinking_approved": False,
        "stable_3_1_release_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("bundle", "installer", "receipt", "audit", "original-wheel",
                "source-patch-receipt", "compiled", "destination", "output"):
        p.add_argument("--" + key, required=True, type=Path)
    a = p.parse_args()
    r = stage(a.bundle, a.installer,
              json.loads(a.receipt.read_text("utf-8")),
              json.loads(a.audit.read_text("utf-8")),
              a.original_wheel,
              json.loads(a.source_patch_receipt.read_text("utf-8")),
              a.compiled, a.destination)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(r, indent=2) + "\n", "utf-8")
    print("Changed-source native bytes staged in copied app; actual loading still to test.")


if __name__ == "__main__":
    main()
