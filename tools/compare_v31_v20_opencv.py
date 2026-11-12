"""Check the exact public 2.0 camera-only OpenCV runtime against 3.1.

Uses already SHA-verified unmodified public 2.0.0 and exact full private
3.1.0 native installers on all four hosts. This is NOT a proof of Python
ABI compatibility, binary replacement rights, or a permitted distribution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tools.compare_v31_v30_opencv import scan

STATUS="UNAPPROVED_PUBLIC_2_0_CAMERA_ONLY_OPENCV_REUSE_REVIEW"
SOURCE_SHA="d852de9a513f83a329c14647ddc86bf3690fb5f5"


def compare(baseline, final, *, target, source_sha):
    if source_sha != SOURCE_SHA:
        raise ValueError("Final 3.1.0 frozen build source is not the exact QA revision")
    if target not in ("linux-x64","windows-x64","macos-arm64","macos-x64"):
        raise ValueError("Unknown native platform")
    old = scan(baseline)
    new = scan(final)
    old_names = {p.rsplit("/",1)[-1].lower() for p in old["native_filenames"]}
    new_names = {p.rsplit("/",1)[-1].lower() for p in new["native_filenames"]}
    original_hashes = {f["sha256"] for f in old["files"]}
    return {
        "schema_version":1,"status":STATUS,"target":target,
        "source_revision_3_1":source_sha,
        "public_2_0_opencv":old,"private_3_1_opencv":new,
        "common_native_filenames":sorted(old_names & new_names),
        "common_content_sha256_count":sum(f["sha256"] in original_hashes
                                          for f in new["files"]),
        "public_2_0_ffmpeg_binary_name_candidates":old["risky_codec_paths"],
        "private_3_1_ffmpeg_binary_name_candidates":new["risky_codec_paths"],
        "candidate_2_0_camera_only_runtime_not_assumed_reusable":True,
        "needs_native_import_camera_backend_and_four_platform_gui_QA":True,
        "corresponding_source_and_relinking_approved":False,
        "public_release_approved":False,
        "reference_original_opencv_source":"v2.0.0/opencv_python_headless-4.14.0.94.tar.gz",
        "reference_windows_patch":"v2.0.0/WINDOWS_OPENCV_SETUP_PATCH.diff",
        "note":"Original v2.0 package and exact final v3.1 OpenCV files are inventoried "
               "without rewriting either. A separately rebuilt 3.1.0 package "
               "needs fresh native linkage, real Tk/camera backend and legal QA.",
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--final",type=Path,required=True)
    p.add_argument("--target",required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    report=compare(a.baseline,a.final,target=a.target,source_sha=a.source_sha)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n","utf-8")
    print(a.target,"public 2.0 OpenCV:",report["public_2_0_opencv"]["native_file_count"],
          "private 3.1 OpenCV:",report["private_3_1_opencv"]["native_file_count"])
    print("FFmpeg/GPL-name candidates 2.0:",
          len(report["public_2_0_ffmpeg_binary_name_candidates"]),
          "3.1:",len(report["private_3_1_ffmpeg_binary_name_candidates"]))
    print("No replacement or release approval assumed.")


if __name__=="__main__":
    main()
