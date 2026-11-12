"""Reject forged Windows camera-only source, patch and wheel evidence."""
from __future__ import annotations
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from tools.qa_v31_windows_camera_only_wheel import inspect, STATUS, PATCH_NAME
from tools.qa_v31_linux_camera_only_wheel import SOURCE_NAME

class FakeRegistry:
    def __init__(self, camera=True,ffmpeg=False):
        self.camera=camera;self.ffmpeg=ffmpeg
    def hasBackend(self, key):
        return self.camera if key==700 else self.ffmpeg if key==1900 else False

class FakeCV2:
    __version__="4.14.0"
    CAP_DSHOW=700
    CAP_FFMPEG=1900
    def __init__(self,camera=True,ffmpeg=False):
        self.ffmpeg=ffmpeg
        self.videoio_registry=FakeRegistry(camera,ffmpeg)
    def getBuildInformation(self):
        return "GUI: NONE\nFFMPEG: "+("YES" if self.ffmpeg else "NO")+"\n"

class WindowsSourceWheelContracts(unittest.TestCase):
    def fixture(self,tmp):
        root=Path(tmp)
        source=root/SOURCE_NAME;source.write_bytes(b"fake pristine source for unit testing")
        patch=root/PATCH_NAME;patch.write_text("fake packaging patch\n","utf-8")
        wheel=root/"opencv_python_headless-4.14.0.94-cp37-abi3-win_amd64.whl"
        with ZipFile(wheel,"w") as archive:
            archive.writestr(
                "opencv_python_headless-4.14.0.94.dist-info/METADATA",
                "Metadata-Version: 2.1\nName: opencv-python-headless\nVersion: 4.14.0.94\n"
            )
            archive.writestr("cv2/cv2.pyd",b"synthetic DirectShow native module")
        def hash_(p):return hashlib.sha256(p.read_bytes()).hexdigest()
        return dict(source=source,patch=patch,wheel=wheel,
                    source_sha=hash_(source),patch_sha=hash_(patch),native_cv2=FakeCV2())

    def test_approved_inputs_only_prove_private_native_backend_not_release(self):
        with TemporaryDirectory() as temp:
            args=self.fixture(temp);r=inspect(**args)
            self.assertEqual(r["status"],STATUS)
            self.assertEqual(r["target"],"windows-x64")
            self.assertTrue(r["directshow_backend_compiled"])
            self.assertTrue(r["opencv_ffmpeg_disabled"])
            for k in ("camera_hardware_tested","installed_frozen_app_tested",
                      "source_companion_review_complete","redistribution_approved",
                      "public_release_approved"):
                self.assertIs(r[k],False)

    def test_reject_wrong_original_bytes_patch_and_missing_capture(self):
        with TemporaryDirectory() as temp:
            args=self.fixture(temp)
            for updates in (
                {"source_sha":"f"*64},
                {"patch_sha":"f"*64},
                {"native_cv2":FakeCV2(camera=False)},
                {"native_cv2":FakeCV2(ffmpeg=True)},
            ):
                with self.subTest(changes=updates),self.assertRaises((RuntimeError,ValueError)):
                    inspect(**{**args,**updates})
            args["patch"].write_text("new unexpected patch","utf-8")
            with self.assertRaises(ValueError):inspect(**args)

    def test_reject_wrong_wheel_tag(self):
        with TemporaryDirectory() as temp:
            args=self.fixture(temp)
            wrong=args["wheel"].with_name(
                "opencv_python_headless-4.14.0.94-cp37-abi3-macosx_11_0_arm64.whl"
            )
            args["wheel"].rename(wrong)
            with self.assertRaises(ValueError):
                inspect(**{**args,"wheel":wrong})

if __name__=="__main__":
    unittest.main()
