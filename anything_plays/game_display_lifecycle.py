"""Shared 3.2 game-video cleanup after a native session is stopped.

Switching consoles and unloading a ROM must have identical cleanup, or one
view can retain a previous game's pixels. The caller stops the emulator first.
No SDL, camera, ROM or native library is opened from this module.
"""

import tkinter as tk


def clear_game_video(app):
    """Clear all representations of an old game, preserving camera data.

    Frame mutations use the emulator lock, as do the native frame readers.
    Clearing the frame serial also invalidates revision-based Tk rendering.
    Repeated calls are safe and do not mutate saves or controller profiles.
    """
    with app.emu.lock:
        app.emu.frame = None
        serial = getattr(app.emu, "frame_serial", None)
        if isinstance(serial, int):
            app.emu.frame_serial = serial + 1

    app.game_photo = None
    app._last_game_render = None
    app._game_image_item = None
    app._game_image_canvas = None
    app.game_canvas.delete("all")
    game_only = getattr(app, "_game_only_canvas", None)
    if game_only is not None:
        try:
            game_only.delete("all")
        except tk.TclError:
            # A detached Game-only window can be destroyed by the user
            # between a native stop and this UI cleanup callback.
            pass

    app._stream_game_frame = None
    app._stream_game_serial = None
    app._stream_last_render = None
    # An OBS capture of the standalone output must not retain the prior
    # game until the next stream refresh. Only the stream's rendered canvas
    # is removed: its live camera snapshot is intentionally preserved.
    stream_canvas = getattr(app, "_stream_canvas", None)
    if stream_canvas is not None:
        try:
            stream_canvas.delete("all")
        except tk.TclError:
            pass
    app._stream_canvas_item = None
    app._stream_photo = None

    bezel = getattr(app, "game_bezel", None)
    if bezel is not None:
        bezel.set_active(False)
