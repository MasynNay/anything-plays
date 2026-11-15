"""3.2 portable-profile validation without cameras, ROMs or native drivers."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from anything_plays.ui_profiles import ProfilesMixin

from anything_plays.portable_profiles import (
    FORMAT, MAX_FILE_BYTES, load_bundle, make_bundle, parse_bundle,
    save_bundle, merge_portable_profile,
)
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import default_for


class PreferencesTransactionTests(unittest.TestCase):
    def test_strict_preference_save_raises_for_import_rollback(self):
        class Variable:
            def __init__(self, value):
                self.value = value
            def get(self):
                return self.value
        class App:
            def read_preferences(self):
                return {}
        app = App()
        app.theme_name = Variable("Dark")
        app.system_key = Variable("gba")
        app.rom_directories = {"gba": ""}
        app._shortcut_bindings = {}
        app.gamepad_enabled = Variable(False)
        app._gamepad_bindings = {}
        app.external_emulators = {}
        app.n64_core_override = ""
        app.n64_embedded = Variable(False)
        app.gamecube_embedded = Variable(False)
        app.gamecube_preview_mode = Variable("Disabled")
        app.view_mode = Variable("Windowed")
        app.volume_percent = Variable(60)
        app._volume_before_mute = 60
        app.preferences_path = Path("/unused/preference.json")
        with patch("anything_plays.ui_profiles.write_json_atomically",
                   side_effect=OSError("disk full")), patch(
                       "anything_plays.ui_profiles.messagebox.showwarning"
                   ) as warning:
            with self.assertRaises(OSError):
                ProfilesMixin.save_preferences(app, strict=True)
            warning.assert_not_called()
            ProfilesMixin.save_preferences(app)
            warning.assert_called_once()


class PortableProfilesTests(unittest.TestCase):
    def setUp(self):
        self.profile = default_for("gba", DEFAULT)
        self.profile["rgb"] = [44, 99, 150]
        self.profile["zones"]["A"] = [.1, .2, .3, .4]
        # These must never be exported, even if the old profile contains them.
        self.profile["zone_image"] = "/home/alex/private-fish-photo.png"
        self.profile["rom_directory"] = "C:\\Users\\Alex\\roms"
        self.themes = ("Dark", "Ocean Light")

    def bundle(self):
        return make_bundle("gba", self.profile, theme="Ocean Light",
                           allowed_themes=self.themes)

    def test_roundtrip_current_console(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "profile.json"
            save_bundle(target, "gba", self.profile, theme="Ocean Light",
                        allowed_themes=self.themes)
            settings, theme, legacy = load_bundle(
                target, selected_system="gba", allowed_themes=self.themes
            )
            self.assertFalse(legacy)
            self.assertEqual(theme, "Ocean Light")
            self.assertEqual(settings["rgb"], [44, 99, 150])
            self.assertEqual(settings["zones"]["A"], [.1, .2, .3, .4])
            self.assertEqual(settings["mapping"]["A"], "A")

    def test_import_merges_controls_without_erasing_local_artwork(self):
        source = copy.deepcopy(self.profile)
        original = copy.deepcopy(source)
        incoming = parse_bundle(
            json.dumps(self.bundle()),
            selected_system="gba", allowed_themes=self.themes,
        )[0]
        incoming["tolerance"] = 39
        merged = merge_portable_profile("gba", source, incoming)
        self.assertEqual(merged["tolerance"], 39)
        self.assertEqual(merged["zone_image"], source["zone_image"])
        self.assertEqual(merged["rom_directory"], source["rom_directory"])
        self.assertEqual(source, original)
        self.assertNotIn("zone_image", incoming)
        merged["zones"]["A"][0] = 0.05
        self.assertEqual(source["zones"]["A"], [.1, .2, .3, .4])

    def test_legacy_profile_merge_disallows_private_path_injection(self):
        incoming = copy.deepcopy(self.profile)
        incoming["zone_image"] = "/not-the-local-zone-background.png"
        incoming["rom_directory"] = "/injected-game-library"
        cleaned, _, legacy = parse_bundle(
            json.dumps(incoming), selected_system="gba",
            allowed_themes=self.themes,
        )
        self.assertTrue(legacy)
        merged = merge_portable_profile("gba", self.profile, cleaned)
        self.assertEqual(merged["zone_image"], self.profile["zone_image"])
        self.assertEqual(merged["rom_directory"], self.profile["rom_directory"])
        with self.assertRaises(ValueError):
            merge_portable_profile(
                "gba", self.profile, dict(cleaned, zone_image="/bad")
            )
        with self.assertRaises(ValueError):
            merge_portable_profile("gb", self.profile, cleaned)

    def test_no_rom_paths_image_paths_or_credentials_leave_machine(self):
        document = self.bundle()
        serialized = json.dumps(document)
        self.assertEqual(document["format"], FORMAT)
        for private in ("Alex", "rom_directory", "zone_image", "camera_frame",
                        "credentials", "/home/"):
            self.assertNotIn(private, serialized)

    def test_reject_wrong_console_without_modification(self):
        source = json.dumps(self.bundle())
        with self.assertRaisesRegex(ValueError, "another console"):
            parse_bundle(source, selected_system="snes",
                         allowed_themes=self.themes)

    def test_legacy_profile_import_discards_private_keys(self):
        clean, theme, legacy = parse_bundle(
            json.dumps(self.profile), selected_system="gba",
            allowed_themes=self.themes
        )
        self.assertTrue(legacy)
        self.assertIsNone(theme)
        self.assertNotIn("zone_image", clean)
        self.assertNotIn("rom_directory", clean)
        self.assertEqual(clean["rgb"], [44, 99, 150])

    def test_unsupported_version_rejected(self):
        document = self.bundle()
        document["version"] = 999
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            parse_bundle(json.dumps(document), selected_system="gba",
                         allowed_themes=self.themes)

    def test_boolean_version_rejected(self):
        document = self.bundle()
        document["version"] = True
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            parse_bundle(json.dumps(document), selected_system="gba",
                         allowed_themes=self.themes)

    def test_unsupported_theme_rejected(self):
        document = self.bundle()
        document["theme"] = "malicious-theme"
        with self.assertRaisesRegex(ValueError, "unsupported theme"):
            parse_bundle(json.dumps(document), selected_system="gba",
                         allowed_themes=self.themes)

    def test_unknown_settings_in_versioned_profile_rejected(self):
        document = self.bundle()
        document["profile"]["private_directory"] = "/tmp/"
        with self.assertRaisesRegex(ValueError, "Unexpected settings"):
            parse_bundle(json.dumps(document), selected_system="gba",
                         allowed_themes=self.themes)

    def test_unknown_zone_and_invalid_rectangle_rejected(self):
        document = self.bundle()
        document["profile"]["zones"]["Exploit"] = [0, 0, 1, 1]
        with self.assertRaisesRegex(ValueError, "Unknown zone"):
            parse_bundle(json.dumps(document), selected_system="gba",
                         allowed_themes=self.themes)
        document = self.bundle()
        document["profile"]["zones"]["A"] = [0, 0, 2, 3]
        with self.assertRaisesRegex(ValueError, "rectangle"):
            parse_bundle(json.dumps(document), selected_system="gba",
                         allowed_themes=self.themes)

    def test_invalid_scalar_and_player_mapping_rejected(self):
        document = self.bundle()
        document["profile"]["tolerance"] = -3
        with self.assertRaisesRegex(ValueError, "tolerance"):
            parse_bundle(json.dumps(document), selected_system="gba",
                         allowed_themes=self.themes)
        document = self.bundle()
        document["profile"]["mapping"]["A"] = "Not a controller button"
        with self.assertRaisesRegex(ValueError, "mapping"):
            parse_bundle(json.dumps(document), selected_system="gba",
                         allowed_themes=self.themes)

    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        for data in ('{"zones": {}, "zones": {}}',
                     '{"zones":{"A":[0,0,NaN,1]}}'):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    parse_bundle(data, selected_system="gba")

    def test_reject_oversized_file_bounded_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.json"
            path.write_bytes(b"x" * (MAX_FILE_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "64 KiB"):
                load_bundle(path, selected_system="gba")

    def test_export_rejects_invalid_setting_instead_of_leaking(self):
        self.profile["rgb"] = [999, 0, 0]
        with self.assertRaisesRegex(ValueError, "rgb"):
            make_bundle("gba", self.profile, allowed_themes=self.themes)


if __name__ == "__main__":
    unittest.main()
