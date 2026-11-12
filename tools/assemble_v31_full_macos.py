"""Owner-only 3.1 full macOS preview, with original released 3.0 native cores.

Verify the public 3.0 DMG SHA256, the 3.1 SDL-enabled preview receipt, then
copy original byte-for-byte source-reviewed eleven-core payload and notices.
Never sign, tag, or publish a stable GitHub Release with this QA candidate.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import time

from anything_plays.v30_gpl_trial import validate_trial_core_directory
from verify_bundle import verify_bundle
from tools.audit_v31_sdl_runtime import inspect_bundle
from tools.verify_v31_rc import validate_staged_identity
from tools.v31_rc2_source import (
    checked_rc2_source_revision, require_rc2_receipt, FULL_STATUS,
)
from tools.v31_final_source import (
    checked_final_source_revision, require_final_receipt,
    FULL_STATUS as FINAL_STATUS,
)

PREVIEW_RUN_SHA = "d176ff54de90a3cc5e585c6fc6ffd4f68388c104"
RC_SOURCE_REVISION = "26de1e1ad1b701d0735e085158347f8c213ce437"


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as src:
        for chunk in iter(lambda: src.read(4 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def command(*args):
    subprocess.run([str(x) for x in args], check=True)


def create_disk_image(app, dmg, *, attempts=4, volume_name="Anything Plays 3.1 Full QA"):
    """Retry *only* transient macOS DiskImages busy failures, never bad input.

    Caller always reopens and validates the finished read-only DMG, including
    the original eleven binary core hashes. No partial image is trusted.
    """
    if attempts < 1 or attempts > 5:
        raise ValueError("Only bounded disk-image create retries are supported")
    args = ["hdiutil", "create", "-volname", volume_name,
            "-srcfolder", str(app), "-ov", "-format", "UDZO", str(dmg)]
    for attempt in range(attempts):
        if dmg.exists():
            if dmg.is_symlink() or not dmg.is_file():
                raise ValueError("Refusing to replace a linked/nonfile DMG")
            dmg.unlink()
        try:
            result = subprocess.run(
                args, check=False, capture_output=True, text=True, timeout=180,
            )
        except subprocess.TimeoutExpired:
            raise
        if result.returncode == 0 and dmg.is_file() and dmg.stat().st_size > 1024 * 1024:
            return
        details = (result.stderr or "") + "\n" + (result.stdout or "")
        busy = ("Resource busy" in details or "resource busy" in details)
        if not busy or attempt == attempts - 1:
            raise RuntimeError("macOS disk image creation failed: " + details[-2200:])
        print("DiskImages was temporarily busy; retrying signed QA DMG",
              attempt + 1, "of", attempts)
        time.sleep(min(5 * (attempt + 1), 20))


@contextmanager
def mount(dmg, location):
    location.mkdir(parents=True, exist_ok=True)
    command("hdiutil", "attach", "-readonly", "-nobrowse",
            "-mountpoint", location, dmg)
    try:
        yield location
    finally:
        # The hosted macOS DiskImages service can briefly hold the verified
        # mount. Do not pretend a failed detach is a successful QA check.
        # Retry only this temporary CI volume, never an actual user disk.
        for attempt in range(8):
            detached = subprocess.run(
                ["hdiutil", "detach", str(location)],
                capture_output=True, text=True,
            )
            if detached.returncode == 0:
                break
            time.sleep(min(2 * (attempt + 1), 10))
        else:
            command("hdiutil", "detach", "-force", location)


def verify_inputs(arch, stable, preview, checksums, receipt, rc1=False, *, rc2=False,
                  final=False, expected_source_revision=None):
    if arch not in ("arm64", "x64"):
        raise ValueError("Only reviewed Apple Silicon or Intel architecture")
    stable_name = "AnythingPlays-3.0.0-macos-" + arch + ".dmg"
    if sum((rc1, rc2, final)) > 1:
        raise ValueError("Cannot mix RC and final source revisions")
    preview_name = ("AnythingPlays-3.1.0-macos-" if final else
                    "AnythingPlays-3.1.0-rc2-macos-" if rc2 else
                    "AnythingPlays-3.1.0-rc1-macos-" if rc1 else
                    "AnythingPlays-3.1.0-preview1-macos-") + arch + ".dmg"
    expected_sha = (checked_final_source_revision(expected_source_revision)
                    if final else checked_rc2_source_revision(expected_source_revision)
                    if rc2 else RC_SOURCE_REVISION if rc1 else PREVIEW_RUN_SHA)
    if (stable.name != stable_name or preview.name != preview_name
            or not stable.is_file() or not preview.is_file()):
        raise ValueError("Missing exact named original/3.1 preview disk image")
    stable_sha = digest(stable)
    if stable_sha + "  " + stable_name not in checksums.read_text("utf-8").splitlines():
        raise ValueError("3.0 public DMG hash mismatch")
    meta = json.loads(receipt.read_text("utf-8"))
    if (meta.get("target") != "macos-" + arch or meta.get("installer") != preview_name
            or meta.get("source_revision") != expected_sha
            or meta.get("sha256") != digest(preview)):
        raise ValueError("Source-stage 3.1 app does not match its original receipt")
    if final:
        require_final_receipt(meta, source=expected_sha, target="macos-" + arch,
                              installer=preview_name, digest=digest(preview),
                              size=preview.stat().st_size)
    if rc2:
        require_rc2_receipt(meta, source=expected_sha, target="macos-" + arch,
                            installer=preview_name, digest=digest(preview), size=preview.stat().st_size)
    return stable_sha


def build(arch, stable, preview, checksums, receipt, output, rc1=False, *,
          rc2=False, final=False, expected_source_revision=None):
    if os.getenv("AP_V31_FULL_TEST_CORES") != "1":
        raise ValueError("Private QA flags not set")
    if sum((rc1, rc2, final)) > 1:
        raise ValueError("Two candidate channels cannot share a native build")
    if final:
        checked_final_source_revision(expected_source_revision)
    elif rc2:
        checked_rc2_source_revision(expected_source_revision)
    elif rc1:
        if os.getenv("AP_V31_RC") != "1" or os.getenv("AP_V31_PREVIEW") == "1":
            raise ValueError("RC1 source assembly requires isolated candidate flags")
    elif os.getenv("AP_V31_PREVIEW") != "1":
        raise ValueError("Original full preview requires preview flag")
    if os.getenv("AP_RELEASE_BUILD") == "1" or os.getenv("AP_V30_APPROVED_RELEASE") == "1":
        raise ValueError("Cannot treat preview as approved stable release")
    stable_sha = verify_inputs(arch, stable, preview, checksums, receipt,
                               rc1=rc1, rc2=rc2, final=final,
                               expected_source_revision=expected_source_revision)
    with tempfile.TemporaryDirectory(prefix="ap31-mac-full-") as temp:
        tmp = Path(temp)
        with mount(stable, tmp/"stable"), mount(preview, tmp/"preview"):
            old = tmp/"stable/AnythingPlays.app/Contents/Resources"
            app_name = ("AnythingPlays31.app" if final else
                        "AnythingPlays31RC2.app" if rc2 else
                        "AnythingPlays31RC.app" if rc1 else "AnythingPlays31Preview.app")
            src = tmp/"preview"/app_name
            app = tmp/app_name
            shutil.copytree(src, app, symlinks=True)
            resources = app/"Contents/Resources"
            orig_core = old/"cores"
            new_core = resources/"cores"
            original = validate_trial_core_directory(orig_core, ".dylib")
            if (original.get("total_source_built_core_families") != 11
                    or original.get("source_built_dolphin") is None
                    or original.get("source_built_tia") is None):
                raise ValueError("Expected verified 3.0 eleven original-source core families")
            shutil.rmtree(new_core)
            shutil.copytree(orig_core, new_core, symlinks=True)
            if validate_trial_core_directory(new_core, ".dylib") != original:
                raise ValueError("3.0 released native core bytes were changed")
            source_licenses = old/"licenses"
            current_licenses = resources/"licenses"
            for item in source_licenses.iterdir():
                if item.is_symlink():
                    raise ValueError("Unexpected symlinked source notice")
                if item.is_file() and item.name not in {
                    "PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
                    "THIRD_PARTY_COMPONENTS.md",
                }:
                    shutil.copy2(item, current_licenses/item.name)
            if not (current_licenses/"python-distribution-notices").is_dir():
                raise ValueError("Preview runtime license receipts missing")
            shutil.copy2(Path(__file__).resolve().parents[1] /
                         "licenses/Pygame-CE-LGPL-2.1.txt",
                         current_licenses/"Pygame-CE-LGPL-2.1.txt")
        info = app/"Contents/Info.plist"
        with info.open("rb") as stream:
            plist = plistlib.load(stream)
        expected_id = ("com.anythingplays.release31" if final else
                       "com.anythingplays.rc31v2" if rc2 else
                       "com.anythingplays.rc31" if rc1 else "com.anythingplays.preview31")
        if plist.get("CFBundleIdentifier") != expected_id:
            raise ValueError("3.1 candidate could overwrite stable 3.0 app")
        verify_bundle(app, "macos", check_native=True)
        command("codesign", "--force", "--sign", "-", app)
        command("codesign", "--verify", "--verbose=2", app)
        verify_bundle(app, "macos", check_native=True)

        output.mkdir(parents=True, exist_ok=True)
        filename = ("AnythingPlays-3.1.0-macos-" if final else
                    "AnythingPlays-3.1.0-rc2-full-macos-" if rc2 else
                    "AnythingPlays-3.1.0-rc1-full-macos-" if rc1 else
                    "AnythingPlays-3.1.0-preview2-macos-") + arch + ".dmg"
        dmg = output/filename
        create_disk_image(app, dmg, volume_name="Anything Plays 3.1" if final
                          else "Anything Plays 3.1 Full QA")
        with mount(dmg, tmp/"final-dmg"):
            installed_app = tmp/"final-dmg"/app.name
            # Native loading from an attached read-only DMG leaves a library
            # mapped into this process, which blocks DiskImages unmount.
            # We already did actual native checks on the extracted .app
            # before DMG creation; here verify *the final mounted bytes*.
            verify_bundle(installed_app, "macos", check_native=False)
            if validate_trial_core_directory(installed_app/"Contents/Resources/cores", ".dylib") != original:
                raise ValueError("Final macOS DMG changed original source binaries")
            # Inventory the *mounted final signed DMG*, not the unsigned app.
            if final:
                validate_staged_identity(installed_app, channel="final_candidate")
            elif rc2:
                validate_staged_identity(installed_app, channel="rc2")
            elif rc1:
                validate_staged_identity(installed_app)
            audit = inspect_bundle(installed_app, "macos-" + arch)
        (output/"SDL_RUNTIME_AUDIT.json").write_text(
            json.dumps(audit, indent=2)+"\n", encoding="utf-8")
        report = {
            "status": (FINAL_STATUS if final else FULL_STATUS if rc2 else
                       "UNRELEASED_3_1_FULL_MACOS_RC1_QA" if rc1 else
                       "UNRELEASED_3_1_FULL_MACOS_QA"),
            "public_release_approved": False,
            "target": "macos-" + arch,
            "original_stable_sha256": stable_sha,
            "original_preview_sha256": digest(preview),
            "source_preview_revision": (expected_source_revision if final or rc2 else
                                        RC_SOURCE_REVISION if rc1 else PREVIEW_RUN_SHA),
            "identity_channel": "final_candidate" if final else "rc2" if rc2 else "rc1" if rc1 else "preview1",
            "settings_namespace": "anything-plays-31" if final else "anything-plays-31-rc2" if rc2 else None,
            "final_release_approved": False,
            "sdl_runtime_audit": "SDL_RUNTIME_AUDIT.json",
            "installer": filename, "sha256": digest(dmg),
            "size_bytes": dmg.stat().st_size,
            "original_source_core_families": original["total_source_built_core_families"],
            "native_core_count": 11,
            "console_profiles": 18,
            "notarized": False,
            "physical_controller_accepted": False,
        }
        (output/"FULL_MACOS_QA_RECEIPT.json").write_text(
            json.dumps(report, indent=2)+"\n", "utf-8")
        print(json.dumps(report, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arch", choices=("arm64", "x64"), required=True)
    for name in ("stable", "preview", "checksums", "receipt", "output"):
        p.add_argument("--"+name, type=Path, required=True)
    p.add_argument("--rc1", action="store_true",
                   help="Assemble full 18-console QA from source-built RC1 app")
    p.add_argument("--rc2", action="store_true", help="Build independent unreleased RC2 full DMG")
    p.add_argument("--final", action="store_true", help="Authentic 3.1.0 full DMG identity, PRIVATE QA only")
    p.add_argument("--expected-source-revision", metavar="EXACT_PR_SHA")
    a = p.parse_args()
    build(a.arch, *(getattr(a, x).resolve() for x in (
        "stable", "preview", "checksums", "receipt", "output")), rc1=a.rc1,
          rc2=a.rc2, final=a.final,
          expected_source_revision=a.expected_source_revision)


if __name__ == "__main__":
    main()
