# Anything Plays 3.2 — Controller and keyboard onboarding

This is a source-only development change, not a published release.

## What changes

The **Controller · Manual Play** panel now includes a full-width
**Guided setup · controller or keyboard** entry point. The non-modal guide
explains connection, testing, and remapping while displaying live status from
the existing SDL reader. It never creates a second SDL instance, starts an
emulator, arms camera input, or uploads device information.

Users can:
1. Connect an Xbox/PlayStation-style compatible controller via USB or Bluetooth.
2. Select **Enable & scan** or **Rescan connected devices**.
3. Press buttons and move sticks to check what the application detects.
4. Open existing **Button mapping** for the selected console, or use
   **Keyboard controls** to configure keyboard input.
5. Copy existing redacted diagnostics if they need help.

The guide explicitly explains cases where a controller has not been detected,
the application is unfocused, or the selected console is using a backend that
does not accept the embedded controller path. A detected SDL controller is
not presented as independently verified physical-controller compatibility.

The status guidance is a pure function in
`anything_plays/controller_onboarding.py`, covered by deterministic unit
tests. The Tk guide is implemented in `ui_controller_guide.py` and is
cleaned up along with other controller resources when the app closes.

## Remaining acceptance

- Run all existing Python and platform-native CI checks.
- Verify opening/closing guide on real Tk across four operating systems.
- Check controller enable, USB/Bluetooth pairing, unplug/reconnect, input
  display, focus loss and safe release on physical devices.
- Check remapping, keyboard fallback and screen layout at minimum window width.
- Keep public v3.1.1 and prior installers unchanged.
