"""Tiny theme-aware controller artwork for the 3.1 manual-play UI.

Native Tk Canvas geometry: no emoji/font dependencies, external image assets,
SDL initialization, or additional PyInstaller resources. Every coordinate is
scaled from a 100 x 60 icon so the small preview and setup dialog match.
"""


def draw_gamepad(canvas, palette, *, connected=False, expanded=False):
    """Paint a game controller at any Canvas size using the current theme.

    A decorative icon only; actual controls are accessible ttk widgets beside
    it. Calling again destroys prior shapes, avoiding buildup on theme changes.
    """
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
    for x0, y0, x1, y1 in ((17, 6, 34, 13), (66, 6, 83, 13)):
        canvas.create_oval(*pt(x0, y0), *pt(x1, y1),
                           fill=field, outline=accent, width=1.3)
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
    for box in ((20, 21, 25, 35), (16, 25, 29, 31)):
        canvas.create_rectangle(*pt(*box), fill=foreground, outline="")
    for x, y, face in ((75, 22, "Y"), (81, 28, "B"),
                       (69, 28, "X"), (75, 34, "A")):
        canvas.create_oval(*pt(x-4, y-4), *pt(x+4, y+4),
                           fill=accent, outline=field, width=1.0)
        if expanded:
            canvas.create_text(*pt(x, y), text=face, fill=surface,
                               font=("TkDefaultFont", 8, "bold"))
    for x, y in ((40, 34), (60, 35)):
        canvas.create_oval(*pt(x-5.2, y-5.2), *pt(x+5.2, y+5.2),
                           fill=field, outline=foreground, width=1.25)
        canvas.create_oval(*pt(x-1.8, y-1.8), *pt(x+1.8, y+1.8),
                           fill=accent, outline="")
    for x in (47, 53):
        canvas.create_oval(*pt(x-1.4, 23), *pt(x+1.4, 25.8),
                           fill=foreground, outline="")

    # Connection marker is purely informational; the adjacent text label
    # remains the authoritative, screen-reader-friendly device status.
    canvas.create_oval(*pt(88, 7), *pt(92, 11),
                       fill=accent if connected else field,
                       outline=foreground, width=0.8)
