"""Read-only release and isolated scratch safety for Linux camera-only swap."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.probe_v31_v20_camera_only_swap import (
    SOURCE_SHA, STATUS, probe, digest,
)

class DisposableLinuxOpenCvSwapTests(unittest.TestCase):
    def prepare(self, root):
        root = Path(root)
        old = root/"extracted2/opt/anything-plays"
        new = root/"extracted31/opt/anything-plays-31"
        for app in (old,new):
            (app/"_internal/cv2").mkdir(parents=True)
        src = old/"_internal/cv2/cv2.abi3.so"
        dst = new/"_internal/cv2/cv2.abi3.so"
        src.write_bytes(b"custom camera-only ABI3 2.0 image" * 300)
        dst.write_bytes(b"official 3.1 OpenCV image" * 320)
        (new/"AnythingPlays").write_bytes(b"legitimate-looking frozen EXE for synthetic unit test")
        extra = new/"_internal/opencv_python_headless.libs"
        extra.mkdir()
        (extra/"libavcodec-binary.so").write_bytes(b"codec")
        (extra/"libavformat-binary.so").write_bytes(b"format")
        (extra/"libpng.so").write_bytes(b"png")
        return old,new,src,dst,extra

    def env(self, root, **overrides):
        return {
            "CI":"true", "AP_V31_DISPOSABLE_QA":"1",
            "AP_V31_QA_SANDBOX":str(Path(root).resolve()), **overrides,
        }

    def test_disposable_copy_removes_only_old_cv2_deps(self):
        with TemporaryDirectory() as temp:
            old,new,src,dst,extra=self.prepare(temp)
            old_hash=digest(src)
            r=probe(old,new,scratch=temp,source_sha=SOURCE_SHA,env=self.env(temp))
            self.assertEqual(r["status"], STATUS)
            self.assertEqual(r["temporary_3_1_opencv_sha256"],old_hash)
            self.assertEqual(digest(src),old_hash)
            self.assertEqual(digest(dst),old_hash)
            self.assertEqual(r["removed_stock_opencv_dependency_file_count"],3)
            self.assertFalse(extra.exists())
            self.assertFalse(r["public_release_approved"])
            self.assertFalse(r["physical_camera_tested"])
            self.assertFalse(r["installed_gui_tested"])
            self.assertFalse(r["release_asset_modified"])

    def test_original_non_ci_or_tampered_version_fails_before_mutation(self):
        for key,value in (
            ("CI","false"),
            ("AP_V31_DISPOSABLE_QA","0"),
            ("AP_V31_QA_SANDBOX","/tmp/other"),
        ):
            with self.subTest(key=key),TemporaryDirectory() as temp:
                old,new,src,dst,extra=self.prepare(temp)
                before=digest(dst)
                with self.assertRaises(ValueError):
                    probe(old,new,scratch=temp,source_sha=SOURCE_SHA,
                          env=self.env(temp,**{key:value}))
                self.assertEqual(digest(dst),before)
                self.assertTrue(extra.is_dir())
        with TemporaryDirectory() as temp:
            old,new,src,dst,extra=self.prepare(temp)
            with self.assertRaises(ValueError):
                probe(old,new,scratch=temp,source_sha="a"*40,env=self.env(temp))
            self.assertTrue(extra.is_dir())

    def test_no_codec_present_or_source_equals_destination_fails(self):
        with TemporaryDirectory() as temp:
            old,new,src,dst,extra=self.prepare(temp)
            (extra/"libavcodec-binary.so").unlink()
            with self.assertRaises(ValueError):
                probe(old,new,scratch=temp,source_sha=SOURCE_SHA,env=self.env(temp))
            (extra/"libavformat-binary.so").unlink()
            (extra/"libavcodec-binary.so").write_bytes(b"codec")
            with self.assertRaises(ValueError):
                probe(old,old,scratch=temp,source_sha=SOURCE_SHA,env=self.env(temp))

    def test_refuse_symlink_or_external_owner_install(self):
        with TemporaryDirectory() as temp,TemporaryDirectory() as external:
            old,new,src,dst,extra=self.prepare(temp)
            with self.assertRaises(ValueError):
                probe(old,Path(external),scratch=temp,source_sha=SOURCE_SHA,
                      env=self.env(temp))
            try:
                dst.unlink()
                dst.symlink_to(src)
            except (OSError,NotImplementedError):
                self.skipTest("Symlinks unsupported")
            with self.assertRaises(ValueError):
                probe(old,new,scratch=temp,source_sha=SOURCE_SHA,env=self.env(temp))

if __name__=="__main__":
    unittest.main()
