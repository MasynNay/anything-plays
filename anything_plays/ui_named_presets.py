"""Named preset library for the selected console, without changing main layout."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from anything_plays.named_presets import NamedPresetStore, validate_name
from anything_plays.portable_profiles import save_bundle, load_bundle
from anything_plays.systems import SYSTEMS
from anything_plays.settings_defaults import DEFAULT
from anything_plays.system_profiles import enabled_zones, normalize
from anything_plays.accessible_layouts import LAYOUTS, build_layout, layout_changes


def _describe_changes(changes):
    """Concise, factual description of effective zone changes."""
    lines = [f"{len(changes['active'])} active camera buttons · "
             f"{len(changes['moved'])} moved · {len(changes['remapped'])} remapped"]
    for key, label in (("disabled", "Newly disabled"), ("enabled", "Newly enabled"),
                       ("remapped", "Remapped")):
        if changes[key]:
            lines.append(label + ": " + ", ".join(changes[key]))
    if changes["shuffle_changed"]:
        lines.append("Shuffle zone visibility changes.")
    return "\n".join(lines)


def show_builtin_layouts(app, parent, system, store, refresh_library):
    """Preview local starter layouts without applying them automatically."""
    existing = getattr(parent, "_built_in_layouts_window", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        return existing
    window = tk.Toplevel(parent)
    parent._built_in_layouts_window = window
    window.title("Built-in control layouts · " + SYSTEMS[system].title)
    window.transient(parent)
    window.minsize(470, 430)
    body = ttk.Frame(window, padding=16)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="Choose a starting layout").pack(anchor="w")
    ttk.Label(body, text="These are optional starting points, not calibrated accessibility "
              "recommendations. Disabled camera buttons can still be used through other "
              "configured input methods.", wraplength=420).pack(anchor="w", pady=(4, 8))
    choices = {label: key for key, (label, _) in LAYOUTS.items()}
    chosen = tk.StringVar(window, next(iter(choices)))
    combo = ttk.Combobox(body, values=tuple(choices), textvariable=chosen,
                         state="readonly")
    combo.pack(fill="x")
    description = tk.StringVar(window)
    ttk.Label(body, textvariable=description, wraplength=420).pack(anchor="w", pady=8)
    comparison = ttk.Frame(body)
    comparison.pack(fill="x")
    palette = app.THEMES[app.theme_name.get()]
    canvases = []
    for index, caption in enumerate(("Current editor", "Built-in layout")):
        frame = ttk.Frame(comparison)
        frame.grid(row=0, column=index, sticky="n", padx=4)
        comparison.columnconfigure(index, weight=1)
        ttk.Label(frame, text=caption).pack(anchor="w")
        canvas = tk.Canvas(frame, width=200, height=120, bg=palette[4],
                           highlightthickness=0)
        canvas.pack()
        canvases.append(canvas)
    differences = tk.StringVar(window)
    ttk.Label(body, textvariable=differences, wraplength=420).pack(anchor="w", pady=8)
    status = tk.StringVar(window)
    ttk.Label(body, textvariable=status, wraplength=420).pack(anchor="w")

    def ready():
        if (app.system_key.get() != system
                or getattr(app, "_calibration_window", None) is not None):
            status.set("Console or calibration changed. Close and reopen the library.")
            return False
        return True

    def preview(_event=None):
        if not ready():
            return
        try:
            key = choices[chosen.get()]
            bundle = build_layout(system, key, app.cfg)
            description.set(LAYOUTS[key][1])
            _draw_layout(canvases[0], system, app.cfg, palette)
            _draw_layout(canvases[1], system, bundle["profile"], palette)
            differences.set(_describe_changes(layout_changes(system, app.cfg, bundle["profile"])))
        except (OSError, ValueError, TypeError, KeyError, tk.TclError):
            status.set("Preview unavailable. Check current controls.")

    def capture():
        if not ready():
            return None
        # Capture current editor values only on explicit user action.
        # Build again so color/detection edits made after preview survive.
        app.read_settings()
        return build_layout(system, choices[chosen.get()], app.cfg)

    def apply():
        try:
            bundle = capture()
            if bundle is not None and app.apply_portable_controls(system, bundle["profile"]):
                status.set("Layout applied. Undo import restores the previous controls.")
                preview()
        except (OSError, ValueError, TypeError, KeyError, tk.TclError):
            status.set("Could not apply layout. Check current controls.")

    def save():
        try:
            bundle = capture()
            if bundle is None:
                return
            name = simpledialog.askstring("Save layout to library", "Name this layout:",
                                          initialvalue=chosen.get(), parent=window)
            if name is None or not ready():
                return
            name = validate_name(name)
            duplicate = any(n.casefold() == name.casefold() for n in store.list(system))
            if duplicate and not messagebox.askyesno("Replace preset?",
                    "Replace the saved layout? Active controls will not change.",
                    parent=window):
                return
            if not ready():
                return
            store.save(system, name, bundle["profile"], replace=duplicate)
            refresh_library(name)
            status.set("Layout saved. Active controls have not changed.")
        except (OSError, ValueError, TypeError, KeyError, tk.TclError):
            status.set("Could not save layout. Check name and storage.")

    def close():
        parent._built_in_layouts_window = None
        window.destroy()

    actions = ttk.Frame(body)
    actions.pack(fill="x", pady=(8, 0))
    for index, (label, command) in enumerate((
        ("Apply layout", apply), ("Save to library", save), ("Close", close),
    )):
        actions.columnconfigure(index, weight=1)
        ttk.Button(actions, text=label, command=command).grid(
            row=0, column=index, sticky="ew", padx=3)
    combo.bind("<<ComboboxSelected>>", preview)
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda _event: close())
    preview()
    combo.focus_set()
    return window



def layout_preview(system, profile):
    """Return visible normalized rectangles and mapped labels, never artwork."""
    normalized = normalize(system, profile, DEFAULT)
    names = enabled_zones(normalized, system)
    if normalized.get("shuffle_enabled", True):
        names.append("Shuffle")
    return tuple(
        (name, normalized["mapping"].get(name, name),
         tuple(normalized["zones"][name]))
        for name in names
    )


def _draw_layout(canvas, system, profile, palette):
    canvas.delete("all")
    if profile is None:
        canvas.create_text(100, 60, text="Select a preset", fill=palette[2])
        return
    for name, action, (x0, y0, x1, y1) in layout_preview(system, profile):
        coords = (4 + 192*x0, 4 + 112*y0, 4 + 192*x1, 4 + 112*y1)
        canvas.create_rectangle(*coords, outline=palette[3], width=1)
        label = name if action == name else f"{name} → {action}"
        if coords[2] - coords[0] >= 26 and coords[3] - coords[1] >= 14:
            canvas.create_text((coords[0]+coords[2])/2, (coords[1]+coords[3])/2,
                               text=label, fill=palette[2], font=("TkDefaultFont", 8),
                               width=max(1, coords[2]-coords[0]-3))


def show_named_presets(app):
    if getattr(app, "_calibration_window", None) is not None:
        messagebox.showinfo("Control presets", "Finish or cancel calibration first.",
                            parent=app.root)
        return
    existing = getattr(app, "_named_presets_window", None)
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.lift()
                return
        except tk.TclError:
            pass
    system = app.system_key.get()
    store = NamedPresetStore(
        Path(app.preferences_path).with_name("named-control-presets.json"), app.THEMES
    )
    window = tk.Toplevel(app.root)
    app._named_presets_window = window
    window.title("Control presets · " + SYSTEMS[system].title)
    window.transient(app.root)
    window.minsize(470, 520)
    outer = ttk.Frame(window, padding=16)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text=SYSTEMS[system].title + " control presets").pack(anchor="w")
    ttk.Label(outer, text="Keep up to 12 named layouts per console. Apply with preview "
              "and Undo import. ROMs, saves, device settings and artwork are not included.",
              wraplength=420).pack(anchor="w", pady=(6, 12))
    table = ttk.Treeview(outer, columns=("name",), show="headings",
                         selectmode="browse", height=7)
    table.heading("name", text="Saved layout")
    table.column("name", width=340)
    table.pack(fill="both", expand=True)
    row_names = {}
    comparison = ttk.Frame(outer)
    comparison.pack(fill="x", pady=(8, 0))
    palette = app.THEMES[app.theme_name.get()]
    maps = []
    for column, caption in enumerate(("Current editor", "Selected preset")):
        panel = ttk.Frame(comparison)
        panel.grid(row=0, column=column, sticky="n", padx=4)
        comparison.columnconfigure(column, weight=1)
        ttk.Label(panel, text=caption).pack(anchor="w")
        canvas = tk.Canvas(panel, width=200, height=120, bg=palette[4],
                           highlightthickness=0)
        canvas.pack()
        maps.append(canvas)
    ttk.Label(outer, text="Zone preview only · disabled controls are hidden.",
              wraplength=420).pack(anchor="w", pady=(4, 0))
    diff_text = tk.StringVar(value="")
    ttk.Label(outer, textvariable=diff_text, wraplength=420).pack(anchor="w", pady=(4, 0))
    status = tk.StringVar(value="")
    ttk.Label(outer, textvariable=status, wraplength=420).pack(anchor="w", pady=8)
    buttons = ttk.Frame(outer)
    buttons.pack(fill="x")

    def close():
        app._named_presets_window = None
        window.destroy()

    def ready():
        if (app.system_key.get() != system
                or getattr(app, "_calibration_window", None) is not None):
            status.set("Console or calibration changed. Close this window and reopen it.")
            return False
        return True

    def compare(_event=None):
        if app.system_key.get() != system:
            for canvas in maps:
                canvas.delete("all")
            diff_text.set("")
            return
        try:
            _draw_layout(maps[0], system, app.cfg, palette)
            selection = table.selection()
            name = row_names.get(selection[0]) if selection else None
            bundle = store.get(system, name) if name is not None else None
            _draw_layout(maps[1], system, bundle["profile"] if bundle else None, palette)
            diff_text.set(_describe_changes(layout_changes(system, app.cfg, bundle["profile"]))
                          if bundle else "")
        except (OSError, ValueError, TypeError, KeyError, tk.TclError):
            diff_text.set("")
            maps[1].delete("all")
            maps[1].create_text(100, 60, text="Preview unavailable", fill=palette[2])

    def refresh(select=None):
        try:
            names = store.list(system)
        except (OSError, ValueError, TypeError):
            status.set("Preset library could not be read. Existing data was not changed.")
            return
        for item in table.get_children():
            table.delete(item)
        row_names.clear()
        for name in names:
            row = table.insert("", "end", values=(name,))
            row_names[row] = name
            if name == select:
                table.selection_set(row)
                table.see(row)
        status.set(f"{len(names)} of 12 presets saved for this console.")
        compare()

    def selected():
        selection = table.selection()
        if not selection:
            status.set("Choose a saved layout first.")
            return None
        # Tcl can coerce numeric-looking values (e.g. 001) into integers.
        # Use the exact stored label rather than round-tripping display text.
        return row_names.get(selection[0])

    def save_current():
        if not ready():
            return
        name = simpledialog.askstring("Save current controls", "Name this layout:",
                                      parent=window)
        if name is None or not ready():
            return
        try:
            name = validate_name(name)
            duplicate = any(n.casefold() == name.casefold() for n in store.list(system))
            if duplicate and not messagebox.askyesno(
                    "Replace preset?", "Replace the saved layout with your current controls?",
                    parent=window):
                return
            if not ready():
                return
            app.read_settings()
            store.save(system, name, app.cfg, theme=app.theme_name.get(), replace=duplicate)
            refresh(name)
        except (OSError, ValueError, TypeError, tk.TclError):
            status.set("Could not save preset. Check its name, controls and storage.")

    def apply():
        name = selected()
        if name is None or not ready():
            return
        try:
            bundle = store.get(system, name)
            if app.apply_portable_controls(system, bundle["profile"], bundle.get("theme")):
                status.set("Preset applied. Use Undo import in the main window to revert.")
                compare()
        except (OSError, ValueError, TypeError, tk.TclError):
            status.set("Could not apply preset. Check current controls before playing.")

    def delete():
        name = selected()
        if name is None or not ready():
            return
        if not messagebox.askyesno("Delete preset?", "Delete this saved layout only? "
                                   "Your active controls will not change.", parent=window):
            return
        if not ready():
            return
        try:
            store.delete(system, name)
            refresh()
        except (OSError, ValueError, TypeError):
            status.set("Could not delete preset. Existing data was retained.")

    def export():
        name = selected()
        if name is None or not ready():
            return
        path = filedialog.asksaveasfilename(parent=window, defaultextension=".json",
            initialfile=f"anything-plays-{system}-controls.json",
            filetypes=[("Control profile", "*.json")])
        if not path or not ready():
            return
        try:
            bundle = store.get(system, name)
            save_bundle(path, system, bundle["profile"], theme=bundle.get("theme"),
                        allowed_themes=app.THEMES)
            status.set("Exported portable controls. The local preset name is not included.")
        except (OSError, ValueError, TypeError):
            status.set("Could not export preset.")

    def import_file():
        if not ready():
            return
        path = filedialog.askopenfilename(parent=window,
                    filetypes=[("Control profile", "*.json")])
        if not path or not ready():
            return
        try:
            profile, theme, legacy = load_bundle(path, selected_system=system,
                                                allowed_themes=app.THEMES)
            if legacy and not messagebox.askyesno(
                    "Legacy profile", "This file has no console identity. Save it for "
                    + SYSTEMS[system].title + "?", parent=window):
                return
            name = simpledialog.askstring("Import preset", "Name this saved layout:",
                                          parent=window)
            if name is None or not ready():
                return
            name = validate_name(name)
            duplicate = any(n.casefold() == name.casefold() for n in store.list(system))
            if duplicate and not messagebox.askyesno("Replace preset?",
                    "Replace this saved layout? Active controls will not change.",
                    parent=window):
                return
            if not ready():
                return
            store.save(system, name, profile, theme=theme, replace=duplicate)
            refresh(name)
        except (OSError, ValueError, TypeError, tk.TclError):
            status.set("Could not import preset. Check its console, format and name.")

    def builtins():
        if ready():
            return show_builtin_layouts(app, window, system, store, refresh)

    for index, (label, command) in enumerate((
        ("Save current", save_current), ("Apply selected", apply),
        ("Import to library", import_file), ("Export selected", export),
        ("Delete selected", delete), ("Built-in layouts", builtins),
        ("Close", close),
    )):
        row, col = divmod(index, 2)
        buttons.columnconfigure(col, weight=1)
        ttk.Button(buttons, text=label, command=command).grid(
            row=row, column=col, sticky="ew", padx=3, pady=3)
    table.bind("<<TreeviewSelect>>", compare)
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda _event: close())
    refresh()
    table.focus_set()
    return window
