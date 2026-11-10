# Anything Plays 3.1 — Controller diagnostics and hardware acceptance

This guide applies to the **3.1 development branch**. It is not a
claim that the public 3.0.0 installer already contains these controls
or that a physical controller has passed every operating-system test.

## Use the controller without a game

1. In the right panel under **CONTROLLER · MANUAL PLAY**, choose
   **Configure…**.
2. Enable controller input. The **LIVE CONTROLLER TEST** panel
   shows recognized buttons and stick directions, even when no ROM
   or emulator is running.
3. When a controller is attached, press A/B, move both sticks,
   squeeze the triggers, and choose **Rescan** to check a fresh
   connection. Keep the real game screen focused when assessing
   gameplay input; switching focus releases held gamepad buttons.
4. Choose **Copy diagnostics**. A confirmation appears in its own
   dedicated line and is **not overwritten** by the live 65 ms
   connection-status polling.
5. Paste the JSON into a support issue or conversation **only if you
   choose to share it**. Anything Plays does not upload it.

The diagnostic contains app version/channel, OS/CPU architecture,
Python, SDL and pygame-ce versions (when available), current
console, currently recognized standard SDL inputs, their mapped
in-game buttons, and whether gamepad, camera controls and embedded
gameplay are enabled. It contains **no ROM filenames, local
filesystem paths, screenshots, camera frames, arbitrary Bluetooth
device names, usernames, hostnames or account identifiers**.

The report also works while no controller is attached; missing
pygame or SDL version fields are recorded as null, not invented.
`physical_device_acceptance_verified` and
`redistribution_approved` are always false in these unreviewed
local snapshots.

## Current reproducible test evidence

- [Four-platform synthetic OpenCV camera and SDL controller
  coexistence](https://github.com/MasynNay/anything-plays/actions/runs/42884824976)
  **PASS 4/4** (Windows x64, Linux x64, macOS Intel, macOS Apple
  Silicon). Real OpenCV image processing uses generated camera frames
  and synthetic SDL controller events through the actual gamepad
  reader, camera mixin, Tk controller routing, and emulated Libretro
  input callbacks.
- The pipeline test covers 18 console profiles, simultaneous
  camera/keyboard/controller input, secondary-color Player 2,
  controller focus loss, hotplug/reconnect, remapped buttons, camera
  disarming, pulse mode, rescan and a 1,000-frame loop.
  A generated image or simulated SDL event is **not** physical hardware.
- [Previously verified installed RC1 GUI startup 4/4](https://github.com/MasynNay/anything-plays/actions/runs/42880420023)
  confirms the older frozen full 18-console QA build opens on all OSes.
  **That older pinned executable predates this newly added copy
  control.** Newer 3.1 source-app artifacts must be rebuilt and
  full-console packages reassembled before claiming this specific UI
  appears in the installable candidate.
- Source tests include an adversarial privacy/clipboard suite:
  unrecognized raw SDL values and arbitrary device strings are
  excluded, malformed settings cannot inject names or file paths,
  copy failures are visible, and the separate confirmation label
  persists while connection status continues updating.

## Physical acceptance still required

For a final 3.1.0 release, a tester with a physical gamepad must
verify actual Xbox/PlayStation or compatible USB and Bluetooth input,
wired-to-wireless transitions, unplug/reconnect, focus loss, sustained
held buttons, controller setup and real game action on supported hosts.

Camera+gamepad simultaneous input must also be tested using actual
camera frames during emulation, with games and saves the tester
has lawful access to. No CI emulation, SDL virtual HID, unit test,
or screenshot can substitute for these device-level checks.

Keep the 3.1 release readiness gates and public release approval
**FALSE** until all relevant acceptance evidence and the outstanding
SDL/LGPL redistribution/source/relinking reviews are completed.
