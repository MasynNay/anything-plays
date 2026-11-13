"""Require authentic FFmpeg-disabled camera-only OpenCV source receipts.

This reuses independently verified original source wheels from the exact
public 3.1.0 clean build. A stock/FFmpeg-enabled cv2 build must never silently
replace those wheels in eventual 3.1.1 public binary packaging.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from tools.qa_v31_linux_camera_only_wheel import SOURCE_SHA256

SOURCE_RUN_BY_TARGET = {
    "linux-x64": 43133383864,
    "windows-x64": 43138596964,
    "macos-arm64": 43137079614,
    "macos-x64": 43137079614,
}
FULL_SHA = re.compile(r"[a-f0-9]{64}\Z")


def require_pinned_native_camera_wheel(receipt_path, target):
    if target not in SOURCE_RUN_BY_TARGET:
        raise ValueError("Unsupported camera wheel target")
    path = Path(receipt_path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 1024*1024:
        raise ValueError("Missing original-source OpenCV wheel receipt")
    report = json.loads(path.read_text("utf-8"))
    if not isinstance(report, dict):
        raise ValueError("Invalid camera receipt")
    expected = {
        "target": target,
        "source_ci_run_id": SOURCE_RUN_BY_TARGET[target],
        "source_sha256": SOURCE_SHA256,
        "native_camera_capture_backend_proven": True,
        "frozen_installer_tested": False,
        "redistribution_approved": False,
        "public_release_approved": False,
    }
    for key, value in expected.items():
        if type(report.get(key)) is not type(value) or report[key] != value:
            raise ValueError("Camera source wheel receipt mismatch: " + key)
    wheel_sha = report.get("native_wheel_sha256")
    if not isinstance(wheel_sha, str) or FULL_SHA.fullmatch(wheel_sha) is None:
        raise ValueError("Missing immutable source-built native wheel hash")
    return report
