# Anything Plays 3.1 — Continuation checkpoint

Verified November 10, 2026. Read this before continuing release or controller engineering.

## Published and tested

- Public 3.1 RC1 prerelease: https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1
- Source code PR #156 merged to main; GitHub publication tag points to main source.
- Four real offline installers: Windows x64, Linux x64, macOS Apple Silicon and Intel.
- Eleven original-source emulator families / 18 console profiles in each RC1.
- Successful source-matched publication workflow: https://github.com/MasynNay/anything-plays/actions/runs/42920357069
- Successful four-OS full installer QA: https://github.com/MasynNay/anything-plays/actions/runs/42905694504
- Successful four-OS installed desktop/settings checks: https://github.com/MasynNay/anything-plays/actions/runs/42906122307
- Successful 180-second real Tk/SDL synthetic camera endurance: https://github.com/MasynNay/anything-plays/actions/runs/42909405091
- Original pygame/SDL tagged source candidates plus SDL notices:
  https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0-rc1 (source companion ZIP).
- Latest stable remains public 3.0.0; 2.0 and 1.5 still public.

## All four operating systems: real source-modified pygame C extension — PASSED

The [Windows original RC1 modified-source Windows CI](https://github.com/MasynNay/anything-plays/actions/runs/42953456034) **PASSED**.
An actual Visual C compiler built an AMD64 CPython 3.13 native
`pygame.base` from the same **changed** pinned pygame-ce 2.5.8
`src_c/base.c` used on Linux and both Macs, with the published
SHA-verified SDL2 2.32.10 developer SDK. The native binary differs
from the original upstream wheel; its new C method was loaded and
executed **from a disposable copy of the actual Windows RC1**.
The copied genuine 18-console frozen desktop successfully started its
Tk event loop and preserved isolated stable 3.0 preferences.

Together with the [Linux source build](https://github.com/MasynNay/anything-plays/actions/runs/42949949019)
and [both Mac source builds](https://github.com/MasynNay/anything-plays/actions/runs/42951159759),
a genuine **source-modified pygame native extension** has now been
compiled and executed on **all four supported platforms**. The
original RC1 installer, signed Mac DMGs, stable 3.0, 2.0 and user
settings were not modified.

These tests cover **one native extension**, not all covered dependencies,
a full GNU LGPL 2.1 Section 6 compliance determination, actual
physical controllers, or final stable 3.1.0 acceptance. [Detailed
Windows and four-platform evidence](V3_1_LGPL_ACTUAL_MODIFIED_PYGAME_WINDOWS_SOURCE_QA.md).

**All six stable-release gates remain false.**

## Genuine source-modified pygame C on both Macs — PASSED

[Source-build and real signed RC1 runtime workflow](https://github.com/MasynNay/anything-plays/actions/runs/42951159759) **PASSED
Apple Silicon and Intel Mac**. Both runners compiled exact upstream
SDL2 **2.32.10** from commit
`5d249570393f7a37e037abf22cd6012a4cc56a71` (matching the
app's bundled SDL), then built the **actually changed** pygame-ce
2.5.8 native C extension with Meson/Ninja. The compiled native binary
differed from original signed wheel code. An isolated disposable copy
of the original signed 18-console RC1 DMG had the extension replaced,
its loader relinked to the existing in-app SDL2, and the changed
binary and app ad-hoc signed and verified.

Actual native CPython 3.13 imported the copied native extension and
invoked its new C method successfully. Both copied original frozen
desktop applications started the real Tk GUI, while 3.0 settings
fixtures remained unchanged. Original DMGs, user data and public
releases were not modified.

Now **Linux x64, macOS ARM and macOS Intel** have real modified-source
pygame C extension compile + native method invocation and frozen-app
startup evidence. **Windows source-modified** builds and complete
LGPL source/relinking, real controller testing, and stable 3.1.0
remain open. [Detailed two-Mac report](V3_1_LGPL_SOURCE_MODIFIED_MACOS_QA.md).

## Verified genuine source-modified LGPL pygame-ce on Linux

[Build and runtime QA](https://github.com/MasynNay/anything-plays/actions/runs/42949949019) **PASSED** against the authentic 3.1 RC1 Linux installer. CI pinned the original pygame-ce 2.5.8 Git commit and LGPL license, patched C source `src_c/base.c` to add a callable method, compiled the changed native CPython 3.13 extension with Meson/Ninja, and swapped its different bytes into a disposable 18-console RC1 app copy. External CPython loaded **the copied app's native file** and invoked the new method; the real frozen RC1 desktop also booted and stable preferences stayed untouched.

Unlike the earlier Linux byte-identical upstream wheel swap, **this proves a changed-source native extension can run**. It does NOT yet prove compiled changes on the other three OSes, actual controller use, all LGPL library replacement/relinking or full corresponding-source/legal compliance. [Evidence and limitations](V3_1_LGPL_ACTUAL_MODIFIED_PYGAME_LINUX_SOURCE_QA.md). All stable 3.1 release approval flags remain false.

## Four-platform original pygame wheel swap and real desktop startup

**All four operating systems passed** limited upstream pygame extension
swap acceptance against genuine pinned full 3.1 RC1 installers. Linux
and Windows had byte-identical original native wheel bytes, and copied
installations passed actual frozen desktop Tk startup plus isolated
legacy settings tests: [two-platform workflow](https://github.com/MasynNay/anything-plays/actions/runs/42937982305).
Apple Silicon and Intel Mac copies replaced differently signed/thinned
compiled base extensions, were ad-hoc re-signed, loaded through the
actual Python native loader and passed frozen GUI startup:
[Mac workflow](https://github.com/MasynNay/anything-plays/actions/runs/42936779875).

These demonstrate practical installation layout and certain native
replacement mechanisms, **not modified-from-source LGPL binaries, complete
corresponding source, legal clearance or final 3.1.0 stable approval.**
[Full limitations and upcoming tests](V3_1_LGPL_FOUR_PLATFORM_UPSTREAM_REPLACEMENT_QA.md).

## New verified macOS LGPL native extension replacement test

The independent [macOS replacement workflow](https://github.com/MasynNay/anything-plays/actions/runs/42936779875) PASSED on both
Apple Silicon and Intel on genuine RC1 builds. A disposable app copy
received the exact SHA-verified official pygame-ce wheel's
`pygame.base` native extension; each copied app was ad-hoc
re-signed, passed a live native loader test, and successfully ran
the **actual frozen Tk desktop GUI smoke**. The readonly original
DMG remained unchanged. See
[step-by-step evidence](V3_1_LGPL_UPSTREAM_EXTENSION_REPLACEMENT_QA.md).

This verifies a practical **upstream ABI-compatible extension swap**,
not a recompiled user modification, complete LGPL compliance or
full native corresponding source. All six final 3.1.0 stable gates
and production release approval remain **false**.

## Verified signed macOS wheel code provenance — November 10, 2026

The original signed 3.1 RC1 Mac installers were independently compared
against official pinned pygame-ce and OpenCV wheels: **241/241** compiled
native `__TEXT,__text` sections matched. Apple Silicon: pygame **120/121**,
OpenCV SDL **1/1**; Intel: pygame **120/120**. These are *code section*
matches, not whole-file binary, corresponding-source or LGPL relinking
approval. [Two-Mac audit](https://github.com/MasynNay/anything-plays/actions/runs/42925583942) · [OpenCV follow-up](https://github.com/MasynNay/anything-plays/actions/runs/42926295393) ·
[Technical details](V3_1_SIGNED_MACOS_WHEEL_CORRESPONDENCE.md).

All six stable 3.1.0 gates and public final-release approval remain false.

## Release issue resolved

GitHub's Actions release creation 403 arose because a workflow token could
not target a feature commit that modified workflow files absent from main.
Use the default branch for unpublished draft creation, merge the exact
tested runtime source, then publish a prerelease targeted at main. This
worked. SHA256SUMS.txt was also adjusted to GitHub's normalized Linux
asset filename (tilde changed to dot), without changing installer bytes.

## Remaining true stable 3.1.0 requirements

- Real USB/Bluetooth controller tests, unplug/rescan/focus behavior and
  saved-game/audio/camera compatibility on final installer hardware.
- Review complete SDL/pygame corresponding-source provenance, transitive
  notices and LGPL native library replacement/relinking instructions.
- Produce actual final 3.1.0 stable installer identity on all four OS
  targets; do not simply rename the RC1 binaries.
- New final stable installer and source receipts with checksums, real
  installed testing, and reviewed release notes.
- Once independently accepted, create stable 3.1.0 release and update
  the latest stable link. Do not overwrite 3.0 or 2.0.

Stable release manifest: config/v3.1-release-readiness.json. All six stable
gates remain false while final work is open. A public RC1 prerelease
does not satisfy stable acceptance.
