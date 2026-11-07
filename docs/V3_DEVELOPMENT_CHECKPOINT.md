# Anything Plays 3.0 — development checkpoint

_Last reviewed: 2026-11-07 UTC. Active branch: `feature/v3.0-unified-test`._

This is an engineering handoff, **not** a release announcement or a promise of
game compatibility. Public stable v2.0 and `main` must remain unchanged until
the 3.0 release gate has objective evidence.

## Product contract

- Support all **18** console profiles from GB through GameCube. **No Wii.**
- All play in the Anything Plays game panel; hardware-accelerated GameCube
  uses embedded Dolphin Libretro, *not* a separately installed Dolphin process.
- One standalone installed package for each OS, containing all **11** required
  native emulator cores and the matching Dolphin `Sys` assets. A connection
  must **not** be required for emulator installation or a first ROM launch.
- Users provide their own lawful game content. Do not distribute ROMs/BIOS.
- After installation, optional reviewed emulator **updates** happen in-app
  with integrity checks, rollback, and no need to restart the entire app.
- Preserve camera controls, console-specific libraries and saves, appearance,
  configurable controls, windowed/borderless/fullscreen options, and long
  unattended uptime. Avoid piling unrelated status text onto the game view.

## Verified work

**Complete offline installer packaging:** GitHub Actions run
[`42349271993`](https://github.com/MasynNay/anything-plays/actions/runs/42349271993)
passed Windows x64, Linux x64, macOS Apple Silicon and macOS Intel. The
internal `v30-full-bundle.yml` lab builds the actual platform packages
with all 11 native Libretro libraries, representing 18 console associations,
plus Dolphin's paired `Sys` content. It verifies installed payloads and
does **not** publish third-party native binaries. A packaging success is NOT
proof that all games boot or that redistributing the native cores is cleared.

**GameCube:** `tools/gamecube-3d-homebrew/source/main.c` now builds an original,
noncommercial GameCube GX 3D animation *and* an original stereo DSP tone
in one executable. `tools/probe_gamecube_app.py` requires continuously moving
3D frames and nonzero native PCM in the SAME embedded Dolphin session.

Observed original-test measurements on the 3D test executable:
- Linux x64: 434 frame callbacks / ~12.28 s = **35.34 FPS**, nonzero PCM verified
  in the native callback (not through physical speakers).
- macOS Apple Silicon: 291 callbacks / ~12.44 s = **23.4 FPS**, nonzero PCM.
- macOS Intel: 151 callbacks / ~12.42 s = **12.16 FPS**, nonzero PCM. Its
  20 FPS compatibility threshold **failed**; do not downgrade the threshold
  merely to make tests green.
- Windows: native accelerated context/packaging smoke has succeeded, but
  full original GameCube GX A/V playback is not verified in CI.
- Across all systems, real retail/homebrew game selection, real speakers,
  save/load behavior, sustained play, and physical camera control need QA.
  The software-only GameCube probe has a known native crash; the release
  runtime is explicitly `embedded-libretro-hardware`.

**Genesis:** The original generated M68000 cartridge still causes native
SIGSEGV inside `genesis_plus_gx_libretro.so` `retro_run()`, confirmed via
gdb and captured in `test-evidence/genesis-original-audio-video.json`.
Changing its invalid bottom-of-RAM supervisor stack pointer to a valid
high-RAM address did not resolve the crash; the signal remains. The isolated
probe now captures the native fault trace and refuses to call a GDB zero exit
a successful emulation. Investigate core input/video callback ABI and the
original ROM opcode/VDP initialization with symbolized native debugging;
do not claim Genesis playback from a green package installer alone.

**Release acceptance:** `config/v3.0-release-acceptance.json` and
`tools/check_v30_release.py` now require 18 bundled console cores,
verified offline payloads for all four platforms, GameCube accelerated
in-panel hardware runtime, complete real A/V/control/saves/stability QA,
and reviewed legal permissions. These requirements deliberately fail closed.

## Important distinction: current test outputs

- `.github/workflows/v30-app.yml` still creates small **mGBA-only starter
  preview artifacts** for basic CI. They are *not* the intended 3.0 release.
- `.github/workflows/v30-full-bundle.yml` builds and inspects **complete
  offline packages** on all four OS targets, but deliberately does not upload
  installers or mark binaries redistribution-approved.
- `.github/workflows/v30-lab.yml` contains exploratory native compatibility
  jobs; experimental failures can be non-blocking to the lab workflow status.
  Read **job-level evidence**, not only the overall green workflow result.
- Changes to the original Genesis test ROM may require updating its
  deterministic header/unit-test contract.
- Recent engineering commits include `673a2d1` (combined GameCube A/V),
  `8bad7dd` (offline release gate and four-platform lab),
  `4b08619` (macOS combined A/V assertion), `f57239b` and `ebe7b1c`
  (Genesis native diagnosis), `0595ac1` (valid 68k stack and crash flag),
  and `ae04869` (update related regression tests).

## Next unblockers, in order

1. Resolve the native Genesis SIGSEGV. Make a real original VDP/PSG ROM pass
   in the production embedded game panel and prove native video/PCM.
2. Measure/fix GameCube performance on Intel Macs and test actual continuous
   GameCube GX A/V + controller responsiveness on Windows. Validate saves.
3. Run real game and original/legal homebrew smoke tests across every profile,
   not just binary presence. Capture video/audio, camera/manual controllers,
   save/restore, and extended memory-growth/crash evidence across each OS.
4. Reconcile alpha UI with the no-first-run-download product contract.
   Missing emulator core in a complete bundle is a packaging defect, not
   an invitation to install external Dolphin/RetroArch. Approved in-app
   **updates** are separate from initial installation.
5. Audit each native core, `Sys` data, Python wheel, corresponding source,
   attributions, OS code signing/notarization and actual public distributable.
6. Only after complete release criteria pass, prepare one professional
   3.0 release per supported OS and retain stable public v2.0 unchanged.

If another conversation is required, open this file and inspect the current
head of `feature/v3.0-unified-test` plus the newest job-level Actions logs
before making changes. Never equate a green builder with playable games.
