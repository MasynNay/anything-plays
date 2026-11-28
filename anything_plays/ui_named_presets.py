"""Named preset library for the selected console, without changing main layout."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from anything_plays.named_presets import NamedPresetStore, validate_name
from anything_plays.portable_profiles import save_bundle, load_bundle
from anything_plays.systems import SYSTEMS


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
    window.minsize(440, 360)
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

    def refresh(select=None):
        try:
            names = store.list(system)
        except (OSError, ValueError, TypeError):
            status.set("Preset library could not be read. Existing data was not changed.")
            return
        for item in table.get_children():
            table.delete(item)
        for name in names:
            row = table.insert("", "end", values=(name,))
            if name == select:
                table.selection_set(row)
                table.see(row)
        status.set(f"{len(names)} of 12 presets saved for this console.")

    def selected():
        selection = table.selection()
        if not selection:
            status.set("Choose a saved layout first.")
            return None
        return str(table.item(selection[0], "values")[0])

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

    for index, (label, command) in enumerate((
        ("Save current", save_current), ("Apply selected", apply),
        ("Import to library", import_file), ("Export selected", export),
        ("Delete selected", delete), ("Close", close),
    )):
        row, col = divmod(index, 2)
        buttons.columnconfigure(col, weight=1)
        ttk.Button(buttons, text=label, command=command).grid(
            row=row, column=col, sticky="ew", padx=3, pady=3)
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda _event: close())
    refresh()
    table.focus_set()
    return window
