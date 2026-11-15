"""Accessible, organized object-tracking controls for Anything Plays 3.0.

The right-hand control column deliberately groups frequent actions separately
from advanced tuning and per-button mappings. All existing Tk variables and
callbacks remain owned by App so saved profiles and controller semantics
remain backward compatible. No tracking logic lives in this layout module.
"""
import tkinter as tk
from tkinter import ttk

from anything_plays.system_profiles import BUTTONS_BY_SYSTEM, DISABLED_MAPPING

ALL_BUTTONS = tuple(dict.fromkeys(
    button for buttons in BUTTONS_BY_SYSTEM.values() for button in buttons
))


def _section(parent, number, title, description=None):
    panel = ttk.LabelFrame(
        parent, text=f"{number}   {title}", padding=(14, 13, 14, 14)
    )
    panel.pack(fill="x", padx=(12, 2), pady=(0, 13))
    if description:
        ttk.Label(
            panel, text=description, style="Helper.TLabel",
            wraplength=520, justify="left",
        ).pack(fill="x", anchor="w", pady=(0, 10))
    return panel


def _actions(parent, items):
    """Equal-width responsive actions; no three long buttons crushed together."""
    frame = ttk.Frame(parent)
    frame.pack(fill="x", pady=(8, 0))
    for i, (title, command) in enumerate(items):
        frame.columnconfigure(i, weight=1, uniform="tracking_actions")
        ttk.Button(
            frame, text=title, command=command, style="Compact.TButton",
        ).grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0))
    return frame


def _color_row(app, parent, *, secondary):
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=(1, 4))
    swatch = tk.Label(
        row, width=4, height=1, relief="solid",
        borderwidth=2, cursor="hand2",
    )
    swatch.pack(side="left", padx=(0, 10), pady=3)
    chooser = app.choose_second_color if secondary else app.choose_color
    swatch.bind("<Button-1>", lambda _event: chooser())
    if secondary:
        app.color2_swatch = swatch
    else:
        app.color1_swatch = swatch
    ttk.Label(
        row, textvariable=app.color2_text if secondary else app.color_text,
        style="Value.TLabel",
    ).pack(side="left", fill="x", expand=True)
    return row


def _setting_row(parent, title, variable, low, high):
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=4)
    ttk.Label(row, text=title).pack(side="left", fill="x", expand=True)
    ttk.Spinbox(
        row, textvariable=variable, from_=low, to=high, width=8,
    ).pack(side="right", padx=(10, 1))


def _toggle_panel(frame, enabled):
    if enabled:
        frame.pack(fill="x", pady=(8, 0))
    else:
        frame.pack_forget()


