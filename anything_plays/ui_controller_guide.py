"""A small, non-modal first-run controller/keyboard helper for Tk.

It reads existing SDL status and does not initialize additional controller
devices, create a game session, or simulate gameplay input.
"""

import tkinter as tk
from tkinter import ttk

from anything_plays.controller_onboarding import setup_guidance


def show_controller_guide(app):
    existing = getattr(app, "_controller_guide_window", None)
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.lift()
                existing.focus_set()
                return
        except tk.TclError:
            pass

    window = tk.Toplevel(app.root)
    app._controller_guide_window = window
    app._controller_guide_job = None
    window.title("Controller & keyboard setup · Anything Plays 3.2")
    window.transient(app.root)
    window.geometry("570x525")
    window.minsize(460, 400)

    shell = ttk.Frame(window, padding=12)
    shell.pack(fill="both", expand=True)
    scroller = ttk.Frame(shell)
    scroller.pack(fill="both", expand=True)
    canvas = tk.Canvas(scroller, highlightthickness=0, borderwidth=0)
    bar = ttk.Scrollbar(scroller, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=bar.set)
    bar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    wrapper = ttk.Frame(canvas, padding=(5, 4))
    content_id = canvas.create_window((0, 0), window=wrapper, anchor="nw")
    wrapper.bind(
        "<Configure>",
        lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.bind(
        "<Configure>",
        lambda event: canvas.itemconfigure(content_id, width=event.width),
    )
    ttk.Label(
        wrapper, text="Get your controls working",
        font=("TkDefaultFont", 17, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        wrapper,
        text="No game or webcam required. Connect a controller, check its "
             "buttons, then choose the game actions. Keyboard play works "
             "without a controller.",
        style="Helper.TLabel", wraplength=515, justify="left",
    ).pack(anchor="w", pady=(4, 14))

    status = ttk.LabelFrame(wrapper, text="YOUR NEXT STEP", padding=12)
    status.pack(fill="x")
    heading = tk.StringVar(master=window)
    description = tk.StringVar(master=window)
    ttk.Label(status, textvariable=heading, style="Value.TLabel").pack(anchor="w")
    ttk.Label(
        status, textvariable=description, wraplength=505,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))

    live = ttk.LabelFrame(wrapper, text="LIVE INPUT (READ-ONLY)", padding=12)
    live.pack(fill="x", pady=(11, 0))
    feedback = tk.StringVar(master=window)
    ttk.Label(
        live, textvariable=feedback, wraplength=505, justify="left",
    ).pack(anchor="w")

    rows = ttk.Frame(wrapper)
    rows.pack(fill="x", pady=(13, 0))
    rows.columnconfigure(0, weight=1, uniform="setup")
    rows.columnconfigure(1, weight=1, uniform="setup")

    def enable_or_scan():
        if not app.gamepad_enabled.get():
            app.gamepad_enabled.set(True)
            app.toggle_gamepad()
        else:
            app.refresh_gamepad()

    ttk.Button(
        rows, text="Enable & scan", command=enable_or_scan,
        style="Accent.TButton",
    ).grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=(0, 8))
    ttk.Button(
        rows, text="Rescan connected devices",
        command=app.refresh_gamepad,
    ).grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=(0, 8))
    ttk.Button(
        rows, text="Button mapping",
        command=lambda: app.open_controller_settings(parent=window),
    ).grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=(0, 8))
    ttk.Button(
        rows, text="Keyboard controls",
        command=app.configure_shortcuts,
    ).grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=(0, 8))
    ttk.Button(
        rows, text="Copy safe diagnostics",
        command=app.copy_gamepad_diagnostics,
    ).grid(row=2, column=0, columnspan=2, sticky="ew")

    ttk.Label(
        wrapper, textvariable=app.gamepad_diagnostics_status,
        style="Helper.TLabel", wraplength=515, justify="left",
    ).pack(anchor="w", pady=(9, 0))
    ttk.Label(
        wrapper,
        text="Input detection is not certification of a physical controller "
             "model. No game controls are changed until you choose a mapping.",
        style="Helper.TLabel", wraplength=515, justify="left",
    ).pack(anchor="w", pady=(7, 0))

    def close():
        job, app._controller_guide_job = (
            getattr(app, "_controller_guide_job", None), None
        )
        app._controller_guide_window = None
        app._controller_guide_close = None
        if job is not None:
            try:
                app.root.after_cancel(job)
            except tk.TclError:
                pass
        try:
            window.destroy()
        except tk.TclError:
            pass

    app._controller_guide_close = close
    footer = ttk.Frame(shell)
    footer.pack(fill="x", pady=(10, 0))
    ttk.Button(
        footer, text="Done", command=close, style="Accent.TButton",
    ).pack(side="right")
    window.protocol("WM_DELETE_WINDOW", close)

    def update():
        if getattr(app, "_closing", False) or app._controller_guide_window is not window:
            return
        try:
            reader = app._gamepad
            connected = app.gamepad_enabled.get() and reader.controller is not None
            observed = len(reader.physical_buttons) if connected else 0
            state = setup_guidance(
                enabled=app.gamepad_enabled.get(),
                connected=connected,
                focused=app.root.focus_get() is not None,
                pressed_count=observed,
                embedded=app.uses_embedded_emulator(),
            )
            heading.set(state[0])
            description.set(state[1])
            feedback.set(app._gamepad_live_message())
            app._controller_guide_job = app.root.after(250, update)
        except tk.TclError:
            close()

    update()
