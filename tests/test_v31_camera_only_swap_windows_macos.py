"""Reject unsafe edits to public 2.0 or finalized 3.1 packages."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.probe_v31_v20_camera_only_swap_windows_macos import swap,hash_file,STATUS,SOURCE_SHA


class WinMacCameraSwapContracts(unittest.TestCase):
    def fixture(self,root,target):
        root=Path(root)
        old=root/"public20"
        new=root/"private31"
        path=("_internal/cv2/cv2.pyd" if target=="windows-x64"
              else "Contents/Frameworks/cv2/cv2.abi3.so")
        (old/Path(path).parent).mkdir(parents=True)
        (new/Path(path).parent).mkdir(parents=True)
        a,b=old/path,new/path
        a.write_bytes(b"original custom FFmpeg-disabled 2.0" * 500)
        b.write_bytes(b"new 3.1 stock opencv video" * 500)
        launcher=("AnythingPlays.exe" if target=="windows-x64"
                  else "Contents/MacOS/AnythingPlays")
        (new/Path(launcher).parent).mkdir(parents=True,exist_ok=True)
        (new/launcher).write_bytes(b"fake exe for contract tests")
        if target=="windows-x64":
            (new/"_internal/cv2/opencv_videoio_ffmpeg4140_64.dll").write_bytes(b"stock ffmpeg dll")
        else:
            libs=new/"Contents/Frameworks/cv2/__dot__dylibs"
            libs.mkdir()
            if target=="macos-arm64":
                (libs/"libavcodec.dylib").write_bytes(b"codec")
            (libs/"libSDL2.dylib").write_bytes(b"shared SDL library")
            (libs/"liblzma.5.dylib").write_bytes(b"needed by PIL/libtiff")
            if target=="macos-x64":
                (old/"Contents/Frameworks/libavif.16.dylib").write_bytes(
                    b"original 2.0 source camera wheel native libavif" * 50
                )
        return old,new,a,b

    def env(self,root):
        return {"CI":"true","AP_V31_DISPOSABLE_QA":"1",
                "AP_V31_QA_SANDBOX":str(Path(root).resolve())}

    def test_compatibility_mutation_requires_sandbox_and_preserves_original(self):
        for target in ("windows-x64","macos-arm64","macos-x64"):
            with self.subTest(target=target),TemporaryDirectory() as temp:
                old,new,a,b=self.fixture(temp,target)
                before=hash_file(a)
                result=swap(target=target,old_app=old,new_app=new,scratch=temp,
                            source_sha=SOURCE_SHA,environ=self.env(temp))
                self.assertEqual(result["status"],STATUS)
                self.assertEqual(hash_file(a),before)
                self.assertEqual(hash_file(b),before)
                if target=="macos-x64":
                    self.assertEqual(result["removed_library_count"],0)
                    avif=result["copied_original_camera_only_shared_dependency"]
                    self.assertEqual(avif["filename"],"libavif.16.dylib")
                    self.assertEqual(
                        hash_file(old/"Contents/Frameworks/libavif.16.dylib"),
                        hash_file(new/"Contents/Frameworks/libavif.16.dylib")
                    )
                else:
                    self.assertGreater(result["removed_library_count"],0)
                    self.assertIsNone(result["copied_original_camera_only_shared_dependency"])
                if target.startswith("macos"):
                    self.assertTrue((new/"Contents/Frameworks/cv2/__dot__dylibs/liblzma.5.dylib").is_file())
                self.assertFalse(result["actual_frozen_app_smoke_passed"])
                self.assertFalse(result["public_release_approved"])
                self.assertFalse(result["redistribution_approved"])

    def test_mac_intel_requires_original_v2_shared_libavif(self):
        with TemporaryDirectory() as temp:
            old,new,a,b=self.fixture(temp,"macos-x64")
            (old/"Contents/Frameworks/libavif.16.dylib").unlink()
            with self.assertRaises(ValueError):
                swap(target="macos-x64",old_app=old,new_app=new,
                     scratch=temp,source_sha=SOURCE_SHA,environ=self.env(temp))
            self.assertFalse((new/"Contents/Frameworks/libavif.16.dylib").exists())

    def test_unsafe_source_and_missing_originals_are_rejected(self):
        with TemporaryDirectory() as temp:
            old,new,a,b=self.fixture(temp,"windows-x64")
            oldsum=hash_file(a)
            kwargs=dict(target="windows-x64",old_app=old,new_app=new,
                        scratch=temp,source_sha=SOURCE_SHA,environ=self.env(temp))
            for value in ("bad", "f"*40):
                with self.assertRaises(ValueError):
                    swap(**{**kwargs,"source_sha":value})
            with self.assertRaises(ValueError):
                swap(**{**kwargs,"environ":{**self.env(temp),"CI":"false"}})
            with self.assertRaises(ValueError):
                swap(**{**kwargs,"new_app":old})
            (new/"_internal/cv2/opencv_videoio_ffmpeg4140_64.dll").unlink()
            with self.assertRaises(ValueError):
                swap(**kwargs)
            self.assertEqual(hash_file(a),oldsum)


if __name__=="__main__":
    unittest.main()
