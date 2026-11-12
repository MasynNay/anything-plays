"""Reject fake 3.1 source-wheel swaps and accidental public release claims."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from tools.probe_v31_source_built_linux_frozen import (
    ORIGINAL_INSTALLER, ORIGINAL_FULL_STATUS, STATUS, source_wheel_swap,
)
from tools.probe_v31_v20_camera_only_swap import SOURCE_SHA, digest
from tools.qa_v31_linux_camera_only_wheel import SOURCE_NAME, STATUS as WHEEL_STATUS


class SourceBuiltWheelFrozenLinux(unittest.TestCase):
    def fixture(self, tmp):
        root=Path(tmp)
        sandbox=root/"scratch"
        app=sandbox/"linux"/"opt/anything-plays-31"
        (app/"_internal/cv2").mkdir(parents=True)
        native=app/"_internal/cv2/cv2.abi3.so"
        native.write_bytes(b"old stock OpenCV native" * 500)
        oldcodec=app/"_internal/opencv_python_headless.libs"
        oldcodec.mkdir(parents=True)
        (oldcodec/"libavcodec.so.61").write_bytes(b"old ffmpeg codec")
        (oldcodec/"libvpx.so.1").write_bytes(b"additional dependency")
        (app/"AnythingPlays").write_bytes(b"frozen full executable")
        installer=root/ORIGINAL_INSTALLER
        installer.write_bytes(b"verified original package" * 50000)
        full_receipt=root/"FULL_LIBRARY_QA_RECEIPT.json"
        full_receipt.write_text(json.dumps({
            "status": ORIGINAL_FULL_STATUS,
            "target": "linux-x64",
            "source_preview_revision": SOURCE_SHA,
            "installer": ORIGINAL_INSTALLER,
            "sha256": digest(installer),
            "native_core_count": 11,
            "console_profiles": 18,
            "identity_channel": "final_candidate",
            "settings_namespace": "anything-plays-31",
            "public_release_approved": False,
            "final_release_approved": False,
        }),"utf-8")
        source=root/SOURCE_NAME
        source.write_bytes(b"fake source for isolated unit tests")
        source_hash=digest(source)
        wheel=root/"opencv_python_headless-4.14.0.94-cp37-abi3-linux_x86_64.whl"
        with ZipFile(wheel,"w") as zipf:
            zipf.writestr("cv2/cv2.abi3.so",b"new source-compiled camera-only OpenCV" * 500)
            zipf.writestr(
                "opencv_python_headless-4.14.0.94.dist-info/METADATA",
                "Metadata-Version: 2.1\nName: opencv-python-headless\nVersion: 4.14.0.94\n",
            )
        wr=root/"LINUX_CAMERA_ONLY_OPENCV_SOURCE_QA_UNAPPROVED.json"
        wr.write_text(json.dumps({
            "status": WHEEL_STATUS,
            "target": "linux-x64",
            "source": SOURCE_NAME,
            "source_sha256": source_hash,
            "package": "opencv-python-headless",
            "version": "4.14.0.94",
            "wheel": wheel.name,
            "wheel_sha256": digest(wheel),
            "opencv_native_module_imported": True,
            "opencv_linux_v4l2_backend_available": True,
            "opencv_ffmpeg_backend_disabled": True,
            "public_release_approved": False,
            "redistribution_approved": False,
            "tested_in_actual_frozen_3_1_app": False,
        }),"utf-8")
        env={"CI":"true","AP_V31_DISPOSABLE_QA":"1",
             "AP_V31_QA_SANDBOX":str(sandbox.resolve())}
        kwargs=dict(app=app,scratch=sandbox,installer=installer,
                    full_receipt=full_receipt,source=source,wheel=wheel,
                    wheel_receipt=wr,environ=env,expected_source_sha=source_hash)
        return kwargs

    def test_valid_source_wheel_uses_correct_native_bytes_and_preserves_inputs(self):
        with TemporaryDirectory() as tmp:
            kw=self.fixture(tmp)
            before_source=digest(kw["source"])
            before_wheel=digest(kw["wheel"])
            before_package=digest(kw["installer"])
            output=source_wheel_swap(**kw)
            self.assertEqual(output["status"],STATUS)
            self.assertEqual(output["removed_original_dependency_count"],2)
            self.assertEqual(len(output["removed_ffmpeg_related_names"]),1)
            self.assertFalse((kw["app"]/"_internal/opencv_python_headless.libs").exists())
            self.assertEqual(output["source_wheel_native_sha256"],
                             digest(kw["app"]/"_internal/cv2/cv2.abi3.so"))
            for flag in ("public_release_approved","redistribution_approved",
                         "physical_camera_tested","release_asset_modified",
                         "native_corresponding_source_approved"):
                self.assertIs(output[flag],False)
            self.assertEqual(before_source,digest(kw["source"]))
            self.assertEqual(before_wheel,digest(kw["wheel"]))
            self.assertEqual(before_package,digest(kw["installer"]))

    def test_refuse_wrong_source_sha_and_forged_wheel_receipt(self):
        with TemporaryDirectory() as tmp:
            kw=self.fixture(tmp)
            before=digest(kw["app"]/"_internal/cv2/cv2.abi3.so")
            with self.assertRaises(ValueError):
                source_wheel_swap(**{**kw,"expected_source_sha":"a"*64})
            wr=kw["wheel_receipt"]
            original=json.loads(wr.read_text("utf-8"))
            for key,bad in (
                ("public_release_approved",True),
                ("redistribution_approved",True),
                ("opencv_ffmpeg_backend_disabled",False),
                ("opencv_linux_v4l2_backend_available",False),
                ("wheel_sha256","f"*64),
            ):
                with self.subTest(field=key):
                    wr.write_text(json.dumps({**original,key:bad}),"utf-8")
                    with self.assertRaises(ValueError):
                        source_wheel_swap(**kw)
            wr.write_text(json.dumps(original),"utf-8")
            self.assertEqual(before,digest(kw["app"]/"_internal/cv2/cv2.abi3.so"))

    def test_refuse_actual_installs_and_tampered_full_receipts(self):
        with TemporaryDirectory() as tmp:
            kw=self.fixture(tmp)
            with self.assertRaises(ValueError):
                source_wheel_swap(**{**kw,"environ":{**kw["environ"],"CI":"false"}})
            with self.assertRaises(ValueError):
                source_wheel_swap(**{**kw,"environ":{**kw["environ"],
                                                     "AP_V31_QA_SANDBOX":"/"}})
            path=kw["full_receipt"]
            original=json.loads(path.read_text("utf-8"))
            for key,bad in (
                ("native_core_count",1), ("console_profiles",17),
                ("source_preview_revision","f"*40),
                ("public_release_approved",True),
                ("sha256","f"*64),
            ):
                with self.subTest(field=key):
                    path.write_text(json.dumps({**original,key:bad}),"utf-8")
                    with self.assertRaises(ValueError):
                        source_wheel_swap(**kw)
            path.write_text(json.dumps(original),"utf-8")
            app=kw["app"]
            original_cv=app/"_internal/cv2/cv2.abi3.so"
            original_cv.rename(app/"_internal/cv2/backup.so")
            try:
                original_cv.symlink_to(app/"_internal/cv2/backup.so")
            except (OSError,NotImplementedError):
                self.skipTest("No symlink support")
            with self.assertRaises(ValueError):
                source_wheel_swap(**kw)


if __name__=="__main__":
    unittest.main()
