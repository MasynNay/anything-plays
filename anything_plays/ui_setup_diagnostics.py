"""Read-only setup troubleshooting window for Anything Plays 3.2.

Each Refresh only reads current local state. It never opens cameras, starts
emulators, downloads assets, changes gamepad mappings or sends diagnostics.
"""

import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from anything_plays.setup_health import build_setup_report


def _snapshot(app):
    selected = app.camera_name.get() in app.camera_options
    active = False
    cap = getattr(app, "cap", None)
    if cap is not None:
        try:
            active = bool(cap.isOpened())
        except Exception:
            active = False
    path = getattr(app.emu, "core_path", None)
    try:
        core_found = bool(path and Path(path).is_file())
    except (OSError, TypeError, ValueError):
        core_found = False
    reader = getattr(app, "_gamepad", None)
    enabled = app.gamepad_enabled.get()
    connected = bool(enabled and reader is not None
                     and reader.controller is not None)
    return build_setup_report(
        system=app.system_key.get(),
        camera_count=len(app.camera_options),
        camera_selected=selected,
        camera_active=active,
        core_found=core_found,
        controller_enabled=enabled,
        controller_detected=connected,
        embedded_mode=bool(app.uses_embedded_emulator()),
    )


def show_setup_diagnostics(app):
    existing = getattr(app, "_setup_diagnostics_window", None)
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.lift()
                existing.focus_set()
                return
        except tk.TclError:
            pass

    window = tk.Toplevel(app.root)
    app._setup_diagnostics_window = window
    window.title("Check my setup · Anything Plays 3.2")
    window.transient(app.root)
    window.geometry("625x615")
    window.minsize(480, 430)

    def close():
        app._setup_diagnostics_window = None
        try:
            window.destroy()
        except tk.TclError:
            pass

    window.protocol("WM_DELETE_WINDOW", close)
    shell = ttk.Frame(window, padding=(15, 14))
    shell.pack(fill="both", expand=True)
    ttk.Label(
        shell, text="What's stopping my setup?",
        font=("TkDefaultFont", 17, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        shell,
        text="Review camera, emulator and controller status without a game "
             "file or network connection. These checks cannot verify every "
             "webcam or game.",
        style="Helper.TLabel", wraplength=575, justify="left",
    ).pack(anchor="w", pady=(4, 10))

    holder = ttk.Frame(shell)
    holder.pack(fill="both", expand=True)
    canvas = tk.Canvas(holder, highlightthickness=0, borderwidth=0,
                       bg=app.THEMES.get(app.theme_name.get(),
                                         app.THEMES["Dark"])[1])
    scroll = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    cards = ttk.Frame(canvas)
    embedded = canvas.create_window((0, 0), window=cards, anchor="nw")
    cards.bind(
        "<Configure>",
        lambda _: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.bind(
        "<Configure>",
        lambda event: canvas.itemconfigure(embedded, width=event.width),
    )

    status = tk.StringVar(master=window)
    snapshot = {"value": None}

    def refresh():
        try:
            report = _snapshot(app)
        except (ValueError, tk.TclError) as exc:
            status.set(f"Unable to check current setup: {str(exc)[:120]}")
            return
        snapshot["value"] = report
        for child in cards.winfo_children():
            child.destroy()
        labels = (
            ("camera", "CAMERA"),
            ("emulator", "EMULATOR"),
            ("controller", "CONTROLLER"),
            ("input_backend", "INPUT PATH"),
        )
        for key, title in labels:
            item = report["checks"][key]
            frame = ttk.LabelFrame(cards, text=title, padding=10)
            frame.pack(fill="x", pady=(0, 9), padx=(0, 3))
            ttk.Label(
                frame, text=item["status"], style="Value.TLabel",
            ).pack(anchor="w")
            ttk.Label(
                frame, text=item["next"], wraplength=545, justify="left",
            ).pack(anchor="w", pady=(3, 0))
        status.set(
            "Local checks refreshed. No device names or personal paths collected."
        )

    def copy():
        # Do not copy until explicitly clicked; always use our allowlisted,
        # locally reconstructed report, not arbitrary status/exception text.
        # A camera or controller may have changed since opening the dialog.
        # Copy a fresh, allowlisted snapshot rather than stale state.
        try:
            report = _snapshot(app)
        except (ValueError, tk.TclError):
            status.set("Cannot copy setup checks until they can be refreshed.")
            return
        try:
            app.root.clipboard_clear()
            app.root.clipboard_append(json.dumps(report, indent=2) + "\n")
            app.root.update_idletasks()
        except (OSError, RuntimeError, tk.TclError):
            messagebox.showerror(
                "Setup checks", "The safe report could not be copied.",
                parent=window,
            )
            return
        status.set(
            "Redacted setup report copied locally. Paste it into a GitHub issue "
            "only if you choose to share it."
        )

    footer = ttk.Frame(shell)
    footer.pack(fill="x", pady=(11, 0))
    ttk.Button(
        footer, text="Refresh checks", command=refresh,
        style="Accent.TButton",
    ).pack(side="left")
    ttk.Button(
        footer, text="Copy safe report", command=copy,
    ).pack(side="left", padx=(8, 0))
    ttk.Button(
        footer, text="Done", command=close,
    ).pack(side="right")
    ttk.Label(
        shell, textvariable=status, style="Helper.TLabel",
        wraplength=575, justify="left",
    ).pack(anchor="w", pady=(8, 0))
    refresh()
