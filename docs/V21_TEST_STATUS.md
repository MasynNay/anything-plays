# Anything Plays 2.1 — test branch status

Branch: `feature/v2.1-unified-test`. This is development/test code, **not an official release**. Keep `main` and the published 2.0 artifacts unchanged until 2.1 is validated.

## Capability matrix

| System | ROM types | Backend | Webcam control zones | What testers need |
| --- | --- | --- | --- | --- |
| GB | .gb | Embedded mGBA | Yes | Supplied ROM |
| GBC | .gbc | Embedded mGBA | Yes | Supplied ROM |
| GBA | .gba | Embedded mGBA | Yes | Supplied ROM |
| SNES | .sfc, .smc | Embedded Snes9x | Yes | Supplied ROM |
| NES | .nes, .unf, .unif | Embedded FCEUmm | Yes | Test core included by opt-in test builds |
| Genesis | .md, .gen, .smd, .bin | Embedded Genesis Plus GX | Yes | Test core included by opt-in test builds |
| N64 | .n64, .z64, .v64 | External RetroArch | **No** | Separate RetroArch and Mupen64Plus-Next installation; configure its input |
| GameCube | .iso, .gcm, .rvz, .gcz, .ciso | External Dolphin | **No** | Separate Dolphin installation; configure its input |

The last two systems are launch/library integrations, not yet camera-controlled play. Do not advertise them as having equivalent camera integration.

## Features to validate

1. Keep every 2.0 console and its profile, ROM folder, themes and saves functioning without data loss.
2. Open an NES and Genesis game, test game audio, keyboard controls, camera tracking, button mapping and repeated game switching.
3. Launch N64 through RetroArch and GameCube through Dolphin; check executable discovery, missing installation errors and launch/exit behavior. Manual controls must be configured in those apps.
4. Switch among Windowed, Borderless, Fullscreen and Game only, especially across displays and with Escape/F10/F11.
5. Customize keys per embedded console, reject collisions (including lower/upper case), reset keys and verify persistence after relaunch.
6. Test zone label, tint, contrast, border thickness and centered text, including on the smallest supported window.
7. Confirm camera permissions, stop control behavior and installer launch on Windows x64, macOS arm64/x86_64 and Linux x64.
8. Run the repository unit tests and Tk smoke test. Inspect GitHub Actions build artifacts; a passing workflow alone does **not** prove actual game/camera behavior.
9. Verify license/source records, approved core versions and binary inventory before any public 2.1 release.

## Build and release boundaries

The dedicated workflow `.github/workflows/v21-test-build.yml` is for alpha testing only; it has no automatic public release step. Optional NES and Genesis native cores are gated by `AP_V21_TEST_CORES=1` and refused in release mode until separately approved. There are no ROMs or BIOS files supplied. The main branch README describes 2.0 unless updated as part of a future release.

## Known limitations

- N64/GameCube launch in separate windows and **cannot currently use Anything Plays camera controls**.
- 2.1 platform binaries and real-hardware gameplay need confirmation before calling the release complete.
- Packaged emulator redistribution and third-party notices need review before a production release.
