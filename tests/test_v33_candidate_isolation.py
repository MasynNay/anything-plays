"""3.3 private candidate identity and native storage isolation contracts.

Source-only tests: no ROMs, graphics devices, native cores or installations.
A candidate must neither impersonate the 3.2 public identity nor touch
earlier developer previews, saved memory cards, downloadable cores or settings.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from anything_plays.build_identity import make_identity, validate_identity
from anything_plays.test_preferences import prepare_test_preferences
from anything_plays import core_packs, libretro_save, preview_storage
from tools.write_v31_identity import choose_channel, write_identity


ENV = {
    "AP_V33_CANDIDATE": "1",
    "AP_V30_MINIMAL_CORE_BUILD": "1",
    "AP_RELEASE_BUILD": "0",
    "AP_V30_APPROVED_RELEASE": "0",
    "AP_V30_STABLE_CANDIDATE": "0",
    "AP_V30_TEST_CORES": "0",
    "AP_V30_GPL_TRIAL": "0",
    "AP_V30_TIA_TRIAL": "0",
    "AP_V32_PREVIEW_BUILD": "0",
    "AP_V32_STABLE_CANDIDATE": "0",
}


class V33PrivateCandidateTests(unittest.TestCase):
    def test_identity_distinct_version_title_namespace_and_rejection(self):
        identity = make_identity("v33_candidate")
        self.assertEqual(identity["version"], "3.3.0-qa")
        self.assertEqual(identity["channel"], "v33_candidate")
        self.assertEqual(
            identity["settings_namespace"], "anything-plays-33-candidate"
        )
        self.assertIn("Private Hardware QA", identity["title"])
        self.assertFalse(identity["public_release_approved"])
        self.assertEqual(validate_identity(identity), identity)
        for channel in ("v32_preview", "v32_stable_candidate", "rc2",
                        "v311_stable_candidate", "final_candidate"):
            self.assertNotEqual(
                identity["settings_namespace"],
                make_identity(channel)["settings_namespace"],
            )
        for key, broken in (
            ("channel", "v32_preview"),
            ("version", "3.2.0"),
            ("settings_namespace", "anything-plays-31"),
            ("public_release_approved", True),
        ):
            with self.subTest(field=key), self.assertRaises(ValueError):
                validate_identity({**identity, key: broken})

    def test_build_flag_exclusive_without_redistribution_permissions(self):
        self.assertEqual(choose_channel(ENV), "v33_candidate")
        for name, value in (
            ("AP_V33_CANDIDATE", "0"),
            ("AP_V32_PREVIEW_BUILD", "1"),
            ("AP_V32_STABLE_CANDIDATE", "1"),
            ("AP_V31_RC2", "1"),
            ("AP_RELEASE_BUILD", "1"),
            ("AP_V30_APPROVED_RELEASE", "1"),
            ("AP_V30_TEST_CORES", "1"),
            ("AP_V30_GPL_TRIAL", "1"),
            ("AP_V30_MINIMAL_CORE_BUILD", "0"),
        ):
            with self.subTest(flag=name), self.assertRaises(ValueError):
                choose_channel({**ENV, name: value})
        with TemporaryDirectory() as tmp:
            marker = Path(tmp) / "assets" / "v31_build_identity.json"
            identity = write_identity(marker, ENV)
            self.assertEqual(identity, make_identity("v33_candidate"))
            self.assertEqual(json.loads(marker.read_text()), identity)

    def test_settings_are_not_imported_from_stable_or_v32(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            for name in ("anything-plays-31",
                         "anything-plays-32-preview"):
                folder = home / ".config" / name
                folder.mkdir(parents=True)
                (folder / "preferences.json").write_text(
                    '{"secret":"STABLE_OR_OLD_PREVIEW"}', encoding="utf-8"
                )
            dest = prepare_test_preferences(home, channel="v33_candidate")
            self.assertEqual(dest.parent.name, "anything-plays-33-candidate")
            self.assertFalse(dest.exists())
            self.assertFalse((dest.parent / "system_profiles.json").exists())
            dest.write_text('{"private_33":true}', encoding="utf-8")
            self.assertEqual(prepare_test_preferences(
                home, channel="v33_candidate"
            ).read_text(), '{"private_33":true}')
            for previous in ("anything-plays-31",
                             "anything-plays-32-preview"):
                self.assertIn("STABLE_OR_OLD_PREVIEW", (
                    home / ".config" / previous / "preferences.json"
                ).read_text())

    def test_candidate_symlinks_cannot_redirect_settings_or_system_directory(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            stable = home / ".config" / "anything-plays-31"
            stable.mkdir(parents=True)
            destination = home / ".config" / "anything-plays-33-candidate"
            try:
                destination.symlink_to(stable, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unsupported on this host")
            with self.assertRaises(ValueError):
                prepare_test_preferences(home, channel="v33_candidate")
            with patch.object(preview_storage, "is_v33_candidate",
                              return_value=True):
                with self.assertRaises(ValueError):
                    preview_storage.preview_system_directory(home)

    def test_core_and_sram_paths_are_distinct_and_private_on_this_os(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            data = home / "data"
            data.mkdir()
            env = {
                "XDG_DATA_HOME": str(data),
                "APPDATA": str(data),
                "LOCALAPPDATA": str(data),
            }
            with (
                patch("pathlib.Path.home", return_value=home),
                patch.dict(os.environ, env),
                patch.object(core_packs, "is_v33_candidate",
                             return_value=True),
                patch.object(core_packs, "is_v32_preview",
                             return_value=False),
                patch.object(libretro_save, "is_v33_candidate",
                             return_value=True),
                patch.object(libretro_save, "is_v32_preview",
                             return_value=False),
            ):
                core = core_packs.managed_core_root()
                sav = libretro_save._user_save_directory()
                native = libretro_save.native_core_save_directory(
                    home / "not-a-real-rom.gba", "gamecube"
                )
                self.assertIn("3.3", str(core))
                self.assertIn("3.3", str(sav))
                self.assertTrue(str(native).startswith(str(sav)))
                self.assertNotIn("3.2", str(core))
                self.assertNotIn("3.2", str(sav))
                self.assertNotIn("anything-plays-31", str(sav))
                self.assertNotIn("3.0", str(core))

            with (
                patch("pathlib.Path.home", return_value=home),
                patch.dict(os.environ, env),
                patch.object(core_packs, "is_v33_candidate",
                             return_value=False),
                patch.object(core_packs, "is_v32_preview",
                             return_value=False),
                patch.object(libretro_save, "is_v33_candidate",
                             return_value=False),
                patch.object(libretro_save, "is_v32_preview",
                             return_value=False),
            ):
                self.assertNotEqual(core, core_packs.managed_core_root())
                self.assertNotEqual(sav, libretro_save._user_save_directory())


if __name__ == "__main__":
    unittest.main()
