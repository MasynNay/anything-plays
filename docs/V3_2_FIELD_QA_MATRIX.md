# Anything Plays 3.2 — physical-device acceptance matrix

**Scope:** post-release 3.2.0 field verification. This is a test procedure, **not** a claim that any specific machine/device passed. The published v3.2.0 installers and the previous v3.1.1 remain unchanged.

The automated four-platform release checks cover native packaging, application startup, old-to-new installer behavior, synthetic preferences and save state, and targeted native mGBA cold-restart tests. They **do not** verify actual webcam permissions, USB/Bluetooth gamepads, physical speakers, commercial game saves, sustained performance, or every GPU. See [roadmap](ROADMAP.md), [release notes](releases/ANYTHING_PLAYS_V3_2_PUBLIC_NOTES.md), [Linux #25](https://github.com/MasynNay/anything-plays/issues/25), [Windows #26](https://github.com/MasynNay/anything-plays/issues/26), and [GameCube performance #27](https://github.com/MasynNay/anything-plays/issues/27).

## Privacy and safety

- Use only games and media the tester is authorized to use. Never attach ROMs, BIOS files, saves, personal directory listings, or camera frames to an issue.
- Test with camera-safe objects in view; close sensitive applications before capturing screenshots. Avoid collecting identifiable footage.
- Never use an actual valuable save as the sole copy: back it up locally and use expendable test progress.
- A failing test should not be silently skipped or marked passing. Use **PASS**, **FAIL**, **BLOCKED**, or **NOT RUN**; include the reason and a minimal reproduction for each FAIL.
- An automated simulation or CI runner is labeled **SIMULATED/CI**, never **PHYSICAL PASS**.

## Tester record (fill before testing)

| Field | Observed value |
| --- | --- |
| Test date and timezone | |
| 3.2.0 installer filename, SHA-256 and release tag | |
| Install path (redact username/private home path) | |
| OS name/version and architecture | |
| CPU, GPU, graphics driver | |
| Webcam model and connection | |
| Controller model, USB or Bluetooth, driver | |
| Display resolution and scaling | |
| Theme and chosen console/core | |
| Prior installed version (clean, 3.1.0, 3.1.1) | |
| Native / virtual / remote / CI | |

Get the installer SHA-256 using the native OS tool (PowerShell `Get-FileHash <installer> -Algorithm SHA256`; macOS/Linux `shasum -a 256 <installer>`). Compare with the official release checksum manifest. Do not publish local usernames in output.

## Execution and results

Run the cases in order, with a new app launch for cases marked **cold start**. For each case, capture **PASS / FAIL / BLOCKED / NOT RUN**, a short observation, and build ID. If a feature is intentionally unavailable on a device, use BLOCKED and explain why rather than forcing a pass.

| ID | Case | Steps and expected observable result |
| --- | --- | --- |
| INS-01 | Native installation | Run the real downloaded installer rather than unpacking an archive; launch the installed desktop app with its original icon |
| INS-02 | Stable upgrade | On a disposable existing 3.1.1 install, back up local settings; install 3.2.0 into the same stable identity; verify prior themes, layouts, ROM directory selections, and save locations remain usable |
| INS-03 | Clean start | On a clean test user profile, launch without any ROM, camera, or gamepad; application remains usable and reports missing resources intelligibly |
| UI-01 | Small-screen layout | At a practical 820×540 window, open Get started, camera calibration, controller setup, profile backup/import, and Check my setup; all primary actions remain accessible |
| UI-02 | Keyboard navigation | Navigate setup, save, cancel and dialogs using keyboard only; focus and Escape/cancel work without accidental gameplay input |
| CAM-01 | Camera permission | Launch without camera access, then explicitly select/allow a camera; no silent camera start, crash or stuck controls |
| CAM-02 | Calibration rollback | Start guided calibration and change primary color; Cancel restores previously saved values; Save persists only confirmed values after relaunch |
| CAM-03 | Target loss | Move tracked object out of view and back repeatedly; released zone inputs do not remain stuck; reacquisition and display remain responsive |
| CAM-04 | Camera reconnect | With controls stopped, disconnect/reconnect USB camera or revoke/regrant permission; choose source again and verify controlled recovery |
| CAM-05 | Secondary/multiple objects | With explicit opt-in where supported, activate and remove two targets; mapping follows configured behavior without unexpected held buttons |
| PAD-01 | Gamepad discovery | Connect a real controller, open live tester and press buttons/axes; observed IDs correspond to physical input |
| PAD-02 | Mapping persistence | Remap one button; stop/restart app and confirm profile still maps to the selected console |
| PAD-03 | Unplug/focus safety | While held input is active, unplug controller, focus another window and reconnect; there is no permanently held gameplay input |
| PAD-04 | Bluetooth reconnect | Disconnect and reconnect wireless controller; rescan if needed and validate game input, not only tester detection |
| KEY-01 | Keyboard fallback | With camera and controller disconnected, load a legal test ROM and control it from keyboard; focus and shortcuts do not unexpectedly activate controls |
| PRO-01 | Single-console export | Export a mapping/profile; inspect text locally to confirm it excludes ROMs, saves, private paths and camera imagery |
| PRO-02 | Import preview and undo | Change layout, import a valid profile with preview, apply, undo and verify original state; cancel must cause no changes |
| PRO-03 | Invalid file rejection | Import malformed, oversized, unknown-field and mismatched-console profiles; no partial live settings mutation or crash |
| PRO-04 | Cross-platform transfer | Move **only** exported configuration to a different OS and verify corresponding console mappings without private machine paths |
| ROM-01 | Switch and reload | With authorized test content: load → unload → load another title → reload the first across GB/GBC/GBA/SNES/N64 where available |
| SAV-01 | Native SRAM restart | With an expendable game/save, make progress, close app normally, cold-start and confirm the new save state is present |
| SAV-02 | Recovery and failure | Back up expendable saves, induce recoverable failure in an isolated test user profile, and confirm original data remains safe; do not modify live saves |
| GCN-01 | GameCube sustained run | On an actual supported GPU, record ~30 min gameplay with game FPS/frame pacing, audio stability and input response, separately from camera preview FPS |
| STR-01 | Stream Mode | Verify capture resize/crop, annotated camera and game output, theme bezel alignment and absence of unintended controls in capture |
| MEM-01 | Long session | Run ≥30 minutes with repeated start/stop and ROM transitions; record initial/peak/end process memory and whether it grows without recovery |
| EXT-01 | Safe shutdown | Stop input and exit during camera/controller disconnection and during normal gameplay; relaunch without a hung process, audio device or stale input |

## Failure template

```text
Build: v3.2.0 / installer SHA256 [hash]
Case ID:
Status: FAIL | BLOCKED
Host: OS/version, CPU, GPU/driver (no username or device serial)
Devices: webcam/controller model, connection type
Reproduce: 1) ... 2) ... 3) ...
Expected:
Actual:
Frequency: N failures / M attempts
Recovery or workaround:
Attach only sanitized log excerpts; no ROM, saves, camera photos or secrets.
```

## Release decision and follow-up

- Do not rewrite earlier successful **CI** runs into physical acceptance; link exact run numbers as separate evidence.
- Prioritize regressions involving stuck buttons, settings migration or save loss over cosmetic defects.
- Confirm each fixed defect with an automated regression where feasible **and** a retest on the originally failing physical device.
- Use a new reviewed patch release for material fixes; never silently modify the existing v3.2.0 release assets.
- GameCube FPS must be measured from actual emulation/gameplay, **not** camera preview rate. Record audio underruns separately when measurable.

**Completion:** A per-platform record with explicit coverage, reproducible results, and honest unknowns. No platform is labeled fully hardware-certified merely because this checklist exists.
