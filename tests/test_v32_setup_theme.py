"""Theme changes refresh every native Canvas in 3.2 setup dialogs.

Headless tests use Tcl StringVar (no Tk or physical GUI required) and verify
both live theme updates and cleanup after the related dialog is destroyed.
"""

from types import SimpleNamespace
import tkinter as tk
import unittest

from anything_plays.ui_setup_theme import bind_theme_canvas


class FakeCanvas:
    def __init__(self):
        self.exists = True
        self.background = None
        self.calls = 0

    def winfo_exists(self):
        return self.exists

    def configure(self, **kwargs):
        self.background = kwargs["bg"]
        self.calls += 1


class FakeWindow:
    def __init__(self):
        self.listeners = {}

    def bind(self, event, callback, add=None):
        self.listeners[event] = callback
        assert add == "+"

    def destroy(self):
        event = SimpleNamespace(widget=self)
        self.listeners["<Destroy>"](event)


class SetupCanvasThemeTests(unittest.TestCase):
    def setUp(self):
        self.interpreter = tk.Tcl()
        self.theme_name = tk.StringVar(
            master=self.interpreter, value="Dark",
        )
        self.app = SimpleNamespace(
            theme_name=self.theme_name,
            THEMES={
                "Dark": ("unused", "#151515"),
                "Light": ("unused", "#f7f7f7"),
                "Plum Dark": ("unused", "#3e264e"),
            },
        )

    def test_updates_live_surface_and_detaches_trace_on_close(self):
        count = len(self.theme_name.trace_info())
        window, canvas = FakeWindow(), FakeCanvas()
        bind_theme_canvas(self.app, window, canvas)
        self.assertEqual(canvas.background, "#151515")
        self.assertEqual(len(self.theme_name.trace_info()), count + 1)
        self.theme_name.set("Light")
        self.assertEqual(canvas.background, "#f7f7f7")
        self.theme_name.set("Plum Dark")
        self.assertEqual(canvas.background, "#3e264e")
        calls = canvas.calls
        window.destroy()
        self.assertEqual(len(self.theme_name.trace_info()), count)
        self.theme_name.set("Dark")
        self.assertEqual(canvas.calls, calls)

    def test_destroying_nested_children_does_not_remove_parent_trace(self):
        window, canvas = FakeWindow(), FakeCanvas()
        bind_theme_canvas(self.app, window, canvas)
        count = len(self.theme_name.trace_info())
        window.listeners["<Destroy>"](
            SimpleNamespace(widget=object())
        )
        self.assertEqual(len(self.theme_name.trace_info()), count)
        self.theme_name.set("Light")
        self.assertEqual(canvas.background, "#f7f7f7")
        window.destroy()

    def test_unknown_theme_falls_back_to_dark_surface(self):
        window, canvas = FakeWindow(), FakeCanvas()
        bind_theme_canvas(self.app, window, canvas)
        self.theme_name.set("Not a theme")
        self.assertEqual(canvas.background, "#151515")
        window.destroy()


if __name__ == "__main__":
    unittest.main()
