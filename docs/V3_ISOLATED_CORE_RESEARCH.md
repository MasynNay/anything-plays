# Anything Plays 3.0 — disposable 2D Libretro worker research

**Status: EXPERIMENTAL / UNAPPROVED.** The real desktop app still selects its original 18-console/11-core 3.0 preview runtime. No normal user-facing backend has been replaced. Public v2.0.0 remains unchanged.

## Why this experiment exists

The macOS Nintendo 64 ROM-switching fix already runs ParaLLEl-N64 in a disposable child process. It uses bounded RGB shared memory, two RetroPad input snapshots, volume and a separate emulator-owned audio device, while keeping the native core outside the Tk application's address space.

This experiment generalizes that **existing** transport strictly for 2D Libretro profiles, excluding the special N64 route and hardware-rendered GameCube/Dolphin. The experimental bridge calls the existing production CoreSession inside the worker, with a new process per loaded cartridge. Original ROMs and saves remain local. No emulator or ROM is downloaded.

The unchanged app continues to use original Snes9x, Genesis Plus GX and all other existing 3.0 cores. The prototype does **not** switch SNES or Sega to the research-built alternatives.

## Native cross-platform test

The existing eight source-build jobs on Windows x64, Linux x64, macOS Apple Silicon and macOS Intel compile the pinned original bsnes and BlastEm cores. For **BlastEm's four targets** only, the research workflow now additionally runs the standalone tool **tools/probe_v30_isolated_sega_process.py** against the newly source-built BlastEm library (six seconds per playback cycle).

This script generates an original Master System Z80 homebrew in a temporary folder and plays it twice in the same Python parent process, each time through a fresh native OS subprocess using the existing bounded frame/input bridge. Both sessions must start gameplay, report at least 12 captured frames, at least 8 nonblank frames and at least two distinct RGB frames, and terminate cleanly. It includes manual Start-button state snapshots, but does **not** claim any particular game's Start action was visually confirmed. It does not install a real app, record physical camera movements or measure the native PCM speaker output. A passing result is narrow technical evidence.

Every workflow result and **ISOLATED_SEGA_PROCESS_UNAPPROVED.json** remains a **research-only artifact**. Never label this as source/binary matching for the existing production Genesis Plus GX ZIP, a complete 18-profile test, or a distributable installer.

## Limitations and decisions still required

Process isolation can make it easier to handle hard native crashes and repeat ROM loads. It is **not** a legal determination that shared-memory IPC makes two components legally independent or that a combined offline installer is a permissible aggregate. A qualified expert must inspect the actual combined program, precise licenses (including GPLv2-only, GPLv2-or-later, GPLv3 and noncommercial), dependencies, and any author permissions. Do not change any release approval fields on the basis of this experiment alone.

Before integration, separately prove full software audio fidelity, real controller/camera action, save and reload, input latency, original native 4-OS packaged sources, game compatibility, repeated ROM switching, memory stability over long sessions and actual hardware. GameCube's accelerated hardware framebuffer cannot use this basic RGB bridge as-is. A solution covering one Sega test game is not a solution covering the four Sega profiles or every other console.

See [Sega licensing decision paths](V3_SEGA_LICENSE_OPTIONS.md), [combined-license review](V3_LICENSE_COMPATIBILITY_GATE.md), [physical QA](V3_PHYSICAL_QA_RUNBOOK.md) and [release gate](V3_PUBLICATION_RUNBOOK.md).
