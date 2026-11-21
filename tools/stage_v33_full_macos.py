"""Private full-native 3.3 macOS DMGs from published exact 3.2 native bytes.

Do not publish, install on user machines, or claim hardware or redistribution
approval. Ad-hoc signing and actual read-only mounted DMG verification are
necessary, but are not Apple notarization or GameCube field acceptance.
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
from tools.v33_candidate_verify import TARGETS
from tools.stage_v33_full_linux import require_private_stage

ARCHITECTURES = ("arm64", "x64")
STATUS = "PRIVATE_3_3_MACOS_11_NATIVE_CORE_18_PROFILE_QA_NOT_RELEASE"
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
        raise ValueError("Unrecognized 3.3 Mac architecture")
    return (
        f"AnythingPlays-3.2.0-macos-{arch}.dmg",
        TARGETS[f"macos-{arch}"],
        f"AnythingPlays-3.3.0-fullqa1-macos-{arch}.dmg",
    )


def source_gate(arch, stable, preview, sums, receipt, revision):
    baseline_name, preview_name, _ = names(arch)
    if type(revision) is not str or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Exact 3.3 Mac candidate source SHA required")
    stable = checked_file(stable, baseline_name)
    preview = checked_file(preview, preview_name)
    sums, receipt = Path(sums), Path(receipt)
    for path, name, limit in (
        (sums, "SHA256SUMS.txt", 16384),
        (receipt, "V33_CANDIDATE_QA_RECEIPT.json", 65536),
    ):
        if (path.name != name or not path.is_file()
                or path.is_symlink() or path.stat().st_nlink != 1
                or not 0 < path.stat().st_size <= limit):
            raise ValueError("Missing or unsafe published/3.3 QA verification")
    if sha256(stable) + "  " + baseline_name not in sums.read_text("utf-8").splitlines():
        raise ValueError("Published 3.2 Mac native installer SHA256 mismatch")
    data = json.loads(receipt.read_text("utf-8"))
    expected = {
        "format": "anything-plays-v33-owner-qa",
        "target": f"macos-{arch}",
        "source_sha": revision,
        "channel": "v33_candidate",
        "version": "3.3.0-qa",
        "settings_namespace": "anything-plays-33-candidate",
        "installer_filename": preview_name,
        "installer_sha256": sha256(preview),
        "bundled_core_names": ["mgba_libretro.dylib"],
        "bundled_core_count": 1,
        "public_release_approved": False,
        "hardware_input_tested": False,
        "physical_camera_tested": False,
        "gamecube_bundled": False,
        "full_18_console_gameplay_tested": False,
        "installer_fully_tested_on_real_host": False,
    }
    if type(data) is not dict or data != expected:
        raise ValueError("Not the exact reviewed private 3.3 Mac source candidate")
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
    validate_staged_identity(bundle, channel="v33_candidate")
    with (bundle / "Contents/Info.plist").open("rb") as inp:
        info = plistlib.load(inp)
    if (info.get("CFBundleIdentifier") != "com.anythingplays.privateqa33"
            or info.get("CFBundleShortVersionString") != "3.3.0"
            or info.get("CFBundleVersion") != "3.3.0.1"):
        raise ValueError("Mac 3.3 QA app cannot share a public stable identity")


def assemble(arch, stable, preview, sums, receipt, revision, output):
    require_private_stage()
    stable, preview = source_gate(arch, stable, preview, sums, receipt, revision)
    _, _, full_name = names(arch)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Private full Mac QA refuses to overwrite any output")
    with tempfile.TemporaryDirectory(prefix=f"ap33-full-{arch}-") as tmp:
        root = Path(tmp)
        with mount(stable, root/"public32"), mount(preview, root/"minimal33"):
            old_app = root/"public32/AnythingPlays31.app"
            new_app = root/"minimal33/AnythingPlays33Candidate.app"
            if not old_app.is_dir() or not new_app.is_dir():
                raise ValueError("Unexpected published 3.2 or private 3.3 Mac application")
            # Identity and exact native mGBA source must pass BEFORE expanding.
            verify_identity(new_app)
            if sorted(p.name for p in (
                    new_app / "Contents/Resources/cores").glob(
                        "*_libretro.dylib")) != ["mgba_libretro.dylib"]:
                raise ValueError("3.3 Mac QA input must contain only mGBA")
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
            app = root/"AnythingPlays33Candidate.app"
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
                raise ValueError("Current 3.3 Python/SDL runtime notices are missing")
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
        create_disk_image(app, full, volume_name="Anything Plays 3.3 Full Private QA")
        with mount(full, root/"installed"):
            mounted = root/"installed/AnythingPlays33Candidate.app"
            if not mounted.is_dir():
                raise ValueError("Repacked private full Mac DMG did not mount an app")
            verify_identity(mounted)
            subprocess.run(["codesign", "--verify", "--verbose=2", str(mounted)],
                           check=True, timeout=90)
            if full_inventory(mounted/"Contents/Resources/cores") != original_record:
                raise ValueError("Mounted full Mac DMG changed original native core bytes")
            if not (mounted/"Contents/MacOS/AnythingPlays").is_file():
                raise ValueError("Mounted 3.3 Mac app is missing its executable")
        record = {
            "schema_version": 1,
            "status": STATUS,
            "target": f"macos-{arch}",
            "installer": full_name,
            "installer_sha256": sha256(full),
            "source_revision": revision,
            "private_3_3_mgba_sha256": sha256(preview),
            "published_3_2_sha256": sha256(stable),
            "native_core_count": 11,
            "console_profiles": 18,
            "native_core_bytes_preserved": True,
            "settings_namespace": "anything-plays-33-candidate",
            "adhoc_signed": True,
            "notarized": False,
            "public_release_approved": False,
            "real_gameplay_tested": False,
            "physical_camera_tested": False,
            "physical_controller_tested": False,
            "all_18_consoles_gameplay_verified": False,
            "redistribution_audit_complete": False,
        }
        (output/"V33_FULL_MACOS_QA_RECEIPT.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", "utf-8",
        )
        (output/"SHA256SUMS.txt").write_text(
            record["installer_sha256"] + "  " + full_name + "\n", encoding="utf-8",
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
