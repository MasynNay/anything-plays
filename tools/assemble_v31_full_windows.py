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
from tools.audit_v31_sdl_runtime import inspect_bundle

STABLE = "AnythingPlaysSetup-3.0.0.exe"
PREVIEW = "AnythingPlaysSetup-3.1.0-preview1.exe"
FULL = "AnythingPlaysSetup-3.1.0-preview2.exe"
SOURCE_REVISION = "d176ff54de90a3cc5e585c6fc6ffd4f68388c104"


def hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as inp:
        for chunk in iter(lambda: inp.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_inputs(stable, preview, sums, receipt):
    if stable.name != STABLE or preview.name != PREVIEW:
        raise ValueError("Unexpected stable/preview filename")
    if not stable.is_file() or not preview.is_file():
        raise ValueError("Source installer missing")
    if (hash_file(stable) + "  " + STABLE
            not in sums.read_text("utf-8").splitlines()):
        raise ValueError("Public stable 3.0 source binary SHA256 mismatch")
    info = json.loads(receipt.read_text("utf-8"))
    if (info.get("target") != "windows-x64"
            or info.get("source_revision") != SOURCE_REVISION
            or info.get("installer") != PREVIEW
            or info.get("sha256") != hash_file(preview)):
        raise ValueError("Controller-enabled 3.1 Preview 1 artifact mismatch")
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


def build(stable, preview, sums, receipt, output):
    if os.getenv("AP_V31_FULL_TEST_CORES") != "1" or os.getenv("AP_V31_PREVIEW") != "1":
        raise ValueError("Private QA flags required")
    if os.getenv("AP_RELEASE_BUILD") == "1" or os.getenv("AP_V30_APPROVED_RELEASE") == "1":
        raise ValueError("No production flags for an owner QA candidate")
    stable_sha = check_inputs(stable, preview, sums, receipt)
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
        enable_windows_trial_runtime(dest/"cores")
        verify_bundle(dest, "windows", check_native=True)

        # Icons are made from the original source artwork, not generic glyphs.
        subprocess.run([os.sys.executable, str(root/"tools/render_v21_icon.py")],
                       check=True, cwd=root)
        subprocess.run([iscc(), "/DV31PreviewBuild=1",
                        "/DAppVersion=3.1.0-preview2",
                        str(root/"packaging/installer.iss")], check=True, cwd=root)
        produced = root/"release"/FULL
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
        audit = inspect_bundle(installed, "windows-x64")
        output.mkdir(parents=True, exist_ok=True)
        (output/"SDL_RUNTIME_AUDIT.json").write_text(
            json.dumps(audit, indent=2)+"\n", encoding="utf-8")
        target = output/FULL
        shutil.copyfile(produced, target)
        report = {
            "status": "UNRELEASED_3_1_FULL_WINDOWS_QA",
            "public_release_approved": False,
            "target": "windows-x64",
            "original_stable_sha256": stable_sha,
            "source_preview1_sha256": hash_file(preview),
            "source_preview_revision": SOURCE_REVISION,
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
    a = p.parse_args()
    build(*(getattr(a, x).resolve() for x in (
        "stable", "preview", "sums", "receipt", "output")))


if __name__ == "__main__":
    main()
