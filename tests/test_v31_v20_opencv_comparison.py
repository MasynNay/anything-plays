"""Source-locked 2.0 camera-only OpenCV comparison contracts."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.compare_v31_v20_opencv import compare, SOURCE_SHA, STATUS


class V20CameraOnlyCompatibilityTests(unittest.TestCase):
    def test_unmodified_2_0_candidate_is_not_automatically_approved(self):
        with TemporaryDirectory() as tmp:
            stable=Path(tmp)/"old"
            final=Path(tmp)/"new"
            for root in (stable, final):
                cv=root/"_internal/cv2"
                cv.mkdir(parents=True)
                (cv/"cv2.abi3.so").write_bytes(b"binaryopencv")
                (cv/"__init__.py").write_text("import cv2\n","utf-8")
            (final/"_internal/cv2/libavcodec.61.dylib").write_bytes(b"ffmpeg")
            record=compare(stable,final,target="linux-x64",source_sha=SOURCE_SHA)
            self.assertEqual(record["status"],STATUS)
            self.assertEqual(record["public_2_0_ffmpeg_binary_name_candidates"],[])
            self.assertEqual(len(record["private_3_1_ffmpeg_binary_name_candidates"]),1)
            self.assertEqual(record["common_content_sha256_count"],2)
            self.assertIn("cv2.abi3.so",record["common_native_filenames"])
            self.assertTrue(record["candidate_2_0_camera_only_runtime_not_assumed_reusable"])
            self.assertFalse(record["corresponding_source_and_relinking_approved"])
            self.assertFalse(record["public_release_approved"])
            with self.assertRaises(ValueError):
                compare(stable,final,target="linux-x64",source_sha="a"*40)
            with self.assertRaises(ValueError):
                compare(stable,final,target="unknown",source_sha=SOURCE_SHA)


if __name__=="__main__":
    unittest.main()