def build_tracking_panel(app, right):
    """Build primary/secondary object, input, zones and advanced settings."""
    app.mirror = tk.BooleanVar()
    primary = _section(
        right, "03", "PRIMARY OBJECT",
        "Choose the color the camera should follow. Tracking can recognize "
        "any object, not just animals.",
    )
    _color_row(app, primary, secondary=False)
    ttk.Button(
        primary, text="Guided camera calibration…",
        command=app.open_calibration_wizard, style="Accent.TButton",
    ).pack(fill="x", pady=(5, 9))
    _actions(primary, (
        ("Pick from camera", app.pick_color),
        ("Pick from image", app.pick_image),
        ("Choose color", app.choose_color),
    ))
    ttk.Checkbutton(
        primary,
        text="Enable multiple objects per color",
        variable=app.multi_fish_enabled,
        command=app.update_tracking_preferences,
        style="Primary.TCheckbutton",
    ).pack(anchor="w", pady=(13, 3))
    ttk.Label(
        primary, style="Helper.TLabel", wraplength=520, justify="left",
        text="Off by default: follow one matching object per color. "
             "Turn on to let several matching objects activate "
             "different buttons simultaneously.",
    ).pack(fill="x")

    secondary = _section(
        right, "04", "SECONDARY OBJECT · OPTIONAL",
        "Add a second independently tracked color, then choose "
        "which player it controls.",
    )
    ttk.Checkbutton(
        secondary, text="Enable secondary object",
        variable=app.color2_enabled, style="Primary.TCheckbutton",
        command=lambda: _secondary_changed(app),
    ).pack(anchor="w", pady=(0, 9))
    app.secondary_color_controls = ttk.Frame(secondary)
    app.secondary_color_controls.pack(fill="x")
    _color_row(app, app.secondary_color_controls, secondary=True)
    _actions(app.secondary_color_controls, (
        ("Pick from camera", app.pick_second_color),
        ("Choose color", app.choose_second_color),
    ))
    player_row = ttk.Frame(app.secondary_color_controls)
    player_row.pack(fill="x", pady=(12, 2))
    ttk.Label(
        player_row, text="Send inputs to", style="Value.TLabel",
    ).pack(side="left", fill="x", expand=True)
    app.color2_port_combo = ttk.Combobox(
        player_row, textvariable=app.color2_player, state="readonly",
        values=["Player 1", "Player 2"], width=16,
    )
    app.color2_port_combo.pack(side="right")
    app.color2_port_combo.bind(
        "<<ComboboxSelected>>", app.update_tracking_preferences
    )
    ttk.Label(
        app.secondary_color_controls,
        text="Player 2 requires a game and console that support "
             "local two-player controls.",
        style="Helper.TLabel", wraplength=520, justify="left",
    ).pack(fill="x", pady=(7, 0))

    behavior = _section(
        right, "05", "INPUT BEHAVIOR",
        "Decide how an object activates a button while it is inside "
        "one of your camera zones.",
    )
    mode_row = ttk.Frame(behavior)
    mode_row.pack(fill="x")
    ttk.Label(
        mode_row, text="Button behavior", style="Value.TLabel",
    ).pack(side="left", fill="x", expand=True)
    mode = ttk.Combobox(
        mode_row, textvariable=app.camera_input_mode, state="readonly",
        values=["Held while visible", "Pulse (classic)"], width=21,
    )
    mode.pack(side="right", padx=(10, 0))
    mode.bind("<<ComboboxSelected>>", app.update_tracking_preferences)
    ttk.Label(
        behavior, text="Held: keep the button pressed while the object "
        "remains in its zone. Pulse: send a timed button press, "
        "subject to the cooldown setting.",
        style="Helper.TLabel", wraplength=520, justify="left",
    ).pack(fill="x", pady=(8, 0))

    zones = _section(
        right, "06", "BUTTON ZONES",
        "Arrange the regions on your camera preview. Objects activate "
        "the button assigned to the region they enter.",
    )
    ttk.Button(
        zones, text="Fit buttons to an even grid",
        command=app.make_symmetric_grid, style="Accent.TButton",
    ).pack(fill="x", pady=(0, 9))
    ttk.Checkbutton(
        zones, text="Mirror camera preview", variable=app.mirror,
    ).pack(anchor="w", pady=2)
    ttk.Checkbutton(
        zones, text="Draw custom button zones",
        variable=app.custom_draw_enabled, command=app.toggle_custom_draw,
    ).pack(anchor="w", pady=(5, 3))
    draw_row = ttk.Frame(zones)
    draw_row.pack(fill="x", pady=(4, 9))
    ttk.Label(draw_row, text="Zone to redraw").pack(side="left", fill="x", expand=True)
    app.zone_combo = ttk.Combobox(
        draw_row, textvariable=app.zone_name, state="readonly",
        values=[*ALL_BUTTONS, "Shuffle"], width=16,
    )
    app.zone_combo.pack(side="right", padx=(10, 0))

    app.mapping_expanded = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        zones, text="Edit individual button mappings",
        variable=app.mapping_expanded, style="Primary.TCheckbutton",
        command=lambda: _toggle_panel(
            app.mapping_controls, app.mapping_expanded.get()
        ),
    ).pack(anchor="w")
    app.mapping_controls = ttk.Frame(zones)
    ttk.Label(
        app.mapping_controls, text="Select which game button each zone sends.",
        style="Helper.TLabel", wraplength=520,
    ).pack(fill="x", pady=(1, 8))
    mapping = ttk.Frame(app.mapping_controls)
    mapping.pack(fill="x")
    mapping.columnconfigure(0, weight=1)
    mapping.columnconfigure(1, weight=1)
    app.mapping_widgets = {}
    for i, name in enumerate(ALL_BUTTONS):
        item = ttk.Frame(mapping)
        item.grid(
            row=i // 2, column=i % 2, sticky="ew",
            padx=(0, 9) if i % 2 == 0 else (9, 0), pady=4,
        )
        var = tk.StringVar()
        app.mapping_vars[name] = var
        ttk.Label(item, text=name, width=7).pack(side="left", padx=(0, 6))
        combo = ttk.Combobox(
            item, textvariable=var, state="readonly", width=11,
            values=[DISABLED_MAPPING, *ALL_BUTTONS],
        )
        combo.pack(side="left", fill="x", expand=True)
        # Keep a widget reference compatible with refresh_system_buttons:
        # the frame is the layout unit, not an individual label/grid cell.
        app.mapping_widgets[name] = (item, combo)
        combo.bind(
            "<<ComboboxSelected>>",
            lambda _event, n=name: app.update_button_mapping(n),
        )

    advanced = _section(
        right, "07", "ADVANCED SETTINGS",
        "Fine-tune detection and customize how zones look. "
        "The defaults work for most setups.",
    )
    app.advanced_tracking_expanded = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        advanced, text="Show advanced detection and appearance",
        variable=app.advanced_tracking_expanded,
        style="Primary.TCheckbutton",
        command=lambda: _toggle_panel(
            app.advanced_tracking_controls,
            app.advanced_tracking_expanded.get(),
        ),
    ).pack(anchor="w")
    app.advanced_tracking_controls = ttk.Frame(advanced)
    app.tolerance = tk.IntVar()
    app.min_area = tk.IntVar()
    app.hold_frames = tk.IntVar()
    app.cooldown = tk.IntVar()
    # The mirror control is initialized before its visible checkbox.
    tuning = ttk.LabelFrame(
        app.advanced_tracking_controls, text="Detection & timing",
        padding=10,
    )
    tuning.pack(fill="x", pady=(0, 10))
    _setting_row(tuning, "Color tolerance", app.tolerance, 1, 90)
    _setting_row(tuning, "Minimum object area (pixels)", app.min_area, 5, 50000)
    _setting_row(tuning, "Button hold (frames)", app.hold_frames, 1, 60)
    _setting_row(tuning, "Cooldown (milliseconds)", app.cooldown, 50, 10000)
    appearance = ttk.LabelFrame(
        app.advanced_tracking_controls, text="Zone appearance", padding=10,
    )
    appearance.pack(fill="x")
    # Label size is controlled once, beside the camera preview on the left.
    ttk.Label(appearance, text="Overlay tint strength").pack(anchor="w")
    ttk.Scale(
        appearance, from_=75, to=100,
        variable=app.zone_opacity, orient="horizontal",
    ).pack(fill="x", pady=(3, 10))
    _appearance_row(
        appearance, "Visual style", app.zone_style,
        ("Bold", "High contrast", "Outline", "Minimal"),
    )
    thickness = ttk.Frame(appearance)
    thickness.pack(fill="x", pady=(4, 10))
    ttk.Label(thickness, text="Border thickness").pack(side="left")
    ttk.Scale(
        thickness, from_=2, to=16,
        variable=app.zone_border_width, orient="horizontal",
    ).pack(side="left", fill="x", expand=True, padx=8)
    ttk.Spinbox(
        thickness, from_=2, to=16,
        textvariable=app.zone_border_width, width=5,
    ).pack(side="right")
    _appearance_row(
        appearance, "Label position", app.zone_label_position,
        ("Center", "Top-left"),
    )
    _actions(appearance, (
        ("Upload PNG", app.choose_zone_art),
        ("Image URL", app.ask_zone_url),
        ("Clear image", app.clear_zone_art),
    ))
    ttk.Label(
        appearance, text="PNG artwork is shown inside each control zone.",
        style="Helper.TLabel",
    ).pack(anchor="w", pady=(5, 0))
    ttk.Checkbutton(
        appearance, text="Enable Shuffle zone",
        variable=app.shuffle_enabled,
    ).pack(anchor="w", pady=(10, 5))
    ttk.Button(
        appearance, text="Shuffle buttons now",
        command=app.shuffle_zones, style="Compact.TButton",
    ).pack(fill="x")


