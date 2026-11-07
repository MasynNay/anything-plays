"""Build-time-only patch for Dolphin Libretro's CPU video frontend.

PINNED UPSTREAM: libretro/dolphin @ 32c61f9d0e933331bb7087ba57e96883241b4960
LICENSE: upstream Dolphin GPL-2.0-or-later (source and patch must accompany
any distributed modified binary, subject to the complete dependency audit).

Why needed:
Dolphin's "Software Renderer" still constructs SWOGLWindow/GLContextLR,
whose Initialize() requires an existing frontend GL context. Anything Plays
uses Tk's software RGB image panel and deliberately provides no HW context.
SWOGLWindow::Create() therefore returns null; SWGfx dereferences m_window
when first executing retro_run(). Both the backend initializer and its patched Libretro subclass must supply
the video surface metrics and forward its CPU SWTexture directly to video_cb,
without requiring a second GPU-backed window.

This script does not modify the user's installation or any 2.0 source.
It fails closed if the pinned upstream source block changes.
"""

import argparse
from pathlib import Path
import subprocess

UPSTREAM_REVISION = "32c61f9d0e933331bb7087ba57e96883241b4960"
HEADER = Path("Source/Core/DolphinLibretro/Video.h")
BACKEND_SOURCE = Path("Source/Core/VideoBackends/Software/SWmain.cpp")
BOOT_SOURCE = Path("Source/Core/DolphinLibretro/Boot.cpp")
LIBRETRO_CMAKE = Path("Source/Core/DolphinLibretro/CMakeLists.txt")
LIBRETRO_CMAKE_ORIGINAL = """target_link_libraries(dolphin_libretro PRIVATE
  dolphin_libretro_common
  dolphin_libretro_videocontexts
)"""
LIBRETRO_CMAKE_REPLACEMENT = """target_link_libraries(dolphin_libretro PRIVATE
  dolphin_libretro_common
  dolphin_libretro_videocontexts
  # Keep Common after the Libretro video-context archive: its GLContextLR
  # object calls DynamicLibrary::Open/GetSymbolAddress. GNU ld needs the
  # provider archive after this static consumer to resolve those symbols.
  common
)"""

BOOT_GBP_CONFIG_ORIGINAL = """  if (Libretro::GBPlayer_active)
  {
    Config::SetBase(Config::MAIN_GBA_ROM_PATHS[Config::GBPLAYER_GBA_INDEX], Libretro::GBPlayer_rom_path);
    INFO_LOG_FMT(BOOT, "GBPlayer: GBA ROM path applied from subsystem: '{}'", Libretro::GBPlayer_rom_path);
    Config::SetBase(Config::MAIN_GBA_SAVES_PATH, std::string(gba_save_dir));
    INFO_LOG_FMT(BOOT, "GBPlayer: ROM save set to: '{}'", gba_save_dir);
    // In order to prevent confusion for the settings of the save location between RA and the
    // emulator we just turn this off
    Config::SetBase(Config::MAIN_GBA_SAVES_IN_ROM_PATH, false);
  }
  else
  {
    Config::SetBase(Config::MAIN_GBA_ROM_PATHS[Config::GBPLAYER_GBA_INDEX], std::string{});
  }

"""
BOOT_SPECIAL_ANCHOR = """bool retro_load_game_special(unsigned game_type, const struct retro_game_info* info, size_t num_info)
{
"""
BOOT_SPECIAL_GUARD = """bool retro_load_game_special(unsigned game_type, const struct retro_game_info* info, size_t num_info)
{
#ifndef HAS_LIBMGBA
  // This standalone GameCube development core omits the optional mGBA
  // dependency. Do not offer its separate Game Boy Player subsystem.
  ERROR_LOG_FMT(BOOT, "Game Boy Player is unavailable in this build; use the bundled mGBA core");
  return false;
#endif
"""

BACKEND_INCLUDE = '#include "VideoBackends/Software/SWGfx.h"'
BACKEND_INCLUDE_REPLACEMENT = """#include "VideoBackends/Software/SWGfx.h"
#ifdef __LIBRETRO__
#include "DolphinLibretro/Video.h"
#endif"""
BACKEND_ORIGINAL = """bool VideoSoftware::Initialize(const WindowSystemInfo& wsi)
{
  std::unique_ptr<SWOGLWindow> window = SWOGLWindow::Create(wsi);
  if (!window)
    return false;

  Clipper::Init();
  Rasterizer::Init();

  return InitializeShared(std::make_unique<SWGfx>(std::move(window)),
                          std::make_unique<SWVertexLoader>(), std::make_unique<PerfQuery>(),
                          std::make_unique<SWBoundingBox>(), std::make_unique<SWEFBInterface>(),
                          std::make_unique<TextureCache>());
}"""
BACKEND_REPLACEMENT = """bool VideoSoftware::Initialize(const WindowSystemInfo& wsi)
{
  // Libretro has no standalone GLFW/OpenGL window: the frontend receives
  // software pixels directly from Libretro::Video::SWGfx::ShowImage().
  // Keep upstream's normal OpenGL window path for non-Libretro builds.
  std::unique_ptr<AbstractGfx> gfx;
#ifdef __LIBRETRO__
  gfx = std::make_unique<Libretro::Video::SWGfx>();
#else
  std::unique_ptr<SWOGLWindow> window = SWOGLWindow::Create(wsi);
  if (!window)
    return false;
  gfx = std::make_unique<SWGfx>(std::move(window));
#endif

  Clipper::Init();
  Rasterizer::Init();

  return InitializeShared(std::move(gfx),
                          std::make_unique<SWVertexLoader>(), std::make_unique<PerfQuery>(),
                          std::make_unique<SWBoundingBox>(), std::make_unique<SWEFBInterface>(),
                          std::make_unique<TextureCache>());
}"""


