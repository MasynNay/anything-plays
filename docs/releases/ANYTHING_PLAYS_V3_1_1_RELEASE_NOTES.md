# Anything Plays 3.1.1 — Maintenance update

> **Release draft. Do not copy into GitHub Releases or announce it until the
> real v3.1.1 four-platform stable installer and source/notice checks pass.**
> The public [v3.1.0 release](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0)
> remains the current stable download.

Anything Plays 3.1.1 focuses on reliability rather than adding consoles or
changing the creative controls you already use. The app stays free and local,
with 18 classic-console profiles and eleven native emulator core families.

## Improvements

- **More resilient camera controls.** Camera discovery continues past failed
  devices and recovers from capture-driver errors. Lost or unplugged cameras
  correctly release camera-held inputs, update on-screen status and stop
  preview timers safely.
- **More reliable USB/Bluetooth controllers.** A failing controller index
  no longer blocks other available devices. SDL startup errors independently
  close video/joystick/controller resources and can recover on retry.
- **Safer game saves.** RAM saves use unique same-folder temporary files,
  flush data before atomic replacement and tolerate brief Windows sharing
  conflicts with bounded retry. Two separate instances no longer fight over
  the same fixed temporary filename.
- **ROM and cover-art library resilience.** Linked, vanished or
  inaccessible entries are isolated rather than hiding healthy games from
  the library.
- **Longer-session reliability.** Additional virtual-time input/save checks,
  actual timed Linux Tk/SDL/OpenCV UI soak testing and crash/error watchdogs
  detect early GUI exits, swallowed Tk callback failures and unexpected
  resource growth.

## Download (publish these exact names only after the checks pass)

| OS | Stable 3.1.1 update installer |
| --- | --- |
| Windows 64-bit | `AnythingPlaysSetup-3.1.1.exe` |
| Ubuntu/Debian 64-bit | `anything-plays-31_3.1.1_amd64.deb` |
| Apple Silicon Mac | `AnythingPlays-3.1.1-macos-arm64.dmg` |
| Intel Mac | `AnythingPlays-3.1.1-macos-x64.dmg` |

A real public release must also include the matching complete SHA256 checksums,
original third-party source and license materials, and the exact source and
native-package verification manifest. Do **not** distribute filenames ending
in `-qa1` or packages whose application identity is `v311_candidate`;
those are intentionally separate private tests, not stable upgrades.

## Updating from 3.1.0

The final, non-QA 3.1.1 packages deliberately retain the same 3.1 installed
application identity and `anything-plays-31` local preference namespace:

- Windows updates the same Inno Setup application ID as the public 3.1.0.
- Linux updates the existing `anything-plays-31` Debian package, instead
  of installing another separate `anything-plays-311-candidate` app.
- macOS replaces the same `AnythingPlays31.app` bundle using the stable
  `com.anythingplays.release31` identifier.
- Keep your ROM files, saved games and settings when updating. Always keep
  a separate backup of important personal game saves before installation.

3.0 and older experimental builds retain their own distinct settings and
download URLs. The 3.1.0 release remains available if you need to roll back.

## What stays the same

Anything Plays still supports eighteen offline console profiles, Stream Mode
with customizable camera/game displays, optional SDL gamepad support, local ROM
libraries, sixteen appearance themes and camera object tracking. It does not
include commercial ROMs, BIOS files, game recordings or streaming uploads.
Mac installers are ad-hoc signed rather than notarized; unsigned Windows
downloads may show normal operating-system warnings.

## Verification scope and licensing

Version 3.1.1 adds rigorous synthetic driver errors, overlapping save
writers, repeated virtual hotplug and a wall-clock graphical soak. Synthetic
checks do **not** establish that every real webcam, HID device, GPU, retail
game/audio/save session or long physical play session will work. The native
installer acceptance results and any known physical-test limitations must
be disclosed when the actual version is released.

The project source uses MIT licensing. Native emulator cores and
dependencies have independent license terms. In particular, the bundled
Snes9x component has noncommercial distribution restrictions. Retain the
published 3.1.0 original pygame/SDL/mpg123 source companion, corresponding
core-source materials, license notices and version-specific native provenance.
The release is free for noncommercial use. Do not claim an unverified
corresponding-source or redistribution approval.

## Help and reporting

[Report a bug](https://github.com/MasynNay/anything-plays/issues) with
your OS, exact Anything Plays version and steps to reproduce. Remove paths,
game ROM content, camera footage and personal data before attaching reports.
[Website](https://anythingplays.masynnay.com/) ·
[Original 3.1.0 stable download](https://github.com/MasynNay/anything-plays/releases/tag/v3.1.0) ·
[Source project](https://github.com/MasynNay/anything-plays)

**Release checklist:** [V311_RELEASE_CANDIDATE_CHECKLIST.md](../development/V311_RELEASE_CANDIDATE_CHECKLIST.md).
