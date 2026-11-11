"""Owner-only Windows 3.1 full-library QA candidate.

Unpack the exact published 3.0.0 and 3.1 Preview 1 Inno Setup programs;
preserve every 3.1 app runtime DLL, SDL wheel and notice while replacing only
the emulation core set with the original 3.0 source-built eleven-core payload.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from anything_plays.v30_gpl_trial import (
    enable_windows_trial_runtime, validate_trial_core_directory,
)
from verify_bundle import verify_bundle
from tools.audit_v31_sdl_runtime import UPSTREAM_LGPL_SHA256, inspect_bundle
from tools.verify_v31_rc import validate_staged_identity
from tools.v31_rc2_source import (
    checked_rc2_source_revision, require_rc2_receipt, FULL_STATUS,
)

STABLE = "AnythingPlaysSetup-3.0.0.exe"
PREVIEW = "AnythingPlaysSetup-3.1.0-preview1.exe"
FULL = "AnythingPlaysSetup-3.1.0-preview2.exe"
SOURCE_REVISION = "d176ff54de90a3cc5e585c6fc6ffd4f68388c104"
RC_PREVIEW = "AnythingPlaysSetup-3.1.0-rc1.exe"
RC_FULL = "AnythingPlaysSetup-3.1.0-rc1-full.exe"
RC_SOURCE_REVISION = "26de1e1ad1b701d0735e085158347f8c213ce437"
RC2_PREVIEW = "AnythingPlaysSetup-3.1.0-rc2.exe"
RC2_FULL = "AnythingPlaysSetup-3.1.0-rc2-full.exe"


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as inp:
        for chunk in iter(lambda: inp.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_inputs(stable, preview, sums, receipt, rc1=False, *, rc2=False,
                 expected_source_revision=None):
    if rc1 and rc2:
        raise ValueError("RC1/RC2 source identity cannot be mixed")
    preview_name = RC2_PREVIEW if rc2 else RC_PREVIEW if rc1 else PREVIEW
    source_sha = (checked_rc2_source_revision(expected_source_revision)
                  if rc2 else RC_SOURCE_REVISION if rc1 else SOURCE_REVISION)
    if stable.name != STABLE or preview.name != preview_name:
        raise ValueError("Unexpected stable/preview filename")
    if not stable.is_file() or not preview.is_file():
        raise ValueError("Source installer missing")
    if (hash_file(stable) + "  " + STABLE
            not in sums.read_text("utf-8").splitlines()):
        raise ValueError("Public stable 3.0 source binary SHA256 mismatch")
    info = json.loads(receipt.read_text("utf-8"))
    if (info.get("target") != "windows-x64"
            or info.get("source_revision") != source_sha
            or info.get("installer") != preview_name
            or info.get("sha256") != hash_file(preview)):
        raise ValueError("Fresh 3.1 source-stage artifact mismatch")
    if rc2:
        require_rc2_receipt(info, source=source_sha, target="windows-x64",
                            installer=preview_name, digest=hash_file(preview, size=preview.stat().st_size)
    return hash_file(stable)


def unpack(installer, target):
    """Actually install Inno Setup in a disposable runner directory.

    Inno 7 compressed installers cannot necessarily be read by 7-Zip.
    Inno's own /DIR flag is the authoritative, testable extraction method.
    /VERYSILENT and /NOICONS avoid a GUI, shortcuts and postinstall launch.
    This runs only on an ephemeral Windows CI host, never on the user's PC.
    """
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES",
         "/NORESTART", "/NOICONS", "/SP-", "/DIR="+str(target)],
        check=True, timeout=600,
    )


def source_app(folder, marker_name):
    """Resolve actual Inno install root, not the parent of its EXE folder."""
    matches = list(folder.rglob(marker_name))
    if len(matches) != 1:
        raise ValueError("Expected exactly one source app marker: " + marker_name)
    marker = matches[0]
    # A native provenance marker lives in {app}/cores/; the executable
    # lives directly in {app}/. Both paths must resolve to the same root.
    return marker.parent.parent if marker_name == "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json" else marker.parent


def iscc():
    program = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if program:
        return program
    for base in (os.getenv("ProgramFiles(x86)", ""),
                 os.getenv("ProgramFiles", "")):
        for version in (7, 6):
            path = Path(base)/f"Inno Setup {version}"/"ISCC.exe"
            if path.is_file():
                return str(path)
    raise ValueError("Inno Setup compiler not found")


def build(stable, preview, sums, receipt, output, rc1=False, *, rc2=False,
          expected_source_revision=None):
    if os.getenv("AP_V31_FULL_TEST_CORES") != "1":
        raise ValueError("Private QA flags required")
    if rc1 and rc2:
        raise ValueError("RC1 and RC2 cannot share a build")
    if rc2:
        checked_rc2_source_revision(expected_source_revision)
    elif rc1:
        if os.getenv("AP_V31_RC") != "1" or os.getenv("AP_V31_PREVIEW") == "1":
            raise ValueError("RC1 assembly requires isolated candidate flags")
    elif os.getenv("AP_V31_PREVIEW") != "1":
        raise ValueError("Original QA requires preview flag")
    if os.getenv("AP_RELEASE_BUILD") == "1" or os.getenv("AP_V30_APPROVED_RELEASE") == "1":
        raise ValueError("No production flags for an owner QA candidate")
    stable_sha = check_inputs(stable, preview, sums, receipt, rc1=rc1,
                               rc2=rc2, expected_source_revision=expected_source_revision)
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="ap31-win-full-") as temp:
        scratch = Path(temp)
        unpack(stable, scratch/"stable")
        unpack(preview, scratch/"preview")
        previous = source_app(scratch/"stable", "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json")
        now = source_app(scratch/"preview", "AnythingPlays.exe")
        originals = previous/"cores"
        first = validate_trial_core_directory(originals, ".dll")
        if (first.get("total_source_built_core_families") != 11
                or first.get("source_built_tia") is None
                or first.get("source_built_dolphin") is None):
            raise ValueError("Published 3.0 lacked eleven exact source-built natives")
        dest = root/"dist/AnythingPlays"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(now, dest, ignore=shutil.ignore_patterns('unins000.*'))
        shutil.rmtree(dest/"cores")
        shutil.copytree(originals, dest/"cores")
        if validate_trial_core_directory(dest/"cores", ".dll") != first:
            raise ValueError("Native source mapping or compiled bytes changed")
        original_notices = previous/"licenses"
        current_notices = dest/"licenses"
        for item in original_notices.iterdir():
            if item.is_symlink():
                raise ValueError("Unexpected original source notice link")
            if item.is_file() and item.name not in {
                    "PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
                    "THIRD_PARTY_COMPONENTS.md"}:
                shutil.copy2(item, current_notices/item.name)
        if not (current_notices/"python-distribution-notices").is_dir():
            raise ValueError("Pygame/SDL license documents missing from candidate")
        pygame_license = root/"licenses/Pygame-CE-LGPL-2.1.txt"
        if hash_file(pygame_license) != UPSTREAM_LGPL_SHA256:
            raise ValueError("Verbatim pygame-ce LGPL checkout altered by line endings")
        shutil.copy2(pygame_license,
                     current_notices/"Pygame-CE-LGPL-2.1.txt")
        enable_windows_trial_runtime(dest/"cores")
        verify_bundle(dest, "windows", check_native=True)

        # Icons are made from the original source artwork, not generic glyphs.
        subprocess.run([os.sys.executable, str(root/"tools/render_v21_icon.py")],
                       check=True, cwd=root)
        setup_mode = ("/DV31RC2Build=1" if rc2 else
                      "/DV31RCBuild=1" if rc1 else "/DV31PreviewBuild=1")
        app_version = ("/DAppVersion=3.1.0-rc2-full" if rc2 else
                       "/DAppVersion=3.1.0-rc1-full" if rc1 else
                       "/DAppVersion=3.1.0-preview2")
        subprocess.run([iscc(), setup_mode, app_version,
                        str(root/"packaging/installer.iss")], check=True, cwd=root)
        produced = root/"release"/(RC2_FULL if rc2 else RC_FULL if rc1 else FULL)
        if not produced.is_file():
            raise ValueError("Expected full candidate Inno Setup EXE was not created")
        # The actual installer is the artifact; require that it unpacks
        # to the exact byte-verified original-source core payload too.
        unpack(produced, scratch/"reinstalled")
        installed = source_app(scratch/"reinstalled", "V30_GPL_TRIAL_PREVIEW_UNAPPROVED.json")
        # Windows locks ctypes-loaded DLLs for the lifetime of the process.
        # Verify actual native initialization in a disposable child process,
        # so Python can clean up the temporary Inno installation on success.
        # Do NOT weaken the installed native check to a manifest-only check.
        subprocess.run(
            [os.sys.executable, "-c",
             ("import sys; from pathlib import Path; "
              "from anything_plays.v30_gpl_trial import enable_windows_trial_runtime; "
              "from verify_bundle import verify_bundle; "
              "app = Path(sys.argv[1]); "
              "enable_windows_trial_runtime(app / 'cores'); "
              "verify_bundle(app, 'windows', check_native=True)"),
             str(installed)],
            check=True, cwd=root, timeout=120,
        )
        verify_bundle(installed, "windows", check_native=False)
        if validate_trial_core_directory(installed/"cores", ".dll") != first:
            raise ValueError("Final Setup installer altered original source-built cores")
        if rc2:
            validate_staged_identity(installed, channel="rc2")
        elif rc1:
            validate_staged_identity(installed)
        audit = inspect_bundle(installed, "windows-x64")
        output.mkdir(parents=True, exist_ok=True)
        (output/"SDL_RUNTIME_AUDIT.json").write_text(
            json.dumps(audit, indent=2)+"\n", encoding="utf-8")
        target = output/(RC_FULL if rc1 else FULL)
        shutil.copyfile(produced, target)
        report = {
            "status": (FULL_STATUS if rc2 else
                       "UNRELEASED_3_1_FULL_WINDOWS_RC1_QA" if rc1 else
                       "UNRELEASED_3_1_FULL_WINDOWS_QA"),
            "public_release_approved": False,
            "target": "windows-x64",
            "original_stable_sha256": stable_sha,
            "source_preview1_sha256": hash_file(preview),
            "source_preview_revision": (expected_source_revision if rc2 else
                                        RC_SOURCE_REVISION if rc1 else SOURCE_REVISION),
            "identity_channel": "rc2" if rc2 else "rc1" if rc1 else "preview1",
            "settings_namespace": "anything-plays-31-rc2" if rc2 else None,
            "final_release_approved": False,
            "sdl_runtime_audit": "SDL_RUNTIME_AUDIT.json",
            "installer": target.name,
            "sha256": hash_file(target),
            "size_bytes": target.stat().st_size,
            "native_core_count": 11,
            "console_profiles": 18,
            "physical_controller_accepted": False,
        }
        (output/"FULL_WINDOWS_QA_RECEIPT.json").write_text(
            json.dumps(report, indent=2)+"\n", "utf-8")
        print(json.dumps(report, indent=2))


def main():
    p = argparse.ArgumentParser()
    for name in ("stable", "preview", "sums", "receipt", "output"):
        p.add_argument("--"+name, type=Path, required=True)
    p.add_argument("--rc1", action="store_true",
                   help="Repack from the exact source-built 3.1 RC1 app")
    p.add_argument("--rc2", action="store_true", help="Full RC2 private QA with separate Inno Setup ID")
    p.add_argument("--expected-source-revision", metavar="EXACT_PR_HEAD_SHA")
    a = p.parse_args()
    build(*(getattr(a, x).resolve() for x in (
        "stable", "preview", "sums", "receipt", "output")), rc1=a.rc1,
          rc2=a.rc2, expected_source_revision=a.expected_source_revision)


if __name__ == "__main__":
    main()
