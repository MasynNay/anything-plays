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
| Neo Geo Pocket Color | Mednafen NeoPop | Four-platform native RGB, nonzero PCM and A/B input, workflow `42388394525` |

**16 of 18** profiles have this level of cross-platform original ROM A/V
verification. Tests typically last 8–20 seconds per profile. They are
**not** evidence that every retail game runs, that physical speakers/cameras
work, that all save formats persist, or that each device stays stable for days.
Sources are test-only original assembly/code generators under `tools/`.
Never ship the generated test ROMs to users.

The profiles **without comparable original playback verification on all four
targets** remain: **monochrome Neo Geo Pocket and GameCube**. NGP's
MIT alignment-calibration fixture passes native changing video and real
manual/camera input on all four operating systems but emits **zero nonzero
PCM values**; that fixture alone is insufficient to certify sound.
See the dedicated `.github/workflows/v30-ngp.yml` and the detailed
continuation log below.

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

1. **Close remaining monochrome NGP audio and genuine flash-save evidence**
   with a sound-producing, legally pinned original ROM on all four platforms.
   NGPC RGB/PCM/manual/camera is verified, and its native state-resume
   fallback passed two cold Linux processes; cartridge `.flash` restoration
   remains unverified/failed. Expand physical-device/retail-game tests.
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


## Continuation log — November 7, 2026: native NGP controls and cartridge saves

**Starting revision:** `77d33419f1cd6efd6f7a454e7b96d36396d74ca3`.
The emulator-verification workflow `42385104431` had **80 completed
successful jobs and eight queued Neo Geo Pocket / Color jobs** before a
new push caused GitHub Actions concurrency cancellation. The eight jobs
had **no success evidence**. Do not count them as passed; new runs must
be inspected by job ID, even if `continue-on-error` makes the overall
workflow green.

**Engineering changes on this same 3.0 branch:**

- `3040b5c`: the NeoPop native playback probe now actuates a manually
  held A button with camera controls disarmed, then camera-pulses B with
  camera controls armed, repeatedly. It measures *nonzero input values
  actually queried by the native Libretro core* and gates RGB+PCM success
  on both paths. A thread-local native serialize/unserialize/serialize
  roundtrip is separately reported, limited to 64 MiB. This diagnostic
  does **not** certify any commercial game's in-game saves.
- `3cf3b3f`: regression tests cover native input gate presence and
  serialize/unserialize diagnostic behavior.
