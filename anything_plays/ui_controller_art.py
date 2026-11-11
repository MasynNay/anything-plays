"""Tiny theme-aware controller artwork for the 3.1 manual-play UI.

Native Tk Canvas geometry: no emoji/font dependencies, external image assets,
SDL initialization, or additional PyInstaller resources. Every coordinate is
scaled from a 100 x 60 icon so the small preview and setup dialog match.
"""


def draw_gamepad(canvas, palette, *, connected=False, expanded=False,
                 pressed=()):
    """Paint a controller with optional read-only highlights for live inputs.

    Native ttk buttons still own all configuration and navigation. Highlights
    show the raw SDL snapshot; no click handlers or hardware initialization
    are attached to this Canvas. Each redraw clears old shapes.
    """
    # Ignore unknown/untrusted inputs instead of constructing new labels,
    # widgets, arbitrary colors or layout positions from device data.
    known = frozenset((
        "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
        "A", "B", "X", "Y", "BACK", "START",
        "LEFT_SHOULDER", "RIGHT_SHOULDER",
        "LEFT_TRIGGER", "RIGHT_TRIGGER",
        "LEFT_STICK_UP", "LEFT_STICK_DOWN", "LEFT_STICK_LEFT",
        "LEFT_STICK_RIGHT", "RIGHT_STICK_UP", "RIGHT_STICK_DOWN",
        "RIGHT_STICK_LEFT", "RIGHT_STICK_RIGHT",
    ))
    active = (frozenset(item for item in pressed
                        if isinstance(item, str) and item in known)
              if isinstance(pressed, (set, frozenset, tuple, list))
              else frozenset())
    if not connected:
        active = frozenset()
    _outer, surface, foreground, accent, button, field = palette
    width, height = (278, 150) if expanded else (105, 68)
    canvas.configure(width=width, height=height, bg=surface)
    canvas.delete("all")

    # Use a fixed logical scene and scale every coordinate; Tk's outline
    # thickness remains readable even in the compact game-panel variant.
    sx, sy = width / 100.0, height / 60.0
    def pt(x, y):
        return x * sx, y * sy

    # Two offset shoulder pads, body shell, and highlighted control surface.
    for box, sources in (
        ((17, 6, 34, 13), ("LEFT_SHOULDER", "LEFT_TRIGGER")),
        ((66, 6, 83, 13), ("RIGHT_SHOULDER", "RIGHT_TRIGGER")),
    ):
        x0, y0, x1, y1 = box
        canvas.create_oval(*pt(x0, y0), *pt(x1, y1),
                           fill=accent if active.intersection(sources) else field,
                           outline=accent, width=1.3)
    shell = [
        20, 12, 33, 10, 67, 10, 80, 12,
        89, 17, 97, 32, 94, 45, 88, 51,
        78, 49, 70, 42, 30, 42, 22, 49,
        12, 51, 6, 45, 3, 32, 11, 17
    ]
    coords = []
    for x, y in zip(shell[::2], shell[1::2]):
        coords.extend(pt(x, y))
    canvas.create_polygon(*coords, fill=button, outline=accent,
                          width=2.0 if expanded else 1.35, smooth=True)

    # D-pad and face buttons intentionally read as familiar controls without
    # copying any specific manufacturer's controller artwork.
    # Each D-pad arm can illuminate independently while preserving its
    # familiar cross silhouette, including in the tiny preview.
    for box, source in (
        ((21, 21, 24, 25), "DPAD_UP"),
        ((21, 31, 24, 35), "DPAD_DOWN"),
        ((16, 26, 21, 30), "DPAD_LEFT"),
        ((24, 26, 29, 30), "DPAD_RIGHT"),
    ):
        canvas.create_rectangle(*pt(box[0], box[1]),
                                *pt(box[2], box[3]),
                                fill=accent if source in active else foreground,
                                outline="")
    canvas.create_rectangle(*pt(21, 25), *pt(24, 31),
                            fill=foreground, outline="")
    for x, y, face in ((75, 22, "Y"), (81, 28, "B"),
                       (69, 28, "X"), (75, 34, "A")):
        pushed = face in active
        canvas.create_oval(*pt(x-4.5 if pushed else x-4,
                               y-4.5 if pushed else y-4),
                           *pt(x+4.5 if pushed else x+4,
                               y+4.5 if pushed else y+4),
                           fill=foreground if pushed else accent,
                           outline=field, width=1.0)
        if expanded:
            canvas.create_text(*pt(x, y), text=face,
                               fill=surface if not pushed else field,
                               font=("TkDefaultFont", 8, "bold"))
    for x, y, prefix in ((40, 34, "LEFT_STICK_"),
                          (60, 35, "RIGHT_STICK_")):
        moving = any(source.startswith(prefix) for source in active)
        canvas.create_oval(*pt(x-5.2, y-5.2), *pt(x+5.2, y+5.2),
                           fill=field,
                           outline=accent if moving else foreground,
                           width=1.6 if moving else 1.25)
        canvas.create_oval(*pt(x-1.8, y-1.8), *pt(x+1.8, y+1.8),
                           fill=foreground if moving else accent, outline="")
    for x, key in ((47, "BACK"), (53, "START")):
        canvas.create_oval(*pt(x-1.4, 23), *pt(x+1.4, 25.8),
                           fill=accent if key in active else foreground,
                           outline="")

    # Connection marker is purely informational; the adjacent text label
    # remains the authoritative, screen-reader-friendly device status.
    canvas.create_oval(*pt(88, 7), *pt(92, 11),
                       fill=accent if connected else field,
                       outline=foreground, width=0.8)
