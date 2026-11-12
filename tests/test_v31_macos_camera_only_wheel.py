"""Fail closed on FFmpeg/AVIF Mac native wheels and missing camera backend."""
from __future__ import annotations
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile
from tools.qa_v31_macos_camera_only_wheel import inspect,STATUS
from tools.qa_v31_linux_camera_only_wheel import SOURCE_NAME

class Registry:
    def __init__(self, ffmpeg=False, camera=True):
        self.ffmpeg=ffmpeg;self.camera=camera
    def hasBackend(self,v):
        return self.ffmpeg if v==1900 else self.camera if v==1200 else False

class FakeCV2:
    __version__="4.14.0"
    CAP_FFMPEG=1900
    CAP_AVFOUNDATION=1200
    def __init__(self,ffmpeg=False,camera=True):
        self.ffmpeg=ffmpeg;self.videoio_registry=Registry(ffmpeg,camera)
    def getBuildInformation(self):
        return "GUI: COCOA\nFFMPEG: "+("YES" if self.ffmpeg else "NO")+"\n"

class CameraOnlyMacWheelContracts(unittest.TestCase):
    def fixture(self,tmp,target,with_avif=False):
        p=Path(tmp)
        source=p/SOURCE_NAME
        source.write_bytes(b"fake original sdist for contract tests only")
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        tag=("macosx_15_0_arm64" if target=="macos-arm64" else "macosx_15_0_x86_64")
        wheel=p/("opencv_python_headless-4.14.0.94-cp37-abi3-"+tag+".whl")
        with ZipFile(wheel,"w") as z:
            z.writestr(
                "opencv_python_headless-4.14.0.94.dist-info/METADATA",
                "Metadata-Version: 2.1\nName: opencv-python-headless\nVersion: 4.14.0.94\n"
            )
            z.writestr("cv2/cv2.abi3.so",b"synthetic native extension" * 100)
            if with_avif:
                z.writestr("cv2/.dylibs/libavif.16.dylib",b"unexpected optional image codec")
        return source,wheel,digest

    def test_mac_intel_and_arm_are_private_with_avfoundation(self):
        for target in ("macos-arm64","macos-x86_64"):
            with self.subTest(target=target),TemporaryDirectory() as d:
                source,wheel,digest=self.fixture(d,target)
                r=inspect(source,wheel,target=target,native_cv2=FakeCV2(),source_sha=digest)
                self.assertEqual(r["status"],STATUS)
                self.assertTrue(r["avfoundation_backend_compiled"])
                self.assertTrue(r["ffmpeg_disabled_in_native_wheel"])
                for key in ("physical_camera_tested","installed_frozen_app_tested",
                            "notarized","redistribution_approved","public_release_approved",
                            "all_native_corresponding_source_reviewed"):
                    self.assertIs(r[key],False)

    def test_missing_actual_native_backend_or_extra_codecs_fails(self):
        with TemporaryDirectory() as d:
            source,wheel,digest=self.fixture(d,"macos-arm64")
            for fake in (FakeCV2(camera=False),FakeCV2(ffmpeg=True)):
                with self.subTest(camera=fake.videoio_registry.camera),self.assertRaises(RuntimeError):
                    inspect(source,wheel,target="macos-arm64",native_cv2=fake,source_sha=digest)
            with self.assertRaises(ValueError):
                inspect(source,wheel,target="macos-arm64",native_cv2=FakeCV2(),source_sha="a"*64)
        with TemporaryDirectory() as d:
            source,wheel,digest=self.fixture(d,"macos-arm64",with_avif=True)
            with self.assertRaises(ValueError):
                inspect(source,wheel,target="macos-arm64",native_cv2=FakeCV2(),source_sha=digest)

    def test_wrong_arch_and_malformed_source_fail(self):
        with TemporaryDirectory() as d:
            source,wheel,digest=self.fixture(d,"macos-x86_64")
            with self.assertRaises(ValueError):
                inspect(source,wheel,target="macos-arm64",native_cv2=FakeCV2(),source_sha=digest)
            source.write_bytes(b"changed original source bytes")
            with self.assertRaises(ValueError):
                inspect(source,wheel,target="macos-x86_64",native_cv2=FakeCV2(),source_sha=digest)

if __name__=="__main__":
    unittest.main()
