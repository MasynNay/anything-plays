"""Unreleased Linux 3.1 full-library candidate from exact verified 3.0 natives.

Base Python GUI/gamepad and runtime dependencies come from 3.1 Preview 1.
All 11 original-source compiled cores plus original source notices come
byte-for-byte from the public verified 3.0.0 Debian installer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from anything_plays.v30_gpl_trial import validate_trial_core_directory
from tools.audit_v31_sdl_runtime import inspect_bundle
from tools.verify_v31_rc import validate_staged_identity
from tools.v31_rc2_source import (
    checked_rc2_source_revision, require_rc2_receipt, FULL_STATUS,
)
from tools.v31_final_source import (
    checked_final_source_revision, require_final_receipt,
    FULL_STATUS as FINAL_STATUS,
)
from verify_bundle import verify_bundle

STABLE = "anything-plays_3.0.0_amd64.deb"
PREVIEW = "anything-plays-31-preview_3.1.0~preview1_amd64.deb"
FULL = "anything-plays-31-preview_3.1.0~preview2_amd64.deb"
SOURCE_REVISION = "d176ff54de90a3cc5e585c6fc6ffd4f68388c104"
RC_PREVIEW = "anything-plays-31-rc1_3.1.0~rc1_amd64.deb"
RC_FULL = "anything-plays-31-rc1_3.1.0~rc1full_amd64.deb"
RC_SOURCE_REVISION = "26de1e1ad1b701d0735e085158347f8c213ce437"
RC2_PREVIEW = "anything-plays-31-rc2_3.1.0~rc2_amd64.deb"
RC2_FULL = "anything-plays-31-rc2_3.1.0~rc2full_amd64.deb"
FINAL_PREVIEW = "anything-plays-31_3.1.0_amd64.deb"
FINAL_FULL = FINAL_PREVIEW


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_inputs(stable, preview, sums, receipt, rc1=False, *, rc2=False,
                    final=False, expected_source_revision=None):
    if sum((rc1, rc2, final)) > 1:
        raise ValueError("Cannot mix RC, preview and final identity channels")
    preview_name = FINAL_PREVIEW if final else RC2_PREVIEW if rc2 else (RC_PREVIEW if rc1 else PREVIEW)
    source_sha = (checked_final_source_revision(expected_source_revision)
                  if final else checked_rc2_source_revision(expected_source_revision)
                  if rc2 else (RC_SOURCE_REVISION if rc1 else SOURCE_REVISION))
    if stable.name != STABLE or preview.name != preview_name:
        raise ValueError("Unexpected native or 3.1 application installer name")
    if not stable.is_file() or not preview.is_file():
        raise ValueError("Missing baseline or 3.1 preview binary")
    checks = sums.read_text("utf-8").splitlines()
    if not any(line.strip() == sha(stable) + "  " + STABLE for line in checks):
        raise ValueError("Published 3.0 SHA-256 does not match")
    meta = json.loads(receipt.read_text("utf-8"))
    if (meta.get("sha256") != sha(preview) or meta.get("installer") != preview_name
            or meta.get("source_revision") != source_sha
            or meta.get("target") != "linux-x64"):
        raise ValueError("Frozen 3.1 source artifact digest/source mismatch")
    if final:
        require_final_receipt(meta, source=source_sha, target="linux-x64",
                              installer=preview_name, digest=sha(preview),
                              size=preview.stat().st_size)
    if rc2:
        require_rc2_receipt(meta, source=source_sha, target="linux-x64",
                            installer=preview_name, digest=sha(preview), size=preview.stat().st_size)
    return sha(stable)


def build(stable, preview, sums, receipt, output_dir, rc1=False, *, rc2=False,
          final=False, expected_source_revision=None):
    if os.getenv("AP_V31_FULL_TEST_CORES") != "1":
        raise ValueError("Full library staging requires owner-only QA flags")
    if sum((rc1, rc2, final)) > 1:
        raise ValueError("Cannot combine RC and final build channels")
    if final:
        checked_final_source_revision(expected_source_revision)
    elif rc2:
        checked_rc2_source_revision(expected_source_revision)
    elif rc1:
        if os.getenv("AP_V31_RC") != "1" or os.getenv("AP_V31_PREVIEW") == "1":
            raise ValueError("RC1 full assembly cannot use the preview channel")
    elif os.getenv("AP_V31_PREVIEW") != "1":
        raise ValueError("Legacy full-preview assembly needs preview flag")
    if os.getenv("AP_RELEASE_BUILD") == "1" or os.getenv("AP_V30_APPROVED_RELEASE") == "1":
        raise ValueError("A full candidate is not automatically an approved release")
    stable_sha = validate_inputs(stable, preview, sums, receipt, rc1=rc1,
                                 rc2=rc2, final=final,
                                 expected_source_revision=expected_source_revision)
    with tempfile.TemporaryDirectory(prefix="ap31-full-") as temp:
        root = Path(temp)
        subprocess.run(["dpkg-deb", "-x", str(stable), str(root/"old")], check=True)
        subprocess.run(["dpkg-deb", "-R", str(preview), str(root/"new")], check=True)
        old = root/"old/opt/anything-plays"
        new = root/("new/opt/anything-plays-31" if final else
                    "new/opt/anything-plays-31-rc2" if rc2 else
                    "new/opt/anything-plays-31-rc1" if rc1 else
                    "new/opt/anything-plays-31-preview")
        oldcores, newcores = old/"cores", new/"cores"
        original = validate_trial_core_directory(oldcores, ".so")
        if (original.get("total_source_built_core_families") != 11
                or original.get("source_built_dolphin") is None
                or original.get("source_built_tia") is None):
            raise ValueError("Expected verified 3.0 eleven original-source core families")
        if any(x.is_symlink() for x in oldcores.rglob("*")):
            raise ValueError("Unsafe core link in 3.0 baseline")
        shutil.rmtree(newcores)
        shutil.copytree(oldcores, newcores)
        if validate_trial_core_directory(newcores, ".so") != original:
            raise ValueError("Original-source emulator core bytes changed")
        oldlicenses, newlicenses = old/"licenses", new/"licenses"
        skip = {"PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
                "THIRD_PARTY_COMPONENTS.md"}
        for path in oldlicenses.iterdir():
            if path.is_symlink():
                raise ValueError("Unsafe license path")
            if path.is_file() and path.name not in skip:
                shutil.copy2(path, newlicenses/path.name)
        if not (newlicenses/"python-distribution-notices").is_dir():
            raise ValueError("3.1 SDL dependency notices missing")
        # Current pygame-ce wheel inventory has no wheel notice files.
        # Include and exact-hash the verbatim pinned upstream LGPL document.
        shutil.copy2(Path(__file__).resolve().parents[1] /
                     "licenses/Pygame-CE-LGPL-2.1.txt",
                     newlicenses/"Pygame-CE-LGPL-2.1.txt")

        ctrl = root/"new/DEBIAN/control"
        data = ctrl.read_text("utf-8")
        pkg = ("anything-plays-31" if final else
               "anything-plays-31-rc2" if rc2 else
               "anything-plays-31-rc1" if rc1 else "anything-plays-31-preview")
        original_version = ("3.1.0" if final else "3.1.0~rc2" if rc2
                            else "3.1.0~rc1" if rc1 else "3.1.0~preview1")
        full_version = ("3.1.0" if final else "3.1.0~rc2full" if rc2
                        else "3.1.0~rc1full" if rc1 else "3.1.0~preview2")
        if ("Package: " + pkg) not in data or ("Version: " + original_version) not in data:
            raise ValueError("Incorrect 3.1 source-stage input package")
        ctrl.write_text(data.replace("Version: " + original_version,
                                      "Version: " + full_version), "utf-8")
        desktop_name = ("anything-plays-31.desktop" if final else
                        "anything-plays-31-rc2.desktop" if rc2 else
                        "anything-plays-31-rc1.desktop" if rc1 else
                        "anything-plays-31-preview.desktop")
        desktop = root/"new/usr/share/applications"/desktop_name
        data = desktop.read_text("utf-8")
        if final:
            if "Name=Anything Plays 3.1" not in data:
                raise ValueError("Independent 3.1 final desktop identity mismatch")
        elif rc2:
            if "Name=Anything Plays 3.1 Release Candidate 2" not in data:
                raise ValueError("Independent RC2 desktop identity mismatch")
        elif rc1:
            if "Name=Anything Plays 3.1 Release Candidate 1" not in data:
                raise ValueError("RC1 desktop identity mismatch")
        else:
            desktop.write_text(data.replace("Name=Anything Plays 3.1 Preview 1",
                                            "Name=Anything Plays 3.1 Full QA Preview"), "utf-8")
        verify_bundle(new, "linux", check_native=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        deb = output_dir/(FINAL_FULL if final else RC2_FULL if rc2 else RC_FULL if rc1 else FULL)
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(root/"new"), str(deb)], check=True)
        subprocess.run(["dpkg-deb", "-x", str(deb), str(root/"installed")], check=True)
        payload = root/("installed/opt/anything-plays-31" if final else
                        "installed/opt/anything-plays-31-rc2" if rc2 else
                        "installed/opt/anything-plays-31-rc1" if rc1 else
                        "installed/opt/anything-plays-31-preview")
        verify_bundle(payload, "linux", check_native=True)
        if validate_trial_core_directory(payload/"cores", ".so") != original:
            raise ValueError("Repackaging modified 3.0 original binaries")
        if final:
            validate_staged_identity(payload, channel="final_candidate")
        elif rc2:
            validate_staged_identity(payload, channel="rc2")
        elif rc1:
            validate_staged_identity(payload)
        audit = inspect_bundle(payload, "linux-x64")
        (output_dir/"SDL_RUNTIME_AUDIT.json").write_text(
            json.dumps(audit, indent=2)+"\n", encoding="utf-8")
        result = {
            "target": "linux-x64",
            "status": (FINAL_STATUS if final else FULL_STATUS if rc2 else
                       "UNRELEASED_3_1_FULL_LINUX_RC1_QA" if rc1 else
                       "UNRELEASED_3_1_FULL_LINUX_QA"),
            "public_release_approved": False,
            "source_stable_sha256": stable_sha,
            "source_preview_sha256": sha(preview),
            "source_preview_revision": (expected_source_revision if final or rc2 else
                                        RC_SOURCE_REVISION if rc1 else SOURCE_REVISION),
            "identity_channel": "final_candidate" if final else "rc2" if rc2 else "rc1" if rc1 else "preview1",
            "settings_namespace": "anything-plays-31" if final else "anything-plays-31-rc2" if rc2 else None,
            "final_release_approved": False,
            "sdl_runtime_audit": "SDL_RUNTIME_AUDIT.json",
            "installer": deb.name,
            "sha256": sha(deb),
            "size_bytes": deb.stat().st_size,
            "native_core_count": 11,
            "console_profiles": 18,
            "source_core_families": original["total_source_built_core_families"],
            "real_controller_accepted": False,
        }
        (output_dir/"FULL_LIBRARY_QA_RECEIPT.json").write_text(
            json.dumps(result, indent=2)+"\n", "utf-8"
        )
        print(json.dumps(result, indent=2))


def main():
    p = argparse.ArgumentParser()
    for name in ("stable", "preview", "sums", "receipt", "output"):
        p.add_argument("--"+name, type=Path, required=True)
    p.add_argument("--rc1", action="store_true",
                   help="Assemble from exact fresh source-built RC1 app instead of frozen Preview 1")
    p.add_argument("--rc2", action="store_true", help="Full RC2 QA only: exact pinned source-stage installer")
    p.add_argument("--final", action="store_true", help="Full authentic 3.1.0 identity, PRIVATE QA only")
    p.add_argument("--expected-source-revision", metavar="PR_HEAD_SHA",
                   help="Required for RC2: exact checked-out source and receipt SHA")
    args = p.parse_args()
    build(*(getattr(args, x).resolve() for x in ("stable", "preview", "sums",
                                                 "receipt", "output")), rc1=args.rc1, rc2=args.rc2,
          final=args.final,
          expected_source_revision=args.expected_source_revision)


if __name__ == "__main__":
    main()
