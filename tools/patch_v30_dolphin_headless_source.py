"""Narrow, auditable Libretro CPU-software-frame initialization patch.

Only applied to an exact pinned Git checkout in an isolated native research
CI job. Never edits the desktop frontend or any externally installed emulator.

Original Dolphin Libretro Core::RunGpuLoop can call g_vertex_manager->Flush()
before a software-only frontend can initialize video: hardware ContextReset()
is never invoked for RETRO_HW_CONTEXT_NONE. Original SWOGLWindow additionally
requires a hardware GL context even in the CPU-only Libretro backend.

Every replacement asserts its exact upstream fragment once; source changes
are retained as a git diff and native build hash for corresponding-source
compliance. Tests must still prove real GameCube video and controller input.
"""
from __future__ import annotations

import argparse
from pathlib import Path

_FILES = {
    "Source/Core/DolphinLibretro/Main.cpp": [
        (
            '#include "VideoCommon/VideoConfig.h"\n',
            '#include "VideoCommon/VideoConfig.h"\n'
            '#include "VideoCommon/VertexManagerBase.h"\n',
        ),
        (
            '  Core::System& system = Core::System::GetInstance();\n\n'
            '  if (Core::GetState(system) == Core::State::Starting &&\n'
            '      !Libretro::g_emuthread_launched)',
            '  Core::System& system = Core::System::GetInstance();\n\n'
            '  // CPU-only Libretro has no hardware ContextReset callback. Initialize\n'
            '  // the software video backend before the GPU FIFO can call Flush().\n'
            '  if (Core::GetState(system) == Core::State::Starting &&\n'
            '      !Libretro::g_emuthread_launched &&\n'
            '      Config::Get(Config::MAIN_GFX_BACKEND) == "Software Renderer" &&\n'
            '      !g_vertex_manager)\n'
            '  {\n'
            '    if (!Libretro::Video::Video_InitializeBackend())\n'
            '    {\n'
            '      ERROR_LOG_FMT(VIDEO, "Failed to initialize Libretro CPU software renderer");\n'
            '      return;\n'
            '    }\n'
            '  }\n\n'
            '  if (Core::GetState(system) == Core::State::Starting &&\n'
            '      !Libretro::g_emuthread_launched)',
        ),
    ],
    "Source/Core/VideoBackends/Software/SWOGLWindow.cpp": [
        (
            '#include "VideoBackends/Software/SWTexture.h"\n',
            '#include "VideoBackends/Software/SWTexture.h"\n'
            '#ifdef __LIBRETRO__\n'
            '#include "DolphinLibretro/Video.h"\n'
            '#endif\n',
        ),
        (
            '  return m_gl_context->IsHeadless();',
            '  // Libretro software frames need no OpenGL context.\n'
            '  return !m_gl_context || m_gl_context->IsHeadless();',
        ),
        (
            'bool SWOGLWindow::Initialize(const WindowSystemInfo& wsi)\n'
            '{\n'
            '  m_gl_context = GLContext::Create(wsi);',
            'bool SWOGLWindow::Initialize(const WindowSystemInfo& wsi)\n'
            '{\n'
            '#ifdef __LIBRETRO__\n'
            '  if (wsi.type == WindowSystemType::Libretro &&\n'
            '      Libretro::Video::hw_render.context_type == RETRO_HW_CONTEXT_NONE)\n'
            '    return true;  // CPU-owned frames delivered through video_cb.\n'
            '#endif\n'
            '  m_gl_context = GLContext::Create(wsi);',
        ),
    ],
    "Source/Core/VideoBackends/Software/SWGfx.cpp": [
        (
            '#include "VideoCommon/Present.h"\n',
            '#include "VideoCommon/Present.h"\n'
            '#ifdef __LIBRETRO__\n'
            '#include "DolphinLibretro/Video.h"\n'
            '#endif\n',
        ),
        (
            '  GLContext* context = m_window->GetContext();\n'
            '  context->Update();\n'
            '  g_presenter->SetBackbuffer(context->GetBackBufferWidth(), context->GetBackBufferHeight());',
            '  GLContext* context = m_window->GetContext();\n'
            '#ifdef __LIBRETRO__\n'
            '  if (!context)\n'
            '  {\n'
            '    g_presenter->SetBackbuffer(Libretro::Video::GetAdjustedBaseWidth(),\n'
            '                               Libretro::Video::GetAdjustedBaseHeight());\n'
            '    return true;\n'
            '  }\n'
            '#endif\n'
            '  context->Update();\n'
            '  g_presenter->SetBackbuffer(context->GetBackBufferWidth(), context->GetBackBufferHeight());',
        ),
        (
            '  GLContext* context = m_window->GetContext();\n'
            '  return {std::max(context->GetBackBufferWidth(), 1u), std::max(context->GetBackBufferHeight(), 1u),\n'
            '          1.0f, AbstractTextureFormat::RGBA8};',
            '  GLContext* context = m_window->GetContext();\n'
            '#ifdef __LIBRETRO__\n'
            '  if (!context)\n'
            '    return {static_cast<u32>(Libretro::Video::GetAdjustedBaseWidth()),\n'
            '            static_cast<u32>(Libretro::Video::GetAdjustedBaseHeight()),\n'
            '            1.0f, AbstractTextureFormat::RGBA8};\n'
            '#endif\n'
            '  return {std::max(context->GetBackBufferWidth(), 1u), std::max(context->GetBackBufferHeight(), 1u),\n'
            '          1.0f, AbstractTextureFormat::RGBA8};',
        ),
    ],
}

def patch_source(root: Path) -> list[str]:
    checked = {}
    for relative, replacements in _FILES.items():
        source = root / relative
        value = source.read_text(encoding="utf-8")
        for before, after in replacements:
            count = value.count(before)
            if count != 1:
                raise RuntimeError(
                    f"Unexpected original Dolphin source ({relative}); "
                    f"exact anchor count={count}, expected 1"
                )
            value = value.replace(before, after, 1)
        checked[source] = value
    # Apply only once all files have passed exact pinned-content checks.
    for file, text in checked.items():
        file.write_text(text, encoding="utf-8")
    return [str(p.relative_to(root)) for p in checked]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    changed = patch_source(args.source)
    for file in changed:
        print(f"Reviewed Dolphin CPU-frame patch: {file}")

if __name__ == "__main__":
    main()
