"""Prevent test builds from overwriting the stable 2.0 preferences."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from anything_plays.test_preferences import (
    LEGACY_DIR, TEST_DIR, prepare_test_preferences,
)


class AlphaSettingsTests(unittest.TestCase):
    def test_copies_profiles_once_but_never_modifies_stable_files(self):
        with TemporaryDirectory() as root:
            home = Path(root)
            stable = home / LEGACY_DIR
            stable.mkdir(parents=True)
            original_preferences = '{"theme":"Light","system":"gba"}'
            original_profiles = '{"gba":{"zones":{},"mapping":{}}}'
            (stable / "preferences.json").write_text(original_preferences)
            (stable / "system_profiles.json").write_text(original_profiles)
            target = prepare_test_preferences(home)
            self.assertEqual(target, home / TEST_DIR / "preferences.json")
            self.assertEqual(target.read_text(), original_preferences)
            self.assertEqual(target.with_name("system_profiles.json").read_text(),
                             original_profiles)
            target.write_text('{"theme":"Dark"}')
            target.with_name("system_profiles.json").write_text("{}")
            self.assertEqual(prepare_test_preferences(home), target)
            self.assertEqual(target.read_text(), '{"theme":"Dark"}')
            self.assertEqual((stable / "preferences.json").read_text(),
                             original_preferences)
            self.assertEqual((stable / "system_profiles.json").read_text(),
                             original_profiles)

    def test_absent_stable_settings_initializes_test_path(self):
        with TemporaryDirectory() as root:
            target = prepare_test_preferences(root)
            self.assertEqual(target.name, "preferences.json")
            self.assertTrue(target.parent.is_dir())
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
