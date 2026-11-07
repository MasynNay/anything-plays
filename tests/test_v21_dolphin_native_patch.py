"""Patch a PINNED Dolphin Libretro checkout; never patch random binaries."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from tools.patch_dolphin_software import (
    HEADER, ORIGINAL, UPSTREAM_REVISION, patched_text,
    patch_source_checkout,
)


class DolphinNativePatchTests(unittest.TestCase):
    def test_cpu_frames_do_not_construct_a_second_opengl_window(self):
        result = patched_text("header\n" + ORIGINAL + "video_cb();\n")
        self.assertNotIn("SWOGLWindow::Create(", result)
        self.assertNotIn("SW::SWGfx::ShowImage(source_texture, source_rc)", result)
        self.assertIn("SW::SWGfx(nullptr)", result)
        self.assertIn("IsHeadless() const override", result)
        self.assertIn("BindBackbuffer(const ClearColor&)", result)
        self.assertIn("GetSurfaceInfo() const override", result)
        self.assertIn("video_cb();", result)

    def test_changes_to_upstream_are_rejected_instead_of_patching_wrong_code(self):
        for invalid in ("unrelated file", ORIGINAL * 2, ""):
            with self.subTest(source=invalid[:20]):
                with self.assertRaisesRegex(ValueError, "source changed"):
                    patched_text(invalid)

    def test_checkout_hash_must_match_reviewed_dolphin_source(self):
        with TemporaryDirectory() as root:
            source = Path(root)
            video = source / HEADER
            video.parent.mkdir(parents=True)
            video.write_text(ORIGINAL, encoding="utf-8")
            with patch("tools.patch_dolphin_software.subprocess.check_output",
                       return_value="another-revision"):
                with self.assertRaisesRegex(ValueError, "Unreviewed"):
                    patch_source_checkout(source)
            self.assertEqual(video.read_text(), ORIGINAL)
            with patch("tools.patch_dolphin_software.subprocess.check_output",
                       return_value=UPSTREAM_REVISION + "\n"):
                patch_source_checkout(source)
            self.assertIn("SW::SWGfx(nullptr)", video.read_text())
            self.assertNotIn("SWOGLWindow::Create(", video.read_text())


if __name__ == "__main__":
    unittest.main()
