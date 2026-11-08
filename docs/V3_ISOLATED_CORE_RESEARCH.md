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

## Verified native laboratory results — November 8, 2026

**Source checks: passed. Native research CI: all eight jobs passed.**
[Full eight-job run 42496671418](https://github.com/MasynNay/anything-plays/actions/runs/42496671418) compiled source-built GPLv3 bsnes/BlastEm from their previously frozen commits. Four BlastEm jobs additionally ran both **genuine** isolated Master System native sessions and emitted original archive evidence. The following results were independently downloaded and SHA-256 verified against each original artifact's unmodified source/native/notice/manifest checksum entries:

| Host | Original CI artifact ID | Full original downloaded ZIP SHA-256 | Two captured RGB-frame counts | Distinct frames |
| --- | ---: | --- | ---: | ---: |
| Linux x64 | 13623128935 | `05a600467dcb29f90d91d482b9916869e210082a641e4e014cbffed0d419b367` | 169 / 173 | 6 / 8 |
| Windows x64 | 13624265997 | `2e9b81b34c9d8da743f45bad7424f822cbc3eb6231e21020ed72b84c00f01af2` | 109 / 119 | 6 / 6 |
| macOS Intel | 13623717202 | `81ababe0551682c9631d5374fa358916fbd7628635688769acb00ccad1f68dda` | 37 / 47 | 4 / 2 |
| macOS Apple Silicon | 13624191967 | `681afe59491f2925c57515cfaa6ccad7dbe44a1e0bbb83406828af4c4934b959` | 31 / 40 | 4 / 2 |

For all **four real operating-system/architecture runners**, each original test contained exactly two successful, terminated, nonblank, changing-video process sessions. In all four unmodified ZIPs, the experimental test report's `real_libretro_core_sha256` matched the source-build manifest's `native_sha256`, and all four entries in the original `SHA256SUMS.txt` matched the extracted bytes. Original BlastEm source commit `2230addc4dd74dd094fd264987fd808abba32d0e` and source TAR SHA-256 `208b420abe72708e2e9f3dbd81a996e19c48b81a9d687f4f514b8fe22e48d868` matched across every preserved original artifact.

**Do not misread the capture counts as emulator FPS.** They include subprocess startup and CI host delays, and no frame pacing, lag or responsiveness target was demonstrated. In particular the two macOS samples were markedly below the Linux/Windows capture counts; performance must be separately instrumented and improved before any attempt to move this experimental bridge into normal gameplay. No physical webcam, actual audio output, native PCM content, save/reload, retail game, signed installer, legal separation or combined-program rights claim was tested. The published product's core integration and release approvals remain unchanged.
