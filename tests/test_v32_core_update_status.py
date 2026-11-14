"""3.2 runtime fixes: approved core-pack filtering and preview messaging."""

import unittest
from unittest.mock import patch

from anything_plays.build_identity import make_identity
from anything_plays.ui_updates import (
    FULL_APP_ONLY, UpdatesMixin, _pending_core_packs,
)


class Value:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class StubApp(UpdatesMixin):
    def __init__(self, system):
        self.system_key = Value(system)
        self._selected_emulator_status = Value()


class EmulatorPreviewTests(unittest.TestCase):
    def test_private_preview_never_auto_checks_online(self):
        app = StubApp("gba")
        app._closing = False
        app._emulator_update_status = Value()
        app.check_emulator_updates = lambda **kwargs: self.fail(
            "3.2 preview cannot initiate an automatic online check"
        )
        with patch(
            "anything_plays.build_identity.current_identity",
            return_value=make_identity("v32_preview"),
        ):
            app.schedule_emulator_update_checks()
        self.assertIn(
            "Automatic emulator update checks are paused",
            app._emulator_update_status.get(),
        )

    def test_dolphin_sys_can_only_be_released_with_full_app(self):
        self.assertIn("dolphin", FULL_APP_ONLY)
        remote = [
            {"name": "dolphin", "sha256": "d" * 64},
            {"name": "mgba", "sha256": "a" * 64},
            {"name": "snes9x", "sha256": "b" * 64},
        ]
        installed = {"mgba": "a" * 64, "snes9x": "0" * 64}
        calls = []

        def revision(name):
            calls.append(name)
            return installed.get(name)

        found = _pending_core_packs(remote, revision)
        self.assertEqual(found, [remote[2]])
        self.assertNotIn("dolphin", calls)

    def test_unbundled_preview_console_does_not_claim_corruption(self):
        app = StubApp("snes")
        with patch(
            "anything_plays.build_identity.current_identity",
            return_value=make_identity("v32_preview"),
        ):
            with patch("anything_plays.core_locator.find_core", return_value=None):
                app.refresh_selected_emulator_state()
        message = app._selected_emulator_status.get()
        self.assertIn("Not bundled in this 3.2 preview", message)
        self.assertNotIn("repair", message.lower())

    def test_preview_mgba_missing_is_real_problem_not_claimed_ready(self):
        app = StubApp("gba")
        with patch(
            "anything_plays.build_identity.current_identity",
            return_value=make_identity("v32_preview"),
        ):
            with patch("anything_plays.core_locator.find_core", return_value=None):
                app.refresh_selected_emulator_state()
        self.assertIn("missing", app._selected_emulator_status.get())

    def test_installed_core_still_reports_ready(self):
        app = StubApp("snes")
        with patch("anything_plays.core_locator.find_core",
                   return_value="/isolated/example_core.so"):
            app.refresh_selected_emulator_state()
        self.assertIn("Ready inside Anything Plays",
                      app._selected_emulator_status.get())


if __name__ == "__main__":
    unittest.main()
