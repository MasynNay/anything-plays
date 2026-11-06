# Anything Plays v2 development snapshot

This is **development source**, not a production release. Do not merge into `main` yet.

## Implemented in this snapshot

- Theme selector: Dark, Light, Midnight, Retro, persisted across launches (from the appearance prototype).
- Expanded label font size controls: 8–160 pixels; existing draggable zone rectangles retained.
- Emulator selector: Game Boy, Game Boy Color, Game Boy Advance, Super Nintendo.
- Independent ROM directory and library filtering for each selected system.
- Per-system core path selection and persistence; automatic lookup in local `cores/` and common RetroArch core directories.
- Existing GBA library preferences migrated non-destructively.

## Not yet finished / verified

- Game Boy / Color and SNES native libretro cores are **not bundled** in this ZIP. Install a matching core yourself and select it using the app. No third-party ROMs are bundled.
- SNES-specific X/Y/L/R control zones and input mappings are not yet wired into the UI. SNES core loading is experimental.
- Cross-platform build workflows still fetch and package only mGBA; they must be extended and tested before releasing v2.
- No GUI runtime or game-play test has been performed on Windows, macOS or Linux for this snapshot.
- The core runner currently supports a limited subset of libretro environment callbacks. Some cores may need additional video or environment support to run reliably.
- The game library artwork remains a generic GBA-style cartridge design.

## Tests performed

`python -m compileall -q app.py gba_emulator.py systems.py`

`python -m unittest discover -s tests -v`

Both passed in the build environment. These tests do not prove that games will run.
