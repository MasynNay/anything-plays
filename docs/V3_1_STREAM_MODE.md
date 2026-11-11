# Anything Plays 3.1 — Stream Mode

Stream Mode provides a dedicated, OBS-friendly window with two live screens. Its default layout is a vertically stacked handheld-inspired display, with the **game on top and annotated camera below**. Streamers can capture one finished-looking window instead of building and manually aligning separate camera and game scenes.

## How to use

1. Launch Anything Plays, start a camera, and run a game using the built-in emulator.
2. Beside **View mode** under **DISPLAY & SOUND**, click **Stream Mode**. You can also press **Ctrl+Shift+S**.
3. Two separate windows open:
   - **Stream Output**: only the composed game, camera, bezel, accent, and unobtrusive screen labels. Select this window in OBS **Window Capture**.
   - **Stream Settings**: customize layout and appearance. This window is **not** included in the capture.
4. Choose **DS stacked** or **Side by side**. Swap the order of the screens, adjust how much space the game occupies, change bezel thickness, select any of the sixteen application themes, pick a custom border color, select a 15, 24, or 30 FPS output refresh rate, and toggle titles and source-status labels.
5. The output automatically switches to a natural portrait or landscape shape when you change layouts. Resize the output window freely afterward; its two source images retain their proportions and letterbox instead of stretching. Settings persist in the current RC2-specific preferences directory.
6. Close the output or select **Close Stream Mode** to release only the streaming view. The original camera, emulator, and desktop workspace remain running.

The default DS-inspired frame is original UI artwork drawn by Pillow and Tk; no third-party Nintendo logos, hardware images or copyrighted screen graphics are bundled.

## Input and privacy

Stream Mode **mirrors existing sources**: it never calls VideoCapture a second time, never launches another emulator, and never injects game buttons. The camera is mirrored **after tracking zones and object outlines are rendered**, so viewers can see what Anything Plays detects. The game is read from the native emulator's existing protected RGB frame buffer. If the webcam stops or disconnects, its stream image is cleared. If a still reference photo is selected, the status says **REFERENCE IMAGE** rather than falsely claiming the camera is live.

For externally launched RetroArch/Dolphin sessions without built-in video, the game panel shows a truthful placeholder instead of pretending to capture another application. OBS can capture an external emulator separately where required.

Stream output contains no ROM paths, camera device identifiers, file locations, profile data, or settings controls. No network transmission or recording is performed by Anything Plays. **OBS handles any streaming, recording, and audio capture**; a Window Capture source records only the composed visual window. Game audio must be configured in OBS separately (for example, with application audio capture).

## Long-session performance and safety

The output is one reusable Tk Canvas image, updated at a chosen rate of 15, 24 (default), or 30 FPS using one cancellable Tk timer. It only recomposes when a source frame, stream setting, viewport size, or source state changes. A game frame is copied under the existing emulator lock only when its serial advances. Existing camera frames are bounded in size and reused as snapshots only while Stream Mode is open. Fonts are cached in a 48-entry bounded table. Rendering failures back off to a one-second retry instead of spinning.

Closing Stream Mode cancels its timer, saves final style changes, destroys both auxiliary windows, and releases all cached image references. It does not modify the camera controls, game save data, stable 3.0, RC1, or emulation core packaging.

## Verification and release scope

`tests/test_v31_stream_mode.py` covers both layouts, 16 themes, custom border colors, swapped live sources, accurate camera/game-off placeholders, untrusted settings, and cached rendering resources. `tests/smoke_gui.py` opens the actual two Toplevel windows under Tk, changes its customization widgets, renders synthetic annotated camera data, verifies single-Canvas-image reuse, closes them safely, and confirms the settings were saved.

Stream Mode is included in the **public [3.1 RC2 prerelease](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc2)**, not in the earlier RC1 installer. The full 18-console RC2 installers and actual installed GUI/Stream Mode acceptance passed on Windows x64, Linux x64, macOS Apple Silicon and macOS Intel in [CI run 43079085633](https://github.com/MasynNay/anything-plays/actions/runs/43079085633). Those automated checks do **not** establish compatibility with every physical webcam, controller or retail game, or complete the pygame/SDL corresponding-source and LGPL relinking review. **Stable 3.1.0 is not yet published**; [3.0.0](https://github.com/MasynNay/anything-plays/releases/latest) remains the stable release.

## RC2 owner test checklist

Use a disposable ROM and camera setup where practical. Never upload private webcam footage or commercial ROM files to issue reports.

1. Install RC2 on a supported OS and confirm that stable 3.0 launches separately and retains its own ROM folders, profiles and preferences.
2. Open **Stream Mode** with **Ctrl+Shift+S**. In OBS, use **Window Capture** on **Stream Output**, not **Stream Settings**.
3. Change between **DS stacked** and **Side by side**; swap screen positions; adjust border color, thickness, theme, screen ratio and labels. Confirm the output remains legible after resizing and that the settings window never appears in the captured content.
4. With a real camera, confirm live tracked outlines appear only in the intended camera pane. Stop or unplug the camera and verify stale camera imagery and the live indicator disappear.
5. Load and unload a legally obtained game in the embedded emulator. Confirm game video and the console activity indicator follow the session accurately. Check controller mapping and reconnect only when real compatible hardware is available.
6. Leave Stream Mode open during a longer play session, change layouts during gameplay, then close and reopen it. Verify no duplicate camera acquisition, game restart, persistent resource growth or saved-setting corruption.
7. Check actual gameplay, audio routing in OBS, save/reload, camera input and controller input independently. Report OS version, app version, console/core, reproduction steps and whether the issue affects RC2 only. Never treat these manual checks as passed until run on real hardware.

**Stable-release gates still open:** physical camera/gamepad and gameplay acceptance, extended real-device sessions, complete corresponding-source identification and legal relinking review, and final stable-installer verification.
