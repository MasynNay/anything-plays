"""Portable control export must not write local console profiles.

All tests use synthetic Tk variables, temporary files and a fake profile store.
No webcam, controller, native core, ROM or user preferences are accessed.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from anything_plays.portable_profiles import load_bundle
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import default_for
from anything_plays.ui_profiles import ProfilesMixin
from tools.verify_v32_installed_gui import REQUIRED_TRUE


class Variable:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value


class Host:
    THEMES = ("Dark",)
    def __init__(self):
        self.cfg = default_for("gba", DEFAULT)
        self.cfg["zone_image"] = "/private/camera-art.png"
        self.cfg["rom_directory"] = "C:/private/game-library"
        self.cfg["tolerance"] = 42
        self.system_key = Variable("gba")
        self.theme_name = Variable("Dark")
        self.status = Variable("")
        self.root = None
        self.profile_store = Mock()
        self._read_count = 0
    def read_settings(self):
        self._read_count += 1


class ExportIsolationTests(unittest.TestCase):
    def test_frozen_installer_requires_export_only_behavior(self):
        self.assertIn("v32_single_control_export_isolated", REQUIRED_TRUE)

    def test_export_writes_portable_file_without_modifying_live_storage(self):
        with TemporaryDirectory() as td:
            target = Path(td) / "portable.json"
            host = Host()
            with patch(
                "anything_plays.ui_profiles.filedialog.asksaveasfilename",
                return_value=str(target),
            ):
                ProfilesMixin.save_profile(host)
            self.assertTrue(target.is_file())
            self.assertEqual(host._read_count, 1)
            host.profile_store.put.assert_not_called()
            host.profile_store.put_many.assert_not_called()
            profile, theme, legacy = load_bundle(
                target, selected_system="gba", allowed_themes=host.THEMES,
            )
            self.assertFalse(legacy)
            self.assertEqual(profile["tolerance"], 42)
            self.assertEqual(theme, "Dark")
            self.assertNotIn("zone_image", target.read_text("utf-8"))
            self.assertNotIn("rom_directory", target.read_text("utf-8"))
            self.assertIn("exported", host.status.get())

    def test_failed_backup_does_not_modify_profile_store_or_show_success(self):
        with TemporaryDirectory() as td:
            target = Path(td) / "portable.json"
            host = Host()
            with patch(
                "anything_plays.ui_profiles.filedialog.asksaveasfilename",
                return_value=str(target),
            ), patch(
                "anything_plays.ui_profiles.save_bundle",
                side_effect=OSError("simulated disk full"),
            ), patch(
                "anything_plays.ui_profiles.messagebox.showerror",
            ) as error:
                ProfilesMixin.save_profile(host)
            error.assert_called_once()
            self.assertFalse(target.exists())
            self.assertEqual(host.status.get(), "")
            host.profile_store.put.assert_not_called()

    def test_cancel_export_keeps_existing_local_state(self):
        host = Host()
        with patch(
            "anything_plays.ui_profiles.filedialog.asksaveasfilename",
            return_value="",
        ):
            ProfilesMixin.save_profile(host)
        host.profile_store.put.assert_not_called()
        self.assertEqual(host.status.get(), "")


if __name__ == "__main__":
    unittest.main()
