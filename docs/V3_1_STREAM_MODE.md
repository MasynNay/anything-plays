# Anything Plays 3.1 — Stream Mode

Stream Mode provides a dedicated, OBS-friendly window with two live screens. Its default layout is a vertically stacked handheld-inspired display, with the **game on top and annotated camera below**. Streamers can capture one finished-looking window instead of building and manually aligning separate camera and game scenes.

## How to use

1. Launch Anything Plays, start a camera, and run a game using the built-in emulator.
2. Beside **View mode** under **DISPLAY & SOUND**, click **Stream Mode**. You can also press **Ctrl+Shift+S**.
3. Two separate windows open:
   - **Stream Output**: only the composed game, camera, bezel, accent, and unobtrusive screen labels. Select this window in OBS **Window Capture**.
   - **Stream Settings**: customize layout and appearance. This window is **not** included in the capture.
4. Choose **DS stacked** or **Side by side**. Swap the order of the screens, adjust how much space the game occupies, change bezel thickness, select any of the sixteen application themes, pick a custom border color, and toggle titles and source-status labels.
5. Resize the output window freely; its two source images retain their proportions and letterbox instead of stretching. Settings persist in the current RC2-specific preferences directory.
6. Close the output or select **Close Stream Mode** to release only the streaming view. The original camera, emulator, and desktop workspace remain running.

The default DS-inspired frame is original UI artwork drawn by Pillow and Tk; no third-party Nintendo logos, hardware images or copyrighted screen graphics are bundled.

## Input and privacy

Stream Mode **mirrors existing sources**: it never calls VideoCapture a second time, never launches another emulator, and never injects game buttons. The camera is mirrored **after tracking zones and object outlines are rendered**, so viewers can see what Anything Plays detects. The game is read from the native emulator's existing protected RGB frame buffer. If the webcam stops or disconnects, its stream image is cleared. If a still reference photo is selected, the status says **REFERENCE IMAGE** rather than falsely claiming the camera is live.

For externally launched RetroArch/Dolphin sessions without built-in video, the game panel shows a truthful placeholder instead of pretending to capture another application. OBS can capture an external emulator separately where required.

Stream output contains no ROM paths, camera device identifiers, file locations, profile data, or settings controls. No network transmission or recording is performed by Anything Plays. **OBS handles any streaming, recording, and audio capture**; a Window Capture source records only the composed visual window. Game audio must be configured in OBS separately (for example, with application audio capture).

## Long-session performance and safety

The output is one reusable Tk Canvas image, updated at most roughly 15 FPS using one cancellable Tk timer. It only recomposes when a source frame, stream setting, viewport size, or source state changes. A game frame is copied under the existing emulator lock only when its serial advances. Existing camera frames are bounded in size and reused as snapshots only while Stream Mode is open. Fonts are cached in a 48-entry bounded table. Rendering failures back off to a one-second retry instead of spinning.

Closing Stream Mode cancels its timer, saves final style changes, destroys both auxiliary windows, and releases all cached image references. It does not modify the camera controls, game save data, stable 3.0, RC1, or emulation core packaging.

## Verification and release scope

`tests/test_v31_stream_mode.py` covers both layouts, 16 themes, custom border colors, swapped live sources, accurate camera/game-off placeholders, untrusted settings, and cached rendering resources. `tests/smoke_gui.py` opens the actual two Toplevel windows under Tk, changes its customization widgets, renders synthetic annotated camera data, verifies single-Canvas-image reuse, closes them safely, and confirms the settings were saved.

Stream Mode is a post-RC1 **3.1 development feature**. It is not included in the currently published RC1 installer. A refreshed RC2 build must compile this exact code, pass the full four-platform QA and installed GUI acceptance, and still satisfy physical camera/game and native redistribution/relinking requirements before any public stable 3.1 release.
