"""Assemble a private 3.2 Linux 18-profile QA package from trusted native cores.

Use the fresh current-head 3.2 frozen GUI and ONLY the SHA256-validated
original source-built native cores from the public 3.1.1 release.
Never publish, install over the stable app or claim physical gameplay QA.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from anything_plays.build_identity import make_identity
from anything_plays.v30_gpl_trial import validate_trial_core_directory
from tools.verify_v31_rc import validate_staged_identity
from tools.verify_v32_preview import FILES, verify as verify_minimal

BASELINE = "anything-plays-31_3.1.1_amd64.deb"
FULL = "anything-plays-32-preview_3.2.0~fullqa1_amd64.deb"
STATUS = "PRIVATE_3_2_LINUX_11_NATIVE_CORE_18_PROFILE_QA_NOT_RELEASE"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_file(path, name):
    path = Path(path)
    if (path.name != name or not path.is_file() or path.is_symlink()
            or path.stat().st_size < 1024 * 1024):
        raise ValueError("Missing, linked or wrongly named QA input: " + name)
    return path


def no_links(folder):
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Missing or linked core/notice directory")
    if any(item.is_symlink() for item in folder.rglob("*")):
        raise ValueError("Linked contents in native payload are forbidden")


def source_gate(stable, preview, sums, receipt, source_sha):
    """Authenticate both installer input files before any extraction."""
    if not re.fullmatch(r"[a-f0-9]{40}", str(source_sha)):
        raise ValueError("Exact 3.2 Git source SHA required")
    stable = checked_file(stable, BASELINE)
    preview = checked_file(preview, FILES["linux-x64"])
    sums, receipt = Path(sums), Path(receipt)
    if (sums.name != "SHA256SUMS.txt" or not sums.is_file()
            or sums.is_symlink() or sums.stat().st_size > 16384
            or not receipt.is_file() or receipt.is_symlink()
            or receipt.stat().st_size > 32768):
        raise ValueError("Missing or unsafe 3.1.1 checksum / preview receipt")
    if sha256(stable) + "  " + BASELINE not in sums.read_text("utf-8").splitlines():
        raise ValueError("Published 3.1.1 DEB checksum mismatch")
    report = json.loads(receipt.read_text("utf-8"))
    if not isinstance(report, dict):
        raise ValueError("Invalid minimal preview receipt")
    required = {
        "status": "UNRELEASED_PRIVATE_QA_ONLY",
        "channel": "v32_preview",
        "version": "3.2.0-preview1",
        "target": "linux-x64",
        "installer": FILES["linux-x64"],
        "source_revision": source_sha,
        "sha256": sha256(preview),
        "size_bytes": preview.stat().st_size,
        "settings_namespace": make_identity("v32_preview")["settings_namespace"],
        "bundled_core_names": ["mgba"],
        "bundled_console_profiles": ["gb", "gbc", "gba"],
        "public_release_approved": False,
        "all_18_consoles_verified": False,
    }
    if any(type(report.get(key)) is not type(value) or report[key] != value
           for key, value in required.items()):
        raise ValueError("Wrong or tampered exact-source preview receipt")
    return stable, preview


def full_inventory(directory):
    no_links(directory)
    info = validate_trial_core_directory(directory, ".so")
    if (info.get("native_core_count") != 11
            or info.get("all_console_profiles") != 18
            or info.get("total_source_built_core_families") != 11
            or not info.get("source_built_dolphin")
            or not info.get("source_built_tia")
            or len(list(directory.glob("*_libretro.so"))) != 11):
        raise ValueError("Missing original-source 11 native cores / 18 profiles")
    return info


def assemble(stable, preview, sums, receipt, source_sha, output):
    if (os.environ.get("AP_V32_PREVIEW_BUILD") != "1"
            or os.environ.get("AP_RELEASE_BUILD") == "1"
            or os.environ.get("AP_V30_APPROVED_RELEASE") == "1"):
        raise ValueError("3.2 full staging requires private non-release flags")
    stable, preview = source_gate(stable, preview, sums, receipt, source_sha)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Refusing to overwrite any QA output or installed app")
    with tempfile.TemporaryDirectory(prefix="ap32-full-linux-") as temp:
        root = Path(temp)
        subprocess.run(["dpkg-deb", "-x", str(stable), str(root/"stable")],
                       check=True, timeout=120)
        subprocess.run(["dpkg-deb", "-R", str(preview), str(root/"preview")],
                       check=True, timeout=120)
        old = root/"stable/opt/anything-plays-31"
        new = root/"preview/opt/anything-plays-32-preview"
        source_core = old/"cores"
        new_core = new/"cores"
        original = full_inventory(source_core)
        no_links(old/"licenses")
        validate_staged_identity(new, channel="v32_preview")
        minimal = verify_minimal("linux-x64", preview, source_sha, bundle=new)
        recorded = json.loads(Path(receipt).read_text("utf-8"))
        if (minimal["sha256"] != recorded["sha256"]
                or minimal["source_revision"] != recorded["source_revision"]):
            raise ValueError("3.2 source app is not the recorded preview artifact")
        no_links(new_core)
        shutil.rmtree(new_core)
        shutil.copytree(source_core, new_core)
        no_links(new/"licenses")
        for item in (old/"licenses").iterdir():
            if item.is_file() and item.name not in {
                    "PYTHON_DISTRIBUTIONS.json", "THIRD_PARTY_NOTICES.md",
                    "THIRD_PARTY_COMPONENTS.md"}:
                shutil.copy2(item, new/"licenses"/item.name)
        if full_inventory(new_core) != original:
            raise ValueError("Staged native core identity differs from published 3.1.1")
        control = root/"preview/DEBIAN/control"
        metadata = control.read_text("utf-8")
        original_version = "Version: 3.2.0~preview1\n"
        if (metadata.count(original_version) != 1
                or "Package: anything-plays-32-preview\n" not in metadata):
            raise ValueError("Private 3.2 Debian identity incorrect")
        control.write_text(metadata.replace(
            original_version, "Version: 3.2.0~fullqa1\n"
        ), "utf-8")
        output.mkdir(parents=True, exist_ok=False)
        built = output/FULL
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group",
                        str(root/"preview"), str(built)],
                       check=True, timeout=240)
        subprocess.run(["dpkg-deb", "-x", str(built), str(root/"installed")],
                       check=True, timeout=120)
        installed = root/"installed/opt/anything-plays-32-preview"
        validate_staged_identity(installed, channel="v32_preview")
        if full_inventory(installed/"cores") != original:
            raise ValueError("Repacked full QA core bytes differ from published source")
        if (root/"installed/opt/anything-plays-31").exists():
            raise ValueError("Full QA would overwrite the public stable install")
        for field, value in (("Package", "anything-plays-32-preview"),
                             ("Version", "3.2.0~fullqa1")):
            read = subprocess.check_output(
                ["dpkg-deb", "--field", str(built), field],
                text=True, timeout=30,
            ).strip()
            if read != value:
                raise ValueError("Full QA Debian control field changed: " + field)
        result = {
            "schema_version": 1,
            "status": STATUS,
            "target": "linux-x64",
            "installer": FULL,
            "installer_sha256": sha256(built),
            "source_revision": source_sha,
            "source_3_2_preview_sha256": sha256(preview),
            "published_3_1_1_sha256": sha256(stable),
            "native_core_count": 11,
            "console_profiles": 18,
            "native_core_bytes_preserved": True,
            "settings_namespace": "anything-plays-32-preview",
            "public_release_approved": False,
            "real_gameplay_tested": False,
            "physical_camera_tested": False,
            "physical_controller_tested": False,
            "all_18_consoles_gameplay_verified": False,
        }
        (output/"V32_FULL_LINUX_QA_RECEIPT.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", "utf-8",
        )
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stable", type=Path, required=True)
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--checksums", type=Path, required=True)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assemble(args.stable, args.preview, args.checksums,
                      args.source_receipt, args.source_sha, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
