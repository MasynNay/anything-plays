"""Creator scene browser; previews only synthetic geometry, never capture pixels."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from anything_plays.named_presets import validate_name
from anything_plays.stream_scenes import (
    SceneStore, STARTERS, starter_scene, import_scene, export_scene,
)
from anything_plays.ui_stream import stream_panel_boxes


def show_stream_scenes(app):
    parent = app._stream_controls_window
    if parent is None:
        return
    existing = getattr(parent, "_scene_window", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        return existing
    store = SceneStore(Path(app.preferences_path).with_name("stream-scenes.json"), app.THEMES)
    window = tk.Toplevel(parent)
    parent._scene_window = window
    window.title("Creator scenes · Stream Mode")
    window.transient(parent)
    window.minsize(460, 530)
    body = ttk.Frame(window, padding=14)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="Reusable Stream Mode scenes").pack(anchor="w")
    ttk.Label(body, text="Preview and switch capture styles. No camera images, game "
              "frames, paths or OBS settings are saved.", wraplength=420).pack(anchor="w")
    table = ttk.Treeview(body, columns=("name", "kind"), show="headings",
                         selectmode="browse", height=7)
    table.heading("name", text="Scene")
    table.heading("kind", text="Source")
    table.column("name", width=260)
    table.column("kind", width=100)
    table.pack(fill="both", expand=True, pady=8)
    rows = {}
    canvas = tk.Canvas(body, width=400, height=180, highlightthickness=0)
    canvas.pack()
    detail = tk.StringVar(window)
    ttk.Label(body, textvariable=detail, wraplength=420).pack(anchor="w")
    status = tk.StringVar(window)
    ttk.Label(body, textvariable=status, wraplength=420).pack(anchor="w", pady=4)
    previous = None
    applied = None

    def ready():
        return (getattr(app, "_stream_controls_window", None) is parent
                and not getattr(app, "_closing", False))

    def selected():
        selection = table.selection()
        return rows.get(selection[0]) if selection else None

    def options():
        row = selected()
        if row is None:
            raise ValueError("Select a scene.")
        kind, name = row
        if kind == "Built-in":
            return starter_scene(name, app._stream_options, app.THEMES)
        return store.entries()[name]

    def preview(_event=None):
        canvas.delete("all")
        try:
            scene = options()
        except (OSError, ValueError, KeyError, TypeError):
            detail.set("Select a scene to preview.")
            return
        palette = app.THEMES[scene["theme"]]
        canvas.configure(bg=palette[0])
        width, height = ((320, 400) if scene["layout"] == "DS stacked" else (640, 400))
        scale = min(390 / width, 170 / height)
        ox, oy = (400-width*scale)/2, (180-height*scale)/2
        names = ("CAMERA", "GAME") if scene["swap_screens"] else ("GAME", "CAMERA")
        for name, (x0,y0,x1,y1) in zip(names, stream_panel_boxes(
                (width,height), scene["layout"], scene["game_size"])):
            canvas.create_rectangle(ox+x0*scale, oy+y0*scale, ox+x1*scale, oy+y1*scale,
                fill=palette[1], outline=scene["border_color"] or palette[3],
                width=max(1, scene["border_width"]*scale))
            canvas.create_text(ox+(x0+x1)*scale/2, oy+(y0+y1)*scale/2,
                               text=name, fill=palette[2])
        detail.set(f"{scene['layout']} · {scene['frame_rate']} · "
                   f"Game share {scene['game_size']}% · {scene['theme']}\n"
                   + ("Headers shown" if scene["show_labels"] else "Headers hidden")
                   + " · schematic preview only")

    def refresh(select=None):
        for item in table.get_children():
            table.delete(item)
        rows.clear()
        for name in STARTERS:
            iid = table.insert("", "end", values=(name, "Built-in"))
            rows[iid] = ("Built-in", name)
        try:
            entries = store.entries()
        except (OSError, ValueError, TypeError):
            status.set("Saved scenes could not be read. Existing data was not changed.")
            entries = {}
        for name in sorted(entries, key=str.casefold):
            iid = table.insert("", "end", values=(name, "Saved"))
            rows[iid] = ("Saved", name)
            if name == select:
                table.selection_set(iid)
                table.see(iid)
        if not table.selection() and table.get_children():
            table.selection_set(table.get_children()[0])
        preview()

    def save_options(scene):
        name = simpledialog.askstring("Save creator scene", "Scene name:", parent=window)
        if name is None or not ready():
            return
        name = validate_name(name)
        duplicate = any(key.casefold() == name.casefold() for key in store.entries())
        if duplicate and not messagebox.askyesno("Replace scene?",
                    "Replace this saved scene?", parent=window):
            return
        if not ready():
            return
        store.save(name, scene, replace=duplicate)
        refresh(name)
        status.set("Scene saved. Live output unchanged.")

    def save_current():
        if not ready():
            return
        try:
            save_options(dict(app._stream_options))
        except (OSError, ValueError, TypeError):
            status.set("Could not save scene. Check name and storage.")

    def save_selected():
        if not ready():
            return
        try:
            save_options(options())
        except (OSError, ValueError, KeyError, TypeError):
            status.set("Choose a valid scene to save.")

    def apply():
        nonlocal previous, applied
        if not ready():
            return
        try:
            scene = options()
            if not messagebox.askyesno("Apply creator scene?",
                    "Change Stream Output style and refresh settings? "
                    "Game and camera controls will not change.", parent=window):
                return
            if not ready():
                return
            prior = dict(app._stream_options)
            if app.apply_stream_scene(scene):
                if prior != app._stream_options:
                    previous, applied = prior, dict(app._stream_options)
                status.set("Scene applied. Undo scene is available after a change.")
                preview()
            else:
                status.set("Scene was not applied.")
        except (OSError, ValueError, KeyError, TypeError, tk.TclError):
            status.set("Scene was not applied.")

    def undo():
        nonlocal previous, applied
        if not ready() or previous is None:
            return
        if app._stream_options != applied and not messagebox.askyesno(
                "Review newer changes", "Undo will replace newer Stream Mode style edits. Continue?",
                parent=window):
            return
        if ready() and app.apply_stream_scene(previous):
            previous = applied = None
            status.set("Previous Stream Mode settings restored.")
            preview()

    def delete():
        row = selected()
        if not ready() or row is None or row[0] != "Saved":
            status.set("Select a saved scene to delete.")
            return
        if not messagebox.askyesno("Delete scene?", "Delete saved scene only?", parent=window):
            return
        if not ready():
            return
        try:
            store.delete(row[1])
            refresh()
        except (OSError, ValueError, TypeError):
            status.set("Could not delete scene.")

    def export():
        if not ready():
            return
        try:
            scene = options()
            path = filedialog.asksaveasfilename(parent=window, defaultextension=".json",
                initialfile="anything-plays-stream-scene.json", filetypes=[("Stream scene", "*.json")])
            if path and ready():
                export_scene(path, scene, app.THEMES)
                status.set("Scene exported without its local name.")
        except (OSError, ValueError, KeyError, TypeError):
            status.set("Could not export scene.")

    def import_file():
        if not ready():
            return
        path = filedialog.askopenfilename(parent=window, filetypes=[("Stream scene", "*.json")])
        if path and ready():
            try:
                save_options(import_scene(path, app.THEMES))
            except (OSError, ValueError, TypeError):
                status.set("Invalid scene file or storage unavailable.")

    actions = ttk.Frame(body)
    actions.pack(fill="x")
    for index, (label, command) in enumerate((
        ("Save current", save_current), ("Save selected", save_selected),
        ("Apply scene", apply), ("Undo scene", undo),
        ("Import scene", import_file), ("Export scene", export),
        ("Delete saved", delete), ("Close", window.destroy),
    )):
        row, col = divmod(index, 2)
        actions.columnconfigure(col, weight=1)
        ttk.Button(actions, text=label, command=command).grid(
            row=row, column=col, sticky="ew", padx=3, pady=2)
    table.bind("<<TreeviewSelect>>", preview)
    window.bind("<Escape>", lambda _event: window.destroy())
    refresh()
    table.focus_set()
    return window
