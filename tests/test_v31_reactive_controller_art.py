"""Reactive native Tk controller artwork must remain accessible and cheap.

A visual highlight is a read-only projection of raw SDL input. It must never
map or inject buttons, create unbounded canvas shapes or require a real pad.
"""
from __future__ import annotations

from types import SimpleNamespace
import unittest

from anything_plays.ui_controller_art import draw_gamepad
from anything_plays.ui_gamepad import GamepadMixin
from anything_plays.ui_theme import ThemeMixin


class Canvas:
    def __init__(self):
        self.settings = {}
        self.shapes = []
        self.clear_count = 0

    def winfo_exists(self):
        return True

    def configure(self, **settings):
        self.settings.update(settings)

    def delete(self, target):
        if target != "all":
            raise AssertionError("Artwork must always clear prior shapes")
        self.shapes.clear()
        self.clear_count += 1

    def create_oval(self, *coords, **opts):
        self.shapes.append(("oval", coords, opts))

    def create_polygon(self, *coords, **opts):
        self.shapes.append(("polygon", coords, opts))

    def create_rectangle(self, *coords, **opts):
        self.shapes.append(("rectangle", coords, opts))

    def create_text(self, *coords, **opts):
        self.shapes.append(("text", coords, opts))


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def fill_at(canvas, kind, coord, tolerance=0.15):
    for shape, points, opts in canvas.shapes:
        if shape == kind and len(points) >= 2 and all(
            abs(points[i] - coord[i]) <= tolerance for i in (0, 1)
        ):
            return opts.get("fill")
    raise AssertionError("Expected controller shape not drawn at " + str(coord))


class ControllerArtLiveTests(unittest.TestCase):
    def test_buttons_dpad_sticks_and_shoulders_light_in_current_theme(self):
        for theme, palette in ThemeMixin.THEMES.items():
            with self.subTest(theme=theme):
                idle = Canvas()
                active = Canvas()
                draw_gamepad(idle, palette, connected=True, expanded=True)
                draw_gamepad(active, palette, connected=True, expanded=True,
                             pressed={"A", "DPAD_UP", "LEFT_STICK_RIGHT",
                                      "LEFT_SHOULDER", "START"})
                sx, sy = 278 / 100, 150 / 60
                face_at = (71 * sx, 30 * sy)
                self.assertEqual(fill_at(idle, "oval", face_at), palette[3])
                self.assertEqual(fill_at(active, "oval", (70.5 * sx, 29.5 * sy)),
                                 palette[2])
                self.assertEqual(fill_at(idle, "rectangle", (21 * sx, 21 * sy)),
                                 palette[2])
                self.assertEqual(fill_at(active, "rectangle", (21 * sx, 21 * sy)),
                                 palette[3])
                self.assertEqual(fill_at(active, "oval", (17 * sx, 6 * sy)),
                                 palette[3])
                self.assertEqual(fill_at(idle, "oval", (17 * sx, 6 * sy)),
                                 palette[5])
                self.assertEqual(fill_at(active, "oval", (34.8 * sx, 28.8 * sy)),
                                 palette[5])
                self.assertEqual(len(active.shapes), len(idle.shapes))
                self.assertGreater(len(active.shapes), 20)

    def test_offline_and_unknown_inputs_do_not_light_buttons(self):
        palette = ThemeMixin.THEMES["Ocean Dark"]
        empty = Canvas()
        unknown = Canvas()
        offline = Canvas()
        draw_gamepad(empty, palette, connected=True, expanded=True)
        draw_gamepad(unknown, palette, connected=True, expanded=True,
                     pressed={"arbitrary_name", "/user/path", 123})
        draw_gamepad(offline, palette, connected=False, expanded=True,
                     pressed={"A", "DPAD_UP"})
        self.assertEqual(empty.shapes, unknown.shapes)
        self.assertEqual(empty.shapes, offline.shapes)

    def test_redraw_count_does_not_accumulate_hidden_objects(self):
        palette = ThemeMixin.THEMES["Ocean Dark"]
        canvas = Canvas()
        draw_gamepad(canvas, palette, connected=True, pressed=("A",))
        count = len(canvas.shapes)
        for _ in range(20):
            draw_gamepad(canvas, palette, connected=True, pressed=("A",))
        self.assertEqual(len(canvas.shapes), count)
        self.assertEqual(canvas.clear_count, 21)

    def test_same_controller_status_still_redraws_new_live_input_once(self):
        app = GamepadMixin()
        app.THEMES = ThemeMixin.THEMES
        app.theme_name = Value("Ocean Dark")
        app.gamepad_enabled = Value(True)
        app.gamepad_status = Value("Gamepad connected")
        app.system_key = Value("gba")
        app._gamepad_bindings = {}
        app._closing = False
        app.gamepad_quick_canvas = Canvas()
        app.gamepad_setup_canvas = Canvas()
        app._refresh_gamepad_live_input = lambda: None
        app.uses_embedded_emulator = lambda: True
        inputs = []
        app.emu = SimpleNamespace(
            running=True, set_gamepad_buttons=lambda buttons: inputs.append(buttons),
            release_gamepad=lambda: None,
        )
        after = []
        app.root = SimpleNamespace(
            focus_get=lambda: object(),
            after=lambda ms, callback: after.append((ms, callback)) or "job",
        )
        current = {"raw": frozenset()}
        reader = SimpleNamespace(
            api=object(), controller=object(),
            physical_buttons=frozenset(),
        )

        def poll(system, bindings):
            reader.physical_buttons = current["raw"]
            return frozenset({"A"}) if "A" in current["raw"] else frozenset(), "Gamepad connected"

        reader.poll = poll
        app._gamepad = reader

        app.gamepad_tick()
        self.assertEqual(app.gamepad_quick_canvas.clear_count, 1)
        self.assertEqual(app.gamepad_setup_canvas.clear_count, 1)
        app.gamepad_tick()
        self.assertEqual(app.gamepad_quick_canvas.clear_count, 1)
        current["raw"] = frozenset({"A"})
        app.gamepad_tick()
        self.assertEqual(app.gamepad_quick_canvas.clear_count, 2)
        self.assertEqual(app.gamepad_setup_canvas.clear_count, 2)
        self.assertEqual(inputs[-1], frozenset({"A"}))
        app.gamepad_tick()
        self.assertEqual(app.gamepad_quick_canvas.clear_count, 2)
        current["raw"] = frozenset()
        app.gamepad_tick()
        self.assertEqual(app.gamepad_quick_canvas.clear_count, 3)
        self.assertTrue(all(interval == 65 for interval, _ in after))

    def test_canvas_is_only_visual_no_control_callbacks(self):
        import inspect
        source = inspect.getsource(draw_gamepad)
        self.assertNotIn(".bind(", source)
        self.assertNotIn("import pygame", source)
        self.assertNotIn("set_gamepad_buttons", source)


if __name__ == "__main__":
    unittest.main()
