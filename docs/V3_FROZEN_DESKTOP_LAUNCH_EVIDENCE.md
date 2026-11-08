# Actual frozen 3.0 desktop launch on all four supported operating systems

**Date:** 8 November 2026. **Result: 4/4 actual frozen desktop launch passes**, not merely native emulator tests. The app and GUI launched successfully on all four GitHub-hosted runners with no ROMs/BIOS. **Status: research preview / redistribution unapproved**.

## Why this run matters

The earlier complete 18-console, 11-native-core installer laboratories successfully built the binaries and exercised their core libraries, but did not require the frozen PyInstaller desktop application itself to start and initialize a live Tk GUI. [Merged PR #97](https://github.com/MasynNay/anything-plays/pull/97), merge SHA `c24010aca82a61418947238696881ef4adf2fa75`, adds a **cold-start of the real packaged executable** on each operating system. The project UI exercises its real Tk root, full `App` initialization, and GUI event loop, then exits cleanly. The automatic webcam probe is suppressed **only** for this explicitly opted-in, nonpublic test run; normal launches are unchanged.

[Original full Windows/Linux/Mac 8-source-family installer Actions run 42529022383](https://github.com/MasynNay/anything-plays/actions/runs/42529022383) **SUCCESS 4/4**; [source regression run 42529022377](https://github.com/MasynNay/anything-plays/actions/runs/42529022377) **SUCCESS** on Python 3.12, Python 3.13 and native mGBA compatibility. The full original eight-source-family native emulator video/PCM and seven-cycle serial switching regressions passed in the same four-platform run. There are two independent frozen-GUI launch reports per OS, both `passed=true`.

## Verified original evidence downloaded and inspected

Each original workflow artifact was downloaded and its entire ZIP SHA-256 calculated independently in the current development session. Each contains **17 JSON reports**, including both actual frozen GUI reports, core identities, native A/V and serial-switch results, and **no public installer**.

| OS | Original research evidence artifact ID | Original ZIP SHA-256 | Actual frozen GUI SHA-256 |
| --- | ---: | --- | --- |
| Windows x64 | 13637160486 | `6e4298d49dbae46cebd465b1ea1874f76133dea967551af3391dabedced2a4be` | `c18a428786c633fc1313e31ecf5bb4118659bf98e898593c276a5e3c53c1ea33` |
| Linux x64 | 13636219750 | `abc4564d7c4bf803a4b53eea23680e40e5fc075fe42b2b63a47e4e7cc88c16ef` | `380355c749e2d85b3d773292d3d03aee9b20cbeac2c6a35fd9607128ed5a67cd` |
| macOS Apple Silicon | 13636746864 | `2bf46a5df15eeaab74c6c4c00cd9b17b3e80cbe4e4199d1b0506c6fe732e9a21` | `2e9cebb41641473c20f876cfdd07b14ea2ded57f8b10a2e2d06dddf696468cb6` |
| macOS Intel | 13636722029 | `19a4b245a2510703257da79506a01aa1e65cdb7b1dafc7a89d9ee3e114be206e` | `677f0a2afb983e9741d7c72b89a165e349623c27c16775bb1285d8e74d1f2f2b` |

The original `ACTUAL_FROZEN_GUI_STARTUP_UNAPPROVED.json` on every OS reports `passed=true`, `frozen_ui_initialized=true`, `native_exit_code=0`, `original_console_profiles=18`, and a true **child original PyInstaller process** with `actual_tk_window_started`, `actual_app_initialized`, `actual_tk_mainloop_ran` and `frozen_binary`. A separate second launch report `ACTUAL_FROZEN_DESKTOP_UI_LAUNCH_UNAPPROVED.json` also independently reports `passed=true`, `actual_app_initialized=true`, `actual_tk_mainloop_ran=true`, `frozen_binary=true`, `console_profile_count=18`.

## Still not a public binary release

This test **does not prove physical USB-camera function, retail ROM behavior, speaker output, sustained memory/runtime stability, signed/notarized installation, or legal permission to distribute these mixed copyleft cores in a single binary program**. It demonstrates that the packaged desktop app *starts* when invoked by the CI test. It does not validate installing the original DEB/DMG/EXE on a fresh end-user machine or troubleshoot every actual external user's environment.

An offline 3.0 installer remains deliberately unapproved: the production license/source lock, combined GPL2/GPL3 review, complete corresponding source for remaining original N64/Dolphin and transitive dependencies, and owner physical QA are still outstanding. The current public GitHub releases remain v1.5.0 and v2.0.0 only. Do not upload unapproved emulator installers or set approval flags by inference. **No third-party repositories were modified or contacted.**
