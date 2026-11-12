"""FFmpeg-free Linux source-wheel QA must never manufacture release approval."""
from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from tools.qa_v31_linux_camera_only_wheel import (
    SOURCE_NAME, STATUS, make_receipt,
)

class FakeRegistry:
    def __init__(self, ffmpeg=False, camera=True):
        self.ffmpeg, self.camera = ffmpeg, camera

    def hasBackend(self, number):
        return {1900: self.ffmpeg, 200: self.camera}.get(number, False)

class FakeCV2:
    __version__ = "4.14.0"
    CAP_FFMPEG = 1900
    CAP_V4L2 = 200

    def __init__(self, *, ffmpeg=False, camera=True):
        self.ffmpeg, self.videoio_registry = ffmpeg, FakeRegistry(ffmpeg, camera)

    def getBuildInformation(self):
        return "GUI: NONE\nFFMPEG: "+("YES" if self.ffmpeg else "NO")+"\n"


class SourceCameraWheelProofTests(unittest.TestCase):
    def fixture(self, directory):
        p=Path(directory)
        source=p/SOURCE_NAME
        source.write_bytes(b"fake original sdist for regression test only")
        wheel=p/"opencv_python_headless-4.14.0.94-cp37-abi3-linux_x86_64.whl"
        with ZipFile(wheel,"w") as archive:
            archive.writestr(
                "opencv_python_headless-4.14.0.94.dist-info/METADATA",
                "Metadata-Version: 2.1\nName: opencv-python-headless\nVersion: 4.14.0.94\n",
            )
        return source,wheel,hashlib.sha256(source.read_bytes()).hexdigest()

    def test_fake_native_camera_only_import_is_private_not_release(self):
        with TemporaryDirectory() as d:
            source,wheel,digest=self.fixture(d)
            r=make_receipt(source,wheel,native_cv2=FakeCV2(),source_digest=digest)
            self.assertEqual(r["status"],STATUS)
            self.assertTrue(r["opencv_native_module_imported"])
            self.assertTrue(r["opencv_linux_v4l2_backend_available"])
            self.assertTrue(r["opencv_ffmpeg_backend_disabled"])
            for flag in ("physical_camera_tested","replaced_existing_installer",
                         "tested_in_actual_frozen_3_1_app",
                         "all_native_corresponding_source_verified",
                         "redistribution_approved","public_release_approved"):
                self.assertIs(r[flag], False)

    def test_source_digest_or_tag_tampering_rejected(self):
        with TemporaryDirectory() as d:
            source,wheel,digest=self.fixture(d)
            with self.assertRaises(ValueError):
                make_receipt(source,wheel,native_cv2=FakeCV2())
            with self.assertRaises(ValueError):
                make_receipt(source,wheel,native_cv2=FakeCV2(),source_digest="a"*64)
            source.write_bytes(source.read_bytes()+b"tampered")
            with self.assertRaises(ValueError):
                make_receipt(source,wheel,native_cv2=FakeCV2(),source_digest=digest)
        with TemporaryDirectory() as d:
            source,wheel,digest=self.fixture(d)
            wheel.rename(wheel.with_name("bad-wheel.whl"))
            with self.assertRaises(ValueError):
                make_receipt(source,wheel.with_name("bad-wheel.whl"),
                             native_cv2=FakeCV2(),source_digest=digest)

    def test_ffmpeg_or_missing_camera_backend_rejected(self):
        with TemporaryDirectory() as d:
            source,wheel,digest=self.fixture(d)
            for fake in (FakeCV2(ffmpeg=True), FakeCV2(camera=False)):
                with self.subTest(ffmpeg=fake.ffmpeg),self.assertRaises(RuntimeError):
                    make_receipt(source,wheel,native_cv2=fake,source_digest=digest)


if __name__=="__main__":
    unittest.main()
