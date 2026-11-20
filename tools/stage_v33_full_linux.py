"""Private full-native 3.3 Linux candidate from published 3.2 exact core bytes.

Never merge into a stable installation or publish: this is an explicitly
unreleased and independently packaged 3.3 owner-acceptance stage. Its public
3.2 baseline is only READ; the current 3.3 QA app keeps a separate package,
settings namespace and system/save/core directories.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from tools.stage_v32_full_linux import checked_file, full_inventory, no_links, sha256
from tools.verify_v31_rc import validate_staged_identity
from tools.v33_candidate_verify import TARGETS

BASELINE = "anything-plays-31_3.2.0_amd64.deb"
SOURCE = TARGETS["linux-x64"]
FULL = "anything-plays-33-candidate_3.3.0~fullqa1_amd64.deb"
STATUS = "UNRELEASED_3_3_FULL_NATIVE_LINUX_OWNER_QA_ONLY"
SKIP_OLD_RUNTIME_NOTICES = frozenset((
    "PYTHON_DISTRIBUTIONS.json",
    "THIRD_PARTY_NOTICES.md",
    "THIRD_PARTY_COMPONENTS.md",
))


def source_gate(stable, candidate, checksums, receipt, source_sha):
    """Reject any unverified baseline or QA application BEFORE repacking."""
    if type(source_sha) is not str or not re.fullmatch("[a-f0-9]{40}", source_sha):
        raise ValueError("Exact 3.3 source commit SHA required")
    stable = checked_file(stable, BASELINE)
    candidate = checked_file(candidate, SOURCE)
    checksums, receipt = Path(checksums), Path(receipt)
    for item, expected_name, bound in (
        (checksums, "SHA256SUMS.txt", 16384),
        (receipt, "V33_CANDIDATE_QA_RECEIPT.json", 65536),
    ):
        if (item.name != expected_name or not item.is_file()
                or item.is_symlink() or item.stat().st_nlink != 1
                or not 0 < item.stat().st_size <= bound):
            raise ValueError("Untrusted 3.3 candidate/source verification file")
    baseline_hash = sha256(stable)
    if baseline_hash + "  " + BASELINE not in checksums.read_text("utf-8").splitlines():
        raise ValueError("Published 3.2 Linux package fails immutable SHA256")
    record = json.loads(receipt.read_text("utf-8"))
    expected = {
        "format": "anything-plays-v33-owner-qa",
        "target": "linux-x64",
        "source_sha": source_sha,
        "channel": "v33_candidate",
        "version": "3.3.0-qa",
        "settings_namespace": "anything-plays-33-candidate",
        "installer_filename": SOURCE,
        "installer_sha256": sha256(candidate),
        "bundled_core_names": ["mgba_libretro.so"],
        "bundled_core_count": 1,
        "public_release_approved": False,
        "hardware_input_tested": False,
        "physical_camera_tested": False,
        "gamecube_bundled": False,
        "full_18_console_gameplay_tested": False,
        "installer_fully_tested_on_real_host": False,
    }
    if type(record) is not dict or record != expected:
        raise ValueError("Source is not the exact reviewed mGBA-only 3.3 QA build")
    return stable, candidate


def require_private_stage():
    required = {
        "AP_V33_CANDIDATE": "1",
        "AP_V30_MINIMAL_CORE_BUILD": "1",
    }
    forbidden = (
        "AP_RELEASE_BUILD", "AP_V30_APPROVED_RELEASE",
        "AP_V30_STABLE_CANDIDATE", "AP_V32_STABLE_CANDIDATE",
        "AP_V32_PREVIEW_BUILD",
    )
    if (any(os.environ.get(k) != v for k, v in required.items())
            or any(os.environ.get(k) == "1" for k in forbidden)):
        raise ValueError("3.3 full-core staging is PRIVATE QA only")


def assemble(stable, candidate, checksums, receipt, source_sha, output):
    require_private_stage()
    stable, candidate = source_gate(
        stable, candidate, checksums, receipt, source_sha,
    )
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Refusing to overwrite an existing QA output")
    with tempfile.TemporaryDirectory(prefix="ap33-private-full-linux-") as d:
        scratch = Path(d)
        old_pkg = scratch / "v32-published"
        new_pkg = scratch / "v33-private"
        subprocess.run(["dpkg-deb", "-x", str(stable), str(old_pkg)],
                       check=True, timeout=180)
        subprocess.run(["dpkg-deb", "-R", str(candidate), str(new_pkg)],
                       check=True, timeout=180)
        old = old_pkg / "opt/anything-plays-31"
        new = new_pkg / "opt/anything-plays-33-candidate"
        originals = old / "cores"
        installed_qa_cores = new / "cores"
        inventory = full_inventory(originals)
        no_links(old / "licenses")
        validate_staged_identity(new, channel="v33_candidate")
        no_links(installed_qa_cores)
        if sorted(p.name for p in installed_qa_cores.glob("*_libretro.so")) != [
                "mgba_libretro.so"]:
            raise ValueError("QA app already includes forbidden full native payload")
        original_marker = list(new.rglob("v31_build_identity.json"))
        if len(original_marker) != 1:
            raise ValueError("Frozen candidate identity is not unique")
        shutil.rmtree(installed_qa_cores)
        shutil.copytree(originals, installed_qa_cores)
        notices = new / "licenses"
        no_links(notices)
        for file in (old / "licenses").iterdir():
            if file.is_file() and file.name not in SKIP_OLD_RUNTIME_NOTICES:
                if file.is_symlink():
                    raise ValueError("Published source notice is linked")
                shutil.copy2(file, notices / file.name)
        if full_inventory(installed_qa_cores) != inventory:
            raise ValueError("3.3 staging modified published native core bytes")
        # Explicit separate install identity and no silent 3.2 replacement.
        control = new_pkg / "DEBIAN/control"
        metadata = control.read_text(encoding="utf-8")
        if (metadata.count("Package: anything-plays-33-candidate\n") != 1
                or metadata.count("Version: 3.3.0~qa1\n") != 1):
            raise ValueError("Not the independently installed 3.3 private app")
        metadata = metadata.replace(
            "Version: 3.3.0~qa1\n", "Version: 3.3.0~fullqa1\n",
        ).replace(
            "Private 3.3 QA; mGBA only (GB/GBC/GBA); not a public release.",
            "3.3 full-native owner QA; not a public release.",
        )
        control.write_text(metadata, encoding="utf-8")
        output.mkdir(parents=True, exist_ok=False)
        built = output / FULL
        subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(new_pkg), str(built)],
            check=True, timeout=300,
        )
        unpacked = scratch / "repacked"
        subprocess.run(["dpkg-deb", "-x", str(built), str(unpacked)],
                       check=True, timeout=180)
        app = unpacked / "opt/anything-plays-33-candidate"
        validate_staged_identity(app, channel="v33_candidate")
        if full_inventory(app / "cores") != inventory:
            raise ValueError("Repacked core bytes differ from published 3.2")
        if (unpacked / "opt/anything-plays-31").exists():
            raise ValueError("3.3 candidate would overwrite stable 3.2")
        for field, expected in (
            ("Package", "anything-plays-33-candidate"),
            ("Version", "3.3.0~fullqa1"),
        ):
            actual = subprocess.check_output(
                ["dpkg-deb", "--field", str(built), field],
                text=True, timeout=30,
            ).strip()
            if actual != expected:
                raise ValueError("Staged Debian package identity changed")
        result = {
            "format": "anything-plays-3.3-linux-full-native-owner-qa",
            "status": STATUS,
            "source_revision": source_sha,
            "target": "linux-x64",
            "installer": FULL,
            "installer_sha256": sha256(built),
            "published_v32_sha256": sha256(stable),
            "private_mgba_candidate_sha256": sha256(candidate),
            "native_core_count": 11,
            "console_profiles": 18,
            "source_native_core_bytes_preserved": True,
            "settings_namespace": "anything-plays-33-candidate",
            "public_release_approved": False,
            "physical_camera_tested": False,
            "physical_controller_tested": False,
            "real_gamecube_gameplay_tested": False,
            "redistribution_audit_complete": False,
        }
        (output / "V33_FULL_NATIVE_LINUX_QA_RECEIPT.json").write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8",
        )
        (output / "SHA256SUMS.txt").write_text(
            result["installer_sha256"] + "  " + FULL + "\n", encoding="utf-8",
        )
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stable", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--checksums", type=Path, required=True)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assemble(args.stable, args.candidate, args.checksums,
                      args.source_receipt, args.source_sha, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
