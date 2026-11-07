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


## November 7, 2026 — Virtual aquarium end-to-end simulated acceptance (NO real fish)

**User context:** User does not currently have fish and requested actual simulation
rather than being asked to test a physical aquarium.

**Created and committed:**
- `tests/simulate_aquarium.py` [commit `6cb8580`]: deterministic BGR
  artificial pink and cyan moving "fish" processed through an actual
  headless Tk `App` instance (Xvfb), `VirtualCamera.read()`,
  `GameplayMixin.tick()`, `CameraMixin.draw_camera()`,
  `Emulator.set_camera_buttons()`, `InputBuffer.before_frame()`
  and `InputBuffer.state()`, exactly the game core's Libretro input
  callback entrypoint. No patched/mock tracking decision and no synthetic
  controller outcomes — the test asserts actual callback states.
  Uses a temporary home for all preferences and no user files/camera.
- `.github/workflows/v30-virtual-aquarium.yml` [commit `10db56c`]:
  independent native Linux Xvfb GUI acceptance job, running on changes
  to camera, tracking, UI, controller, profile and test sources. Uploads
  JSON evidence to GitHub Actions for 30 days and fails on any unmet
  assertion; does not require ROMs or third-party emulator apps.

**Verified CI acceptance:**
[Run `42402602944`](https://github.com/MasynNay/anything-plays/actions/runs/42402602944)
at exact commit `10db56cd5b65161efd5f9b897b9b6ca816a2e388` concluded
**SUCCESS**, with 34/34 actual UI-to-Libretro-callback assertions passed,
zero exceptions/failures.
[Download detailed JSON evidence](https://github.com/MasynNay/anything-plays/actions/runs/42402602944/artifacts/13585553166).

Verified behaviors: multi-fish OFF by default (two same-colored fish
cause only one control); opt-in same-color multi-fish presses A+B
simultaneously; one shape leaves and B is released; all fish absent
releases remaining buttons; Color 2 disabled never presses an extra
button; independent Color 2 sharing Player 1 or controlling Player 2;
Color 2 disable releases P2; classic pulse lasts exactly two emulated
frames and expires even when a fish stays visible; held mode coexists
with manual keyboard input; STOP immediately releases both camera
controller ports while preserving manual P1 input; simulated camera
disconnect disarms and clears all camera state; both GameCube and
Nintendo 64 native input callbacks emit independent opposite-direction
P1/P2 analog sticks with immediate STOP release; 100 camera simulation
frames reuse one Tk camera canvas item and keep input queue bounded.

**Scope boundary:** This *does not* use a physical aquarium, webcam driver,
real fish with reflections/occlusion, real commercial or homebrew multiplayer
game, real native 3D emulation loop, or physical controller/speaker. The
Libretro input callback path is tested, but actual two-player *gameplay*
with real aquarium lighting and camera exposure remains unverified.
Passing simulation is strong integration evidence, not a substitute for
physical compatibility QA. Stable 2.0 and main untouched.


## November 7, 2026 — Object-neutral right-side UI redesign + GameCube readback pacing

**User request:** User supplied an Apple Silicon 3.0 screenshot and requested
the right side be organized, readable and not fish-specific; clarified the
project is Anything Plays, suitable for *any* camera-trackable objects. User
also reported GameCube native emulation worked but looked uneven. They
explicitly requested the code be developed and packaged, not a mockup.

**Implemented, stable v2.0 and `main` untouched:**

- New `anything_plays/ui_tracking_panel.py` builds dedicated, spacious
  labeled 03 Primary Object, 04 Secondary Object (optional), 05 Input
  Behavior, 06 Button Zones, 07 Advanced Settings sections. Primary
  object and secondary object show **clickable RGB color swatches**, color
  picker actions, readable labels and plain-language explanations.
- All visible UI tracking controls are object-neutral: **Enable multiple
  objects per color** (OFF by default), **Enable secondary object** (OFF by
  default), **When an object...** phrasing, Primary/Secondary object counts
  and color values; left camera label is now *Live tracking preview*.
- Advanced detection/timing and zone appearance controls are collapsed
  by default. Individual zone-to-button remapping is separately expandable
  and retains all prior per-console mapping objects/callbacks. Primary and
  secondary tracking continue working with either panel hidden.
- The game area groups display + in-app volume (and GameCube preview rate)
  in a nested **DISPLAY & SOUND** panel. Emulator maintenance/update
  controls are still accessible but collapsed by default. Current-game
  status has a distinct section. Right pane gets a slight width increase.
- `anything_plays/ui_theme.py` defines theme-aware bold value labels,
  helper labels and more legible checkbox/button typography without
  discarding the existing 16 color palettes.
- `anything_plays/ui_camera.py` refreshes the new swatches and
  secondary section while preserving existing saved profiles, camera
  routing, optional multi-object input and independent two-player controls.
- **GameCube performance:** The new
  `anything_plays/gamecube_preview.py` policy and updated
  `anything_plays/gamecube_gpu.py` limit only *synchronous*
  OpenGL->CPU framebuffer readback to selectable 20 / 30 / 60 FPS
  preview budgets: Performance (20), Balanced (30, default),
  Quality (60). `anything_plays/ui_gameplay.py` aligns the Tk
  preview timer with the selected mode. All Dolphin native frames,
  Libretro audio, controller updates and game saves still execute.
  Mode may change while playing and persists in preferences. This is
  an attempted reduction of GPU readback and UI CPU cost, NOT a proven
  boost to GameCube's actual emulation FPS on macOS.
- `tests/test_v30_gamecube_preview_optimization.py` invokes the actual
  GameCube hardware video callback with controlled clock and a synthetic
  offscreen host; asserts 7 native callbacks, only 3 expensive readbacks
  across live mode switches, no erroneous stop, and proper null-frame
  behavior. Existing full GUI, 18-console profile, tracking, and
  2-player simulation tests continue to pass.
- UI source is grouped in dedicated modules; original callbacks and
  update/rollback actions remain present. The public v2.0 release
  was not changed.

**Strict passing build evidence at exact code revision
`784798b0ba75224ec5aa3b8af7a9935c63c1c43a`:**

- [Full offline installer CI run 42406279267](https://github.com/MasynNay/anything-plays/actions/runs/42406279267) — **SUCCESS**, all
  four jobs (Windows x64, Intel Mac, Apple Silicon, Linux x64).
  Verified 18 profiles/11 bundled emulator cores and Dolphin Sys,
  new 12 multi-color/audio tests, new GameCube readback tests,
  and headless Linux Xvfb GUI smoke. No external emulator download.
- [Application/regression CI run 42406279349](https://github.com/MasynNay/anything-plays/actions/runs/42406279349) — **SUCCESS**,
  all six jobs including full source + GUI regression and
  Windows/Linux/two Mac application staging.
- [Latest independent virtual aquarium test](https://github.com/MasynNay/anything-plays/actions/runs/42405777852) —
  **SUCCESS**, 34/34 actual UI-to-Libretro controller assertions after
  converting the status labels from fish to objects.

**User-test download artifacts (GitHub Actions ZIPs, test-only, 14-day retention):**

- Apple Silicon (M2 Pro):
  [13586924633](https://github.com/MasynNay/anything-plays/actions/runs/42406279267/artifacts/13586924633)
- Intel macOS:
  [13587383778](https://github.com/MasynNay/anything-plays/actions/runs/42406279267/artifacts/13587383778)
- Windows x64:
  [13587027930](https://github.com/MasynNay/anything-plays/actions/runs/42406279267/artifacts/13587027930)
- Linux x64:
  [13587985332](https://github.com/MasynNay/anything-plays/actions/runs/42406279267/artifacts/13587985332)

Each ZIP holds a native installer and digest/limitations manifest. These
are **unnotarized, developer-only previews**, NOT a public, signed or
legally cleared stable 3.0 release. Observe remaining NGP monochrome
sound fixture, GameCube native FPS on real devices, commercial 2-player
compatibility, native camera/objects and third-party license checks.
Real Apple Silicon GameCube smoothness must be measured in actual
gameplay; the synthetic video test demonstrates skipped copies only.

**Continuation instruction:** Read this checkpoint before editing,
preserve exact opt-in defaults and existing emulator/update/save
functionality. The production source SHA under which all build jobs
passed is `784798b0` (documentation-only updates after this point
do not require rebuilding the installers).


## November 7, 2026 — Original logo preservation, NOT a redesign

**User's explicit correction:** Do not redesign or regenerate the fish icon!
They want the existing cute fish, expression, handheld, colors, and rounded
cyan frame left exactly as-is. The ONLY requested edit is transparency of
the unwanted black matte **outside** that frame. An unrelated generated
replacement illustration is REJECTED and is not used or added to GitHub.

**Implemented:**

- Canonical ORIGINAL artwork remains
  `assets/anything_plays_v21.webp`, Git **blob SHA-1
  `c620c4154e80768687dfde4c0541f544779af2ff`**.
  Neither this file nor stable v2.0 artwork was touched.
- `anything_plays/icon_cleanup.py` now changes **only the alpha channel
  of edge-connected dark exterior matte**. Every RGB color byte in the
  *entire original image* is preserved. An earlier proposed 2px fringe
  smoothing was deliberately removed because it could damage dark
  linework around the cute face, handheld, or cyan border.
- Native icon generator `tools/render_v21_icon.py` and live Tk icon
  `anything_plays/ui_icon.py` both read the same original WebP and use
  the strictly alpha-only exterior cleanup. Fixed script-direct import
  path on all four OSes; no new fish graphic is involved.
- `tests/test_v30_icon_matte.py` now enforces exact original WebP Git
  blob, all source RGB pixels byte-for-byte unchanged, central fish alpha
  unchanged, transparent outer corners, native PNG/small PNG/ICO corners
  transparent, and already-transparent graphics left unchanged.
- All four full offline 18-console preview installers
  [CI 42411730145](https://github.com/MasynNay/anything-plays/actions/runs/42411730145)
  passed **SUCCESS** at source code `b16ed7194fd9b2f6337294d16f7402d3e60feeec`.
  The [application/GUI build and regressions](https://github.com/MasynNay/anything-plays/actions/runs/42411729849)
  also passed all jobs at the same source code commit.
- New preview downloads: [Apple Silicon M2 Pro artifact 13589628802](https://github.com/MasynNay/anything-plays/actions/runs/42411730145/artifacts/13589628802),
  [Intel Mac 13589892315](https://github.com/MasynNay/anything-plays/actions/runs/42411730145/artifacts/13589892315),
  [Windows 13589931714](https://github.com/MasynNay/anything-plays/actions/runs/42411730145/artifacts/13589931714),
  [Linux 13588939472](https://github.com/MasynNay/anything-plays/actions/runs/42411730145/artifacts/13588939472).

**Other changes in this same preview:** the left camera panel now includes
an always-visible **Shuffle control zones now** button, native emulator
launch state distinguishes startup in progress vs true failed boot, N64
object-control arming may wait for the launch to complete, stale failure
details remain visible, and the game panel offers **Restart game** to try
reloading the selected ROM. Source/UI regressions passed. The user's exact
original N64 ROM crash has NOT been reproduced or verified as fully
resolved on their Mac; don't claim it has.

**IMPORTANT:** Never generate a replacement fish logo, change the original
WebP, soften its exterior outlines, or reinterpret the illustrated handheld.
If further image changes are needed, use only the canonical source and
get explicit user approval before touching interior pixels. Stable main
and v2.0 remain untouched.


## November 7, 2026 — N64 only plays first ROM: ROOT CAUSE REPRODUCED AND FIXED

**User-reported exact failure:** Nintendo 64 game runs once, then after
Unload/Restart/Different ROM it never produces video again. Quitting and
reopening Anything Plays fixes one game only. User also tested GB, GBC,
GBA, SNES and GameCube, which did not show the same repeatability defect.

**Hard evidence before fix:** A new real-native regression
[`tools/probe_n64_restart.py` CI run 42414504317](https://github.com/MasynNay/anything-plays/actions/runs/42414504317)
used pinned public-domain SaveTest-N64 homebrew and the production
`Emulator.start()`/`stop()` worker in one Python process.
**All four OSes failed on second ROM boot**: Linux, Windows, Intel macOS and
Apple Silicon macOS. The first produced nonblank core video and stopped
cleanly; the second boot produced no usable frames without a useful Python
exception. Earlier CI only checked one successful launch.

**Root cause:** ParaLLEl N64 retains process-global native graphics/core
state beyond `retro_unload_game` / `retro_deinit`; merely spawning a fresh
Python thread to `ctypes.CDLL` the *same resident native module* does not
reset it. On Linux and Windows, explicitly releasing its library handle
AFTER complete core unload/deinit and callback release resets the core.
A first attempt to apply native `dlclose` to macOS produced a genuine
**SIGSEGV on both Mac architectures**
[`42414731946`](https://github.com/MasynNay/anything-plays/actions/runs/42414731946);
that unsafe approach is **NOT** shipped on macOS.

**Safe production solution, no external emulators:**

- `anything_plays/libretro_native_loader.py` supplies
  `release_inactive_core_library`, enforcing unloaded/deinitialized core
  and cleared callback pointers before releasing N64's native module on
  **Linux/Windows only**. GB/GBC/GBA/SNES/GC and all other core loaders
  retain their previous lifecycle and are not subjected to forced unloading.
- `anything_plays/n64_process.py` is the **macOS-only** per-game
  subprocess bridge. Each N64 ROM boots an entirely NEW spawned operating
  system process with its bundled ParaLLEl native core, so macOS never
  invokes unsafe `dlclose`, and all N64 globals disappear when the worker
  process exits. Parent Tk UI remains running. Bounded shared memory passes
  decoded frames (up to 1024×1024), 30FPS preview and two local Retropad
  digital/analog states; the child's native PortAudio sink handles sound,
  live game-only volume and existing saves. Existing camera/manual input
  and Player 2 routing remain connected. A crashed child cannot segfault
  the parent UI. Native processes are stopped/joined and terminated if they
  refuse to shut down. `app.py` invokes `multiprocessing.freeze_support`
  so a frozen PyInstaller child does not start a duplicate GUI.
- `anything_plays/gba_emulator.py` chooses safe per-game Mac child only
  for N64. Windows/Linux use explicit handle release only for N64; other
  consoles and GameCube continue unchanged.
- Additional UI repair from preceding checkpoint: preserves failed launch
  status and offers Restart game; does not force new external downloads.

**Passed AFTER fix:** focused
[4-OS real native triple-restart run 42415242942](https://github.com/MasynNay/anything-plays/actions/runs/42415242942)
at code SHA `24553f4ab4f95fca48e82bf716a936b137396dd7` —
**SUCCESS: 4/4 native jobs, three real nonblank and cleanly stopped N64
games each**, no app restart. The subsequent `app.py` change to invoke
`freeze_support` leaves the session implementation unchanged.

Full offline installer and source GUI validation at code SHA
`bbdcdfc9fd971f9a414003eb317746535a909f7e`:

- [Full 18-profile/11-core installer run 42415284318](https://github.com/MasynNay/anything-plays/actions/runs/42415284318):
  **SUCCESS, all four native OS packages passed**.
  - [Apple Silicon / user's M2 Pro artifact 13591515884](https://github.com/MasynNay/anything-plays/actions/runs/42415284318/artifacts/13591515884)
  - [Intel Mac artifact 13591621104](https://github.com/MasynNay/anything-plays/actions/runs/42415284318/artifacts/13591621104)
  - [Windows x64 artifact 13590164796](https://github.com/MasynNay/anything-plays/actions/runs/42415284318/artifacts/13590164796)
  - [Linux x64 artifact 13590994185](https://github.com/MasynNay/anything-plays/actions/runs/42415284318/artifacts/13590994185)
- [Full application regression and installer run 42415284288](https://github.com/MasynNay/anything-plays/actions/runs/42415284288):
  **SUCCESS, all six jobs**, including source/GUI long-run regression.

**Evidence for other user-tested consoles:** existing
[`native-eleven-console-lifecycle-soak` in emulator run 42412156427](https://github.com/MasynNay/anything-plays/actions/runs/42412156427)
passed 12 repeated start/stop cycles of 11 original homebrew console profiles,
including GB, GBC, GBA and SNES, using six native cores in one process;
other 3D GameCube engine has its own embedded GPU tests and has not been
changed by this N64-only fix.

**Release and honesty:** This is a **full developer TEST installer**, not
a public stable 3.0 release; bundles may be unsigned/notarized and GitHub
artifact links expire. The exact user's Majora's Mask and other commercial
ROMs on their personal Mac have not been executed by CI. Native game audio,
input bridge, freeze_support and saves are implemented but need hands-on
owner verification in the installed Mac DMG. No ROMs, BIOS or external
emulator are bundled beyond licensed native cores and Dolphin Sys. The
original fish artwork remains immutable; main and stable 2.0 untouched.

**If a stream fails:** resume from this verified SHA, not the broken
single-boot assumption. Do NOT re-enable macOS `dlclose`. A user test
should repeat N64 ROM A → Unload → ROM B → Unload → ROM A with sound and
manual/camera controls. Record any error display or hangs and then improve
only the failing path.


## November 7, 2026 — Public roadmap and Windows physical QA handoff

User asked for professional public GitHub roadmap to document authentic development
activity, maintenance, productive ideas and evidence for future contributors and
hiring reviews. Published `ROADMAP.md` on BOTH main (public stable landing page)
and 3.0 development branch, with explicit completed work, active/queued QA,
proposals, blockers and clear rules separating CI evidence from physical testing.
Linked roadmap in both branch README files; updated stale 3.0 development
README to accurately distinguish full offline 18-profile developer installer
vs optional starter and to document N64 multi-ROM fix and pending GameCube
performance. No stable 2.0 application source or published release was changed.

Created focused public issues:
- [#25 Linux clean-install and real-device QA](https://github.com/MasynNay/anything-plays/issues/25) (queued after Windows)
- [#26 Windows clean-install and real-device QA](https://github.com/MasynNay/anything-plays/issues/26) (**in progress**, user says Windows machine is ready; no Windows real-device results yet)
- [#27 GameCube GPU smoothness and endurance](https://github.com/MasynNay/anything-plays/issues/27)
- [#28 License, code signing, provenance and distribution readiness](https://github.com/MasynNay/anything-plays/issues/28)
- Existing [#24 overall 3.0 compatibility tracker](https://github.com/MasynNay/anything-plays/issues/24) remains.

**Windows handoff package:** [Full Windows x64 developer preview artifact
13590164796](https://github.com/MasynNay/anything-plays/actions/runs/42415284318/artifacts/13590164796)
in successful [run 42415284318](https://github.com/MasynNay/anything-plays/actions/runs/42415284318),
source SHA `bbdcdfc9fd971f9a414003eb317746535a909f7e`. GitHub
artifact confirmed not expired. Download artifact ZIP, extract Windows EXE,
install and test ROM switching N64 A→B→A, other available consoles, game
volume, manual buttons, save/reload and GameCube real GPU. Record physical
results in #26; do NOT claim pass before user reports it.

**Important:** roadmap's forward-looking ideas are proposals, not committed
release features. Review statuses only after verified engineering work.


## November 7, 2026 — Linux GameCube permission failure (real-device report)

**Physical testing:** User reports **Windows full preview worked with no
issues in features tried** (partial smoke; not complete console certification).
On Linux the other previously tested consoles seem functional, but GameCube
startup fails with:

```
[Errno 13] Permission denied:
'/opt/anything-plays-30-preview/cores/dolphin-emu/Sys/codehandler.bin'
```

**Root cause:** `CoreSession._make_system_directory` previously returned
the immutable packaged `/opt/.../cores` parent as
`RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY`. Native Dolphin tries opening
`dolphin-emu/Sys/codehandler.bin` for write, which cannot work as a normal
nonroot Linux user after installing a DEB. CI previously exercised a writable
staging directory rather than a read-only extracted DEB and missed this.

**Implemented on 3.0 development branch, pending CI verification:**
- `anything_plays/gamecube_sys.py` stages a validated copy of **all** Sys
  files under `$XDG_DATA_HOME/anything-plays/dolphin-system/<sha256>`
  (or `~/.local/share/anything-plays/dolphin-system/<sha256>`) on Linux.
  Cache fingerprint covers each filename, size and SHA-256; it verifies
  cached bytes, detects tampering, rejects links and oversized payloads,
  uses an exclusive Linux file lock and atomic replacement. Files in the
  user copy are owner-writable; the bundled source, core binary and ROMs
  remain untouched. Other OS paths remain unchanged.
- `anything_plays/gba_emulator.py` passes this new system root to Dolphin
  through its existing Libretro environment callback. GameCube save
  directory remains independently user-writable as before.
- `tests/test_v30_gamecube_linux_writable_sys.py` checks root-owned-style
  read-only Sys, real Libretro GET_SYSTEM_DIRECTORY, writable
  codehandler.bin, unchanged source, save directory separation, cached
  copy repair, symlink rejection and non-Linux compatibility.
- `.github/workflows/v30-full-bundle.yml` runs the new tests and now
  extracts the **actual Linux DEB**, makes the installed tree read-only,
  then runs the real GPU GameCube homebrew playback probe against that
  packaged core. This is a release-gating regression; no fake success.
- GitHub [Linux QA #25](https://github.com/MasynNay/anything-plays/issues/25)
  documents this physical blocker; [Windows QA #26](https://github.com/MasynNay/anything-plays/issues/26)
  records positive partial physical testing.

**Verification pending at time of this checkpoint:**
[full offline build 42418643784](https://github.com/MasynNay/anything-plays/actions/runs/42418643784)
and [app/source regression 42418643783](https://github.com/MasynNay/anything-plays/actions/runs/42418643783).
Do NOT claim a completed Linux fix or link an unverified new installer
until these complete successfully. User should NOT chmod or chown /opt or
run the GUI as root. Stable main/v2.0 remain unchanged.

If stream fails, inspect current workflow run statuses, fix any CI failures,
append verified results and give the user the new Linux full offline artifact
to test on their actual machine.


### Linux GameCube read-only /opt fix — verified milestone

**Linux test installer is ready.** The first verified full offline Linux
artifact is [13591769697](https://github.com/MasynNay/anything-plays/actions/runs/42418643784/artifacts/13591769697)
from [run 42418643784](https://github.com/MasynNay/anything-plays/actions/runs/42418643784).
Its Linux job succeeded, including **real native GameCube homebrew playback
against a read-only extracted DEB**. That earlier run's Windows job failed
only because a newly added unit test compared Windows short-path and
long-path aliases as literal strings; runtime Windows GameCube was unchanged.

Updated the new Windows/macOS compatibility test to compare canonical paths
and updated an old GameCube software test to expect the Linux XDG Sys
copy instead of the old unsafe packaged directory. At source commit
`cf34b7968fab613fb2afc3ee0b0a11501066f9e3`:

- [App regression run 42418828051](https://github.com/MasynNay/anything-plays/actions/runs/42418828051):
  **source-and-gui SUCCESS, 440 tests passed (3 skipped)**, including
  all four new Linux Sys tests; Linux and Windows starter build jobs
  also passed. Remaining Mac starter jobs may still be running.
- [Full offline run 42418828118](https://github.com/MasynNay/anything-plays/actions/runs/42418828118):
  **Linux and Windows full installer jobs SUCCESS**, including new Linux
  Sys unit test and exact **read-only DEB native GameCube playback**
  step 13 (SUCCESS). Intel Mac and Apple Silicon full jobs may still
  be queued; do not claim four-platform final success until confirmed.
- **Preferred newest Linux full artifact**:
  [13592183266](https://github.com/MasynNay/anything-plays/actions/runs/42418828118/artifacts/13592183266).
  Install over the previous preview using
  `sudo dpkg -i 'anything-plays-preview_3.0.0~alpha1_amd64.deb'`.
  Launch app normally as nonroot. Existing user settings and saves are
  outside the installation and should be preserved.
- Linux user has not yet reported physical GameCube retest after installing
  this fixed DEB. Keep [#25](https://github.com/MasynNay/anything-plays/issues/25)
  open until actual user confirmation. Windows was positive partial physical
  QA and is documented in [#26](https://github.com/MasynNay/anything-plays/issues/26).

No `sudo chmod 777` or `chown` of installed `/opt` resources; no
replacement fish logo; stable 2.0 and main unchanged.
