"""3.3.1: emulator update discovery must survive local cache failures.

These tests exercise the real UI worker with a synchronous fake thread:
no network, native cores, webcams, ROMs, or graphical Tk session.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from anything_plays.ui_updates import UpdatesMixin


class ImmediateThread:
    def __init__(self, *, target, **kwargs):
        self.target = target

    def start(self):
        self.target()


class EmulatorUpdateCacheTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.cache = self.directory / "emulator_updates.json"
        self.panel = UpdatesMixin()
        self.panel._closing = False
        self.panel._updates_busy = False
        self.panel.preferences_path = self.directory / "preferences.json"
        self.panel.root = Mock()
        self.panel.root.after.side_effect = lambda delay, callback: callback()
        self.panel._emulator_update_status = Mock()
        self.report = {"cores": [{"status": "review-upstream"}]}

    def check(self):
        with patch("anything_plays.ui_updates.Thread", ImmediateThread), \
             patch("anything_plays.ui_updates._search_directories",
                   return_value=[]), \
             patch("anything_plays.ui_updates.check_emulator_updates",
                   return_value=self.report) as check_remote, \
             patch("anything_plays.ui_updates.discover_core_packs",
                   return_value=[]):
            self.panel.check_emulator_updates(automatic=True)
        return check_remote

    def assert_live_result(self):
        self.assertFalse(self.panel._updates_busy)
        self.assertEqual(self.panel._available_core_packs, [])
        final = self.panel._emulator_update_status.set.call_args.args[0]
        self.assertIn("upstream source(s) changed", final)
        self.assertNotIn("unavailable", final.lower())

    def test_success_writes_complete_cache_without_leftover_temp_files(self):
        self.assertEqual(self.check().call_count, 1)
        data = json.loads(self.cache.read_text(encoding="utf-8"))
        self.assertEqual(data["report"], self.report)
        self.assertIsInstance(data["checked_at_unix"], (int, float))
        self.assertEqual(list(self.directory.glob("emulator_updates.json.*.tmp")), [])
        self.assert_live_result()

    def test_valid_json_array_cache_is_ignored_and_refreshed(self):
        # Valid JSON with the wrong type must not raise AttributeError in Tk.
        self.cache.write_text("[]", encoding="utf-8")
        self.assertEqual(self.check().call_count, 1)
        self.assertEqual(json.loads(self.cache.read_text())["report"], self.report)
        self.assert_live_result()

    def test_stale_fixed_name_temp_symlink_is_not_followed(self):
        sentinel = self.directory / "unrelated.txt"
        sentinel.write_text("do not touch", encoding="utf-8")
        stale = self.directory / "emulator_updates.tmp"
        try:
            stale.symlink_to(sentinel)
        except (OSError, NotImplementedError):
            self.skipTest("creating a test symlink is unsupported on this runner")
        self.assertEqual(self.check().call_count, 1)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not touch")
        self.assertTrue(stale.is_symlink())
        self.assertEqual(json.loads(self.cache.read_text())["report"], self.report)
        self.assert_live_result()

    def test_cache_write_failure_does_not_hide_successful_update_check(self):
        with patch("anything_plays.ui_updates.write_json_atomically",
                   side_effect=OSError("simulated read-only directory")):
            self.assertEqual(self.check().call_count, 1)
        self.assertFalse(self.cache.exists())
        self.assert_live_result()

    def test_failed_atomic_replace_retains_prior_complete_cache(self):
        previous = '{"checked_at_unix": 0, "report": {"cores": []}}\n'
        self.cache.write_text(previous, encoding="utf-8")
        with patch("anything_plays.atomic_storage.os.replace",
                   side_effect=OSError("simulated disk failure")):
            self.assertEqual(self.check().call_count, 1)
        self.assertEqual(self.cache.read_text(encoding="utf-8"), previous)
        self.assertEqual(list(self.directory.glob("*.tmp")), [])
        self.assert_live_result()


if __name__ == "__main__":
    unittest.main()