def _appearance_row(parent, label, variable, choices):
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=(0, 10))
    ttk.Label(row, text=label).pack(side="left", fill="x", expand=True)
    ttk.Combobox(
        row, textvariable=variable, values=list(choices),
        state="readonly", width=17,
    ).pack(side="right")


def _secondary_changed(app):
    app.update_tracking_preferences()
    update_secondary_controls(app)


def update_secondary_controls(app):
    """Keep secondary controls unobtrusive until explicitly enabled."""
    frame = getattr(app, "secondary_color_controls", None)
    if frame is None:
        return
    if app.color2_enabled.get():
        frame.pack(fill="x", pady=(4, 0))
    else:
        frame.pack_forget()


def refresh_color_swatches(app):
    """Update swatches without allocating new widgets or losing themes."""
    for name, key, fallback in (
        ("color1_swatch", "rgb", [255, 0, 0]),
        ("color2_swatch", "rgb2", [255, 30, 180]),
    ):
        widget = getattr(app, name, None)
        if widget is None:
            continue
        rgb = app.cfg.get(key, fallback)
        if (isinstance(rgb, (tuple, list)) and len(rgb) == 3
                and all(type(value) is int and 0 <= value <= 255
                        for value in rgb)):
            widget.configure(bg="#%02x%02x%02x" % tuple(rgb))
