"""Verify the lean OpenCV wheel still supports the user's camera backend.

Anything Plays owns its GUI with Tkinter. Requiring a headless OpenCV wheel
avoids packaging extra Qt/X11 components, but must not remove video capture.
This checks compile-time backend availability; it cannot test real cameras in CI.
"""

import os
import re
import sys

def verify_opencv_build(cv2_module=None, platform=None):
    if cv2_module is None:
        import cv2 as cv2_module
    if platform is None:
        platform = sys.platform
    info = cv2_module.getBuildInformation()
    gui = re.search(r"^\s*GUI:\s*(\S+)", info, flags=re.MULTILINE)
    detected_gui = gui.group(1).upper() if gui else "UNKNOWN"
    # Official macOS headless wheels can still report COCOA due to native
    # Apple frameworks; bundled Qt GUI libraries remain disallowed.
    allowed_gui = {"NONE", "COCOA"} if platform == "darwin" else {"NONE"}
    if detected_gui not in allowed_gui:
        raise RuntimeError(f"OpenCV must be built without bundled Qt/GUI extras "
                           f"(observed: {detected_gui})")
    ffmpeg = re.search(r"^\\s*FFMPEG:\\s*(YES|NO)", info, flags=re.MULTILINE)
    ffmpeg_status = ffmpeg.group(1) if ffmpeg else "UNKNOWN"
    if os.environ.get("AP_REQUIRE_OPENCV_FFMPEG_OFF") == "1" and ffmpeg_status != "NO":
        raise RuntimeError(f"Camera-only OpenCV requires FFMPEG: NO; got {ffmpeg_status}")
    backend_by_platform = {
        "win32": ("DirectShow", "CAP_DSHOW"),
        "darwin": ("AVFoundation", "CAP_AVFOUNDATION"),
    }
    name, constant = backend_by_platform.get(platform, ("V4L2", "CAP_V4L2"))
    backend_id = getattr(cv2_module, constant, None)
    if backend_id is None or not cv2_module.videoio_registry.hasBackend(backend_id):
        raise RuntimeError(f"Headless OpenCV does not support required {name} capture backend")
    result = {"opencv_version": cv2_module.__version__, "gui": detected_gui,
              "capture_backend": name, "backend_id": backend_id,
              "ffmpeg_enabled": ffmpeg_status,
              "camera_hardware_tested": False}
    print(f"OpenCV {result['opencv_version']} headless: {name} capture backend available; "
          "camera hardware untested")
    return result


if __name__ == "__main__":
    verify_opencv_build()
