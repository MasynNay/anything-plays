"""Static Stream Mode chassis caching preserves rendered pixels and ownership."""
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops

from anything_plays import ui_stream
from anything_plays.ui_stream import StreamPanelResizeCache, compose_stream_output
from anything_plays.ui_theme import ThemeMixin


class StreamStaticChassisTests(unittest.TestCase):
    def setUp(self):
        self.cache = StreamPanelResizeCache()
        self.game = Image.new("RGB", (160, 144), (251, 1, 157))
        self.camera = Image.new("RGB", (64, 48), (19, 249, 199))
        self.themes = ThemeMixin.THEMES

    def render(self, *, cache=True, size=(760, 980), settings=None,
               game_active=True, camera_active=True, camera_reference=False):
        return compose_stream_output(
            self.game, self.camera, size=size, settings=settings or {},
            themes=self.themes, game_active=game_active,
            camera_active=camera_active, camera_reference=camera_reference,
            resize_cache=self.cache if cache else None,
        )

    def assert_pixels_equal(self, a, b):
        self.assertEqual(a.size, b.size)
        self.assertIsNone(ImageChops.difference(a, b).getbbox())

    def test_pixel_equivalence_across_layout_and_geometry_extremes(self):
        for size in ((320, 400), (760, 980), (1180, 720), (1920, 1600)):
            for layout in ui_stream.LAYOUTS:
                for swap in (False, True):
                    for labels in (False, True):
                        with self.subTest(size=size, layout=layout,
                                          swap=swap, labels=labels):
                            options = {"layout": layout, "swap_screens": swap,
                                       "show_labels": labels, "border_width": 16,
                                       "game_size": 30, "border_color": "#aa11ee"}
                            self.assert_pixels_equal(
                                self.render(size=size, settings=options),
                                self.render(cache=False, size=size, settings=options),
                            )
                            # Repeat to exercise actual cache reuse.
                            self.assert_pixels_equal(
                                self.render(size=size, settings=options),
                                self.render(cache=False, size=size, settings=options),
                            )

    def test_300_changing_frames_draw_chassis_only_once(self):
        with patch.object(ui_stream, "_draw_stream_chassis",
                          wraps=ui_stream._draw_stream_chassis) as draw:
            for n in range(300):
                self.game = Image.new("RGB", (24, 16), (n % 256, 7, 89))
                self.camera = Image.new("RGB", (24, 16), (2, n % 256, 74))
                image = self.render(size=(400, 500))
                self.assertIsNot(image, self.cache._chassis_image)
            self.assertEqual(draw.call_count, 1)
        self.assertEqual(len(self.cache._entries), 2)

    def test_static_chassis_contains_neither_capture_source(self):
        first = self.render()
        template = self.cache._chassis_image
        self.assertIsNotNone(template)
        self.assertNotIn((251, 1, 157), template.getdata())
        self.assertNotIn((19, 249, 199), template.getdata())
        self.assertIn((251, 1, 157), first.getdata())
        self.assertIn((19, 249, 199), first.getdata())
        pristine = template.copy()
        first.paste((255, 255, 255), (0, 0, first.width, first.height))
        self.assert_pixels_equal(template, pristine)
        self.assert_pixels_equal(self.render(), self.render(cache=False))

    def test_settings_palette_dimensions_and_status_rebuild_single_entry(self):
        with patch.object(ui_stream, "_draw_stream_chassis",
                          wraps=ui_stream._draw_stream_chassis) as draw:
            self.render()
            original = self.cache._chassis_image
            self.render(settings={"border_color": "#123456"})
            self.assertIsNot(self.cache._chassis_image, original)
            self.render(size=(780, 980), settings={"border_color": "#123456"})
            self.render(size=(780, 980), settings={"border_color": "#123456"},
                        camera_active=False, camera_reference=True)
            self.assertEqual(draw.call_count, 4)
        self.assertEqual(self.cache._chassis_image.size, (780, 980))

    def test_idle_and_side_by_side_missing_sources_release_static_chassis(self):
        self.render()
        self.assertIsNotNone(self.cache._chassis_image)
        for game_active, camera_active in ((True, False), (False, True),
                                           (False, False)):
            opts = {"layout": "Side by side"}
            self.assert_pixels_equal(
                self.render(settings=opts, game_active=game_active,
                            camera_active=camera_active),
                self.render(cache=False, settings=opts, game_active=game_active,
                            camera_active=camera_active),
            )
            self.assertIsNone(self.cache._chassis_image)
            self.assertIsNone(self.cache._chassis_key)
        self.render()
        self.render(game_active=False, camera_active=False)
        self.assertIsNone(self.cache._chassis_image)
        self.assertEqual(self.cache._entries, {})

    def test_stacked_single_source_matches_original_across_geometry(self):
        for size in ((320, 400), (760, 980), (1920, 1600), (1920, 400)):
            for game_active, camera_active in ((True, False), (False, True)):
                for share in (30, 53, 70):
                    for swap in (False, True):
                        for labels in (False, True):
                            opts = {"layout": "DS stacked", "game_size": share,
                                    "swap_screens": swap, "show_labels": labels,
                                    "border_width": 16}
                            with self.subTest(size=size, game=game_active, opts=opts):
                                cached = self.render(size=size, settings=opts,
                                    game_active=game_active, camera_active=camera_active)
                                self.assertIsNotNone(self.cache._chassis_image)
                                original = self.render(cache=False, size=size,
                                    settings=opts, game_active=game_active,
                                    camera_active=camera_active)
                                self.assert_pixels_equal(cached, original)

    def test_game_only_animation_reuses_chassis_for_300_frames(self):
        with patch.object(ui_stream, "_draw_stream_chassis",
                          wraps=ui_stream._draw_stream_chassis) as draw:
            for n in range(300):
                self.game = Image.new("RGB", (24, 16), (n % 256, 7, 89))
                self.render(size=(400, 500), camera_active=False)
            self.assertEqual(draw.call_count, 1)
        self.assertEqual(set(self.cache._entries), {"GAME"})
        self.assertIsNotNone(self.cache._chassis_image)

    def test_camera_only_animation_reuses_chassis_for_300_frames(self):
        with patch.object(ui_stream, "_draw_stream_chassis",
                          wraps=ui_stream._draw_stream_chassis) as draw:
            for n in range(300):
                self.camera = Image.new("RGB", (24, 16), (2, n % 256, 74))
                self.render(size=(400, 500), game_active=False)
            self.assertEqual(draw.call_count, 1)
        self.assertEqual(set(self.cache._entries), {"CAMERA"})

    def test_frame_rate_change_does_not_rebuild_static_art(self):
        with patch.object(ui_stream, "_draw_stream_chassis",
                          wraps=ui_stream._draw_stream_chassis) as draw:
            for rate in ui_stream.FRAME_RATES:
                self.render(settings={"frame_rate": rate}, camera_active=False)
            self.assertEqual(draw.call_count, 1)

    def test_single_source_transition_does_not_retain_disconnected_pixels(self):
        self.render()
        before = self.cache._chassis_image
        game_only = self.render(camera_active=False)
        self.assertIsNot(before, self.cache._chassis_image)
        self.assertNotIn("CAMERA", self.cache._entries)
        self.assertNotIn((19, 249, 199), game_only.getdata())
        self.assertNotIn((251, 1, 157), self.cache._chassis_image.getdata())
        self.assert_pixels_equal(game_only,
                                 self.render(cache=False, camera_active=False))
        camera_only = self.render(game_active=False)
        self.assertNotIn("GAME", self.cache._entries)
        self.assertNotIn((251, 1, 157), camera_only.getdata())

    def test_clear_all_releases_chassis_and_fits(self):
        self.render()
        self.cache.clear()
        self.assertIsNone(self.cache._chassis_image)
        self.assertIsNone(self.cache._chassis_key)
        self.assertEqual(self.cache._entries, {})

    def test_reference_camera_is_pixel_equivalent_and_cacheable(self):
        opts = {"theme": next(iter(self.themes)), "swap_screens": True}
        cached = self.render(settings=opts, camera_active=False,
                             camera_reference=True)
        self.assertIsNotNone(self.cache._chassis_image)
        self.assert_pixels_equal(cached, self.render(
            cache=False, settings=opts, camera_active=False,
            camera_reference=True,
        ))


if __name__ == "__main__":
    unittest.main()
