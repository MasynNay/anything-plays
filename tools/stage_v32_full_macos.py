"""Assemble private full-native macOS 3.2 QA DMG from public 3.1.1 cores.

Use only the exact-head newly built 3.2 frozen app, and copy only the
checksum-pinned, source-built 11-core native payload and original notices
from the matching architecture of the published v3.1.1 installer.
Technical native inventory and frozen GUI acceptance are not permission to
redistribute, a real-game compatibility claim, or Apple notarization.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tempfile

from anything_plays.v30_gpl_trial import validate_trial_core_directory
from tools.assemble_v31_full_macos import create_disk_image, mount
from tools.stage_v32_full_linux import checked_file, no_links, sha256
from tools.verify_v31_rc import validate_staged_identity
from tools.verify_v32_preview import FILES, verify as verify_minimal

ARCHITECTURES = ("arm64", "x64")
STATUS = "PRIVATE_3_2_MACOS_11_NATIVE_CORE_18_PROFILE_QA_NOT_RELEASE"
OMIT_OLD_RUNTIME_NOTICES = frozenset((
    "PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
    "THIRD_PARTY_COMPONENTS.md",
))
ORIGINAL_CORE_NOTICES = (
    "GPL-TRIAL-Supafaust-COPYING.txt",
    "GPL-TRIAL-BlastEm-COPYING.txt",
    "GPL-TRIAL-PCE-COPYING.txt",
    "MPL-TRIAL-mGBA-ORIGINAL-LICENSE.txt",
    "GPL-TRIAL-tia-ORIGINAL-SPDX.txt",
    "GPL-TRIAL-DOLPHIN-ORIGINAL-COPYING.txt",
)


def names(arch):
    if arch not in ARCHITECTURES:
        raise ValueError("Unrecognized Mac architecture")
    return (
        f"AnythingPlays-3.1.1-macos-{arch}.dmg",
        FILES[f"macos-{arch}"],
        f"AnythingPlays-3.2.0-fullqa1-macos-{arch}.dmg",
    )


def source_gate(arch, stable, preview, sums, receipt, revision):
    """Validate exact release/source installer bytes without mounting them."""
    baseline_name, preview_name, _ = names(arch)
    if not isinstance(revision, str) or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Exact 3.2 Git source revision is required")
    stable = checked_file(stable, baseline_name)
    preview = checked_file(preview, preview_name)
    sums, receipt = Path(sums), Path(receipt)
    if (sums.name != "SHA256SUMS.txt" or not sums.is_file()
            or sums.is_symlink() or not 0 < sums.stat().st_size <= 16384
            or not receipt.is_file() or receipt.is_symlink()
            or not 0 < receipt.stat().st_size <= 32768):
        raise ValueError("Missing or unsafe published SHA256SUMS/private 3.2 receipt")
    if sha256(stable) + "  " + baseline_name not in sums.read_text("utf-8").splitlines():
        raise ValueError("Published Mac 3.1.1 native package checksum mismatch")
    data = json.loads(receipt.read_text("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Private 3.2 Mac source receipt must be an object")
    required = {
        "status": "UNRELEASED_PRIVATE_QA_ONLY",
        "channel": "v32_preview",
        "version": "3.2.0-preview1",
        "target": f"macos-{arch}",
        "installer": preview_name,
        "source_revision": revision,
        "sha256": sha256(preview),
        "size_bytes": preview.stat().st_size,
        "settings_namespace": "anything-plays-32-preview",
        "bundled_console_profiles": ["gb", "gbc", "gba"],
        "bundled_core_names": ["mgba"],
        "public_release_approved": False,
        "all_18_consoles_verified": False,
        "notarized": False,
    }
    if any(type(data.get(key)) is not type(value) or data[key] != value
           for key, value in required.items()):
        raise ValueError("Incorrect exact-source 3.2 preview Mac receipt")
    return stable, preview


def full_inventory(directory):
    """Verify all source-built library bytes, including pinned Dolphin files."""
    no_links(directory)
    record = validate_trial_core_directory(directory, ".dylib")
    if (record.get("native_core_count") != 11
            or record.get("all_console_profiles") != 18
            or record.get("total_source_built_core_families") != 11
            or not record.get("source_built_dolphin")
            or not record.get("source_built_tia")
            or len(list(directory.glob("*_libretro.dylib"))) != 11):
        raise ValueError("Mac native payload lacks 11 source-built cores / 18 profiles")
    return record


def verify_identity(bundle):
    validate_staged_identity(bundle, channel="v32_preview")
    with (bundle/"Contents/Info.plist").open("rb") as inp:
        info = plistlib.load(inp)
    if (info.get("CFBundleIdentifier") != "com.anythingplays.privatepreview32"
            or info.get("CFBundleShortVersionString") != "3.2.0"
            or info.get("CFBundleVersion") != "3.2.0.1"):
        raise ValueError("Full Mac QA must retain only the separate 3.2 preview identity")


def assemble(arch, stable, preview, sums, receipt, revision, output):
    if (os.environ.get("AP_V32_PREVIEW_BUILD") != "1"
            or os.environ.get("AP_RELEASE_BUILD") == "1"
            or os.environ.get("AP_V30_APPROVED_RELEASE") == "1"):
        raise ValueError("Full Mac 3.2 staging requires private non-release flags")
    stable, preview = source_gate(arch, stable, preview, sums, receipt, revision)
    _, _, full_name = names(arch)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Private full Mac QA refuses to overwrite any output")
    with tempfile.TemporaryDirectory(prefix=f"ap32-full-{arch}-") as tmp:
        root = Path(tmp)
        with mount(stable, root/"public311"), mount(preview, root/"minimal32"):
            old_app = root/"public311/AnythingPlays31.app"
            new_app = root/"minimal32/AnythingPlays32Preview.app"
            if not old_app.is_dir() or not new_app.is_dir():
                raise ValueError("Unexpected published 3.1.1 or private 3.2 Mac app")
            # Identity and exact native mGBA source must pass BEFORE expanding.
            verify_identity(new_app)
            verify_minimal(f"macos-{arch}", preview, revision, bundle=new_app)
            original_cores = old_app/"Contents/Resources/cores"
            original_record = full_inventory(original_cores)
            original_notices = old_app/"Contents/Resources/licenses"
            no_links(original_notices)
            for filename in ORIGINAL_CORE_NOTICES:
                f = original_notices/filename
                if not f.is_file() or f.is_symlink() or f.stat().st_size < 50:
                    raise ValueError("Missing original source-core notice: " + filename)
            # The 3.2 app, settings, SDL, OpenCV and Python binaries come
            # exclusively from the current preview DMG. Framework symlinks
            # inside the NEW app must retain their intended macOS structure.
            app = root/"AnythingPlays32Preview.app"
            shutil.copytree(new_app, app, symlinks=True)
            target_cores = app/"Contents/Resources/cores"
            no_links(target_cores)
            shutil.rmtree(target_cores)
            shutil.copytree(original_cores, target_cores)
            target_notices = app/"Contents/Resources/licenses"
            no_links(target_notices)
            for f in original_notices.iterdir():
                if f.is_file() and f.name not in OMIT_OLD_RUNTIME_NOTICES:
                    shutil.copy2(f, target_notices/f.name)
            if full_inventory(target_cores) != original_record:
                raise ValueError("Copied Mac source-built core bytes changed")
            if not (target_notices/"python-distribution-notices").is_dir():
                raise ValueError("Current 3.2 Python/SDL runtime notices are missing")
            verify_identity(app)
        # Re-sign the changed app's resource seal. This is ad-hoc only;
        # neither a Developer ID signature nor notarization is claimed.
        subprocess.run(["codesign", "--force", "--sign", "-", str(app)],
                       check=True, timeout=150)
        subprocess.run(["codesign", "--verify", "--verbose=2", str(app)],
                       check=True, timeout=90)
        verify_identity(app)
        if full_inventory(app/"Contents/Resources/cores") != original_record:
            raise ValueError("Signing changed source-reviewed Mac emulator bytes")
        output.mkdir(parents=True, exist_ok=False)
        full = output/full_name
        create_disk_image(app, full, volume_name="Anything Plays 3.2 Full QA")
        with mount(full, root/"installed"):
            mounted = root/"installed/AnythingPlays32Preview.app"
            if not mounted.is_dir():
                raise ValueError("Repacked private full Mac DMG did not mount an app")
            verify_identity(mounted)
            subprocess.run(["codesign", "--verify", "--verbose=2", str(mounted)],
                           check=True, timeout=90)
            if full_inventory(mounted/"Contents/Resources/cores") != original_record:
                raise ValueError("Mounted full Mac DMG changed original native core bytes")
            if not (mounted/"Contents/MacOS/AnythingPlays").is_file():
                raise ValueError("Mounted 3.2 Mac app is missing its executable")
        record = {
            "schema_version": 1,
            "status": STATUS,
            "target": f"macos-{arch}",
            "installer": full_name,
            "installer_sha256": sha256(full),
            "source_revision": revision,
            "source_3_2_preview_sha256": sha256(preview),
            "published_3_1_1_sha256": sha256(stable),
            "native_core_count": 11,
            "console_profiles": 18,
            "native_core_bytes_preserved": True,
            "settings_namespace": "anything-plays-32-preview",
            "adhoc_signed": True,
            "notarized": False,
            "public_release_approved": False,
            "real_gameplay_tested": False,
            "physical_camera_tested": False,
            "physical_controller_tested": False,
            "all_18_consoles_gameplay_verified": False,
        }
        (output/"V32_FULL_MACOS_QA_RECEIPT.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", "utf-8",
        )
        return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arch", choices=ARCHITECTURES, required=True)
    p.add_argument("--stable", type=Path, required=True)
    p.add_argument("--preview", type=Path, required=True)
    p.add_argument("--checksums", type=Path, required=True)
    p.add_argument("--source-receipt", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = assemble(args.arch, args.stable, args.preview, args.checksums,
                      args.source_receipt, args.source_sha, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
