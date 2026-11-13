"""Stage a verifiable, original native 3.1.1 release REVIEW, never publish.

Input is FOUR full stable-update installers, their original SHA/core receipts
and four real frozen-Tk startup receipts from a SINGLE successful source SHA.
Bundle the byte-identical 3.1.0 LGPL upstream source companion ONLY as an
explicitly shared source reference; do not relabel its original 3.1.0 manifest
as new 3.1.1 source. Corresponding-source/legal acceptance is a separate gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil

from tools.verify_v311_installed_smoke import PASSED_STATUS, QA_STATUS
from tools.verify_v311_stable_source_stage import INSTALLERS, digest

SOURCE_ZIP = "AnythingPlays-3.1.0-PYGAME-SDL-MPG123-ORIGINAL-SOURCE.zip"
SOURCE_ZIP_SHA = "469b75685b385a7992f018d04bc4ddb1ffa06b061b6471cf50ae4fcda6e746d8"
OLD_SHA = {
    "linux-x64": "e91bdb3be315a86a37144cf8480822d9677bd06a013712bc128bc4b12915f55e",
    "windows-x64": "574b5fda1e6cb1a708fb910271dc80fb6671f12c2013fb69076755b6c0a12bb0",
    "macos-arm64": "ddec3be8356e0b1729ff0a4131bc362128739fe39a1cdc48dfd83921feb8e49a",
    "macos-x64": "ed7dd44e457b1a6c5458f7f6dce54089c98401418c1cc02d145e36f68494bae9",
}
REPORT_NAMES = {
    "linux-x64": "V311_FULL_LINUX_QA_RECEIPT.json",
    "windows-x64": "V311_FULL_WINDOWS_QA_RECEIPT.json",
    "macos-arm64": "V311_FULL_MACOS_QA_RECEIPT.json",
    "macos-x64": "V311_FULL_MACOS_QA_RECEIPT.json",
}
STAGED_STATUS = "PRIVATE_3_1_1_EIGHT_ORIGINAL_ASSETS_FOR_REVIEW_NOT_RELEASED"
SOURCE_RE = re.compile(r"[a-f0-9]{40}\Z")


def contained_one(root, name):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Original per-host artifact folder missing or linked")
    files = [x for x in root.rglob(name) if x.is_file()]
    if len(files) != 1:
        raise ValueError("Expected precisely one native receipt or package: " + name)
    found = files[0]
    if (found.is_symlink() or not found.resolve().is_relative_to(root.resolve())):
        raise ValueError("Unsafe linked or escaping artifact: " + name)
    return found


def checked_json(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or not 0 < p.stat().st_size < 1024*1024:
        raise ValueError("Native QA receipt missing or not size-bounded")
    result = json.loads(p.read_text("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Native QA receipt is not a JSON object")
    return result


def assemble(root, source_zip, source_sha, output):
    root, source_zip, output = Path(root), Path(source_zip), Path(output)
    if (not isinstance(source_sha, str) or SOURCE_RE.fullmatch(source_sha) is None
            or not root.is_dir() or root.is_symlink()):
        raise ValueError("Original four-platform artifacts and exact source SHA required")
    if output.exists() or output.is_symlink():
        raise ValueError("Refuse to mutate or overwrite a prior release staging folder")
    if (source_zip.name != SOURCE_ZIP or not source_zip.is_file()
            or source_zip.is_symlink()
            or digest(source_zip) != SOURCE_ZIP_SHA):
        raise ValueError("Only the original public 3.1.0 LGPL source companion is accepted")
    native_rows = []
    candidates = {}
    for target, name in INSTALLERS.items():
        directory = root / target
        file = contained_one(directory, name)
        receipt = checked_json(contained_one(directory, REPORT_NAMES[target]))
        installed = checked_json(contained_one(directory, "V311_INSTALLED_FULL_GUI_RECEIPT.json"))
        if file.stat().st_size < 1024*1024:
            raise ValueError("Incomplete full stable installer: " + target)
        binary_sha = digest(file)
        baseline_key = ("baseline_3_1_0_sha256" if target == "linux-x64"
                        else "old_stable_sha256")
        hash_key = ("installer_sha256" if target == "linux-x64" else "sha256")
        source_key = ("app_source_sha" if target == "linux-x64" else "new_source_revision")
        expected = {
            "status": QA_STATUS[target], "target": target, "installer": name,
            "version": "3.1.1", "identity_channel": "v311_stable_candidate",
            "settings_namespace": "anything-plays-31",
            "stable_in_place_update": True,
            "native_core_count": 11, "console_profiles": 18,
            "public_release_approved": False,
            "full_four_platform_311_verified": False,
            hash_key: binary_sha,
            source_key: source_sha,
            baseline_key: OLD_SHA[target],
        }
        for key, value in expected.items():
            if type(receipt.get(key)) is not type(value) or receipt[key] != value:
                raise ValueError("Full native 3.1.1 source/core mismatch: "+target+"/"+key)
        camera_sha = receipt.get("sourcebuilt_ffmpeg_off_camera_wheel_sha256")
        if (not isinstance(camera_sha, str) or re.fullmatch("[a-f0-9]{64}",camera_sha) is None):
            raise ValueError("Original camera-only OpenCV wheel absent: "+target)
        expected_installed = {
            "status": PASSED_STATUS, "target": target, "installer": name,
            "source_revision": source_sha, "installer_sha256": binary_sha,
            "native_core_count": 11, "console_profiles": 18,
            "frozen_desktop_started": True,
            "stream_mode_started_and_closed": True,
            "stable_settings_namespace_retained": True,
            "hardware_gameplay_verified": False,
            "physical_camera_verified": False,
            "physical_controller_verified": False,
            "third_party_relinking_verified": False,
            "public_release_approved": False,
        }
        for key, value in expected_installed.items():
            if type(installed.get(key)) is not type(value) or installed[key] != value:
                raise ValueError("Actual installed 3.1.1 UI QA mismatch: "+target+"/"+key)
        candidates[target] = file
        native_rows.append({
            "target":target,"installer":name,"sha256":binary_sha,
            "bytes":file.stat().st_size, "app_source_sha":source_sha,
            "baseline_310_sha256":OLD_SHA[target],
            "sourcebuilt_ffmpeg_off_camera_sha256":camera_sha,
            "installed_frozen_gui_verified":True,
            "native_core_count":11,"console_profiles":18,
        })
    output.mkdir(parents=True,exist_ok=False)
    for item in native_rows:
        file = candidates[item["target"]]
        shutil.copyfile(file, output/file.name)
        if digest(output/file.name) != item["sha256"]:
            raise ValueError("The private staged installer changed during copy")
    shutil.copyfile(source_zip, output/SOURCE_ZIP)
    if digest(output/SOURCE_ZIP) != SOURCE_ZIP_SHA:
        raise ValueError("Shared original source companion changed during copy")
    report = {
        "schema_version":1, "status":STAGED_STATUS,
        "version":"3.1.1","source_revision":source_sha,
        "original_310_shared_source_companion":SOURCE_ZIP,
        "original_310_shared_source_sha256":SOURCE_ZIP_SHA,
        "original_310_source_companion_manifest_relabelled":False,
        "native_installers":native_rows,
        "sourcebuilt_camera_only_opencv_receipts_required":True,
        "real_frozen_gui_tests_passed_on_four_native_hosts":True,
        "installed_native_source_cores":11,"supported_console_profiles":18,
        "physical_controller_or_camera_approved":False,
        "universal_retail_gameplay_approved":False,
        "complete_corresponding_source_and_relink_review_approved":False,
        "public_release_approved":False,
    }
    (output/"V311_PRIVATE_RELEASE_REVIEW_MANIFEST.json").write_text(
        json.dumps(report, indent=2)+"\n","utf-8")
    guide = """# Anything Plays 3.1.1 — Corresponding-source access and scope (review copy)

