# Anything Plays 3.2 — Local setup diagnostics

**Source development, not a public v3.2 release.**

A **Check my setup · camera, game, controller** button now appears in
Safety & Profiles. It opens a non-modal, read-only troubleshooting screen
for four topics:

1. **Camera**: whether cameras have been found, a camera is selected, or the
   local preview is open. Suggests refresh, USB checks and checking OS privacy
   permissions without inventing a specific permission-denial result.
2. **Emulator**: whether a configured native core path currently points to a
   local file. This is not a guarantee of console compatibility or successful
   native loading.
3. **Controller**: whether optional controller input is disabled, waiting for
   a device, or has an attached SDL handle. This is not physical HID testing.
4. **Input backend**: whether the current configuration is routed to the
   embedded emulator or an external backend requiring its own controls.

The user can manually **Refresh checks**, **Copy safe report**, or close the
window. Opening and refreshing it must not start cameras, games, SDL, ROM
scans, update checks or any network request.

## Privacy contract

The clipboard report is constructed exclusively by
`anything_plays.setup_health.build_setup_report` and contains only a known
console ID and four fixed-phrase status/next-action objects.

Excluded from the report:
- ROM files, selected game names, library locations or firmware paths
- Home directories and native emulator paths
- Webcam frames, images, camera device labels and device identifiers
- Controller brand, serial number or Bluetooth identifiers
- Credentials, IP addresses or arbitrary exception text

The clipboard is only written when the user explicitly presses **Copy safe
report**. No upload feature is added.

## Acceptance before merge

- Run Python source and native CI, including pure diagnostics tests.
- Exercise the UI with no camera/controller, an attached camera/controller,
  missing native core and external emulator configuration.
- Confirm small-window scrolling, refresh, clipboard feedback and clean
  shutdown.
- Keep supported 3.1.1 and earlier public release assets unchanged.
- Do not claim that the presence of a core file or an SDL handle constitutes
  full real-hardware certification.
