# Anything Plays 3.1 — Analog input stability

**Scope:** optional manual gamepad input, without modifying emulator cores,
camera tracking, ROMs, or the user's saved control bindings.

## Why this change matters

Before this patch, the SDL gamepad reader used one threshold to both press
and release each analog stick direction and trigger. A value oscillating
around that number could cause an emulated button to flicker rapidly during
ordinary controller movement. Repeated reading of the same signed stick
axis for opposing directions also allowed a driver to return inconsistent
values within a single 65 ms polling pass.

The reader now samples each of the four signed stick axes just once per
poll. It applies **12,000 on press and 9,000 on release** to stick
directions, and **15,000 on press and 11,000 on release** to triggers.
These SDL raw input ranges are not percentages. A previously inactive
direction or trigger still needs to cross the original press threshold;
a briefly fluctuating held input stays steady until it recedes below
its lower release threshold.

## Input safety

Hysteresis latches live only in the connected reader, not in
preferences or ROM save state. They are cleared on controller disconnect,
user rescan, disable and application shutdown. A failed SDL read discards
the incomplete sample before mapping buttons, ensuring that stale
buttons do not remain held.

The camera input pipeline, keyboard control, gamepad-to-console mappings
and user-selected custom bindings remain independent. The unchanged
`InputBuffer` still applies the physical-input snapshot atomically.

## Verification

`tests/test_v31_gamepad.py` checks stick jitter around both thresholds,
single sampling of each signed axis, trigger jitter, and safe latch
reset after disconnect/reconnect. Existing runtime tests also verify
hotplug recovery, settings isolation, native SDL initialization and
gamepad versus keyboard input separation.

This is synthetic and native SDL source validation, **not a substitute
for USB/Bluetooth gamepad acceptance on real Windows, Linux, and Mac
hardware**. All six
[3.1 stable release gates](../config/v3.1-release-readiness.json) remain
unapproved pending physical device, complete source/notice/relinking,
installer and final rollout review.
