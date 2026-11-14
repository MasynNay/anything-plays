"""3.2 development preview uses an isolated, opt-in local settings channel."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from anything_plays.build_identity import current_identity, make_identity
from anything_plays.test_preferences import prepare_test_preferences


class V32SourcePreviewTests(unittest.TestCase):
    def test_source_preview_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "absent-identity.json"
            with patch.dict(os.environ, {"AP_V32_PREVIEW": "1"}):
                with patch.object(sys, "frozen", False, create=True):
                    identity = current_identity(path=missing)
                    self.assertEqual(identity["channel"], "v32_preview")
                    self.assertEqual(
                        identity["settings_namespace"], "anything-plays-32-preview"
                    )
                    self.assertFalse(identity["public_release_approved"])
            with patch.dict(os.environ, {"AP_V32_PREVIEW": ""}):
                self.assertEqual(
                    current_identity(path=missing)["channel"], "preview1"
                )

    def test_a_frozen_install_cannot_select_preview_via_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "no-marker.json"
            with patch.dict(os.environ, {"AP_V32_PREVIEW": "1"}):
                with patch.object(sys, "frozen", True, create=True):
                    self.assertEqual(
                        current_identity(path=missing)["channel"], "preview1"
                    )

    def test_valid_embedded_stable_marker_overrides_source_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "v31-marker.json"
            marker.write_text(
                json.dumps(make_identity("v311_stable_candidate")),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"AP_V32_PREVIEW": "1"}):
                self.assertEqual(
                    current_identity(path=marker)["channel"],
                    "v311_stable_candidate",
                )

    def test_preview_never_reads_copies_or_changes_older_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            stable = home / ".config" / "fish-plays-pokemon-studio"
            old_preview = home / ".config" / "anything-plays-31-preview"
            for location in (stable, old_preview):
                location.mkdir(parents=True)
                (location / "preferences.json").write_text(
                    '{"rom_directories": {"gba": "/private/user/roms"}}',
                    encoding="utf-8",
                )
                (location / "system_profiles.json").write_text(
                    '{"gba": {"rgb": [1, 2, 3]}}', encoding="utf-8"
                )
            path = prepare_test_preferences(home, channel="v32_preview")
            self.assertEqual(
                path, home / ".config" / "anything-plays-32-preview" / "preferences.json",
            )
            self.assertFalse(path.exists())
            self.assertFalse(path.with_name("system_profiles.json").exists())
            # Repeated launch has no migration even when old configs exist.
            self.assertEqual(
                prepare_test_preferences(home, channel="v32_preview"),
                path,
            )
            for location in (stable, old_preview):
                self.assertIn(
                    "/private/user/roms",
                    (location / "preferences.json").read_text(encoding="utf-8"),
                )
                self.assertIn(
                    '"rgb": [1, 2, 3]',
                    (location / "system_profiles.json").read_text(encoding="utf-8"),
                )

    def test_preview_rejects_linked_preference_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            stable = home / ".config" / "fish-plays-pokemon-studio"
            stable.mkdir(parents=True)
            source = stable / "preferences.json"
            source.write_text('{"user": "private"}', encoding="utf-8")
            preview = home / ".config" / "anything-plays-32-preview"
            preview.mkdir(parents=True)
            target = preview / "preferences.json"
            try:
                target.symlink_to(source)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink test unavailable on host")
            with self.assertRaisesRegex(ValueError, "linked"):
                prepare_test_preferences(home, channel="v32_preview")
            self.assertEqual(source.read_text(encoding="utf-8"),
                             '{"user": "private"}')


if __name__ == "__main__":
    unittest.main()
