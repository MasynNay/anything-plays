# 3.2 first-run path — integrated development candidate

**This is an unreleased 3.2 development feature.** The public v3.1.1
installers and update channel have not been changed.

## One clear entrance

A **Get started** button appears beside the Anything Plays title. The
optional, non-modal getting-started window provides a four-step path:

1. **Pick a console:** focus the main-window console selector. The software
   includes no ROMs, proprietary BIOS files, or commercial game assets.
2. **Choose how to control it:** optionally run guided camera calibration.
   Users can skip the webcam entirely for keyboard and compatible controller
   input.
3. **Test inputs:** open the controller/keyboard setup guide. The separate
   controller dialog now includes physical **press-to-remap** input capture
   and keeps button mapping visible in a scrollable area.
4. **Check and play:** open local, privacy-safe troubleshooting. An
   **Open a game…** button provides the existing user-ROM loading path.

Merely opening the launchpad never accesses a camera, starts SDL, starts an
emulator, arms camera input, reads or copies game files, or phones home.
All actions are explicit buttons. Each separate guide remains non-modal so a
user can interact with the existing camera, console and input panes.

## Calibration safety and guidance

The calibration guide monitors the existing camera feed, with at most 90
temporary (center, zone) observations, and retains no video data. Its advice
is based on observed color matches and zone hits, **not** a fabricated
accuracy percentage. It now asks users to collect at least eight frames and
observe the object at least once after sampling before saving.

Closing the application during unfinished calibration cancels it **before**
the normal shutdown profile save. Cancel and switching consoles restore the
exact pre-calibration profile. Saves are never silently approved by closing
a window.

## Controller input safety

When choosing an in-game button and physically pressing a controller
control, the app ignores any button already held before capture started,
rejects ambiguous simultaneous new inputs, requires focus, and suppresses
controller-to-game input during capture **and until release**. Other consoles'
controller mappings are unchanged.

## Release acceptance remaining

- Full source and four-platform synthetic UI/soak tests on the integrated
  candidate.
- Real webcam, permissions, disconnection and 30-minute camera/input tests.
- Real USB/Bluetooth gamepad connection, release and button-capture checks.
- GUI review of all dialogs at compact window dimensions and 16 themes.
- Correct optional webcam path and separate external emulator messaging.
- Preview artifact/install tests without changing the public stable release.
- Third-party redistribution/source and installer license verification.

Only after those gates should this candidate be proposed for a public v3.2
release. Automated synthetic success alone is insufficient hardware evidence.
