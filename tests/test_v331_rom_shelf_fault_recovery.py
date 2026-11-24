"""3.3.1: ROM shelves finish failed scans and bound local cover-art work.

Only synthetic temporary files, fake worker scheduling, and small generated PNGs.
No real ROMs, user images, Tk window, device, or network share is touched.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from PIL import Image

from anything_plays.cartridge_art import (
    MAX_COVER_SOURCE_PIXELS, cartridge_image,
)
from anything_plays.ui_library import LibraryMixin


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class ImmediateWorker:
    """Keep the real Queue/Event contract without a background thread."""

    def __init__(self, *, target, daemon, name):
        self.target = target
        self.name = name
        self.daemon = daemon

    def start(self):
        self.target()


class ShelfHost(LibraryMixin):
    def __init__(self, folder):
        self.rom_directory = folder
        self.system_key = Value("gba")
        self.root = Mock()
        self.library_grid = Mock()
        self.library_grid.winfo_children.return_value = []
        self.library_images = []
        self.library_summary = Value("")
        self.shelf_drag = None
        self._closing = False
        self._rom_scan_generation = 0
        self.cancel_shelf_momentum = Mock()
        self.cancel_shelf_animation = Mock()
        self._render_rom_batch = Mock()


class ROMShelfWorkerRecoveryTests(unittest.TestCase):
    def test_faults_retire_scan_without_polling_forever_or_exposing_paths(self):
        for error in (OSError("PRIVATE /Users/owner/secret-library"),
                      RuntimeError("PRIVATE USB drive id ABC123"),
                      ValueError("PRIVATE home /home/owner")):
            with self.subTest(failure=type(error).__name__), \
                 tempfile.TemporaryDirectory() as tmp:
                app = ShelfHost(tmp)
                with patch("anything_plays.ui_library.Thread", ImmediateWorker), \
                     patch("anything_plays.ui_library.scan_rom_directory",
                           side_effect=error):
                    app.populate_inline_library()
                # The worker posted one terminal error, not a perpetually
                # empty Queue that reschedules another 90 ms Tk poll.
                app.root.after.assert_called_once()
                app.root.after.call_args.args[1]()
                self.assertIn("Could not scan folder", app.library_summary.get())
                self.assertIn("refresh", app.library_summary.get())
                self.assertNotIn("PRIVATE", app.library_summary.get())
                self.assertNotIn("/Users/", app.library_summary.get())
                self.assertNotIn("ABC123", app.library_summary.get())
                self.assertEqual(app.root.after.call_count, 1)
                app._render_rom_batch.assert_not_called()

    def test_healthy_scan_still_renders_original_cartridge_shelf(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Sample.GBA").write_bytes(b"synthetic fixture")
            app = ShelfHost(tmp)
            with patch("anything_plays.ui_library.Thread", ImmediateWorker):
                app.populate_inline_library()
            app.root.after.call_args.args[1]()
            self.assertIn("1 game(s)", app.library_summary.get())
            app._render_rom_batch.assert_called_once()
            self.assertEqual(
                [p.name for p in app._render_rom_batch.call_args.args[0]],
                ["Sample.GBA"],
            )

    def test_outdated_worker_failure_cannot_replace_newer_shelf(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = ShelfHost(tmp)
            with patch("anything_plays.ui_library.Thread", ImmediateWorker), \
                 patch("anything_plays.ui_library.scan_rom_directory",
                       side_effect=OSError("old disconnected network share")):
                app.populate_inline_library()
            old_callback = app.root.after.call_args.args[1]
            app._rom_scan_generation += 1
            app.library_summary.set("ROM LIBRARY · Newer directory selected")
            old_callback()
            self.assertEqual(
                app.library_summary.get(),
                "ROM LIBRARY · Newer directory selected",
            )
            self.assertEqual(app.root.after.call_count, 1)


class BoundedCoverArtTests(unittest.TestCase):
    def test_normal_small_cover_preserves_artwork_and_cartridge_transparency(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "Sample.png"
            Image.new("RGB", (120, 90), (245, 40, 20)).save(art)
            cover = cartridge_image("Sample", "gba", art)
            self.assertEqual(cover.size, (300, 226))
            self.assertEqual(cover.getpixel((0, 0))[3], 0)
            self.assertEqual(cover.getpixel((150, 138))[:3], (245, 40, 20))

    def test_oversized_header_is_rejected_before_image_decode(self):
        fake_source = MagicMock()
        fake_source.__enter__.return_value = fake_source
        fake_source.size = (5000, 3000)
        self.assertGreater(5000 * 3000, MAX_COVER_SOURCE_PIXELS)
        with patch("anything_plays.cartridge_art.Image.open",
                   return_value=fake_source):
            result = cartridge_image("Sample", "gba", "/synthetic/huge.png")
        fake_source.thumbnail.assert_not_called()
        fake_source.convert.assert_not_called()
        self.assertEqual(result.size, (300, 226))
        self.assertEqual(result.getpixel((0, 0))[3], 0)

    def test_corrupt_optional_cover_does_not_break_default_cartridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "corrupt.png"
            art.write_bytes(b"not a real image")
            fallback = cartridge_image("Synthetic", "snes")
            actual = cartridge_image("Synthetic", "snes", art)
            self.assertEqual(actual.tobytes(), fallback.tobytes())

    def test_symlinked_cover_is_not_opened_even_when_passed_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "private.png"
            Image.new("RGB", (32, 32), (255, 0, 0)).save(outside)
            link = root / "cover.png"
            try:
                link.symlink_to(outside)
            except (NotImplementedError, OSError):
                self.skipTest("Symlinks unavailable on this runner")
            with patch("anything_plays.cartridge_art.Image.open") as op:
                actual = cartridge_image("Synthetic", "gb", link)
            op.assert_not_called()
            self.assertEqual(actual.getpixel((0, 0))[3], 0)

    def test_decompression_bomb_warning_falls_back_without_fatal_error(self):
        import warnings
        with patch("anything_plays.cartridge_art.Image.open") as op:
            def warn(*_args, **_kwargs):
                warnings.warn("synthetic decompression bomb",
                              Image.DecompressionBombWarning)
                return MagicMock()
            op.side_effect = warn
            output = cartridge_image("Synthetic", "gba", "/synthetic/bomb.png")
        self.assertEqual(output.size, (300, 226))
        self.assertEqual(output.getpixel((0, 0))[3], 0)

    def test_accepted_cover_resizes_before_rgb_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "art.jpg"
            Image.new("RGB", (2000, 1000), (34, 200, 15)).save(art)
            actual = cartridge_image("Synthetic", "gba", art)
            # JPEG chroma subsampling can round RGB channels slightly
            # differently in each platform's Pillow/libjpeg build.
            pixel = actual.getpixel((150, 138))
            for observed, expected in zip(pixel[:3], (34, 200, 15)):
                self.assertLessEqual(abs(observed - expected), 5)
            self.assertEqual(actual.getpixel((0, 0))[3], 0)


if __name__ == "__main__":
    unittest.main()
