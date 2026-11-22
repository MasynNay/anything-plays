"""3.3.1 camera scan must not mark empty/malformed driver reads as usable.

No real video devices, permissions, frames or native drivers are accessed.
"""
import unittest
from unittest.mock import Mock, patch

import numpy as np

from anything_plays import cameras


class CameraValidFrameDiscoveryTests(unittest.TestCase):
    def _scan(self, first, second):
        opens = []
        def capture(index, _backend):
            opens.append(index)
            if index == 0:
                return first
            if index == 1:
                return second
            raise AssertionError("unexpected third camera index")
        with (
            patch.object(cameras.cv2, "VideoCapture", side_effect=capture),
            patch.object(cameras, "name_for",
                         side_effect=lambda index: f"Camera {index}"),
            patch.object(cameras.time, "sleep") as sleep,
            patch.object(cameras.platform, "system", return_value="Linux"),
        ):
            found = cameras.discover(max_index=2)
        return found, opens, sleep

    @staticmethod
    def _opened(read_value=None, *, error=None):
        camera = Mock()
        camera.isOpened.return_value = True
        if error is not None:
            camera.read.side_effect = error
        else:
            camera.read.return_value = read_value
        return camera

    def test_success_with_no_frame_does_not_register_phantom_webcam(self):
        first = self._opened((True, None))
        second = self._opened((True, np.zeros((8, 8, 3), dtype=np.uint8)))
        found, opens, sleep = self._scan(first, second)
        self.assertEqual(found, [(1, "Camera 1")])
        self.assertEqual(opens, [0, 0, 0, 1])
        self.assertEqual(first.release.call_count, 3)
        second.release.assert_called_once()
        self.assertEqual(sleep.call_count, 2)

    def test_success_with_empty_numpy_buffer_is_not_usable(self):
        first = self._opened((True, np.empty((0, 0, 3), dtype=np.uint8)))
        second = self._opened((True, np.zeros((2, 2, 3), dtype=np.uint8)))
        found, opens, _ = self._scan(first, second)
        self.assertEqual(found, [(1, "Camera 1")])
        self.assertEqual(opens, [0, 0, 0, 1])
        self.assertEqual(first.release.call_count, 3)

    def test_failed_read_tuple_isolated_from_other_devices(self):
        first = self._opened((True,))  # A buggy backend omitted the frame.
        second = self._opened((True, np.zeros((4, 4, 3), dtype=np.uint8)))
        found, opens, _ = self._scan(first, second)
        self.assertEqual(found, [(1, "Camera 1")])
        self.assertEqual(opens, [0, 0, 0, 1])
        self.assertEqual(first.release.call_count, 3)

    def test_vendor_specific_read_exception_does_not_hide_later_camera(self):
        class BrokenVendorRead(Exception):
            pass

        first = self._opened(error=BrokenVendorRead("private USB serial"))
        second = self._opened((True, np.zeros((2, 2, 3), dtype=np.uint8)))
        found, opens, _ = self._scan(first, second)
        self.assertEqual(found, [(1, "Camera 1")])
        self.assertEqual(opens, [0, 0, 0, 1])
        self.assertEqual(first.release.call_count, 3)

    def test_unexpected_release_exception_cannot_abort_scan(self):
        class FailedVendorRelease(Exception):
            pass

        first = self._opened((False, None))
        first.release.side_effect = FailedVendorRelease("driver gone")
        second = self._opened((True, np.zeros((2, 2, 3), dtype=np.uint8)))
        found, opens, _ = self._scan(first, second)
        self.assertEqual(found, [(1, "Camera 1")])
        self.assertEqual(opens, [0, 0, 0, 1])
        self.assertEqual(first.release.call_count, 3)
        second.release.assert_called_once()

    def test_valid_black_image_is_still_a_healthy_webcam(self):
        first = self._opened((True, np.zeros((8, 8, 3), dtype=np.uint8)))
        second = self._opened((True, np.ones((8, 8, 3), dtype=np.uint8)))
        found, opens, sleep = self._scan(first, second)
        self.assertEqual(found, [(0, "Camera 0"), (1, "Camera 1")])
        self.assertEqual(opens, [0, 1])
        self.assertEqual(sleep.call_count, 0)
        first.release.assert_called_once()
        second.release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
