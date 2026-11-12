"""Tests for accurate OpenCV frozen-binary reuse comparison."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.compare_v31_v30_opencv import compare, scan, STATUS
SHA="d852de9a513f83a329c14647ddc86bf3690fb5f5"


class OpenCvCompatibilityAuditTests(unittest.TestCase):
    def fixture(self,base):
        old=Path(base)/"stable"
        new=Path(base)/"final"
        for root in (old,new):
            directory=root/"_internal"/"cv2"
            directory.mkdir(parents=True)
            (directory/"cv2.abi3.so").write_bytes(b"native opencv binary")
            (directory/"__init__.py").write_text("# Python cv2 loader\n","utf-8")
        (new/"_internal/cv2/libx264.164.dylib").write_bytes(b"risky codec")
        (new/"_internal/cv2/libavcodec.61.dylib").write_bytes(b"FFmpeg codec")
        return old,new

    def test_different_native_packages_are_reported_not_approved(self):
        with TemporaryDirectory() as temp:
            old,new=self.fixture(temp)
            report=compare(old,new,platform="linux-x64",final_source_sha=SHA)
            self.assertEqual(report["status"],STATUS)
            self.assertEqual(report["stable_3_0_opencv"]["total_files"],2)
            self.assertEqual(report["final_3_1_opencv"]["total_files"],4)
            self.assertFalse(report["stable_has_ffmpeg_or_gpl_codec_name_candidates"])
            self.assertTrue(report["final_has_ffmpeg_or_gpl_codec_name_candidates"])
            self.assertEqual(len(report["final_3_1_opencv"]["risky_codec_paths"]),2)
            self.assertFalse(report["old_native_3_0_reusable_without_rebuild_or_test"])
            self.assertFalse(report["technical_replacement_and_camera_verified"])
            self.assertFalse(report["public_release_approved"])

    def test_source_pinning_and_empty_or_symlink_paths_fail(self):
        with TemporaryDirectory() as temp:
            old,new=self.fixture(temp)
            with self.assertRaises(ValueError):
                compare(old,new,platform="linux-x64",final_source_sha="a"*40)
            with self.assertRaises(ValueError):
                compare(old,new,platform="bogus",final_source_sha=SHA)
            (new/"_internal/cv2/cv2.abi3.so").unlink()
            (new/"_internal/cv2/__init__.py").unlink()
            (new/"_internal/cv2/libx264.164.dylib").unlink()
            (new/"_internal/cv2/libavcodec.61.dylib").unlink()
            with self.assertRaises(ValueError):
                scan(new)
            try:
                linked=Path(temp)/"link"
                linked.symlink_to(old, target_is_directory=True)
            except (OSError,NotImplementedError):
                self.skipTest("No symlink support")
            with self.assertRaises(ValueError):
                scan(linked)

if __name__=="__main__":
    unittest.main()
