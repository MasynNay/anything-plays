"""Shared game-video cleanup after a native session is stopped.

Native video state is retired before touching optional Tk canvases. If one
widget was destroyed while switching ROMs, the other views still clear and
the next game starts without the previous game's OBS-facing pixel objects.
This never opens a camera, changes controller state or accesses a ROM.
"""


def clear_game_video(app):
    """Retire old game frames in every view; preserve live camera pixels.

    Call after stopping the emulator. The native frame must be revoked under
    its lock first. In-memory Tk/Stream references are revoked before any
    optional UI methods, which may fail during window destruction or from
    third-party widget wrappers.
    """
    with app.emu.lock:
        app.emu.frame = None
        serial = getattr(app.emu, "frame_serial", None)
        if type(serial) is int:
            app.emu.frame_serial = serial + 1

    app.game_photo = None
    app._last_game_render = None
    app._game_image_item = None
    app._game_image_canvas = None
    app._stream_game_frame = None
    app._stream_game_serial = None
    app._stream_last_render = None
    app._stream_canvas_item = None
    app._stream_photo = None

    # Clear all three independently. A destroyed main canvas must not prevent
    # revoking OBS pixels, and an unresponsive OBS surface must not prevent
    # a fresh ROM from using the primary canvas. Do not expose driver paths
    # or extension-defined exception text to the user.
    for name in ("game_canvas", "_game_only_canvas", "_stream_canvas"):
        canvas = getattr(app, name, None)
        if canvas is not None:
            try:
                canvas.delete("all")
            except Exception:
                pass

    bezel = getattr(app, "game_bezel", None)
    if bezel is not None:
        try:
            bezel.set_active(False)
        except Exception:
            # Cosmetic border failure cannot resurrect a stopped game.
            pass
