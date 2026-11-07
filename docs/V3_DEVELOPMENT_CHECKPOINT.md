# Anything Plays 3.0 — development handoff and verified release gates

_Last checked: 2026-11-07 UTC. Active branch: `feature/v3.0-unified-test`._
_This is an engineering checkpoint, NOT a 3.0 release announcement._

## The nonnegotiable product contract

- **18 console profiles** (GB through GameCube, **no Wii**).
- **All 11 required native cores**, plus the matching bundled Dolphin `Sys` data,
  are included in a single, initially **offline** app installer on each target OS.
  No separate emulator, RetroArch, ROM downloader, BIOS, or first-run emulator
  download is required. Players supply their own lawful games.
- Games run in the Anything Plays panel. Embedded GameCube uses Dolphin Libretro
  hardware acceleration, **not** a separate Dolphin application or game window.
- Approved *updates* can be installed, verified and rolled back in-app between
  game sessions, without restarting the application. Updates are not prerequisites
  to first launch.
- Preserve the original fish/camera mechanics, per-console ROM shelves, manual
  keyboard controls, configurable shortcuts, saves, visual themes, game-only
  viewing, borderless and full-screen modes.
- Normal use must remain stable after many hours, repeated game switching,
  camera disconnect/reconnect and idle uptime.
- Keep public main and the published 2.0 release **unchanged** pending acceptance.

## Evidence — production-style native A/V in all four OS environments

The following consoles have **passed original/legal homebrew video and
nonzero native audio PCM** in production `CoreSession` on **Windows x64,
Linux x64, macOS Intel x64 and macOS Apple Silicon**:

| Profiles | Native core | Evidence |
| --- | --- | --- |
| Game Boy, Game Boy Color, Game Boy Advance | mGBA | Four-platform workflow `42352993417` |
| NES | FCEUmm | Four-platform workflow `42349568501` |
| SNES | Snes9x | Four-platform workflow `42379612917` |
| Sega Genesis/Mega Drive | Genesis Plus GX | Four-platform workflow `42352993417` |
| Sega Master System, Game Gear, SG-1000 | Genesis Plus GX | Four-platform workflow `42379035447` |
| Atari 2600 | Stella 2014 | Four-platform workflow `42349568501` |
| Atari 7800 | ProSystem | Four-platform workflow `42382893807` |
| PC Engine (HuCard) | Mednafen PCE Fast | Four-platform workflow `42382893807` |
| WonderSwan, WonderSwan Color | Mednafen WonderSwan | Four-platform workflow `42382893807` |
| Nintendo 64 | ParaLLEl-N64, embedded software video | Four-platform workflow `42349568501` |

**15 of 18** profiles have this level of cross-platform original ROM A/V
verification. Tests typically last 8–20 seconds per profile. They are
**not** evidence that every retail game runs, that physical speakers/cameras
work, that all save formats persist, or that each device stays stable for days.
Sources are test-only original assembly/code generators under `tools/`.
Never ship the generated test ROMs to users.

The profiles **without comparable original playback verification on all four
targets** remain: **Neo Geo Pocket, Neo Geo Pocket Color, and GameCube**.
The two MIT-licensed NeoPop homebrew tests are pinned and CI-only; workflow
`42383623857` was queued at the time of this handoff. Do not call them passed
until their native RGB **and PCM** job-level tests succeed.

## Longevity and native lifecycle validation

- **132 native Libretro start/stop and console-switch cycles PASS**, all in
  **one process**, testing eleven profiles and six emulator engines. All started
  original homebrew and produced a video frame, manual/camera input pulses
  were issued, no stuck Python emulator workers or controller state remained,
  and RSS grew only **0.76 MiB** after the first full cycle. Workflow
  `42381687786`, job `native-eleven-console-lifecycle-soak`. Runner: Linux.
- **15-minute synthetic camera/video/Tk GUI endurance PASS** under Xvfb.
  Bounded canvas items, scheduled timers, and RSS growth. Workflow
  `42378515296`, job `gui-15-minute-soak`. This is not physical camera QA.
- **10-minute *native* embedded GameCube endurance PASS on Linux**:
  29,904 frame callbacks, **49.83 FPS**, moving RGB frames, native controller
  polls and **57,407,600** nonzero PCM values, with **51.81 MiB** RSS growth
  after warm-up (limit 192 MiB). Same workflow, job
  `gamecube-10-minute-native-soak`. Headless runner has no speaker device.
  This is original PowerPC 3D homebrew, NOT a commercial retail game.

The audio engine was corrected after a real Linux headless `PortAudioError`
when `sounddevice.query_devices(kind="output")` had no default device. It
now continues with a visible warning rather than terminating the emulator.
Unusual source sample rates such as **131072 Hz** (GB/GBC) and **65536 Hz**
(GBA) are converted to supported output device rates with bounded stereo
PCM queues. Audio output remains explicitly unverified on physical speakers.

