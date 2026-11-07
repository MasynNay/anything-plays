"""Ensure native and Tk icons contain no opaque black exterior halo."""
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw

from anything_plays.icon_cleanup import clean_icon_background
from tools.render_v21_icon import render, SOURCE


class IconMatteTests(unittest.TestCase):
    def test_only_dark_exterior_is_transparent(self):
        image = Image.new("RGBA", (256, 256), (0, 0, 0, 255))
        painter = ImageDraw.Draw(image)
        painter.rounded_rectangle(
            (13, 13, 243, 243), radius=38,
            fill=(14, 43, 87, 255), outline=(5, 220, 250, 255), width=9,
        )
        # Dark eye/detail inside remains opaque.
        painter.ellipse((95, 95, 130, 130), fill=(0, 0, 0, 255))
        fixed = clean_icon_background(image)
        for point in ((0, 0), (255, 0), (0, 255), (255, 255)):
            self.assertEqual(fixed.getpixel(point)[3], 0)
        self.assertEqual(fixed.getpixel((112, 112))[3], 255)
        self.assertEqual(fixed.getpixel((128, 13))[3], 255)
        self.assertEqual(fixed.size, image.size)

    def test_real_icon_is_transparent_outside_closed_border(self):
        with Image.open(SOURCE) as source:
            fixed = clean_icon_background(source)
            self.assertEqual(fixed.mode, "RGBA")
            corners = ((0, 0), (fixed.width - 1, 0),
                       (0, fixed.height - 1),
                       (fixed.width - 1, fixed.height - 1))
            self.assertTrue(all(fixed.getpixel(xy)[3] == 0 for xy in corners))
            self.assertGreater(fixed.getpixel(
                (fixed.width // 2, fixed.height // 2))[3], 180)

    def test_all_generated_platform_icon_pieces_have_clean_corners(self):
        with TemporaryDirectory() as folder:
            png, small, ico = render(output=Path(folder))
            for icon_file in (png, small, ico):
                with self.subTest(path=icon_file.name):
                    with Image.open(icon_file) as original:
                        converted = original.convert("RGBA")
                        w, h = converted.size
                        for xy in ((0, 0), (w - 1, 0),
                                   (0, h - 1), (w - 1, h - 1)):
                            self.assertEqual(converted.getpixel(xy)[3], 0)

    def test_precleaned_transparent_corner_icon_untouched(self):
        image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        ImageDraw.Draw(image).rounded_rectangle(
            (12, 12, 243, 243), radius=42,
            fill=(15, 30, 70, 255), outline=(0, 170, 250, 255), width=6,
        )
        self.assertEqual(clean_icon_background(image).tobytes(), image.tobytes())


if __name__ == "__main__":
    unittest.main()
