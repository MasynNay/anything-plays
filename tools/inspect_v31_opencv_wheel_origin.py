"""Trace the extra Apple Silicon SDL2 library to a pinned PyPI OpenCV wheel.

The pygame wheel explains 120/121 frozen native Mach-O __text sections.
The remaining file is cv2's own SDL2 image. Compare ONLY the machine-code
section and retain exact original wheel digests. The binary's complete
corresponding source, linked transitive deps and LGPL obligations are not
certified by matching compiled sections.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from tools.inspect_v31_macos_text_provenance import (
    executable_text_fingerprint, sha256_file, MAX_NATIVE_BYTES,
)

WHEEL = "opencv_python_headless-4.14.0.94-cp37-abi3-macosx_13_0_arm64.whl"
WHEEL_SHA = "bc7db37dc234f7bb3190a158fd9dd750357246fc7d8adb23698843ef721a993b"
RC_APP_COMMIT = "26de1e1ad1b701d0735e085158347f8c213ce437"
MISSING_PATH = "Contents/Frameworks/cv2/__dot__dylibs/libSDL2-2.0.0.dylib"
MISSING_SHA = "92d781dfdf0935e05c9cb11359ed35624e4dabe587149f5989927750c4c36e78"
TEXT_SHA = "93485b815db3d2aec3ae06cce142e167fe96d9eb8d3bf906b3585fcad4756afb"
TEXT_LENGTH = 840688
EXPECTED_PACKAGE_NATIVE_COUNT = 121
EXPECTED_PYGAME_MATCHED_COUNT = 120
MIN_WHEEL_BYTES = 40_000_000
MAX_WHEEL_BYTES = 60_000_000


def inspect(original_arm_report, wheel):
    """Refuse an incorrect frozen source report or an altered wheel."""
    report = original_arm_report
    if (report.get("status") != "PUBLIC_RC1_READ_ONLY_MACOS_TEXT_SECTION_AUDIT"
            or report.get("target") != "macos-arm64"
            or report.get("source_app_commit") != RC_APP_COMMIT
            or report.get("installed_frozen_native_files_audited") != EXPECTED_PACKAGE_NATIVE_COUNT
            or report.get("exact_executable_text_section_matches") != EXPECTED_PYGAME_MATCHED_COUNT
            or report.get("unmatched_installed_native_sections") != 1
            or report.get("redistribution_approved") is not False
            or report.get("stable_3_1_release_approved") is not False):
        raise ValueError("Wrong or falsely approved original signed Mac audit")
    unmatched = [r for r in report.get("native_file_evidence", [])
                 if not r.get("upstream_matching_wheel_members")]
    if len(unmatched) != 1 or len(report["native_file_evidence"]) != EXPECTED_PACKAGE_NATIVE_COUNT:
        raise ValueError("Wrong frozen native candidate coverage")
    leftover = unmatched[0]
    if (leftover.get("path") != MISSING_PATH
            or leftover.get("sha256") != MISSING_SHA
            or leftover.get("text_section") != {"size": TEXT_LENGTH, "sha256": TEXT_SHA}):
        raise ValueError("Unexpected, forged or changed extra cv2 SDL2 native")
    wheel = Path(wheel)
    if (wheel.is_symlink() or not wheel.is_file()
            or wheel.name != WHEEL or not MIN_WHEEL_BYTES <= wheel.stat().st_size <= MAX_WHEEL_BYTES
            or sha256_file(wheel) != WHEEL_SHA):
        raise ValueError("OpenCV wheel does not match the official PyPI hash")
    candidates = []
    with zipfile.ZipFile(wheel) as data:
        entries = set()
        for item in data.infolist():
            name = item.filename
            if (name in entries or name.startswith("/") or "\\" in name
                    or ".." in name.split("/")
                    or item.file_size > MAX_NATIVE_BYTES):
                raise ValueError("Invalid official OpenCV wheel archive entry")
            entries.add(name)
            if (not name.startswith("cv2/") or "/.dylibs/" not in name
                    or not name.endswith("/libSDL2-2.0.0.dylib")):
                continue
            text = executable_text_fingerprint(data.read(item), "arm64")
            if text:
                candidates.append({"wheel_member": name, "text_section": text,
                                   "matches_frozen_signed_binary":
                                       text == leftover["text_section"]})
    if len(candidates) != 1:
        raise ValueError("Expected precisely one original ARM OpenCV SDL2 dylib")
    match = candidates[0]["matches_frozen_signed_binary"]
    return {
        "schema_version": 1,
        "status": "PUBLIC_3_1_RC1_SIGNED_OPENCV_SDL_CODE_PROVENANCE_AUDIT",
        "target": "macos-arm64",
        "source_app_commit": RC_APP_COMMIT,
        "opencv_package_version": "4.14.0.94",
        "official_opencv_wheel": WHEEL,
        "official_opencv_wheel_sha256": WHEEL_SHA,
        "signed_cv2_dylib": MISSING_PATH,
        "signed_cv2_dylib_sha256": MISSING_SHA,
        "wheel_native_text_comparison": candidates[0],
        "original_pygame_code_section_matches": EXPECTED_PYGAME_MATCHED_COUNT,
        "additional_opencv_code_section_match": bool(match),
        "total_native_code_section_matches": EXPECTED_PYGAME_MATCHED_COUNT + int(match),
        "installed_native_candidates": EXPECTED_PACKAGE_NATIVE_COUNT,
        "wheel_file_complete_binary_identity_verified": False,
        "upstream_opencv_sdl_source_tree_correspondence_verified": False,
        "complete_transitive_license_reviewed": False,
        "lgpl_relinking_verified": False,
        "redistribution_approved": False,
        "stable_3_1_release_approved": False,
        "interpretation": "Identical executable sections in original published wheels; not complete binary correspondence or source/relinking certification",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--signed-report", type=Path, required=True)
    p.add_argument("--wheel", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    r = json.loads(args.signed_report.read_text("utf-8"))
    result = inspect(r, args.wheel)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    print("Exact OpenCV SDL text-section match:", result["additional_opencv_code_section_match"])
    print("Total native code sections associated with official wheels:",
          result["total_native_code_section_matches"],
          "/", result["installed_native_candidates"])
    print("Corresponding source and LGPL release approval: NOT VERIFIED")


if __name__ == "__main__":
    main()
