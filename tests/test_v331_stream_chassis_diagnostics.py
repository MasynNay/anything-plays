"""Static Stream Mode cache diagnostics remain separate, bounded and private."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from PIL import Image

from anything_plays.ui_stream import (
    StreamPanelResizeCache, StreamCadenceTracker, StreamMixin,
    stream_safe_qa_report, compose_stream_output,
)
from anything_plays.ui_setup_diagnostics import _stream_cadence_summary_lines
from anything_plays.ui_theme import ThemeMixin


class StaticChassisDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.cache = StreamPanelResizeCache()
        self.app = SimpleNamespace(
            _stream_output_window=object(),
            _stream_cadence=StreamCadenceTracker(),
            _stream_resize_cache=self.cache,
        )

    def report(self):
        return StreamMixin.stream_performance_snapshot(self.app)

    def test_300_compositions_report_one_build_and_299_reuses(self):
        game = Image.new("RGB", (24, 16), "red")
        camera = Image.new("RGB", (24, 16), "green")
        for _ in range(300):
            compose_stream_output(game, camera, size=(400, 500),
                                  settings={}, themes=ThemeMixin.THEMES,
                                  game_active=True, camera_active=True,
                                  resize_cache=self.cache)
        report = self.report()
        self.assertEqual(report["metrics"]["stream_chassis_cache_builds"], 1)
        self.assertEqual(report["metrics"]["stream_chassis_cache_hits"], 299)
        self.assertEqual(report["metrics"]["stream_resize_cache_misses"], 2)
        self.assertEqual(report["metrics"]["stream_resize_cache_hits"], 598)
        safe = stream_safe_qa_report(report)
        self.assertEqual(safe["metrics"]["stream_chassis_cache_hits"], 299)
        self.assertIn("299 reused · 1 built (decoration only)",
                      "\n".join(_stream_cadence_summary_lines(report)))

    def test_clear_keeps_lifetime_counts_but_releases_canvas(self):
        self.cache.chassis("a", lambda: Image.new("RGB", (320, 400)))
        self.cache.clear()
        self.assertIsNone(self.cache._chassis_image)
        self.assertEqual(self.cache.snapshot()["stream_chassis_cache_builds"], 1)
        self.cache.chassis("a", lambda: Image.new("RGB", (320, 400)))
        self.assertEqual(self.cache.snapshot()["stream_chassis_cache_builds"], 2)

    def test_bad_new_counts_do_not_remove_valid_legacy_resize_counts(self):
        for bad in (-1, True, "PRIVATE", 2**63, 1.5):
            with self.subTest(bad=bad):
                self.cache.chassis_hits = bad
                report = self.report()
                self.assertIn("stream_resize_cache_hits", report["metrics"])
                self.assertNotIn("stream_chassis_cache_hits", report["metrics"])
                self.assertNotIn("stream_chassis_cache_builds", report["metrics"])

    def test_clipboard_rejects_invalid_counts_and_unknown_pixels(self):
        for bad in (-1, True, "PRIVATE", 2**63, 1.5):
            report = {"metrics": {"stream_resize_cache_hits": 5,
                                  "stream_chassis_cache_hits": bad,
                                  "raw_image": "PRIVATE /home/user"}}
            safe = stream_safe_qa_report(report)
            self.assertEqual(safe["metrics"], {"stream_resize_cache_hits": 5})

    def test_legacy_report_omits_new_line_without_claiming_zero(self):
        with patch.object(self.cache, "snapshot", return_value={
            "stream_resize_cache_hits": 2, "stream_resize_cache_misses": 1,
        }):
            report = self.report()
        lines = "\n".join(_stream_cadence_summary_lines(report))
        self.assertIn("Source resize cache: 2 reused", lines)
        self.assertNotIn("Static chassis cache:", lines)

    def test_no_report_after_output_closes(self):
        self.app._stream_output_window = None
        self.assertIsNone(self.report())


if __name__ == "__main__":
    unittest.main()
