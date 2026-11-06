# Anything Plays 2.1 — unified testing build

This branch combines the requested new features **in one test version**. It
does not modify the public [2.0.0 release](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0).

## How to test

Open the most recent successful
[2.1 unified test workflow](https://github.com/MasynNay/anything-plays/actions/workflows/v21-test-build.yml),
select its run, and download the **TEST** artifact for your OS under Artifacts.

These are temporary CI test artifacts, **not a public stable release**.
They have distinct installation identities so stable 2.0 can remain installed:

- Windows installs to **Anything Plays 2.1 Test** under a separate Inno Setup
  AppId and folder.
- macOS creates **AnythingPlays21Test.app** in its own
  `AnythingPlays-2.1.0-alpha.1.dmg`.
- Linux installs `anything-plays-test` in
  `/opt/anything-plays-21-test` and launches as `anything-plays-21-test`.
- User settings live in `~/.config/anything-plays-21-test/`.
  On the first launch the test version copies existing 2.0 preferences and
  profiles **without writing changes back into the 2.0 profile**.

The app never provides or downloads commercial game ROMs or BIOS images.

## What's in 2.1

### Display, controls and overlays

- Windowed, borderless, fullscreen and game-only fullscreen modes.
- F11 toggles fullscreen, F10 toggles borderless and Escape exits a
  fullscreen view and stops object controls.
- Keyboard shortcuts can be changed **per embedded console** in the game panel by
  capturing keys; conflicting or reserved shortcuts are rejected, including uppercase/lowercase collisions. Keys stay
  app-local and do not inject operating-system input.
- Bolder camera control zones: new **Bold** style, centered label option,
  border thickness 2–16 px and stronger readable button labels. Existing
  Outline, High contrast, Minimal, opacity and image overlays remain.
- Legacy 2.0 profiles, separate ROM shelves, live camera color tracking,
  fit-to-grid controls, manual keyboard play, themes and saves remain.

### Embedded native cores

| Console | Engine | Inputs |
| --- | --- | --- |
| Game Boy / Game Boy Color / Game Boy Advance | mGBA | D-pad / A/B / L/R as appropriate |
| Super Nintendo | Snes9x | D-pad / A/B/X/Y/L/R |
| Nintendo Entertainment System | FCEUmm | D-pad / A/B / Start / Select |
| Sega Genesis / Mega Drive | Genesis Plus GX | D-pad / A/B/C/X/Y/Z / Mode / Start |

The NES and Genesis cores are downloaded **only during 2.1 testing builds**
when `AP_V21_TEST_CORES=1`; their exact binary fingerprints, version strings
and source URLs are captured in the test bundle's
`cores/CORE_PROVENANCE.json`. The full upstream FCEUmm GPLv2 and Genesis
Plus GX noncommercial license notices are included in the test packages.
New core binaries are **not yet approved for a public release** and require
pinned source and independent native gameplay verification first.

### External hardware-rendered emulators

| Console | Required separate installation | Behavior |
| --- | --- | --- |
| Nintendo 64 | RetroArch with Mupen64Plus-Next core | Anything Plays scans N64 games and launches RetroArch with the selected native core |
| Nintendo GameCube | Dolphin Emulator | Anything Plays scans discs and launches Dolphin's own GPU window |

Select the external executable (and, for N64, its RetroArch core) if
auto-discovery fails. No external emulator binaries or commercial game files
are bundled or silently downloaded.

**New experimental camera and keyboard bridges:**

- **N64:** Anything Plays writes a temporary RetroArch configuration for
  Network RetroPad input, then sends controller button/axis events to
  `127.0.0.1:55400`. The main-stick camera zones become analog stick input;
  the C-button zones become right-stick input. RetroArch remains a separate
  GPU-rendered game window.
- **GameCube on macOS and Linux:** Anything Plays creates a dedicated 2.1
  Dolphin user folder with a named-pipe controller. The camera zones provide
  A/B/X/Y, Z, shoulder buttons, main stick and C-stick directions. Dolphin
  remains a separate GPU-rendered game window. This isolated test profile
  stores its saves separately from a regular Dolphin installation.
- **GameCube on Windows:** The named-pipe bridge is not supported in this
  alpha. Use Dolphin's own controller settings.
- **Manual keys:** Custom keys work while the Anything Plays game panel has
  keyboard focus; when RetroArch/Dolphin has focus, its own local controller
  mappings apply instead. Camera tracking can continue in the background.

**Do not confuse input integration with video integration.** The N64 and
GameCube graphics are **NOT yet drawn in the Anything Plays game panel**.
A proper hardware-accelerated Libretro frontend would need to own a GPU
context, render the core's framebuffer and manage its lifecycle. The existing
Tk canvas/software-video path cannot do this by itself. No real-GPU game
startup, saved-game, latency or camera compatibility has been confirmed yet.

**Security:** RetroArch's Network RetroPad receiver has no authentication.
Although Anything Plays sends only to localhost, RetroArch may listen on
other network interfaces. The per-launch `--appendconfig` file sets
`config_save_on_exit = false`; don't test this bridge on untrusted networks.
Dolphin uses local named pipes and its separate alpha user profile.

Dolphin accepts fullscreen and borderless display settings at startup.
The embedded Game only view is limited to software-rendered Libretro cores.

## Testing priorities

1. Validate each installer starts without replacing stable 2.0.
2. Start an existing game on each legacy console; confirm save RAM/audio.
3. Use a legally obtained homebrew/test NES and Genesis ROM, check all
   gamepad buttons and save/reload.
4. Select all four view modes and verify F11/F10/Escape behavior, including
   game-only fullscreen.
5. Rebind two keyboard keys and confirm restart persistence, conflict
   rejection and per-console independence.
6. Set Bold camera zones to 8–12px borders and centered text; check target
   tracking on the raw camera feed and readability at real camera distance.
7. Launch N64 through installed RetroArch and GameCube through Dolphin;
   confirm camera and manual gamepad responses, analog directions, launcher
   errors, and release-on-stop. Check GameCube saves in the isolated test
   profile rather than regular Dolphin.
8. Compare FPS, idle CPU, memory usage and latency with stable 2.0.

## Known technical boundaries

This is an alpha. Runtime tests use synthetic camera frames and test cores;
physical webcam/graphics compatibility varies with installed emulators,
controllers and OS permissions. New NES/Genesis binary/source licensing and
cross-platform real-game smoke tests are required before public 2.1.
Do not move or overwrite the published 2.0.0 tag or replace its assets.

The GitHub project remains MIT-licensed only for its original application
source. FCEUmm is GPLv2; Genesis Plus GX is noncommercial; existing
Snes9x and mGBA keep their separate terms. Bundled new test cores are
development artifacts, not a general license to commercially redistribute
third-party emulator binaries.
