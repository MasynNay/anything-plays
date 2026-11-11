"""Bezel activity follows real camera and game session lifecycle events.

Synthetic UI contract tests avoid requiring a physical webcam, paid ROM or Tk
display; the real composed widgets are checked by tests/smoke_gui.py.
"""
from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from anything_plays.ui_camera import CameraMixin
from anything_plays.ui_library import LibraryMixin


class Value:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Activity:
    def __init__(self):
        self.events = []

    def set_active(self, state):
        assert type(state) is bool
        self.events.append(state)


class FakeCapture:
    def __init__(self, opened):
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def release(self):
        self.released = True


def camera_stub():
    panel = SimpleNamespace(
        camera_name=Value("USB Camera"),
        camera_options={"USB Camera": 0},
        camera_bezel=Activity(),
        status=Value(),
        cap=None,
        frame=None,
        camera_photo=None,
        reference_image=False,
        _static_preview_next_draw=0,
        _camera_canvas_item=None,
        _camera_reconnect_job=None,
        _camera_reconnect_name=None,
        _camera_reconnect_attempts=0,
        stop_controls=lambda: None,
        cancel_camera_reconnect=lambda: None,
        canvas=SimpleNamespace(delete=lambda _name: None),
    )
    panel.stop_camera = lambda **kw: CameraMixin.stop_camera(panel, **kw)
    return panel


def game_stub():
    emulator = SimpleNamespace(
        running=False,
        core_path="native-libretro.so",
        lock=nullcontext(),
        start=lambda _path: None,
        stop=lambda: None,
        find_system_core=lambda: "native-libretro.so",
        frame=None,
    )
    app = SimpleNamespace(
        game_bezel=Activity(),
        emu=emulator,
        game_status=Value(),
        current_rom=None,
        game_canvas=SimpleNamespace(delete=lambda _name: None),
        system_key=Value("gba"),
        root=object(),
        _core_install_busy=False,
        uses_embedded_emulator=lambda: True,
        stop_external_emulator=lambda: None,
        stop_controls=lambda: None,
        deactivate_manual=lambda: None,
        show_playing_info=lambda: None,
        show_library=lambda: None,
    )
    return app


class BezelLifecycleTests(unittest.TestCase):
    def test_camera_only_lights_after_successful_device_open(self):
        app = camera_stub()
        successful = FakeCapture(True)
        with patch("anything_plays.ui_camera.cv2.VideoCapture", return_value=successful):
            CameraMixin.start_camera(app)
        self.assertEqual(app.camera_bezel.events, [False, True])
        self.assertIn("Camera ready", app.status.get())
        CameraMixin.stop_camera(app)
        self.assertEqual(app.camera_bezel.events[-1], False)
        self.assertTrue(successful.released)

    def test_camera_failed_open_never_claims_camera_on(self):
        app = camera_stub()
        denied = FakeCapture(False)
        with patch("anything_plays.ui_camera.cv2.VideoCapture", return_value=denied):
            with patch("anything_plays.ui_camera.messagebox.showerror"):
                CameraMixin.start_camera(app)
        self.assertNotIn(True, app.camera_bezel.events)

    def test_camera_reconnect_reports_active_only_after_success(self):
        app = camera_stub()
        app._queue_camera_retry = lambda _name: None
        with patch("anything_plays.ui_camera.cv2.VideoCapture", return_value=FakeCapture(True)):
            CameraMixin.start_camera(app, reconnecting=True)
        self.assertEqual(app.camera_bezel.events[-1], True)
        self.assertIn("reconnected", app.status.get())
        self.assertIsNone(app._camera_reconnect_name)

    def test_game_marks_session_only_after_start_returns(self):
        app = game_stub()
        LibraryMixin.start_rom(app, "/tmp/mytest.gba")
        self.assertEqual(app.game_bezel.events, [False, True])
        self.assertEqual(app.current_rom, "/tmp/mytest.gba")
        self.assertIn("Starting", app.game_status.get())

    def test_game_start_failure_does_not_light_console(self):
        app = game_stub()

        def raise_from_core(_path):
            raise RuntimeError("broken core")

        app.emu.start = raise_from_core
        with patch("anything_plays.ui_library.messagebox.showerror"):
            LibraryMixin.start_rom(app, "/tmp/mytest.gba")
        self.assertEqual(app.game_bezel.events, [False, False])
        self.assertIn("could not start", app.game_status.get())

    def test_game_unload_clears_console_session(self):
        app = game_stub()
        LibraryMixin.start_rom(app, "/tmp/mytest.gba")
        LibraryMixin.unload_rom(app)
        self.assertEqual(app.game_bezel.events[-1], False)
        self.assertIsNone(app.current_rom)
        self.assertEqual(app.game_status.get(), "No ROM loaded")

    def test_legacy_fake_app_without_bezel_remains_supported(self):
        app = camera_stub()
        del app.camera_bezel
        with patch("anything_plays.ui_camera.cv2.VideoCapture", return_value=FakeCapture(True)):
            CameraMixin.start_camera(app)
        CameraMixin.stop_camera(app)
        game = game_stub()
        del game.game_bezel
        LibraryMixin.start_rom(game, "/tmp/test.gba")
        LibraryMixin.unload_rom(game)


if __name__ == "__main__":
    unittest.main()
