# GameCube software-renderer experiment — 2.1 only

The standard Dolphin Libretro core's software renderer still creates
`SWOGLWindow`. Its Libretro OpenGL context requires a frontend GPU context,
which Anything Plays' Tk RGB frame viewer deliberately does not provide.
The standard core can initialize and load a GameCube homebrew executable but
segfaults during the first `retro_run()` call. CI records the failed native
stack and does **not** count core download/installer success as playable games.

## Source and modifications

- Pinned source: [libretro/dolphin](https://github.com/libretro/dolphin/tree/32c61f9d0e933331bb7087ba57e96883241b4960)
- License: Dolphin GPL-2.0-or-later with per-file licensing/dependencies.
- Source changes: [strict source patch](../tools/patch_dolphin_software.py).
- CI build: [isolated native build script](../tools/build_patched_dolphin_core.sh).
- Actual content probe: [verified zlib-licensed homebrew](../tools/gamecube_homebrew_fixture.py)
  through the existing CoreSession and Libretro video callback.

The proposed C++ source modification avoids creating the unneeded OpenGL
window when software frame pixels are sent to the frontend; it implements the
window-sensitive virtual methods on the Libretro subclass instead. It is an
**experiment**, not an assertion of native correctness or adequate performance.

CI builds modified native code separately from stable 2.0 and from ordinary
2.1 alpha packaging. It collects crash/frame evidence, not a redistributable
patched binary. Do not ship the modified core until its complete GPL source,
build scripts, transitive license inventory, platform-specific dependencies,
checksums and signing have been reviewed.

## Before completing 2.1

The patched core must load the licensed homebrew, produce actual changing RGB
frames, accept camera/controller input and run without crashes at practical
frame rates. Then repeat on Windows and both Mac architectures, with clean
installation, saves, game-only and borderless views, multi-hour camera soak,
and legally user-provided game discs. The full 2.1 release gate stays closed
until all eight consoles pass.


## Libretro backend constructor correction

The pinned upstream `SW::VideoSoftware::Initialize` in
`Source/Core/VideoBackends/Software/SWmain.cpp` creates
`SWOGLWindow` before instantiating `SW::SWGfx`. Patching only
`DolphinLibretro/Video.h` was insufficient because that Libretro subclass
was never constructed. The experimental build-time patch now modifies both
pinned source files, retains the original path outside Libretro, and emits a
combined source diff digest. Native compilation and real frame evidence are
still required before GameCube can be marked playable.


## Pinned Game Boy Player compile compatibility

The full pinned Linux native compilation uncovered that `DolphinLibretro/Boot.cpp`
uses `Config::MAIN_GBA_ROM_PATHS` and other Game Boy Player settings
defined only under `HAS_LIBMGBA`. This experiment deliberately builds with
`USE_MGBA=OFF`, because Anything Plays already bundles its own mGBA core
for GB/GBC/GBA. The additional reviewed source patch guards these
Game Boy Player-only settings and rejects `retro_load_game_special` when
mGBA is unavailable, without altering normal GameCube disc/homebrew boot.
The three-file source diff is retained and hashed. This is a compile fix,
not evidence that Dolphin now renders playable frames.