- **Important upstream discovery:** Beetle NeoPop returns `NULL` and
  zero for `RETRO_MEMORY_SAVE_RAM` (only `RETRO_MEMORY_SYSTEM_RAM`
  is exposed). Actual cartridge saves use `<rom-stem>.flash` under
  `RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY`, written by the core itself.
  See pinned upstream behavior:
  [libretro.c](https://github.com/libretro/beetle-ngp-libretro/blob/master/libretro.c)
  and [system.c](https://github.com/libretro/beetle-ngp-libretro/blob/master/mednafen/ngp/system.c).
  Existing generic `SaveRAM` alone cannot preserve this flash.
- `49dac30` and `4b9a63c`: added a writable, user-owned, per-ROM
  Neo Geo Pocket flash directory with a collision-resistant path hash
  and passed its actual directory pointer to Libretro
  `GET_SAVE_DIRECTORY`. Two identically named games from different
  folders no longer point to the same `.flash` file. GameCube and other
  platforms retain their prior save-directory routing.
- `ef7abac`: tested distinct save directories and native Libretro
  environment pointer routing for both NGP and NGPC. The source tests
  do not establish a real cartridge committing and reloading flash.
- `66e637e`: isolate all NGP native CI save paths in disposable
  Windows APPDATA / HOME / XDG_DATA_HOME and report actual `.flash` files
  discovered **after** the core is unloaded, without claiming they represent
  a completed save/restore cycle.
- `fc8e09a`: make all eight NGP/NGPC native RGB, PCM and controller
  playback jobs **blocking CI**, rather than masking a failed native
  probe with `continue-on-error: true`. The last push intentionally
  restarts the affected verification run. Inspect job conclusions on
  the current branch head, not an earlier cancelled run.

**Next verified action:** inspect the *latest* workflow head and all eight
Neo Geo Pocket native jobs after the final documentation change; review
their actual video, nonzero PCM, manual A and camera B values. If any fail,
read the job log and make a specific code correction. Then add a legally
distributable homebrew fixture that **writes flash and reads it after a
full core unload/reload**. Save-state roundtrip and path-unit tests alone
do not meet that persistent-flash release gate.

**Unchanged blockers:** GameCube Intel Mac performance, real Windows GPU,
real commercial-game compatibility, clean-install physical input/audio,
extended real-hardware soak, legal/source review, signing and installed
package acceptance. The original 2.0 release and `main` remain untouched.


## Continuation log — November 7, 2026: focused NGP CI and verified recovery

**Follow-on starting point:** `926c8e1`, after the initial NeoPop
save-directory and controller work. Work continued on
`feature/v3.0-unified-test`, with no merge to `main` or modification of
the public 2.0 release.

### Native fixes and evidence

- `7ff21ec`, `b1e5455`, `d2f37df`: Beetle NeoPop's
  physical button **A** maps to Libretro **B**, and physical **B** to
  Libretro **A**. Corrected manual/fish-camera mappings, then updated
  the strict native callback tests and regressions.
- `b2130aa`, `295c4ba`, `6212ed0`: original, immutable
  MIT StarGunner native experiment crosses **three completely separate
  core processes** with real menu presses, captures the in-game
  CONTINUES pixel region and inspects the `.flash` written by core unload.
- `847dcde`, `cf1b65a`, `5f15627`: Dolphin GameCube virtual
  memory-card paths are now platform-user-owned and separate from
  packaged, read-only Dolphin Sys; shared across GameCube games.
  Source environment pointer regressions pass. Actual GameCube retail
  memory-card writes/reads are NOT yet verified.
- `d50e744`, `b1467e3`, `b715cfb`: dedicated
  `.github/workflows/v30-ngp.yml` with eight genuine native RGB/PCM/
  manual/camera jobs, plus original cartridge-flash investigation.
  Moved these jobs out of the 80+ job generic emulator matrix so they
  can finish without unrelated pushes repeatedly cancelling results.
- Real run [42388394525](https://github.com/MasynNay/anything-plays/actions/runs/42388394525)
  reported **all four NGPC native jobs passed** (Windows/Linux/Intel Mac/
  Apple Silicon). Mono NGP jobs ran real emulation and passed changing LCD,
  input polling and state serialization on all four platforms, but failed
  nonzero native sound: `a_align_calib_v12.ngp` is a silent calibration
  fixture. The gate remains strict; do not certify mono audio without a
  properly licensed sound-producing mono NGP fixture.
- Same run: the real StarGunner Options `.flash` test created a
  272-byte `StarGunner.flash`; the modified Options pixels changed, and
  the file remained byte-identical after cold core restart, **but the game
  displayed the baseline number instead of the saved number**. Do not
  claim genuine cartridge-flash restoration. See original `flash.c`,
  `rom.c` and `system.c` in
  [Beetle NeoPop upstream](https://github.com/libretro/beetle-ngp-libretro).
- `8986f98`, `20a5942`, `64b9795`, `bae9bfb`:
  introduced independent `anything_plays/libretro_state.py`
  full-machine save-state fallback for NGP and NGPC. Bounded 64 MiB,
  SHA-256 of exact ROM/core/serialized payload, atomic fsync+replace,
  per-game names, reject invalid and incompatible states. This layer
  does **not** overwrite or substitute native cartridge `.flash`.
  A game launch restores only a correctly fingerprinted checkpoint;
  a save failure warns without killing gameplay.
- `223c89c`, `732d2b4`, `0f2412e`: separated the genuine
  native `.flash` experiment (`--mode flash`, recovery disabled)
  from `--mode state` (recovery enabled, no cartridge flash written).
  **Native two-cold-process save-state resume PASSED** in real job
  `ngpc-independent-native-state-resume`, workflow
  [42389452506](https://github.com/MasynNay/anything-plays/actions/runs/42389452506).
  The first StarGunner process changes the actual in-game Options
  pixels and saves a real core state; second process loads the state,
  reads back the **identical** cropped 8x16 RGB pixels, and reports
  `native_state_resume_applied=true` and zero `.flash` files.
  This is tested native fallback, not proof of in-game cartridge saves.
- `65423ec`: updated the relocated NeoPop unit test to match the
  dedicated workflow. The old assertion was the only reason the
  Linux source regression and focused NGP contract test failed in
  [42389452506](https://github.com/MasynNay/anything-plays/actions/runs/42389452506).
  At revision `65423ec`, the global application workflow
  [42389708320](https://github.com/MasynNay/anything-plays/actions/runs/42389708320)
  **passed** and targeted `ngp-unit-contracts` in run
  [42389708324](https://github.com/MasynNay/anything-plays/actions/runs/42389708324)
  **passed**. The targeted aggregate run stays red because the
  mono audio and raw flash experiments remain unresolved.
- `2010934`, `3178f28`: game UI now reports a verified native
  NGP/NGPC restored session for about 20 seconds instead of silently
  replacing the message with Playing, and headless GUI tests cover
  its precedence and lifecycle. Latest CI must still be inspected.

### Remaining engineering blockers

1. Obtain or source-generate a genuinely sound-producing **monochrome NGP**
   homebrew with clear redistribution permission; require actual nonzero
   native PCM on Windows/Linux/both macOS architectures. Existing mono
   calibration is deliberately NOT certified for audio.
2. Diagnose native NeoPop's failure to **reload a modified flash-backed
   StarGunner Options value** on cold boot. The separate verified native
   state fallback must not hide this in the native flash acceptance job.
3. Verify native recovery across actual core updates/rollbacks and both
   macOS platforms plus Windows, not just the Linux cold restart. Validate
   physical speakers/camera controls and genuine games.
4. GameCube still requires a real Windows GPU with OpenGL 3.3+;
   acceptable Intel Mac 3D FPS; saves, sound devices, camera controls,
   real-game compatibility, long hardware soaks. Do not fake a passing
   GameCube matrix.
5. All complete offline installers, licenses and source obligations,
   signing/notarization, clean installs and distribution acceptance must
   pass `tools/check_v30_release.py` before public release.

**Continue after another stream error:** inspect the actual branch head,
then the most recent `v30-ngp.yml` individual job statuses (especially
`ngp-original-native-av` mono, `ngpc-real-flash-restart-lab`,
`ngpc-independent-native-state-resume`, and `ngp-unit-contracts`).
Inspect `v30-app.yml` and `v30-cores.yml` too. Do not infer
pass/fail from aggregate labels when the raw flash lab uses
`continue-on-error: true`. Branch is not ready for user acceptance.


## November 7, 2026 — continuation after input stream error: native NGP flash root cause and proof

**Original restart head:** `65423ec895400cd20115bd3b0543ae0b33fdf1ad`.
Prior automated application-build failure was a stale test assertion referencing
the moved NGP workflow; it was fixed in `65423ec`. Application-build workflow
[42389708320](https://github.com/MasynNay/anything-plays/actions/runs/42389708320)
completed **all six jobs successfully**, including Linux, Windows, both Macs
and the full source/GUI regressions.

**Focused native Pocket evidence before cartridge-size correction:**

- Workflow [42389708324](https://github.com/MasynNay/anything-plays/actions/runs/42389708324):
  Neo Geo Pocket Color native LCD, real nonzero PCM, manual physical A and
  camera physical B all **passed on four target platforms**.
  Monochrome NGP LCD and both input types passed, but its pinned MIT
  *alignment calibration ROM emits zero-valued PCM*, so its four native jobs
  remain failed. A silent fixture does not demonstrate broken audio hardware;
  **NGP mono audio acceptance remains open** until a suitable pinned,
  permissively licensed, deliberately audible monochrome homebrew is obtained
  and tested across all four platforms.
- A true Libretro save-state checkpoint was added in
  `8986f98` and `20a5942`; `bae9bfb` tests same-ROM/core fingerprints,
  checksum rejection, 64 MiB bounds and cold restart. The native
  **independent** recovery experiment passed in both
  [42389452506](https://github.com/MasynNay/anything-plays/actions/runs/42389452506)
  and subsequent Pocket run [42390603019](https://github.com/MasynNay/anything-plays/actions/runs/42390603019).
  This preserves live session recovery if cartridge flash is unavailable,
  but is *not* a substitute for testing normal in-game cartridge saves.

**Flash root cause was isolated, NOT merely hidden with save-states:**

The 79,765-byte MIT StarGunner development `.ngc` contains code that writes
its 512-byte options/high-score journal near address **0x3FA000** (4,169,728),
near the top of a 4 MiB cartridge. The bare development ROM is too short to
back that address in NeoPop. In native test
[42390351125](https://github.com/MasynNay/anything-plays/actions/runs/42390351125),
the emulator wrote a 272-byte `.flash` file containing **one 256-byte
block** at 0x3FA000. File content persisted, but a new process showed the
old CONTINUES value; this was a legitimate failed save restoration.

The **disposable CI-only test fixture** now pads *only the unused* ROM area to
4,194,304 bytes with erased-flash 0xFF, retaining each of the 79,765 original
bytes and recording SHA-256 hashes before and after staging. The fixture was
verified by immutable Git blob SHA-1 **before** this padding. No commercial
ROM is downloaded and no end-user ROM is edited.

With that accurate cartridge capacity, the same actual Beetle NeoPop core
produced **528-byte `.flash` data with one full 512-byte block**, still at
0x3FA000. Workflow
[42390603019](https://github.com/MasynNay/anything-plays/actions/runs/42390603019),
job `ngpc-real-flash-restart-lab`, **PASSED** its strict 3-process test:
unmodified baseline screen hash `feaac5a7...`, modified options hash
`0d6a43a5...`, and reloaded options hash `0d6a43a5...`, with the same
validated flash file persisting across restart. This demonstrates **real in-game
native cartridge flash save and cold restore for one original MIT homebrew on
Linux**. Do NOT generalize it to all games or hardware or claim the production
frontend automatically stages undersized homebrew cartridges.

**Defensive save validation introduced:**

- `a5a2ad8`: added `anything_plays/neopop_flash.py`, validating NeoPop
  native `.flash` magic 0x0053, 8-byte header, 8-byte padded block headers,
  declared size, 1–256 blocks, 24-bit cartridge addresses, truncation, symlinks,
  and an 8 MiB total bound. Does not rewrite malformed files.
- `db75ee4`: `CoreSession._load_game` checks expected cartridge flash
  **before** invoking native `retro_load_game`; malformed files get
  actionable errors and are preserved.
- `a1573f1`: unit tests exercise corruption, oversize, block layout,
  filename handling and failure before native execution.
- `54af5de`: native flash lab reports file format, physical block sizes,
  block addresses, and hashes, making partial saves visible.
- `79f4501`, `68748f7`, `a94f66b`: bounded, verified 4 MiB homebrew
  staging and unit tests for unchanged original ROM bytes. Test staging
  is intentionally separate from normal user ROM loading.
- `11942b2`: focused CI watches native flash-validation source changes.

**Current passing verification:** application-build workflow
[42390602938](https://github.com/MasynNay/anything-plays/actions/runs/42390602938)
passed all six jobs; Pocket verification
[42390603019](https://github.com/MasynNay/anything-plays/actions/runs/42390603019)
passed four NGPC native OS jobs, unit contracts, actual state restart and
real cartridge flash restart. Four NGP mono native jobs remain **failed
solely on the silent original test ROM's nonzero PCM gate**. Preserve that
failure rather than weakening the sound requirement to get green CI.

**Next steps, in order:**

1. Find/build **a legally redistributable, deliberately audible original NGP
   monochrome game/demo**, pin full source and byte hashes, and verify native
   sound alongside video, controls, and recoverable progress on Linux,
   Windows x64, Intel Mac and Apple Silicon.
2. Only after evaluating actual compatibility, consider an **optional,
   non-destructive, bounded virtual cartridge-capacity staging** mechanism
   for undersized user-owned homebrew. Never pad/overwrite original ROM
   libraries, silently change their identity, or falsely infer a game's
   intended flash capacity from filename.
3. Finish remaining GameCube requirements: actual GPU-driven Windows
   OpenGL 3.3+ playback, Intel Mac rendering ≥20 FPS under representative
   hardware, real controller and speaker QA, extended runtime acceptance.
4. Check all game/profile release gates, licensing and native offline
   distribution/signing; do not release 3.0 or touch stable 2.0 yet.

**Recovery instructions:** inspect latest branch HEAD and focused workflow
`.github/workflows/v30-ngp.yml` on that exact SHA; the last known native
full-cartridge flash success is run `42390603019`. All changes above are
committed, including this append-only durable checkpoint. 


## November 7, 2026 — FIRST INSTALLABLE ALL-CONSOLE 3.0 TEST PACKAGE

**User requested a build to try.** The full offline, test-only packaging workflow
[42391351246](https://github.com/MasynNay/anything-plays/actions/runs/42391351246)
**completed SUCCESS at exact code SHA `215b9d40c37884239bdf528c48f735d6feb9f0bb`**.
All FOUR independent GitHub Actions installation jobs succeeded, including:
Windows x64, Linux x64, macOS Intel x86_64 and macOS Apple Silicon arm64.
Each test package includes **18 system profiles, 11 Libretro core binaries,
Dolphin Sys resources, core hash provenance and bundled license notices**;
`verify_bundle.py --check-native` passed inside the builder on each target.
No separate RetroArch/Dolphin/emulator installation is required. The preview
runs separately from public stable 2.0 and contains no ROMs or BIOS.

**Actual authenticated GitHub Actions download artifacts (14-day retention):**

- Apple Silicon / M2 Pro: [Artifact 13581656191](https://github.com/MasynNay/anything-plays/actions/runs/42391351246/artifacts/13581656191),
  `AnythingPlays-3.0.0-FULL-TEST-ONLY-macos-arm64`;
- Intel Mac: [Artifact 13581766643](https://github.com/MasynNay/anything-plays/actions/runs/42391351246/artifacts/13581766643),
  `AnythingPlays-3.0.0-FULL-TEST-ONLY-macos-x64`;
- Windows x64: [Artifact 13581672063](https://github.com/MasynNay/anything-plays/actions/runs/42391351246/artifacts/13581672063),
  `AnythingPlays-3.0.0-FULL-TEST-ONLY-windows-x64`;
- Linux x64: [Artifact 13581642019](https://github.com/MasynNay/anything-plays/actions/runs/42391351246/artifacts/13581642019),
  `AnythingPlays-3.0.0-FULL-TEST-ONLY-linux-x64`.

Each ZIP contains its native installer, `SHA256SUMS.txt`, and
`FULL_PREVIEW_INFO.json` declaring code revision and package limitations.
Artifact ZIP download requires GitHub authentication. The macOS package is
ad-hoc signed but *not* notarized; for a trusted personal test installation,
use ordinary macOS user-confirmed Open workflow, never disable Gatekeeper
globally. Public `v2.0.0` release and `main` are unchanged.

**Important honesty:** A successful offline installer does NOT certify that all
18 console profiles play all real games. NGP monochrome sound remains unproven
because the immutable legal calibration fixture produces silence. GameCube
still needs real Windows GPU/Intel Mac performance proof, and cross-platform
real-game, physical camera, speaker, long-run and redistribution/signing
acceptance. The full test package is for testing these remaining failures;
do NOT promote its label or artifact SHA to a stable `v3.0.0` release.

**Additional build repair:** `01d42a4` added bounded retry of an intermittent
Intel macOS `hdiutil: Resource busy` (DMG creation only; verification still
strict). `215b9d4` amended `.github/workflows/v30-full-bundle.yml` to
retain full offline developer test installers as GitHub Actions artifacts
instead of discarding them. Prior bundle test
[42349271993](https://github.com/MasynNay/anything-plays/actions/runs/42349271993)
had also passed all four install targets but did not upload files.

**Next:** collect user-installed real-world behavior on Apple Silicon,
especially embedded Dolphin gameplay, device camera/controls, speaker audio,
game-only display and 30+ minute runtime, without marking unmet public
release gates complete. Inspect run `42391351246` first if another chat
stream is lost.


## November 7, 2026 — 3.0 quality-of-life update / optional multi-color input

**User-tested baseline:** User successfully loaded GameCube and Nintendo 64
emulation from 3.0 preview and requested a game-panel volume rocker,
multi-fish same-color input, optional Color 2, and local Player 2 controls.
User then clarified **multiple fish per color MUST be optional and OFF by
default**. All changes are committed on
`feature/v3.0-unified-test`; stable 2.0 and `main` untouched.

**Implemented:**

- `anything_plays/libretro_audio.py` supports bounded, callback-applied
  per-application PCM gain and immediate silent output while draining existing
  queued samples. Native core PCM is untouched. Startup defaults to 35%.
- `anything_plays/ui_volume.py` isolates volume initialization, mute and
  previous unmuted-level persistence from the otherwise compact `app.py`.
  The primary game panel and **Game only** view expose a 0–100% slider,
  mute/unmute, and Ctrl+Shift+M shortcut, without OS volume changes.
- `anything_plays/tracking.py` provides `locate_targets` to track up to
  16 detached same-hue contours; the legacy largest-contour API is retained.
  Profile `multi_fish_enabled` default **False** and UI checkbutton
  **Enable multiple fish per color (multi-input)** control whether the
  tracker considers one or all separated matching fish. This setting is
  per-console and legacy profiles migrate with it OFF.
- Color 2 remains OFF by default, with separate in-video picker, RGB choice,
  Color 2 preview marker and Player 1 / Player 2 selector. Both colors can
  work simultaneously, even when each tracks only one fish.
- Camera input now has **Held while visible** and **Pulse (classic)** modes.
  Per-frame input snapshots permit multiple simultaneous buttons on the
  same controller, independently for two local Libretro ports. STOP clears
  both ports immediately and preserves manual keyboard controls.
- Native controller P2 is attached through
  `retro_set_controller_port_device(1, RETRO_DEVICE_JOYPAD)` after core ROM
  load on systems that support two controller ports. N64/GameCube P2 digital
  and analogue states are generated independently of P1; unsupported
  platforms/optional external bridge show a warning rather than faking P2.
- Preview displays two colors' tracking marker outlines, number of visible
  fish and currently held P1/P2 buttons. Multiple occupied zones highlight.
- All options are profile-persistent and documented step-by-step at
  `docs/V3_AUDIO_MULTIFISH_CONTROLS.md`.

**Regression repairs, all explicitly verified without relaxing tests:**

- Existing `tests/test_source_contracts.py` limits `app.py` to fewer
  than 250 lines. Adding direct volume init raised it over the limit;
  refactored into `VolumeMixin`; `app.py` now **249 lines**.
- GameCube's original controller test assumed only port 0 existed. New
  `tests/test_v21_gamecube_software.py` explicitly requires BOTH
  `call(0,1)` and `call(1,1)` after ROM load.
- Original installer lab contract forbade ALL full-build artifact uploads.
  `tests/test_v30_offline_installer_lab.py` now requires clearly labeled,
  14-day owner-only FULL-TEST-ONLY GitHub Actions artifacts, and still forbids
  promoting them to a public GitHub release.
- Added `tests/test_v30_multi_fish_qol.py` (12 checks) and expanded GUI smoke
  test with opt-in default, persistence, mute, restored previous volume and
  settings reset. The focused tests passed on Apple Silicon, Windows, Linux
  in full offline installer jobs (Intel pending when recorded).
- The first Linux full-build failed *only* at the new GUI smoke invocation
  because direct execution from tests/ did not add project root to
  `PYTHONPATH`; `9af1afe` explicitly sets `PYTHONPATH=.` before Xvfb.
  Re-run **PASSED** the Linux full offline packaging.
- Application workflow
  [42394490773](https://github.com/MasynNay/anything-plays/actions/runs/42394490773)
  passed **all six jobs**, including full source/unit/GUI regression suite,
  30-second redraw soak and all four starter installer builds at code
  `5805447ea9b9a0a1d31fec070b28654410e708b6`.

**Updated full offline 18-profile preview built from identical application
source** (workflow YAML fix only at `9af1afe`), run
[42394706785](https://github.com/MasynNay/anything-plays/actions/runs/42394706785):

- Apple Silicon:
  [artifact 13583470513](https://github.com/MasynNay/anything-plays/actions/runs/42394706785/artifacts/13583470513)
  — passed native package verification, all 12 audio/multi-fish regressions.
- Windows x64:
  [artifact 13582767985](https://github.com/MasynNay/anything-plays/actions/runs/42394706785/artifacts/13582767985)
  — passed package verification and new QoL regressions.
- Linux x64:
  [artifact 13582509228](https://github.com/MasynNay/anything-plays/actions/runs/42394706785/artifacts/13582509228)
  — passed package verification, new QoL regressions **and actual Xvfb GUI
  smoke** after PYTHONPATH fix.
- Intel macOS job still compiling when this checkpoint was appended; check
  run `42394706785` for final job status and latest artifact ID. Earlier
  code-identical first full run had passed Intel macOS packaging.

**Important distinctions:** New 3.0 test builds are NOT a certified stable
release; GameCube real hardware/long-run acceptance, monochrome NGP audio
and broad 18-console commercial gameplay still require verification. Native
Libretro local P2 support is wired and tested synthetically; a real game's
two-player mode with actual aquarium tracking still needs user feedback.
No netplay/online multiplayer is implemented. GitHub Actions artifacts
expire after 14 days and may require sign-in; don't invent sandbox links.

**Next action after any interruption:** Fetch latest branch HEAD, workflow
run `42394706785`, report status and artifact refs for all four systems.
Do not repeat already completed changes or run new code modifications
unless a test or real-device failure warrants them.


### Final QoL preview CI completion — all four platforms PASSED

All four offline 3.0 preview package jobs **COMPLETED SUCCESSFULLY** at source
commit `9af1afe50ad1a9379c02e3302876e51d9c271646`:
[full installer run 42394706785](https://github.com/MasynNay/anything-plays/actions/runs/42394706785).
This includes Linux Xvfb real GUI smoke test and all 12 dedicated volume,
opt-in same-color multi-fish and independent P1/P2 tests on every target.

The final remaining macOS Intel artifact is:
[macos-x64 artifact 13582134993](https://github.com/MasynNay/anything-plays/actions/runs/42394706785/artifacts/13582134993),
`AnythingPlays-3.0.0-FULL-TEST-ONLY-macos-x64`.

The paired [application build and full GUI regression run
42394706787](https://github.com/MasynNay/anything-plays/actions/runs/42394706787)
also completed **all six jobs successfully** at the same source SHA.
Earlier provisional note "Intel pending" above is therefore resolved.

Current downloads all correspond to the same QoL source revision:
Apple Silicon `13583470513`, Intel Mac `13582134993`,
Windows x64 `13582767985`, Linux x64 `13582509228`.
They are developer test packages, NOT a GitHub release. Keep 2.0 stable.
