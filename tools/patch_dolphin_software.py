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
    # Validate BOTH reviewed source anchors before touching either file.
    # A half-applied native patch could compile but silently select the
    # unmodified OpenGL backend at runtime.
    patched_header = patched_text(header.read_text(encoding="utf-8"))
    patched_backend = patched_backend_text(backend.read_text(encoding="utf-8"))
    header.write_text(patched_header, encoding="utf-8")
    backend.write_text(patched_backend, encoding="utf-8")
    print(f"Patched embedded GameCube CPU renderer: {header}", flush=True)
    print(f"Patched Dolphin software backend initialization: {backend}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_checkout", type=Path)
    args = parser.parse_args()
    patch_source_checkout(args.source_checkout)
