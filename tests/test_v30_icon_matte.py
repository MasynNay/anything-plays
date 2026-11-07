"""Ensure native and Tk icons contain no opaque black exterior halo."""
from pathlib import Path
import hashlib
import unittest
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw
import numpy as np

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
            original = source.convert("RGBA")
            fixed = clean_icon_background(source)
            self.assertEqual(fixed.mode, "RGBA")
            # The approved cute fish artwork is never repainted, redrawn,
            # recolored, smoothed, or replaced. Every source RGB byte is
            # immutable, including the face and blue rounded border.
            before = np.asarray(original)
            after = np.asarray(fixed)
            np.testing.assert_array_equal(
                before[:, :, :3], after[:, :, :3],
                err_msg="Icon cleaner changed original fish/logo colors!",
            )
            self.assertLessEqual(int(np.sum(after[:, :, 3] != before[:, :, 3])),
                                 original.width * original.height // 2)
            self.assertTrue(np.all(
                after[:, :, 3] <= before[:, :, 3]
            ), "Cleaning must never make original pixels more opaque")
            # Interior should never change alpha, including dark fish lines.
            h, w = original.height, original.width
            np.testing.assert_array_equal(
                before[h // 4:3*h // 4, w // 4:3*w // 4, 3],
                after[h // 4:3*h // 4, w // 4:3*w // 4, 3],
                err_msg="Icon cleaner touched original fish interior!",
            )
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

    def test_artwork_is_still_exact_original_repository_source(self):
        # A redesigned generated icon must NEVER be substituted into the
        # build pipeline. Only the pinned original WebP is authoritative.
        source = Path(__file__).resolve().parents[1] / "assets" / "anything_plays_v21.webp"
        self.assertEqual(SOURCE, source)
        self.assertEqual(source.name, "anything_plays_v21.webp")
        # Pin the Git blob of the PRE-EXISTING original icon, not a newly
        # generated fish. This test fails if anybody substitutes artwork.
        data = source.read_bytes()
        blob_sha = hashlib.sha1(
            b"blob " + str(len(data)).encode() + bytes([0]) + data
        ).hexdigest()
        self.assertEqual(
            blob_sha, "c620c4154e80768687dfde4c0541f544779af2ff",
            "Original user-approved fish artwork was replaced!",
        )
        renderer = (source.parents[1] / "tools" / "render_v21_icon.py").read_text("utf-8")
        tkicon = (source.parents[1] / "anything_plays" / "ui_icon.py").read_text("utf-8")
        self.assertIn('SOURCE = ROOT / "assets" / "anything_plays_v21.webp"', renderer)
        self.assertIn('artwork = base / "assets" / "anything_plays_v21.webp"', tkicon)

    def test_precleaned_transparent_corner_icon_untouched(self):
        image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        ImageDraw.Draw(image).rounded_rectangle(
            (12, 12, 243, 243), radius=42,
            fill=(15, 30, 70, 255), outline=(0, 170, 250, 255), width=6,
        )
        self.assertEqual(clean_icon_background(image).tobytes(), image.tobytes())


if __name__ == "__main__":
    unittest.main()
