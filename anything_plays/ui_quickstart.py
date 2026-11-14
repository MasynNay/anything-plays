"""Accessible, non-modal launchpad for Anything Plays 3.2 first-time setup.

This is navigation only: entering the guide never opens a camera, reads a
ROM, starts SDL, or arms object controls. Every operation needs a user click.
"""

import tkinter as tk
from tkinter import ttk
from anything_plays.ui_setup_theme import bind_theme_canvas


def show_quick_start(app):
    previous = getattr(app, "_quick_start_window", None)
    if previous is not None:
        try:
            if previous.winfo_exists():
                previous.lift()
                previous.focus_set()
                return
        except tk.TclError:
            pass

    window = tk.Toplevel(app.root)
    app._quick_start_window = window
    window.title("Get started · Anything Plays 3.2")
    window.transient(app.root)
    window.geometry("575x550")
    window.minsize(450, 410)

    def close():
        app._quick_start_window = None
        try:
            window.destroy()
        except tk.TclError:
            pass

    window.protocol("WM_DELETE_WINDOW", close)
    shell = ttk.Frame(window, padding=14)
    shell.pack(fill="both", expand=True)

    ttk.Label(
        shell, text="Make something move. Play a game.",
        font=("TkDefaultFont", 16, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        shell,
        text="A short setup path. Use a webcam to turn color and motion "
             "into controls, or just play with a keyboard or controller. "
             "No game files are included.",
        style="Helper.TLabel", wraplength=520, justify="left",
    ).pack(anchor="w", pady=(4, 10))

    from anything_plays.build_identity import current_identity
    if current_identity()["channel"] == "v32_preview":
        ttk.Label(
            shell,
            text="DEVELOPMENT PREVIEW · Only GB, GBC and GBA are bundled "
                 "in the test installers. Other console profiles may need "
                 "a separate native core. The preview starts with fresh, "
                 "separate game saves. Your stable installation, saved games "
                 "and settings are not imported or overwritten.",
            style="Helper.TLabel",
            wraplength=510, justify="left",
        ).pack(anchor="w", pady=(0, 10))

    holder = ttk.Frame(shell)
    holder.pack(fill="both", expand=True)
    surface = app.THEMES.get(
        app.theme_name.get(), app.THEMES["Dark"]
    )[1]
    canvas = tk.Canvas(
        holder, borderwidth=0, highlightthickness=0, bg=surface,
    )
    bind_theme_canvas(app, window, canvas)
    scroll = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    body = ttk.Frame(canvas)
    embedded = canvas.create_window((0, 0), window=body, anchor="nw")
    body.bind(
        "<Configure>",
        lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.bind(
        "<Configure>",
        lambda event: canvas.itemconfigure(embedded, width=event.width),
    )

    # A small, explicitly refreshed status summary makes the first-run
    # guide useful without requiring a troubleshooting dialog. Reuse the
    # same redacted, read-only report as Check my setup: no cameras, ROMs,
    # controllers, native cores or network connections are started here.
    readiness = ttk.LabelFrame(body, text="CURRENT SETUP", padding=(11, 9))
    readiness.pack(fill="x", padx=(1, 5), pady=(0, 10))
    ttk.Label(
        readiness,
        text="Camera and controller are optional. Keyboard play needs "
             "a compatible emulator core and your own game file.",
        style="Helper.TLabel", wraplength=485, justify="left",
    ).pack(anchor="w", pady=(0, 6))
    names = (
        ("emulator", "Emulator"),
        ("camera", "Camera"),
        ("controller", "Controller"),
        ("input_backend", "Input path"),
    )
    readiness_vars = {
        key: tk.StringVar(master=window, value=title + ": Not checked")
        for key, title in names
    }
    window._setup_readiness_vars = readiness_vars
    for key, _title in names:
        ttk.Label(
            readiness, textvariable=readiness_vars[key],
            style="Helper.TLabel", wraplength=485, justify="left",
        ).pack(anchor="w", pady=(2, 0))

    def refresh_readiness():
        try:
            from anything_plays.ui_setup_diagnostics import _snapshot
            checks = _snapshot(app)["checks"]
        except (ValueError, tk.TclError, OSError, RuntimeError, KeyError):
            for key, title in names:
                readiness_vars[key].set(
                    title + ": Could not check; open Check my setup."
                )
            return
        for key, title in names:
            readiness_vars[key].set(
                title + ": " + checks[key]["status"]
            )

    ttk.Button(
        readiness, text="Refresh status", command=refresh_readiness,
        style="Compact.TButton",
    ).pack(anchor="w", pady=(8, 0))
    refresh_readiness()

    def show_console():
        app.root.lift()
        app.system_combo.focus_set()

    def step(number, title, explanation, action_label, action):
        panel = ttk.LabelFrame(
            body, text=f"{number}  {title.upper()}", padding=(11, 9)
        )
        panel.pack(fill="x", padx=(1, 5), pady=(0, 9))
        ttk.Label(
            panel, text=explanation, style="Helper.TLabel",
            wraplength=490, justify="left",
        ).pack(anchor="w")
        ttk.Button(
            panel, text=action_label, command=action,
            style="Compact.TButton",
        ).pack(anchor="w", pady=(8, 0))

    step(
        "01", "Pick a console",
        "Choose one of the available console profiles in the main window. "
        "You supply your own legally obtained games.",
        "Choose console", show_console,
    )
    step(
        "02", "Choose how to control it",
        "A camera is optional. For color tracking, choose a webcam and "
        "sample the object in the live preview. You can skip this for "
        "keyboard or controller play.",
        "Calibrate camera (optional)", app.open_calibration_wizard,
    )
    step(
        "03", "Test your inputs",
        "Connect a controller and assign buttons, or configure keyboard "
        "controls. The setup guide shows live button detection.",
        "Set up controller or keyboard", app.open_controller_setup_guide,
    )
    step(
        "04", "Check and play",
        "Run local setup checks if something is missing. When ready, "
        "open your own game from the main library.",
        "Check my setup", app.open_setup_diagnostics,
    )

    footer = ttk.Frame(shell)
    footer.pack(fill="x", pady=(10, 0))
    ttk.Button(
        footer, text="Open a game…",
        command=app.load_rom, style="Accent.TButton",
    ).pack(side="left")
    ttk.Button(
        footer, text="Done", command=close,
    ).pack(side="right")
