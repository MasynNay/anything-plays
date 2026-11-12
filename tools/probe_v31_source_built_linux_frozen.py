"""Test an independently source-built camera-only OpenCV wheel in a throwaway 3.1 GUI.

No user installation, released installer, DMG, GitHub Release or original
wheel is modified. All inputs are exact hash-pinned/private evidence only.
The frozen Stream Mode GUI and real camera remain separate acceptance gates.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import zipfile

from tools.probe_v31_v20_camera_only_swap import checked_scratch_path, SOURCE_SHA, digest
from tools.qa_v31_linux_camera_only_wheel import SOURCE_SHA256, SOURCE_NAME, STATUS as WHEEL_STATUS
from tools.verify_custom_opencv_wheel import verify_custom_wheel

STATUS = "PASSED_PRIVATE_SOURCE_WHEEL_IN_DISPOSABLE_FULL_3_1_LINUX_UNAPPROVED"
ORIGINAL_INSTALLER = "anything-plays-31_3.1.0_amd64.deb"
ORIGINAL_FULL_STATUS = "PRIVATE_FULL_3_1_0_FINAL_IDENTITY_QA"


def require_fields(data, expected, *, label):
    if not isinstance(data, dict):
        raise ValueError(label + " must be a JSON receipt")
    for key, value in expected.items():
        if type(data.get(key)) is not type(value) or data[key] != value:
            raise ValueError(label + " receipt mismatch: " + key)


def safe_receipt(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("No original bounded receipt file")
    obj = json.loads(path.read_text("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Receipt must be an object")
    return obj


def source_wheel_swap(*, app, scratch, installer, full_receipt, source,
                      wheel, wheel_receipt, environ=None, expected_source_sha=SOURCE_SHA256):
    env = os.environ if environ is None else environ
    scratch = Path(scratch).absolute()
    if (env.get("CI") != "true" or env.get("AP_V31_DISPOSABLE_QA") != "1"
            or env.get("AP_V31_QA_SANDBOX") != str(scratch.resolve())):
        raise ValueError("Only isolated GitHub CI scratch installations may be modified")
    app = checked_scratch_path(app, scratch)
    installer = Path(installer)
    source = Path(source)
    wheel = Path(wheel)
    if any(x.is_symlink() or not x.is_file() for x in (installer, source, wheel)):
        raise ValueError("A supplied artifact is missing, linked or not a file")
    if installer.name != ORIGINAL_INSTALLER or installer.stat().st_size < 1024 * 1024:
        raise ValueError("Expected the exact final full Linux 3.1 original installer")
    if source.name != SOURCE_NAME or digest(source) != expected_source_sha:
        raise ValueError("Pinned official OpenCV source bytes do not match")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_source_sha):
        raise ValueError("Source SHA256 must be lower-case hex")
    receipt = safe_receipt(full_receipt)
    require_fields(receipt, {
        "status": ORIGINAL_FULL_STATUS, "target": "linux-x64",
        "source_preview_revision": SOURCE_SHA,
        "installer": ORIGINAL_INSTALLER,
        "sha256": digest(installer),
        "native_core_count": 11, "console_profiles": 18,
        "identity_channel": "final_candidate",
        "settings_namespace": "anything-plays-31",
        "public_release_approved": False, "final_release_approved": False,
    }, label="original full installer")
    w = safe_receipt(wheel_receipt)
    require_fields(w, {
        "status": WHEEL_STATUS, "target": "linux-x64",
        "source": SOURCE_NAME, "source_sha256": expected_source_sha,
        "package": "opencv-python-headless", "version": "4.14.0.94",
        "wheel": wheel.name, "wheel_sha256": digest(wheel),
        "opencv_native_module_imported": True,
        "opencv_linux_v4l2_backend_available": True,
        "opencv_ffmpeg_backend_disabled": True,
        "public_release_approved": False, "redistribution_approved": False,
        "tested_in_actual_frozen_3_1_app": False,
    }, label="source-built camera-only wheel")
    verified = verify_custom_wheel(wheel, w["wheel_sha256"], "linux-x86_64")
    if verified["redistribution_approved"] is not False:
        raise ValueError("A source-wheel input cannot grant rights")
    if not app.is_dir() or not (app / "AnythingPlays").is_file():
        raise ValueError("Expected extracted fully assembled frozen GUI")
    original = app / "_internal/cv2/cv2.abi3.so"
    codec_dir = app / "_internal/opencv_python_headless.libs"
    checked_scratch_path(original, scratch)
    checked_scratch_path(codec_dir, scratch)
    if (not original.is_file() or original.is_symlink() or
            original.stat().st_size < 1024 or not codec_dir.is_dir()):
        raise ValueError("Original frozen cv2 and codec folder not present")
    dependency_paths = list(codec_dir.rglob("*"))
    if any(x.is_symlink() for x in dependency_paths):
        raise ValueError("Do not remove linked native dependency trees")
    old_files = [x for x in dependency_paths if x.is_file()]
    codec_names = [x.name.lower() for x in old_files]
    if not any("libavcodec" in name for name in codec_names):
        raise ValueError("Expected original FFmpeg-bearing OpenCV wheel missing")
    with zipfile.ZipFile(wheel) as archive:
        entries = [name for name in archive.namelist()
                   if name == "cv2/cv2.abi3.so"]
        if len(entries) != 1 or archive.getinfo(entries[0]).file_size < 1024:
            raise ValueError("Exactly one source-built native OpenCV extension is required")
        replaced_bytes = archive.read(entries[0])
    previous_hash = digest(original)
    # Unchanged bytes of the SOURCE-BUILT wheel, not repackaged public 2.0.
    tmp = original.with_name("cv2.abi3.so.temp-source-qa")
    if tmp.exists() or tmp.is_symlink():
        raise ValueError("Source-wheel scratch destination already exists")
    try:
        tmp.write_bytes(replaced_bytes)
        src_digest = digest(tmp)
        if src_digest == previous_hash:
            raise ValueError("Source-built cv2 unexpectedly matches stock codec build")
        os.replace(tmp, original)
    finally:
        if tmp.exists():
            tmp.unlink()
    # The existing isolated Linux 2.0 camera-only frozen GUI check proved
    # that this stock codec tree is not needed for ordinary Tk/Stream startup.
    # Verify the new source wheel in that same separate scratch environment.
    shutil.rmtree(codec_dir)
    if digest(original) != src_digest or codec_dir.exists():
        raise ValueError("Disposable full application was not modified as expected")
    return {
        "schema_version": 1, "status": STATUS, "target": "linux-x64",
        "original_final_source_revision": SOURCE_SHA,
        "original_full_installer_sha256": digest(installer),
        "source_wheel_sha256": digest(wheel),
        "source_wheel_native_sha256": src_digest,
        "stock_opencv_native_sha256": previous_hash,
        "removed_ffmpeg_related_names": sorted(name for name in codec_names
                                                if "libav" in name or "libsw" in name),
        "removed_original_dependency_count": len(old_files),
        "package_python_abi": verified["target"],
        "release_asset_modified": False,
        "frozen_gui_test_result_pending": True,
        "physical_camera_tested": False,
        "actual_gameplay_tested": False,
        "native_corresponding_source_approved": False,
        "redistribution_approved": False,
        "public_release_approved": False,
    }
