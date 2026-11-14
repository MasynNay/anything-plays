"""Keep non-modal setup-dialog canvases synchronized with app themes.

ttk widgets follow App's themes but native Tk Canvas surfaces do not.
A variable trace updates only the affected canvas, and is detached when the
child window is destroyed so subsequent theme changes never reference a
destroyed widget.
"""

import tkinter as tk


def bind_theme_canvas(app, window, canvas):
    """Theme a scroll canvas for its lifetime; never keep stale Tcl traces."""
    token = None

    def refresh(*_):
        try:
            theme = app.THEMES.get(
                app.theme_name.get(), app.THEMES["Dark"],
            )
            if canvas.winfo_exists():
                canvas.configure(bg=theme[1])
        except tk.TclError:
            # During Tk teardown, the window or Tcl variables may be gone.
            pass

    token = app.theme_name.trace_add("write", refresh)

    def forget(event):
        if event.widget is not window:
            return
        try:
            app.theme_name.trace_remove("write", token)
        except (tk.TclError, ValueError):
            pass

    window.bind("<Destroy>", forget, add="+")
    refresh()
