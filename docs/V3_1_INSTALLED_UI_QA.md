# Anything Plays 3.1 RC1 — Installed desktop UI startup checks

**Result: PASS on all four native operating system targets.**
This is real frozen application startup validation, not an emulation,
physical USB/Bluetooth controller, real-camera or license approval.

[Four-platform installed RC1 UI smoke run 42880420023](https://github.com/MasynNay/anything-plays/actions/runs/42880420023)
completed successfully on November 10, 2026.
The input installer set is the unchanged
[full 18-console RC1 QA run 42865608433](https://github.com/MasynNay/anything-plays/actions/runs/42865608433);
its original source-app revision was pinned to
`86baa6972ed923540f6ab49b636652a0f499d45c`.

| Test host | Full RC1 installed desktop GUI | CI result |
| --- | --- | --- |
| Linux x64, Debian/Ubuntu | Extracted DEB, actual frozen App through Xvfb | PASS |
| Windows x64 | Silent Inno Setup to isolated test directory, real .exe | PASS |
| macOS Apple Silicon | Original signed RC1 .app from read-only mounted DMG | PASS |
| macOS Intel | Original signed RC1 .app from read-only mounted DMG | PASS |

The real application already contains an opt-in diagnostic
`--ap-v30-ui-smoke`; it was embedded in the source-built 3.1 app
and exercised on each installed RC1 package. The name is historical;
it does **not** mean the runtime is the old 3.0 application.

With `AP_V30_UI_SMOKE_CHECK=1` and a fresh report path, the diagnostic
creates the actual Tk root and the full `App`, starts the GUI event
loop, verifies the live window and configured system, then closes.
The independent `tools/verify_v31_installed_ui_smoke.py` gate
verifies:

- frozen executable and real GUI root/App event loop were initialized
  successfully, no exception, active system and 18 console profiles;
- original full RC1 installer SHA-256, source revision,
  11 original-source native cores, QA release flags still false;
- single reviewed, embedded 3.1 RC1 window-build identity in the
  installed app, distinct from old stable or preview settings;
- all real hardware and distribution approval fields remain **FALSE**.

Only an installed package passing these checks receives a separate
`RC1_INSTALLED_UI_RECEIPT.json`. All results are retained as four
temporary 14-day, unreleased QA artifacts in the Actions run, available
through approximately **November 24, 2026**.

This makes the four previously passing installer/core checks materially
stronger: the real desktop application itself can start on every native
target. It still does **not** show a ROM/game was played, controller
buttons were detected from physical hardware, cameras were opened,
save states or audio were exercised, or the libraries have complete
corresponding source/relinking approval.

**Next** is actual physical device and game acceptance, exact
SDL2 native correspondence and LGPL review, then separately built
stable 3.1.0 installation/upgrade identities and explicit release
acceptance. Stable public
[Anything Plays 3.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0)
remains unchanged.
