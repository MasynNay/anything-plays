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
from verify_bundle import verify_bundle

STABLE = "anything-plays_3.0.0_amd64.deb"
PREVIEW = "anything-plays-31-preview_3.1.0~preview1_amd64.deb"
FULL = "anything-plays-31-preview_3.1.0~preview2_amd64.deb"
SOURCE_REVISION = "ffee5dcdf0415440c9f5bffc7f9049a07c094ff3"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_inputs(stable, preview, sums, receipt):
    if stable.name != STABLE or preview.name != PREVIEW:
        raise ValueError("Unexpected native or 3.1 application installer name")
    if not stable.is_file() or not preview.is_file():
        raise ValueError("Missing baseline or 3.1 preview binary")
    checks = sums.read_text("utf-8").splitlines()
    if not any(line.strip() == sha(stable) + "  " + STABLE for line in checks):
        raise ValueError("Published 3.0 SHA-256 does not match")
    meta = json.loads(receipt.read_text("utf-8"))
    if (meta.get("sha256") != sha(preview) or meta.get("installer") != PREVIEW
            or meta.get("source_revision") != SOURCE_REVISION
            or meta.get("target") != "linux-x64"):
        raise ValueError("3.1 Preview 1 original artifact digest/source mismatch")
    return sha(stable)


def build(stable, preview, sums, receipt, output_dir):
    if os.getenv("AP_V31_PREVIEW") != "1" or os.getenv("AP_V31_FULL_TEST_CORES") != "1":
        raise ValueError("Full library staging requires owner-only QA flags")
    if os.getenv("AP_RELEASE_BUILD") == "1" or os.getenv("AP_V30_APPROVED_RELEASE") == "1":
        raise ValueError("A full candidate is not automatically an approved release")
    stable_sha = validate_inputs(stable, preview, sums, receipt)
    with tempfile.TemporaryDirectory(prefix="ap31-full-") as temp:
        root = Path(temp)
        subprocess.run(["dpkg-deb", "-x", str(stable), str(root/"old")], check=True)
        subprocess.run(["dpkg-deb", "-R", str(preview), str(root/"new")], check=True)
        old = root/"old/opt/anything-plays"
        new = root/"new/opt/anything-plays-31-preview"
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

        ctrl = root/"new/DEBIAN/control"
        data = ctrl.read_text("utf-8")
        if "Package: anything-plays-31-preview" not in data or "Version: 3.1.0~preview1" not in data:
            raise ValueError("Incorrect 3.1 Preview 1 input package")
        ctrl.write_text(data.replace("Version: 3.1.0~preview1",
                                      "Version: 3.1.0~preview2"), "utf-8")
        desktop = root/"new/usr/share/applications/anything-plays-31-preview.desktop"
        data = desktop.read_text("utf-8")
        desktop.write_text(data.replace("Name=Anything Plays 3.1 Preview 1",
                                        "Name=Anything Plays 3.1 Full QA Preview"), "utf-8")
        verify_bundle(new, "linux", check_native=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        deb = output_dir/FULL
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(root/"new"), str(deb)], check=True)
        subprocess.run(["dpkg-deb", "-x", str(deb), str(root/"installed")], check=True)
        payload = root/"installed/opt/anything-plays-31-preview"
        verify_bundle(payload, "linux", check_native=True)
        if validate_trial_core_directory(payload/"cores", ".so") != original:
            raise ValueError("Repackaging modified 3.0 original binaries")
        result = {
            "status": "UNRELEASED_3_1_FULL_LINUX_QA",
            "public_release_approved": False,
            "source_stable_sha256": stable_sha,
            "source_preview_sha256": sha(preview),
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
    args = p.parse_args()
    build(*(getattr(args, x).resolve() for x in ("stable", "preview", "sums",
                                                 "receipt", "output")))


if __name__ == "__main__":
    main()
