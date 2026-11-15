# Anything Plays 3.2.0

**A major usability update** for the free, open-source, camera-and-controller game interface. This public stable upgrade retains the installed 3.1.x application identity and existing local settings instead of installing a second preview app.

## New in 3.2

- Get started onboarding and improved camera calibration with measured tracking stability, cancellation and safe restoration of any unsaved edits.
- Easier keyboard shortcuts and controller remapping, clearer controller setup and disconnected-device feedback.
- Portable single-console and whole-library control-profile backups with validation, import preview, reset and Undo.
- Independent artwork per console, safer profile storage and restoration, and privacy-preserving setup diagnostics.
- Native support package retains the same 11 original Libretro core families from v3.1.1 for 18 console profiles; no new commercial game data, firmware or ROMs are included.

## Install / upgrade

Download the installer matching your system. Windows x64 installs with Inno Setup, Linux x64 with DEB, and Macs with the matching Intel or Apple Silicon DMG. Version 3.2 replaces the **3.1.x stable app**, not a side-by-side preview, and retains the stable settings namespace. Back up your settings, ROM libraries and saves before upgrading, especially if you have custom arrangements.

## Compatibility and limits

GitHub-hosted Windows, Linux, Intel Mac and Apple Silicon QA verified the actual original 3.1.1-to-3.2 installer upgrade paths and synthetic settings and save-memory restoration. Source CI also checked GB/GBC original homebrew battery SRAM through an actual mGBA native cold restart. These checks do **not** certify every commercial game or existing save, physical webcam and gamepad combinations, real speakers or extended gameplay. GameCube has known performance limitations on some systems. Windows builds may be unsigned; macOS builds are ad-hoc signed and not notarized.

## Licensing and source access

The original application is MIT licensed; the eleven separately licensed emulator cores, runtime dependencies and artwork retain their own license terms. This free noncommercial/nonpromotional distribution carries forward the **same native emulator binaries and pinned Python dependencies** as the already public 3.1.1 release, without adding commercial ROMs or BIOS data.

The GitHub source archive for this tag contains the exact 3.2 application and packaging code. The attached original SDL/pygame/mpg123 source companion is unchanged from v3.1.1, and the exact original Libretro emulator sources and original notices are available at https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0-sources . See the attached source-access review and QA manifest for evidence, platform build hashes, remaining coverage limits and instructions for obtaining individual component sources.

Report problems at https://github.com/MasynNay/anything-plays/issues . The older v3.1.1 downloads remain available for rollback.
