"""Named control presets: bounded local storage and existing portable import."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.named_presets import (
    NamedPresetStore, MAX_PRESETS_PER_CONSOLE, MAX_LIBRARY_BYTES, validate_name,
)
from anything_plays.portable_profiles import merge_portable_profile, parse_bundle
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM, default_for


class NamedPresetTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "named-control-presets.json"
        self.store = NamedPresetStore(self.path, ("Dark", "Ocean Dark"))
        self.profile = default_for("gba", DEFAULT)

    def test_multiple_named_layouts_persist_across_reopen(self):
        self.profile["tolerance"] = 12
        self.store.save("gba", "Bright room", self.profile, theme="Dark")
        self.profile["tolerance"] = 39
        self.store.save("gba", "Low light", self.profile)
        reopened = NamedPresetStore(self.path, ("Dark", "Ocean Dark"))
        self.assertEqual(reopened.list("gba"), ("Bright room", "Low light"))
        self.assertEqual(reopened.get("gba", "Bright room")["profile"]["tolerance"], 12)
        self.assertEqual(reopened.get("gba", "Low light")["profile"]["tolerance"], 39)

    def test_all_console_profiles_remain_independent(self):
        for system in BUTTONS_BY_SYSTEM:
            self.store.save(system, "Default", default_for(system, DEFAULT))
        for system in BUTTONS_BY_SYSTEM:
            bundle = self.store.get(system, "Default")
            self.assertEqual(bundle["system"], system)
            self.assertEqual(self.store.list(system), ("Default",))
            self.assertEqual(set(bundle["profile"]["mapping"]), set(BUTTONS_BY_SYSTEM[system]))

    def test_duplicate_requires_explicit_replace(self):
        self.store.save("gba", "Room", self.profile)
        prior = self.path.read_bytes()
        self.profile["tolerance"] = 25
        with self.assertRaises(ValueError):
            self.store.save("gba", "room", self.profile)
        self.assertEqual(self.path.read_bytes(), prior)
        self.store.save("gba", "room", self.profile, replace=True)
        self.assertEqual(self.store.list("gba"), ("room",))
        self.assertEqual(self.store.get("gba", "room")["profile"]["tolerance"], 25)

    def test_numeric_and_unicode_names_preserve_exact_text(self):
        for name in ("001", "Café", "Game room"):
            self.store.save("gba", name, self.profile)
            self.assertEqual(self.store.get("gba", name)["system"], "gba")
        self.assertIn("001", self.store.list("gba"))

    def test_invalid_names_are_rejected(self):
        for name in ("", "  ", "x" * 49, "line\nbreak", None):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_name(name)

    def test_capacity_does_not_overwrite_existing_layouts(self):
        for index in range(MAX_PRESETS_PER_CONSOLE):
            self.store.save("gba", str(index), self.profile)
        prior = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.save("gba", "overflow", self.profile)
        self.assertEqual(self.path.read_bytes(), prior)
        self.store.save("gba", "0", self.profile, replace=True)
        self.assertEqual(len(self.store.list("gba")), MAX_PRESETS_PER_CONSOLE)

    def test_portable_data_excludes_private_values_and_preserves_local_art(self):
        self.profile.update({"zone_image": "/home/private/art.png",
                             "rom_directory": "/private/roms",
                             "token": "SECRET"})
        self.store.save("gba", "Layout", self.profile, theme="Dark")
        self.assertNotIn("private", self.path.read_text())
        self.assertNotIn("SECRET", self.path.read_text())
        bundle = self.store.get("gba", "Layout")
        imported, theme, legacy = parse_bundle(json.dumps(bundle),
            selected_system="gba", allowed_themes=("Dark",))
        self.assertEqual(theme, "Dark")
        self.assertFalse(legacy)
        merged = merge_portable_profile("gba", self.profile, imported)
        self.assertEqual(merged["zone_image"], self.profile["zone_image"])

    def test_delete_changes_only_selected_saved_preset(self):
        self.store.save("gba", "Keep", self.profile)
        self.store.save("gba", "Delete", self.profile)
        self.store.save("gb", "Delete", default_for("gb", DEFAULT))
        self.store.delete("gba", "Delete")
        self.assertEqual(self.store.list("gba"), ("Keep",))
        self.assertEqual(self.store.list("gb"), ("Delete",))

    def test_returned_bundle_cannot_mutate_saved_layout(self):
        self.store.save("gba", "Layout", self.profile)
        saved = self.store.get("gba", "Layout")
        saved["profile"]["zones"].clear()
        self.assertTrue(self.store.get("gba", "Layout")["profile"]["zones"])

    def test_corrupt_library_is_not_overwritten(self):
        for payload in (b"{broken", b'{"format":"anything-plays-named-presets","version":2,"presets":{}}',
                        b'{"format":"anything-plays-named-presets","version":1,"version":1,"presets":{}}',
                        b"x" * (MAX_LIBRARY_BYTES + 1)):
            self.path.write_bytes(payload)
            with self.assertRaises(ValueError):
                self.store.save("gba", "Layout", self.profile)
            self.assertEqual(self.path.read_bytes(), payload)

    def test_wrong_console_bundle_rejects_library_without_mutation(self):
        self.store.save("gba", "Layout", self.profile)
        doc = json.loads(self.path.read_bytes())
        doc["presets"]["gba"]["Layout"]["system"] = "gb"
        self.path.write_text(json.dumps(doc), encoding="utf-8")
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.delete("gba", "Layout")
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_atomic_write_retains_old_file(self):
        self.store.save("gba", "Keep", self.profile)
        before = self.path.read_bytes()
        with patch("anything_plays.named_presets.write_json_atomically",
                   side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.store.save("gba", "New", self.profile)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.list("gba"), ("Keep",))


if __name__ == "__main__":
    unittest.main()
