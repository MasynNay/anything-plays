"""Patch a PINNED Dolphin Libretro checkout; never patch random binaries."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from tools.patch_dolphin_software import (
    HEADER, ORIGINAL, UPSTREAM_REVISION, patched_text,
    BACKEND_SOURCE, BACKEND_INCLUDE, BACKEND_ORIGINAL, patched_backend_text,
    BOOT_SOURCE, BOOT_GBP_CONFIG_ORIGINAL, BOOT_SPECIAL_ANCHOR,
    LIBRETRO_CMAKE, LIBRETRO_CMAKE_ORIGINAL, patched_libretro_cmake_text,
    patched_boot_text, patch_source_checkout,
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

    def test_native_backend_instantiates_libretro_software_gfx(self):
        result = patched_backend_text(BACKEND_INCLUDE + "\n" + BACKEND_ORIGINAL)
        self.assertIn("std::make_unique<Libretro::Video::SWGfx>()", result)
        self.assertIn("#ifdef __LIBRETRO__", result)
        self.assertIn("std::move(gfx)", result)
        # Non-Libretro builds retain their normal upstream window path.
        self.assertIn("SWOGLWindow::Create(wsi)", result)

    def test_native_libretro_linker_resolves_dynamic_library_in_archive_order(self):
        result = patched_libretro_cmake_text(LIBRETRO_CMAKE_ORIGINAL)
        self.assertIn("dolphin_libretro_videocontexts", result)
        self.assertLess(result.index("dolphin_libretro_videocontexts"),
                        result.index("  common\n"))
        with self.assertRaisesRegex(ValueError, "CMake source changed"):
            patched_libretro_cmake_text("unrelated CMake configuration")

    def test_optional_gbplayer_settings_are_disabled_when_mgba_is_not_built(self):
        result = patched_boot_text(BOOT_SPECIAL_ANCHOR + BOOT_GBP_CONFIG_ORIGINAL)
        self.assertIn("#ifdef HAS_LIBMGBA", result)
        self.assertIn("#ifdef HAS_LIBMGBA", result.splitlines())
        self.assertIn("#endif", result.splitlines())
        self.assertIn("#ifndef HAS_LIBMGBA", result)
        self.assertIn("use the bundled mGBA core", result)
        self.assertIn(BOOT_GBP_CONFIG_ORIGINAL, result)

    def test_gbplayer_boot_patch_requires_exact_source(self):
        with self.assertRaisesRegex(ValueError, "boot source changed"):
            patched_boot_text("not pinned Dolphin boot source")

    def test_backend_patch_rejects_mismatched_upstream_source(self):
        for invalid in ("missing header", BACKEND_ORIGINAL, BACKEND_ORIGINAL * 2):
            with self.subTest(source=invalid[:20]):
                with self.assertRaisesRegex(ValueError, "backend source changed"):
                    patched_backend_text(invalid)

    def test_changes_to_upstream_are_rejected_instead_of_patching_wrong_code(self):
        for invalid in ("unrelated file", ORIGINAL * 2, ""):
            with self.subTest(source=invalid[:20]):
                with self.assertRaisesRegex(ValueError, "source changed"):
                    patched_text(invalid)

    def test_checkout_hash_must_match_reviewed_dolphin_source(self):
        with TemporaryDirectory() as root:
            source = Path(root)
            video = source / HEADER
            backend = source / BACKEND_SOURCE
            video.parent.mkdir(parents=True)
            backend.parent.mkdir(parents=True)
            video.write_text(ORIGINAL, encoding="utf-8")
            backend.write_text(BACKEND_INCLUDE + "\n" + BACKEND_ORIGINAL,
                               encoding="utf-8")
            boot = source / BOOT_SOURCE
            boot.write_text(BOOT_SPECIAL_ANCHOR + BOOT_GBP_CONFIG_ORIGINAL,
                            encoding="utf-8")
            cmake = source / LIBRETRO_CMAKE
            cmake.write_text(LIBRETRO_CMAKE_ORIGINAL, encoding="utf-8")
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
            self.assertIn("Libretro::Video::SWGfx", backend.read_text())
            self.assertIn("#ifdef __LIBRETRO__", backend.read_text())
            self.assertIn("#ifdef HAS_LIBMGBA", boot.read_text())
            self.assertIn("  common", cmake.read_text())


if __name__ == "__main__":
    unittest.main()