## GameCube — important remaining work

The *same* original 3D-and-audio GameCube test runs embedded without a
separately installed Dolphin process. Results so far:

- Linux EGL: **49.83 FPS over 600 seconds**, real PCM and 51.81 MiB
  post-warm-up RSS growth, test PASS.
- macOS Apple Silicon: native original game PPU/GPU and audio demonstrated,
  with one combined test measuring **25.56 FPS**, passing the 20 FPS threshold.
  This is not yet an extended native soak on real user hardware.
- macOS Intel: moving 3D frames, input polls and nonzero PCM are real,
  but combined playback measured only **10–14 FPS** on hosted runners.
  Fail the 20 FPS acceptance threshold: DO NOT change the threshold just to
  make an Action green. GPU readback represented ~6–7% of total runtime, so
  merely reducing framebuffer readback will not solve this bottleneck.
- Windows hosted runner: WGL creation failed with
  `wglCreateContextAttribsARB not found`: runner lacks a graphics
  driver supporting OpenGL 3.3+. A downloadable package and context smoke
  are NOT proof of playable Windows GameCube on a real compatible GPU.

For a public release, verify a normal installed GameCube ROM in the actual
app panel with controllers, saves, real speakers, and prolonged uptime
on all four supported targets. Do not silently substitute the crashing
experimental CPU-only GameCube renderer.

## Installer, source, update and release gating

- `.github/workflows/v30-full-bundle.yml` **successfully built and inspected
  full offline packages** containing all 11 cores and paired Dolphin `Sys`
  for Windows x64, Linux x64, macOS Intel and Apple Silicon; workflow
  `42349271993` passed. This **does not** prove each packaged game plays,
  that application signing/notarization is complete, or that distribution
  permission for every third-party native component has been cleared.
- `.github/workflows/v30-app.yml` still produces *small mGBA-only starter
  CI previews*. **Never represent those artifacts as complete 3.0
  installers.** Only the full-bundle lab represents the intended package
  layout, and those lab binaries are deliberately not published.
- Legacy `ROM-name.sav` game progress is still supported. On read-only,
  disconnected or restricted ROM libraries, SRAM saves automatically fall back
  to a user-owned per-game path, with collision-resistant names and atomic
  writes. The latest fallback copy wins over a stale legacy save.
- Main 3.0 UI no longer offers **Download emulator** for missing cores.
  Missing core files are treated as a damaged/incomplete package with repair
  instructions. Approved in-app updates and rollbacks remain separate.
- `config/v3.0-release-acceptance.json` and
  `tools/check_v30_release.py` fail closed until every profile, legal
  permission, installed payload, signing and real-world QA requirement
  is fulfilled. Never bypass these gates to create a cosmetic green result.
- Real ROMs/BIOS must not be bundled. Audit every native core license,
  corresponding source and attribution, Python dependencies, Dolphin `Sys`
  assets, public redistributables, signing/notarization and documentation.

## Next engineering steps, in order

1. **Close Neo Geo Pocket and Neo Geo Pocket Color cross-platform playback evidence** with original
   rigorously pinned legal homebrew, real video and PCM on all platforms. Add manual input and save/restore checks
   for each platform, not just test ROM startup.
2. **Fix/verify GameCube on actual Windows GPU hardware and Intel Mac.** Keep
   test evidence and performance thresholds honest. Add long native soaks
   and real in-panel QA for the Mac and Windows hardware paths.
3. Exercise *all 18* profiles, peripheral/camera input, game-only/
   borderless/fullscreen rendering, save/restore, core update/rollback,
   unplugged cameras, disconnected storage and genuine audio devices from
   clean-installed packages. Perform unattended multi-day physical QA.
4. Reconcile the final offline installer UX, crash diagnostics, license
   notices, update integrity verification, Windows code signing, macOS
   signing/notarization and Linux desktop integration.
5. Once every release gate is satisfied, publish ONE professional 3.0
   release with correctly matched per-platform assets, keeping 2.0 stable.

## Continuation rule after a conversation stream error

1. Inspect the **current SHA** of `feature/v3.0-unified-test`, then inspect
   the newest *job-level* GitHub Actions logs; do not infer success only from
   the overall workflow status. Some exploratory jobs have
   `continue-on-error: true`.
2. Confirm no new commit invalidated earlier evidence; rerun impacted tests.
3. Continue from the *actual last passing state*. Do not reintroduce
   first-run core downloads, ship copyrighted game ROMs or remove blockers
   simply to mark 3.0 ready.
4. Stable `main` / public 2.0 remain untouched; do not ask the user to test
   until all intended console profiles and full package requirements are met.
