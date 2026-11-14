# 3.2 first-run path — integrated development candidate

**This is an unreleased 3.2 development feature.** The public v3.1.1
installers and update channel have not been changed.

## Run the source-only 3.2 preview (no installer)

Check out the **feature/v3.2-integration** branch, install the regular Python
dependencies documented in the repository, then run:

```bash
python run_v32_preview.py
```

Do not use `python app.py` as the 3.2 preview entrypoint: that old entrypoint
intentionally retains the 3.1 source preview identity for compatibility.

This launcher explicitly selects the **3.2 development preview** identity
and creates only `~/.config/anything-plays-32-preview/`, with no automatic
migration from stable 3.0/3.1/3.1.1 or former release-candidate settings.
It includes no game ROMs or proprietary BIOS. It does not publish releases,
open webcams or scan controllers merely by selecting a settings channel.
A frozen release package cannot switch identity via that environment flag.

No public v3.2 installer exists yet. The preview is unverified with real
camera/gamepad hardware and should not be presented as release quality.

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

## Automated real Tk setup smoke

The integration branch now adds `tests/smoke_v32_gui.py` to the standard
source-check workflow, executed under Xvfb on Python 3.12 and 3.13. Unlike a
pure source-contract test, this starts the real App and Tk root with temporary
preferences, opens the Get started launchpad, calibration wizard, controller
helper and setup troubleshooter, checks that calibration cannot arm object
controls, copies and checks a redacted diagnostic report, and closes each UI.
Device enumeration is suppressed and no physical hardware is used.

The smoke is an **automated GUI lifecycle check only**; it is not evidence
that USB cameras, Bluetooth controllers or commercial game files work.

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
