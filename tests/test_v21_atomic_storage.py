"""Crash safety of persistent emulator settings and per-console profiles."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from anything_plays.atomic_storage import write_json_atomically
from anything_plays.system_profiles import ProfileStore


BASE = {"zones": {}, "mapping": {}, "tolerance": 20}


class AtomicStorageTests(unittest.TestCase):
    def test_write_then_update_complete_unicode_preferences(self):
        with TemporaryDirectory() as root:
            target = Path(root) / "prefs" / "preferences.json"
            write_json_atomically(target, {"theme": "Slate", "label": "Pokémon"})
            self.assertEqual(json.loads(target.read_text())["label"], "Pokémon")
            write_json_atomically(target, {"theme": "Dark"})
            self.assertEqual(json.loads(target.read_text()), {"theme": "Dark"})
            self.assertEqual(list(target.parent.glob("*.tmp")), [])

    def test_failed_replace_retains_previous_valid_settings(self):
        with TemporaryDirectory() as root:
            target = Path(root) / "preferences.json"
            target.write_text('{"theme": "Slate"}\n', encoding="utf-8")
            with patch("anything_plays.atomic_storage.os.replace",
                       side_effect=OSError("disk disconnected")):
                with self.assertRaises(OSError):
                    write_json_atomically(target, {"theme": "Dark"})
            self.assertEqual(json.loads(target.read_text()), {"theme": "Slate"})
            self.assertEqual(list(target.parent.glob("*.tmp")), [])

    def test_unserializable_preferences_never_overwrite_saved_profile(self):
        with TemporaryDirectory() as root:
            target = Path(root) / "profiles.json"
            write_json_atomically(target, {"gba": {"enabled": True}})
            with self.assertRaises(TypeError):
                write_json_atomically(target, {"bad": object()})
            self.assertEqual(
                json.loads(target.read_text()), {"gba": {"enabled": True}}
            )
            self.assertEqual(list(target.parent.glob("*.tmp")), [])

    def test_profile_store_uses_atomic_replacement(self):
        with TemporaryDirectory() as root:
            target = Path(root) / "profiles.json"
            store = ProfileStore(target, BASE)
            current = store.get("gba")
            current["tolerance"] = 21
            store.put("gba", current)
            self.assertEqual(ProfileStore(target, BASE).get("gba")["tolerance"], 21)
            self.assertEqual(list(target.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
