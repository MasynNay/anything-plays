"""Fail-closed staging of four installed-tested RC2 binaries; no publication.

Requires the original source-pinned full-core and installed desktop
receipts for ALL four OS targets. Technical QA is not license approval.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

STATUS = "UNRELEASED_3_1_FULL_RC2_QA"
GUI_STATUS = "PASSED_RC2_REAL_FROZEN_TK_STARTUP_QA_ONLY"
TARGETS = {
    "linux-x64": ("anything-plays-31-rc2_3.1.0~rc2full_amd64.deb", "FULL_LIBRARY_QA_RECEIPT.json"),
    "windows-x64": ("AnythingPlaysSetup-3.1.0-rc2-full.exe", "FULL_WINDOWS_QA_RECEIPT.json"),
    "macos-arm64": ("AnythingPlays-3.1.0-rc2-full-macos-arm64.dmg", "FULL_MACOS_QA_RECEIPT.json"),
    "macos-x64": ("AnythingPlays-3.1.0-rc2-full-macos-x64.dmg", "FULL_MACOS_QA_RECEIPT.json"),
}
CHECKS = (
    ("identity_channel", "rc2"), ("settings_namespace", "anything-plays-31-rc2"),
    ("native_core_count", 11), ("console_profiles", 18),
    ("public_release_approved", False), ("final_release_approved", False),
)
GUI_CHECKS = (
    ("actual_tk_window_started", True), ("actual_app_initialized", True),
    ("actual_tk_mainloop_ran", True), ("stream_output_window_opened", True),
    ("stream_appearance_configured", True), ("stream_closed_cleanly", True),
    ("console_profiles", 18), ("native_core_count", 11),
    ("public_release_approved", False), ("relinking_reviewed", False),
)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def receipt(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Missing, linked or oversized QA evidence: " + path.name)
    result = json.loads(path.read_text("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("QA evidence must be a dictionary")
    return result


def ensure(item, checks, target):
    for key, value in checks:
        if item.get(key) != value:
            raise ValueError("Invalid " + target + " receipt: " + key)


def stage(full, installed, output, source_sha, qa_run_id):
    full, installed, output = Path(full), Path(installed), Path(output)
    if not re.fullmatch(r"[a-f0-9]{40}", source_sha):
        raise ValueError("Exact forty-character source SHA required")
    if not isinstance(qa_run_id, int) or qa_run_id < 1:
        raise ValueError("Completed four-platform GitHub run ID required")
    if output.exists() or not full.is_dir() or not installed.is_dir():
        raise ValueError("Destination must be new and both QA roots present")
    if full.is_symlink() or installed.is_symlink():
        raise ValueError("Linked QA roots are not accepted")
    inputs = {}
    for target, (name, report_name) in TARGETS.items():
        group, evidence = full / target, installed / target
        if any(p.is_symlink() or not p.is_dir() for p in (group, evidence)):
            raise ValueError("Missing independent source or installed QA: " + target)
        binary = group / name
        if not binary.is_file() or binary.is_symlink() or binary.stat().st_size < 1024 * 1024:
            raise ValueError("Missing genuine native RC2 installer: " + target)
        digest = sha(binary)
        source = receipt(group / report_name)
        gui = receipt(evidence / "RC2_INSTALLED_RECEIPT.json")
        ensure(source, (("status", STATUS), ("target", target), ("installer", name),
                        ("sha256", digest), ("source_preview_revision", source_sha)) + CHECKS, target)
        ensure(gui, (("status", GUI_STATUS), ("target", target), ("installer", name),
                     ("installer_sha256", digest), ("source_revision", source_sha)) + GUI_CHECKS, target)
        inputs[target] = (binary, name.replace("~", "."), digest)
    output.mkdir(parents=True)
    summary = {}
    for target, (binary, name, digest) in inputs.items():
        dest = output / name
        shutil.copy2(binary, dest)
        if sha(dest) != digest:
            raise ValueError("Staging changed native bytes: " + target)
        summary[target] = {"filename": name, "sha256": digest, "bytes": dest.stat().st_size}
    (output / "RC2_QA_MANIFEST.json").write_text(json.dumps({
        "status": "PRERELEASE_QA_PASSED_SOURCE_AND_RIGHTS_REVIEW_STILL_OPEN",
        "source_revision": source_sha, "qa_run_id": qa_run_id,
        "installers": summary, "native_core_count": 11, "console_profiles": 18,
        "public_release_approved": False, "relinking_reviewed": False,
        "physical_hardware_verified": False, "stable_3_1_approved": False,
    }, indent=2) + "\n", "utf-8")
    (output / "RC2_SOURCE_ACCESS.md").write_text(
        "# 3.1 RC2 source and limitations\n\n"
        "Exact application source: https://github.com/MasynNay/anything-plays/tree/" + source_sha + "\n\n"
        "Eleven original emulator source trees: https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources\n\n"
        "pygame-ce/SDL upstream candidate source audit: https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1\n\n"
        "These are source access pointers, not a claim of complete LGPL relinking or legal clearance.\n"
        "Real cameras, physical controllers, retail games and prolonged use remain unverified.\n"
        "No game ROMs or firmware are included. The files must not be represented as a stable 3.1 release.\n",
        "utf-8",
    )
    names = sorted(p for p in output.iterdir() if p.is_file())
    (output / "SHA256SUMS.txt").write_text(
        "".join(sha(p) + "  " + p.name + "\n" for p in names), "ascii"
    )
    if len(names) != 6:
        raise ValueError("Expected exactly four installers plus source and QA manifest")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--full", type=Path, required=True)
    p.add_argument("--installed", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--run-id", type=int, required=True)
    a = p.parse_args()
    result = stage(a.full, a.installed, a.output, a.source_sha, a.run_id)
    print("Verified four installed RC2 QA packages:", ", ".join(result))
    print("Source/relinking and public release rights NOT approved by this staging step")


if __name__ == "__main__":
    main()
