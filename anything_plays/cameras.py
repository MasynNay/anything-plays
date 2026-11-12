"""Discover OpenCV cameras and resolve platform-specific device labels.

Camera probing is deliberately conservative: each capture is released even
when a frame cannot be read, and macOS probing respects AVFoundation counts.
"""

import os
import platform
import time

import cv2


def name_for(index):
    """Return the best available human-readable label for a camera index."""
    system = platform.system()
    if system == 'Linux':
        path = f'/sys/class/video4linux/video{index}/name'
        if os.path.isfile(path):
            try:
                with open(path, encoding='utf-8') as camera_name_file:
                    return camera_name_file.read().strip()
            except OSError:
                pass
    if system == 'Darwin':
        # OpenCV does not expose camera display names; list devices via AVFoundation.
        try:
            from AVFoundation import AVCaptureDevice, AVMediaTypeVideo
            devices = AVCaptureDevice.devicesWithMediaType_(AVMediaTypeVideo)
            if index < len(devices):
                return str(devices[index].localizedName())
        except Exception:
            pass
    return f'Camera {index}'


def discover(max_index=8):
    """Probe available devices, releasing each capture even on read failure."""
    result = []
    backend = (cv2.CAP_DSHOW if os.name == 'nt' else
               cv2.CAP_AVFOUNDATION if platform.system() == 'Darwin' else cv2.CAP_ANY)
    # On macOS, AVFoundation uses contiguous device indexes; probing beyond
    # available devices emits noisy errors and can delay camera permission.
    if platform.system() == 'Darwin':
        try:
            from AVFoundation import AVCaptureDevice, AVMediaTypeVideo
            devices = AVCaptureDevice.devicesWithMediaType_(AVMediaTypeVideo)
            if devices is not None:
                # An explicit empty AVFoundation list means there are no
                # devices. Do not probe eight missing indices, which can
                # repeatedly wake permission prompts and stall discovery.
                max_index = min(max_index, len(devices))
        except Exception:
            max_index = min(max_index, 3)
    for index in range(max_index):
        attempts = 3 if index == 0 else 2
        for attempt in range(attempts):
            cap = None
            try:
                # Devices can vanish during enumeration, construction,
                # isOpened, read or even release. One bad webcam must not
                # prevent healthy devices at later indices being discovered.
                cap = cv2.VideoCapture(index, backend)
                if cap is not None and cap.isOpened():
                    ok, _ = cap.read()
                    if ok:
                        result.append((index, name_for(index)))
                        break
            except (cv2.error, OSError, RuntimeError):
                # Treat a failed device as a local transient discovery error.
                # Camera selection stays disabled until a real successful read.
                pass
            finally:
                if cap is not None:
                    try:
                        cap.release()
                    except (cv2.error, OSError, RuntimeError):
                        pass
            if attempt + 1 < attempts:
                time.sleep(.25)
    return result
