# Anything Plays 3.1 — Live controller visualization

The controller graphic on the right and in **Configure…** now responds
to actual live SDL inputs. Pressing a face button illuminates that button.
D-pad directions light independently. Both sticks, shoulder buttons,
triggers, Start and Back illuminate their corresponding regions.

The graphic remains **read-only**: the settings dialog still uses
accessible native Tk buttons, labels and mapping controls; the image
itself has no undisclosed click targets.

## Responsive and efficient

Both the compact control card and the larger settings diagram use
the same theme palette. Only known normalized SDL button identifiers
can change their highlights. Arbitrary device names, filesystem paths
or other unexpected inputs cannot change labels or draw extra objects.
The graphic clears previous shapes on every redraw.

The gamepad reader refreshes its raw held-button snapshot on the normal
65 ms loop. This update compares the connection and pressed-input
snapshot with the last rendered state and redraws only when something
changes. Idle polling does not rebuild either Canvas. Disconnecting,
rescanning or disabling the pad clears its live highlights.

## Verification

`tests/test_v31_reactive_controller_art.py` checks all application
themes, face and directional highlighting, untrusted input filtering,
disconnect behavior, repeated redraw object counts and a mocked real
`GamepadMixin.gamepad_tick` loop. The simulation deliberately varies
physical inputs while the connection status text stays unchanged.

This change does not affect keyboard or camera input, emulation,
preferences, ROMs, system networking or installer contents. Live
USB/Bluetooth hardware acceptance and all 3.1 stable release gates
remain separate and unapproved. The previously published 3.1 RC1
does **not** contain these post-RC1 improvements.
