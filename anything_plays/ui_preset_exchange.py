"""Local collection exchange: review, select, relabel, import or export."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from anything_plays.named_presets import validate_name
from anything_plays.preset_exchange import (
    read_collection, write_collection, MAX_COLLECTION_ENTRIES,
)
from anything_plays.systems import SYSTEMS


def show_preset_exchange(app, parent, store, refresh_library):
    existing = getattr(parent, "_preset_exchange_window", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        return existing
    window = tk.Toplevel(parent)
    parent._preset_exchange_window = window
    window.title("Preset collection exchange")
    window.transient(parent)
    window.minsize(620, 470)
    body = ttk.Frame(window, padding=16)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="Share or import a collection of control layouts").pack(anchor="w")
    ttk.Label(body, text="No account or network connection. Choose layouts and public "
              "labels before exporting. Imports never overwrite saved presets or apply "
              "controls. Collection labels and portable calibration settings are shared.",
              wraplength=580).pack(anchor="w", pady=(4, 10))
    mode = tk.StringVar(window, "export")
    entries = {}
    controls = ttk.Frame(body)
    controls.pack(fill="x")
    tree = ttk.Treeview(body, columns=("system", "local", "label"),
                        show="headings", selectmode="extended", height=10)
    for key, caption, width in (
        ("system", "Console", 155), ("local", "Source label", 175),
        ("label", "Collection label", 190),
    ):
        tree.heading(key, text=caption)
        tree.column(key, width=width, minwidth=100)
    tree.pack(fill="both", expand=True, pady=8)
    preview = tk.StringVar(window, "")
    ttk.Label(body, textvariable=preview, wraplength=580).pack(anchor="w")
    status = tk.StringVar(window, "")
    ttk.Label(body, textvariable=status, wraplength=580).pack(anchor="w", pady=6)

    def populate(rows, new_mode):
        for item in tree.get_children():
            tree.delete(item)
        entries.clear()
        mode.set(new_mode)
        for index, (system, source_name, label, bundle) in enumerate(rows):
            row = str(index)
            entries[row] = (system, source_name, label, bundle)
            tree.insert("", "end", iid=row, values=(
                SYSTEMS[system].title, source_name, label))
        preview.set("")
        status.set(f"{len(entries)} layouts available. Select one or more rows.")

    def local():
        try:
            candidates = store.collection_candidates()
            counts = {}
            rows = []
            for system, name, bundle in candidates:
                counts[system] = counts.get(system, 0) + 1
                # Local names are visible in the editor only. Share generic
                # labels by default, unless the user explicitly relabels.
                rows.append((system, name, f"Layout {counts[system]}", bundle))
            populate(rows, "export")
        except (OSError, ValueError, TypeError, tk.TclError):
            status.set("Could not read local preset library.")

    def open_file():
        path = filedialog.askopenfilename(parent=window,
                    filetypes=[("Preset collections", "*.json")])
        if not path:
            return
        try:
            document = read_collection(path, app.THEMES)
            populate([(item["bundle"]["system"], item["label"], item["label"],
                       item["bundle"]) for item in document["layouts"]], "import")
        except (OSError, ValueError, TypeError, OverflowError):
            status.set("Collection could not be validated. Existing data was not changed.")

    def selection():
        return [entries[row] for row in tree.selection() if row in entries]

    def describe(_event=None):
        selected = selection()
        if len(selected) != 1:
            preview.set(f"{len(selected)} selected")
            return
        system, _, label, bundle = selected[0]
        from anything_plays.ui_named_presets import layout_preview
        zones = layout_preview(system, bundle["profile"])
        active = ", ".join(name for name, _, _ in zones)
        profile = bundle["profile"]
        preview.set(f"{label}: {len(zones)} visible zones · {active}\n"
                    f"Theme: {bundle.get('theme', 'keep current')} · "
                    f"Input mode: {profile.get('camera_input_mode', 'Held while visible')}")

    def relabel():
        rows = tree.selection()
        if len(rows) != 1 or rows[0] not in entries:
            status.set("Select exactly one layout to rename its collection label.")
            return
        row = rows[0]
        system, name, old, bundle = entries[row]
        label = simpledialog.askstring("Collection label", "Label included in this collection:",
                                       initialvalue=old, parent=window)
        if label is None:
            return
        try:
            label = validate_name(label)
        except ValueError:
            status.set("Use 1–48 printable characters.")
            return
        entries[row] = (system, name, label, bundle)
        tree.set(row, "label", label)
        describe()

    def selected_entries():
        chosen = selection()
        if not 1 <= len(chosen) <= MAX_COLLECTION_ENTRIES:
            status.set(f"Select 1–{MAX_COLLECTION_ENTRIES} layouts.")
            return None
        return [{"label": label, "bundle": bundle}
                for _, _, label, bundle in chosen]

    def export_file():
        if mode.get() != "export":
            status.set("Choose Local presets before exporting.")
            return
        chosen = selected_entries()
        if chosen is None:
            return
        if not messagebox.askyesno("Review shared collection",
                f"Export {len(chosen)} selected layout(s)?\n\n"
                "Public collection labels, console, zone maps, tracking colors and "
                "other portable control values are included. Local names, ROMs, "
                "saves, paths and device settings are excluded. Review labels "
                "for personal information before sharing.", parent=window):
            return
        path = filedialog.asksaveasfilename(parent=window, defaultextension=".json",
            initialfile="anything-plays-collection.json",
            filetypes=[("Preset collections", "*.json")])
        if not path:
            return
        try:
            write_collection(path, chosen, app.THEMES)
            status.set(f"Exported {len(chosen)} layouts. Share the file yourself.")
        except (OSError, ValueError, TypeError):
            status.set("Could not export collection. Review duplicate labels and storage.")

    def import_selected():
        if mode.get() != "import":
            status.set("Open a collection before importing.")
            return
        chosen = selected_entries()
        if chosen is None:
            return
        if getattr(app, "_calibration_window", None) is not None:
            status.set("Finish or cancel calibration before importing.")
            return
        if not messagebox.askyesno("Import selected layouts",
                f"Save {len(chosen)} selected layout(s) to the preset library?\n\n"
                "Active controls will not change. Identical presets are skipped. "
                "Conflicting names or insufficient slots cancel the entire import.",
                parent=window):
            return
        if getattr(app, "_calibration_window", None) is not None:
            return
        try:
            added, skipped = store.import_collection(chosen)
            refresh_library()
            status.set(f"Imported {added} · already present {skipped}. Active controls unchanged.")
        except (OSError, ValueError, TypeError):
            status.set("Nothing imported. Check name conflicts, available slots or storage.")

    def close():
        parent._preset_exchange_window = None
        window.destroy()

    for label, command in (("Local presets", local), ("Open collection", open_file),
                           ("Rename collection label", relabel)):
        ttk.Button(controls, text=label, command=command).pack(side="left", padx=3)
    actions = ttk.Frame(body)
    actions.pack(fill="x")
    for label, command in (("Export selected", export_file),
                           ("Import selected", import_selected), ("Close", close)):
        ttk.Button(actions, text=label, command=command).pack(side="left", padx=3)
    tree.bind("<<TreeviewSelect>>", describe)
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda _event: close())
    local()
    tree.focus_set()
    return window