**PRIVATE PRE-PUBLICATION REVIEW. This file alone grants no release approval.**

The four newly built 3.1.1 applications share original-source, unchanged
Libretro core bytes with the corresponding SHA-verified 3.1.0 platform.
The exact code revision for the new application is:
`{sha}`.

Python/SDL/pygame-ce/mpg123 original upstream source packages are carried
forward BYTE FOR BYTE from stable 3.1.0 in `{source}` at SHA-256
`{digest}`. Its internal manifest honestly names the original 3.1.0
application. The shared-source assertion must remain conditional on native
library versions/hashes actually matching the two releases; this private
staging file is not independent proof of legal or relinking compliance.

Upstream emulator original-source archives and terms remain available from
https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources
and the LGPL recipient rebuild/replacement instructions from
https://github.com/MasynNay/anything-plays/blob/main/docs/V3_1_LGPL_REBUILD_REPLACEMENT.md

- Native bundled Snes9x has **noncommercial** restrictions; neither the
  application's MIT license nor this bundle overrides emulator terms.
- Original OpenCV 4.14.0.94 wheels were built with FFmpeg disabled from pinned
  source; per-host exact native wheel hashes are in the QA manifest.
- **No physical webcam, controller, retail-ROM save/audio or long-session
  acceptance is claimed**, despite actual native frozen UI tests.
- Public distribution, LGPL recipient-access obligations and final release
  notices require separate review and acceptance before publishing.
""".format(sha=source_sha,source=SOURCE_ZIP,digest=SOURCE_ZIP_SHA)
    (output/"V311_SOURCE_ACCESS_REVIEW_DRAFT.md").write_text(guide,"utf-8")
    paths=[x for x in output.iterdir() if x.is_file()]
    (output/"SHA256SUMS.txt").write_text(
        "".join(digest(p)+"  "+p.name+"\n" for p in sorted(paths,key=lambda v:v.name)),
        "ascii")
    # A README in the review folder is intentionally NOT copied to the public
    # release. Status must remain unapproved until independent gate review.
    assert set(x.name for x in output.iterdir())=={
        *INSTALLERS.values(), SOURCE_ZIP, "V311_PRIVATE_RELEASE_REVIEW_MANIFEST.json",
        "V311_SOURCE_ACCESS_REVIEW_DRAFT.md","SHA256SUMS.txt",
    }
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--original-source",required=True,type=Path)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    manifest=assemble(a.root,a.original_source,a.source_sha,a.output)
    print("Staged",len(manifest["native_installers"]),"exact original-source full",
          "3.1.1 verified GUI packages as PRIVATE REVIEW, NOT PUBLIC")


if __name__=="__main__":
    main()