ORIGINAL = """  SWGfx()
    : SW::SWGfx(SWOGLWindow::Create(
            WindowSystemInfo(WindowSystemType::Libretro, nullptr, nullptr, nullptr)))
  {
  }
  void ShowImage(const AbstractTexture* source_texture,
                 const MathUtil::Rectangle<int>& source_rc) override
  {
    SW::SWGfx::ShowImage(source_texture, source_rc);
"""

REPLACEMENT = """  // Anything Plays embedded CPU rendering: no OpenGL window is created.
  // The existing frontend owns the screen and receives RGBA8 SWTexture
  // bytes directly through the regular libretro video refresh callback.
  SWGfx() : SW::SWGfx(nullptr) {}

  // The frontend DOES present frames even though the CPU renderer has no
  // native Dolphin window. Avoid the base class's null m_window access.
  bool IsHeadless() const override { return false; }

  bool BindBackbuffer(const ClearColor&) override { return true; }

  SurfaceInfo GetSurfaceInfo() const override
  {
    return {static_cast<u32>(GetAdjustedBaseWidth()),
            static_cast<u32>(GetAdjustedBaseHeight()),
            1.0f, AbstractTextureFormat::RGBA8};
  }

  void ShowImage(const AbstractTexture* source_texture,
                 const MathUtil::Rectangle<int>& source_rc) override
  {
    // Do not call SW::SWGfx::ShowImage(): it forwards to SWOGLWindow.
"""


def patched_text(source):
    """Replace exactly one upstream Libretro software renderer constructor."""
    if source.count(ORIGINAL) != 1:
        raise ValueError(
            "Upstream Dolphin video source changed; review the native patch"
        )
    return source.replace(ORIGINAL, REPLACEMENT)


def patched_backend_text(source):
    """Patch the actual SW::VideoSoftware construction path as well."""
    if source.count(BACKEND_INCLUDE) != 1 or source.count(BACKEND_ORIGINAL) != 1:
        raise ValueError(
            "Upstream Dolphin software backend source changed; review the native patch"
        )
    return (source.replace(BACKEND_INCLUDE, BACKEND_INCLUDE_REPLACEMENT, 1)
                  .replace(BACKEND_ORIGINAL, BACKEND_REPLACEMENT, 1))


def patched_boot_text(source):
    """Guard obsolete GB Player config references when USE_MGBA=OFF."""
    if (source.count(BOOT_GBP_CONFIG_ORIGINAL) != 1
            or source.count(BOOT_SPECIAL_ANCHOR) != 1):
        raise ValueError(
            "Upstream Dolphin Game Boy Player boot source changed; review native patch"
        )
    return (source.replace(
        BOOT_GBP_CONFIG_ORIGINAL,
        "#ifdef HAS_LIBMGBA\n" + BOOT_GBP_CONFIG_ORIGINAL + "#endif\n", 1,
    ).replace(BOOT_SPECIAL_ANCHOR, BOOT_SPECIAL_GUARD, 1))


def patched_libretro_cmake_text(source):
    """Keep the static Common provider after its Libretro video-context consumer."""
    if source.count(LIBRETRO_CMAKE_ORIGINAL) != 1:
        raise ValueError("Upstream Dolphin Libretro CMake source changed; review native patch")
    return source.replace(LIBRETRO_CMAKE_ORIGINAL, LIBRETRO_CMAKE_REPLACEMENT, 1)


def patch_source_checkout(root):
    """Verify the exact reviewed source revision before modifying its header."""
    root = Path(root).resolve()
    sha = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True,
    ).strip()
    if sha != UPSTREAM_REVISION:
        raise ValueError(
            f"Unreviewed Dolphin revision: {sha}, expected {UPSTREAM_REVISION}"
        )
    header = root / HEADER
    backend = root / BACKEND_SOURCE
    boot = root / BOOT_SOURCE
    cmake = root / LIBRETRO_CMAKE
    # Validate all pinned source anchors before touching any of the files.
    patched_header = patched_text(header.read_text(encoding="utf-8"))
    patched_backend = patched_backend_text(backend.read_text(encoding="utf-8"))
    patched_boot = patched_boot_text(boot.read_text(encoding="utf-8"))
    patched_cmake = patched_libretro_cmake_text(cmake.read_text(encoding="utf-8"))
    header.write_text(patched_header, encoding="utf-8")
    backend.write_text(patched_backend, encoding="utf-8")
    boot.write_text(patched_boot, encoding="utf-8")
    cmake.write_text(patched_cmake, encoding="utf-8")
    print(f"Patched embedded GameCube CPU renderer: {header}", flush=True)
    print(f"Patched Dolphin software backend initialization: {backend}", flush=True)
    print(f"Disabled unsupported Game Boy Player-only config: {boot}", flush=True)
    print(f"Patched Dolphin Libretro static archive order: {cmake}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_checkout", type=Path)
    args = parser.parse_args()
    patch_source_checkout(args.source_checkout)
