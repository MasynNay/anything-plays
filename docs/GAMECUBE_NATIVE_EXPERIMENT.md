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


## Pinned static linker compatibility fix

The full Linux native C++ compile progressed through all 1,274 objects and
then exposed GNU ld unresolved references to
`Common::DynamicLibrary::Open/GetSymbolAddress` from the
`dolphin_libretro_videocontexts` static archive. The functions exist in the
`common` archive, but the original Libretro final link placed that
provider earlier in the static archive sequence. The source-build-only patch
now includes the pinned `DolphinLibretro/CMakeLists.txt` and explicitly links
`common` **after** `dolphin_libretro_videocontexts`. This is a linker-order
repair, **not yet proven** by a completed native link or playback run.


### Follow-up: direct DynamicLibrary object for cyclic static archives

The first archive-order change reached the final link but the remaining
transitive `dolphin_libretro_videocontexts` archive was scanned after
`libcommon.a` again. Its `GLContextLR.cpp` unresolved symbols persisted.
The next native experiment adds upstream
`Source/Core/Common/DynamicLibrary.cpp` as a directly compiled source of
the Libretro shared target. That implementation is already part of
`libcommon.a`; ordinary archive extraction does not pull a duplicate
object when the shared target's object resolves all its symbols first.
This deliberately changes only the reviewable build-time patch.
Neither public v2.0 nor the unmodified upstream source repository is touched.
A complete native link and homebrew runtime probe are still required.


## First-frame software GPU FIFO crash (runtime diagnostic)

After native compilation and linking succeeded, the pinned homebrew loaded
and the first `retro_run()` crashed at
`VertexManagerBase::Flush()` called by `Fifo::FifoManager::RunGpuLoop()`.
The pinned `Core::EmuThread` deliberately skips native video backend
initialization for Libretro, expecting frontend hardware `ContextReset()`.
The software renderer has no hardware context callback; the upstream
`Main.cpp` only allocated a bare `g_gfx` rather than the vertex manager
and other backend resources. The reviewed source patch replaces that manual
allocation with `Libretro::Video::ContextReset()` for software and null
backend startup, causing the already-patched `VideoSoftware::Initialize`
to create the complete renderer before the frontend processes the FIFO.
This is a hypothesis grounded in the first-frame native backtrace and
upstream lifecycle, not an assertion of working gameplay. A new native
homebrew runtime probe must verify it.


## JIT versus cached-interpreter diagnostic

With the CPU renderer initialized, Dolphin now passes native compilation,
links, initializes Libretro and loads the homebrew, but the first `retro_run()`
segfaults on the separate emulated CPU thread inside executable JIT code
(`0x7ffc...` with no ordinary source symbol). The CI experiment now launches
**two isolated probes** of the same pinned binary: default JIT and
`dolphin_cpu_core=5` (cached interpreter), both with native GDB backtraces
and separate reports. The interpreter option is test-only; installed-player
settings and release readiness remain unchanged. These two outcomes will
help distinguish JIT-specific behavior from the software render path.

## Explicit GameCube controller-port initialization

Dolphin Libretro requires the frontend to select a controller type on port
zero. Registering an input callback alone can leave the emulator with no
active GameCube pad. The shared Libretro frontend now calls the exported
`retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD)` **after** a
GameCube game is successfully loaded, with no change to non-GameCube
emulators. The isolated homebrew test records both actual native
`input_state` callback counts and nonzero input samples while pulsing buttons.

This addresses an input-lifecycle omission; it does not by itself certify
rendering speed, audio or GameCube compatibility. Keep the release gate closed
until real updated frames and usable controls are observed.
