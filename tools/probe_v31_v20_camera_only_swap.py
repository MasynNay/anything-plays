"""Replace OpenCV in an *ephemeral Linux 3.1 install* using public 2.0.

This is deliberately not an installer repackager or distribution approval.
The caller must have SHA-verified both original package files and extracted
them under an explicitly designated disposable scratch directory. The
operation cannot run against the owner's real installed application.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

SOURCE_SHA = "d852de9a513f83a329c14647ddc86bf3690fb5f5"
STATUS = "UNAPPROVED_TEMP_LINUX_3_1_0_FROZEN_CAMERA_ONLY_OPENCV_SWAP"


def digest(file: Path):
    h = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checked_scratch_path(path, scratch):
    scratch = Path(scratch)
    path = Path(path)
    if (not scratch.is_absolute() or not scratch.is_dir()
            or scratch.is_symlink()
            or scratch.resolve() in (Path("/"), Path.home().resolve())):
        raise ValueError("Refusing missing/non-isolated disposable QA sandbox")
    candidate = path.resolve(strict=True)
    if not candidate.is_relative_to(scratch.resolve()) or path.is_symlink():
        raise ValueError("The original installed app cannot be modified")
    for parent in (path, *list(path.parents)):
        if parent == scratch:
            break
        if parent.is_symlink():
            raise ValueError("Symlink inside scratch extraction")
    return path


def probe(old_app, new_app, *, scratch, source_sha, env=None):
    env = os.environ if env is None else env
    if (env.get("CI") != "true" or env.get("AP_V31_DISPOSABLE_QA") != "1"
            or env.get("AP_V31_QA_SANDBOX") != str(Path(scratch).resolve())):
        raise ValueError("Only explicit isolated CI scratch replacements allowed")
    if source_sha != SOURCE_SHA:
        raise ValueError("Original, unchanged full 3.1.0 QA source revision required")
    old_app = checked_scratch_path(old_app, scratch)
    new_app = checked_scratch_path(new_app, scratch)
    if old_app == new_app:
        raise ValueError("Cannot replace the source installation")
    if not old_app.is_dir() or not new_app.is_dir():
        raise ValueError("Both original public 2.0 and final 3.1 extracts needed")
    old_cv = old_app / "_internal/cv2/cv2.abi3.so"
    new_cv = new_app / "_internal/cv2/cv2.abi3.so"
    codec_dir = new_app / "_internal/opencv_python_headless.libs"
    for path in (old_cv, new_cv):
        checked_scratch_path(path, scratch)
        if not path.is_file() or path.stat().st_size < 1024:
            raise ValueError("Missing actual OpenCV binary")
    checked_scratch_path(codec_dir, scratch)
    if not codec_dir.is_dir():
        raise ValueError("No stock 3.1 OpenCV private dependency tree to remove")
    original_digest = digest(old_cv)
    previous_digest = digest(new_cv)
    if original_digest == previous_digest:
        raise ValueError("Expected distinct original public 2.0 and 3.1 OpenCV images")
    files = list(codec_dir.rglob("*"))
    if not files or any(item.is_symlink() for item in files):
        raise ValueError("Unexpected empty or linked frozen OpenCV dependency tree")
    codec_files = [str(item.relative_to(codec_dir)) for item in files if item.is_file()]
    if not any("libavcodec" in path.lower() for path in codec_files):
        raise ValueError("Expected to demonstrate removing the stock FFmpeg dependency")
    if not (new_app / "AnythingPlays").is_file():
        raise ValueError("Not a complete extracted 3.1 Linux application")
    # Mutate only the throwaway extracted Linux 3.1 package. Never sign,
    # redistribute, or alter any original EXE/DEB/DMG/Release object.
    shutil.copyfile(old_cv, new_cv)
    shutil.rmtree(codec_dir)
    if digest(new_cv) != original_digest or codec_dir.exists():
        raise ValueError("Temporary OpenCV swap did not complete correctly")
    return {
        "schema_version": 1,
        "status": STATUS,
        "target": "linux-x64",
        "source_revision": source_sha,
        "public_2_0_opencv_sha256": original_digest,
        "original_private_3_1_opencv_sha256": previous_digest,
        "temporary_3_1_opencv_sha256": digest(new_cv),
        "removed_stock_opencv_dependency_file_count": len(codec_files),
        "removed_stock_ffmpeg_named_file_count":
            sum("libav" in name.lower() or "libsw" in name.lower() for name in codec_files),
        "new_build_compiled": False,
        "installed_app_source_modified": False,
        "physical_camera_tested": False,
        "installed_gui_tested": False,
        "rebuild_or_relinking_verified": False,
        "public_release_approved": False,
        "release_asset_modified": False,
        "next_step": "Boot the actual swapped frozen binary with isolated Tk/Stream Mode GUI acceptance and verify compiled camera backend separately.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--old-app", type=Path, required=True)
    p.add_argument("--new-app", type=Path, required=True)
    p.add_argument("--sandbox", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    report = probe(a.old_app, a.new_app, scratch=a.sandbox,
                   source_sha=a.source_sha)
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, indent=2)+"\n","utf-8")
    print("Temporary Ubuntu OpenCV 2.0 camera-only extension installed. "
          "Actual frozen GUI and camera capability must still be tested.")


if __name__ == "__main__":
    main()
