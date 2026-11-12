"""Test actual source-modified pygame.base replacement in a clean final Linux 3.1 app.

This validates ONE LGPL native extension from the original, immutable
full 18-console 3.1.0 installer. It is not third-party license signoff.
Original binaries and public releases are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from tools.build_v31_modified_pygame_probe import PYGAME_COMMIT, PROBE_VALUE
from tools.inventory_v31_final_native import digest

SOURCE_SHA = "104b96621ec4cb8dc39fde8c3fe96fc854c406ed"
INSTALLER_NAME = "anything-plays-31_3.1.0_amd64.deb"
WHEEL_NAME = "pygame_ce-2.5.8-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl"
WHEEL_SHA256 = "5bb966b610e161a8f6d908b4c62ef3a1f3e922bc7bed73bd70a3e15dc780b90e"
BASENAME = "base.cpython-313-x86_64-linux-gnu.so"
RELATIVE = Path("_internal/pygame") / BASENAME


def _file(path: Path, minimum: int, maximum: int):
    if path.is_symlink() or not path.is_file() or not minimum <= path.stat().st_size <= maximum:
        raise ValueError("Missing, linked or incorrectly sized file: " + str(path))


def stage(*, bundle, installer, receipt, wheel, source_change, compiled, destination):
    bundle, installer, wheel = map(Path, (bundle, installer, wheel))
    compiled, destination = map(Path, (compiled, destination))
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError("Extracted original full app must be a real directory")
    _file(installer, 1024 * 1024, 2 * 1024**3)
    if installer.name != INSTALLER_NAME:
        raise ValueError("Incorrect full final Linux installer")
    exact = {
        "target": "linux-x64",
        "installer": INSTALLER_NAME,
        "sha256": digest(installer),
        "source_preview_revision": SOURCE_SHA,
        "identity_channel": "final_candidate",
        "settings_namespace": "anything-plays-31",
        "native_core_count": 11,
        "console_profiles": 18,
        "status": "PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA",
        "public_release_approved": False,
        "final_release_approved": False,
    }
    for key, expected in exact.items():
        if type(receipt.get(key)) is not type(expected) or receipt[key] != expected:
            raise ValueError("Not the checked original clean full final receipt: " + key)
    if (source_change.get("original_source_revision") != PYGAME_COMMIT
            or source_change.get("expected_modified_native_method") != "_ap31_relink_probe"
            or source_change.get("expected_modified_native_result") != PROBE_VALUE
            or source_change.get("not_official_unmodified_pygame_wheel") is not True
            or source_change.get("full_lgpl_compliance_approved") is not False
            or source_change.get("stable_3_1_release_approved") is not False
            or source_change.get("original_base_c_sha256")
               == source_change.get("patched_base_c_sha256")):
        raise ValueError("Unverified actual source modification receipt")
    original = bundle / RELATIVE
    _file(original, 100_000, 20 * 1024**2)
    _file(compiled, 100_000, 20 * 1024**2)
    if compiled.name != BASENAME:
        raise ValueError("Wrong CPython 3.13 compiled extension")
    if (original.resolve().is_relative_to(compiled.resolve())
            or compiled.resolve().is_relative_to(original.resolve())):
        raise ValueError("Source-compiled replacement is not independent")
    _file(wheel, 1_000_000, 70 * 1024**2)
    if wheel.name != WHEEL_NAME or digest(wheel) != WHEEL_SHA256:
        raise ValueError("Official original pygame CE wheel differs from pinned source")
    with zipfile.ZipFile(wheel) as archive:
        matches = [entry for entry in archive.infolist()
                   if entry.filename == "pygame/" + BASENAME and not entry.is_dir()]
        if len(matches) != 1:
            raise ValueError("Unambiguous official pygame.base is missing")
        donor = archive.read(matches[0])
    original_sha = digest(original)
    if hashlib.sha256(donor).hexdigest() != original_sha:
        raise ValueError("Frozen final original pygame.base does not match official wheel")
    new_sha = digest(compiled)
    if new_sha == original_sha:
        raise ValueError("No genuine native source modification")
    if (destination.exists() or destination.is_symlink()
            or destination.resolve().is_relative_to(bundle.resolve())
            or bundle.resolve().is_relative_to(destination.resolve())):
        raise ValueError("Only fresh, out-of-tree disposable installation copies")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, destination, symlinks=True)
    replaced = destination / RELATIVE
    if (replaced.is_symlink() or not replaced.is_file()
            or digest(replaced) != original_sha):
        raise ValueError("Copied final original extension changed unexpectedly")
    shutil.copyfile(compiled, replaced)
    replaced.chmod(0o755)
    if digest(replaced) != new_sha or digest(original) != original_sha:
        raise ValueError("Replacement bytes altered or original full app was modified")
    return {
        "schema_version": 1,
        "status": "CLEAN_FINAL_3_1_LINUX_CHANGED_SOURCE_PYGAME_BASE_STAGED_NOT_LEGAL_APPROVAL",
        "target": "linux-x64",
        "source_app_revision": SOURCE_SHA,
        "installer": INSTALLER_NAME,
        "installer_sha256": digest(installer),
        "original_upstream_pygame_sha": PYGAME_COMMIT,
        "official_wheel_sha256": digest(wheel),
        "original_extension_sha256": original_sha,
        "compiled_changed_source_extension_sha256": new_sha,
        "native_replacement_path": RELATIVE.as_posix(),
        "source_c_sha256": source_change["patched_base_c_sha256"],
        "original_installer_unchanged": True,
        "changed_c_method_executed": False,
        "actual_frozen_final_tk_booted": False,
        "physical_controller_tested": False,
        "corresponding_source_review_complete": False,
        "lgpl_relinking_approved": False,
        "public_release_approved": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("bundle", "installer", "receipt", "wheel", "source-change",
                "compiled", "destination", "output"):
        p.add_argument("--" + key, required=True, type=Path)
    a = p.parse_args(argv)
    for name in ("receipt", "source_change"):
        file = getattr(a, name)
        _file(file, 1, 1024 * 1024)
    result = stage(bundle=a.bundle, installer=a.installer,
                   receipt=json.loads(a.receipt.read_text("utf-8")),
                   wheel=a.wheel,
                   source_change=json.loads(a.source_change.read_text("utf-8")),
                   compiled=a.compiled, destination=a.destination)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    print("Actual clean final Linux full installer copied; changed pygame C native staged.")


if __name__ == "__main__":
    main()
