# Anything Plays 3.1 — Refreshed native SDL evidence

**Historical engineering QA, verified November 10, 2026; 3.1 RC1 is now a public prerelease.**
These checks consume the exact latest four-platform full 18-console
RC1 packages from [run 42886791394](https://github.com/MasynNay/anything-plays/actions/runs/42886791394), containing
controller diagnostics and application source `fe0da0b8b5f478cf1172734ef38546c4f1e86229`.
They do not authorize a public stable 3.1 release.

| Native verification | Outcome | Run |
| --- | --- | --- |
| Earlier *whole installed-file hash* original tagged pygame-ce 2.5.8 source / official wheel comparison | PASS audit; Linux **74/74** and Windows **62/62** candidates match exactly; Apple Silicon **0/121**, Intel **0/120** match | [42888996921](https://github.com/MasynNay/anything-plays/actions/runs/42888996921) |
| New signed-Mac original wheel **code-section** audit | **241/241**: 120 ARM and 120 Intel pygame wheel matches, plus ARM OpenCV SDL match. Full binary hashes and legal review remain open. | [Pygame Mac](https://github.com/MasynNay/anything-plays/actions/runs/42925583942) · [OpenCV SDL](https://github.com/MasynNay/anything-plays/actions/runs/42926295393) |
| Signed Mac native-linkage, `codesign`, `otool`, `lipo` and complete SHA-256 inventory | PASS both Mac targets, **121** ARM and **120** Intel signed library files | [42888996877](https://github.com/MasynNay/anything-plays/actions/runs/42888996877) |
| Duplicate-name SDL2 dylib collision audit | PASS detection: Apple Silicon **one** mismatched `libSDL2-2.0.0.dylib` basename with runtime versions 2.32.8 and 2.32.10; Intel **zero** | [42889343414](https://github.com/MasynNay/anything-plays/actions/runs/42889343414) |
| Actual signed native SDL2 library loading + joystick/game-controller subsystem init | PASS both Macs, including Apple Silicon's two libraries loaded in **either order** | [42889343645](https://github.com/MasynNay/anything-plays/actions/runs/42889343645) |
| Native SDL2 virtual joystick attach, press, release, read, and detach | PASS both Macs; both ARM native SDL builds pass in **both load orders** | [42889944381](https://github.com/MasynNay/anything-plays/actions/runs/42889944381) |

## What the new virtual joystick test actually exercised

`tools/probe_v31_macos_virtual_joystick.py` uses the exact **signed
dylibs inside the readonly mounted RC1 DMGs**, SHA-256-verified against
the independently produced current linkage report. Within an isolated
native process, it invokes SDL's actual `SDL_JoystickAttachVirtual`,
`SDL_JoystickSetVirtualButton`, `SDL_JoystickUpdate`,
`SDL_JoystickGetButton` and `SDL_JoystickDetachVirtual` APIs.
A button must read **1** when pressed and **0** after release; the
virtual device must disappear after closing. On Apple Silicon the
sequence is repeated with both SDL libraries in both load orders.
Test output is a per-architecture signed-library QA JSON, retained
for about fourteen days from the run.

This is a genuine native joystick interaction, but the device is
**virtual**, not an Xbox, PlayStation or other physical controller.
It does not test real USB/Bluetooth, camera drivers, live game
behavior, save files, audio, performance or long sessions.

## Corresponding-source limitations still open

The source audit pinned the official pygame-ce Git version and
tagged SDL component source candidates. Linux/Windows native audit
files match official wheel bytes, but the Mac signed/thinned compiled
files **do not** match the upstream universal2 wheel files byte
for byte; neither architecture's signed dylib source provenance
or transformation chain has been fully proven. The five candidate
SDL component source tags and project LGPL notice are not alone
a complete corresponding-source package or verification of
end-user dynamic-library replacement/relinking rights.

**All public-release acceptance flags remain false.** The report
does not replace real camera+physical gamepad trials, games and save
acceptance, full SDL/LGPL review, final stable 3.1 upgrade isolation
and explicit release approval. Public 3.0.0 and 2.0 stay untouched.

Details:
[Source investigation](V3_1_SDL_SOURCE_REVIEW.md) ·
[Release acceptance](V3_1_RELEASE_ACCEPTANCE.md) ·
[Current 3.1 RC QA downloads](V3_1_RC_QA_DOWNLOADS.md).
