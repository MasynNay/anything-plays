# Anything Plays v2.0 — development status

## Included in this source package
- GB, GBC, GBA, SNES selector and per-system ROM library preferences.
- Four appearance themes and expanded label sizing.
- Libretro integration for Gambatte (GB/GBC), mGBA (GBA), and Snes9x (SNES).
- SNES X, Y, L, R inputs and keyboard bindings (A/S and Q/W), in addition to existing inputs.
- Windows, macOS and Linux build scripts now download **all three** platform-specific cores and **fail the build** if any core is missing. The installers bundle the resulting binaries; end users do not download cores.
- Existing v1.5 settings location and profile migration retained.

## Not yet verified / release blockers
- **Not a finished installer.** This ZIP contains source code. Build-time core downloading requires internet access on the CI runner. The execution environment used for these edits cannot access the libretro buildbot, so binaries for all target platforms are **not** included in this ZIP.
- Actual gameplay with Gambatte, mGBA and Snes9x, audio, SRAM saves, and camera input must be tested in packaged builds.
- Native core redistribution licenses and any accompanying notices must be reviewed before public release.
- SNES uses the same configurable zones as other systems; its new X/Y/L/R zones initially overlap at the center and should be positioned in the camera preview or loaded from a custom profile.
- Profiles currently remain user-selected rather than automatically switching by console. Auto-switching requires further work.
- macOS notarization is not configured; the DMG is ad-hoc signed.

## Building
Run the platform build script from the source directory on a supported host with internet access. Each script fetches Gambatte, mGBA, and Snes9x cores before packaging. No core-path selection is necessary for end users.

Do not merge this into `main` or publish a v2.0 release until these blockers are resolved.
