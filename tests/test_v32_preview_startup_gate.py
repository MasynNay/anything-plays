"""The frozen 3.2 QA startup predicate is strict and side-effect-free."""

from pathlib import Path
from types import SimpleNamespace
import unittest

from anything_plays.build_identity import make_identity
from anything_plays.preview_startup_gate import verify_preview_startup


class FakeRoot:
    def __init__(self, title):
        self.value = title

    def title(self):
        return self.value


class PreviewStartupGateTests(unittest.TestCase):
    def fixtures(self):
        identity = make_identity("v32_preview")
        app = SimpleNamespace(
            preferences_path=Path(
                "/home/test/.config/anything-plays-32-preview/preferences.json"
            ),
            cap=None,
            _gamepad=SimpleNamespace(api=None),
            armed=False,
        )
        return app, FakeRoot(identity["title"]), identity

    def test_exact_frozen_preview_is_accepted_without_devices(self):
        app, root, identity = self.fixtures()
        self.assertTrue(
            verify_preview_startup(
                app, root, identity=identity, frozen=True,
            )
        )

    def test_environment_only_source_preview_cannot_pass_frozen_gate(self):
        app, root, identity = self.fixtures()
        self.assertFalse(
            verify_preview_startup(
                app, root, identity=identity, frozen=False,
            )
        )

    def test_previous_stable_identity_or_settings_cannot_pass(self):
        app, root, identity = self.fixtures()
        self.assertFalse(
            verify_preview_startup(
                app, root,
                identity=make_identity("v311_stable_candidate"),
                frozen=True,
            )
        )
        app.preferences_path = Path(
            "/home/test/.config/anything-plays-31/preferences.json"
        )
        self.assertFalse(
            verify_preview_startup(
                app, root, identity=identity, frozen=True,
            )
        )

    def test_corrupted_marker_cannot_pass(self):
        app, root, identity = self.fixtures()
        identity["public_release_approved"] = True
        self.assertFalse(
            verify_preview_startup(
                app, root, identity=identity, frozen=True,
            )
        )

    def test_started_camera_controller_or_armed_controls_cannot_pass(self):
        app, root, identity = self.fixtures()
        for changed in (
            ("cap", object()),
            ("_gamepad", SimpleNamespace(api=object())),
            ("armed", True),
        ):
            with self.subTest(changed=changed[0]):
                other, _, _ = self.fixtures()
                setattr(other, changed[0], changed[1])
                self.assertFalse(
                    verify_preview_startup(
                        other, root, identity=identity, frozen=True,
                    )
                )

    def test_wrong_title_or_missing_controller_reader_cannot_pass(self):
        app, root, identity = self.fixtures()
        self.assertFalse(
            verify_preview_startup(
                app, FakeRoot("Anything Plays 3.1.1"),
                identity=identity, frozen=True,
            )
        )
        del app._gamepad
        self.assertFalse(
            verify_preview_startup(
                app, root, identity=identity, frozen=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
