# 3.3 — camera-to-native input timing (opt-in, source development)

This procedure measures **software handoff stages**, not end-to-end physical
camera-to-display latency. It is intended for the experimental 3.3 source
branch and does not describe a feature in the public 3.2.0 installers.

## Local use

1. Run the development app normally. In **Check my setup**, click **Start
   input timing**. Timing is off by default, and this action does not open
   cameras, start games or enable object controls.
2. Load a supported embedded game using authorized content, select a camera,
   and enable object controls in **Held while visible** mode.
3. Move one or two tracked objects between active input zones for at least
   30 seconds. Use normal gameplay; keep sensitive material out of frame.
4. Open **Check my setup** again, click **Refresh checks**, then **Copy safe
   report** if you want a local aggregate report. Click **Stop input timing**
   to stop collection. Starting again creates a fresh measurement session.

No video frames, pixel locations, button names, ROM paths, usernames, serials,
device names, sample-by-sample timestamps or raw timing traces are retained in
the report. A new observation can supersede an older one that never reached a
native frame. A new frame with an invalid or unavailable optional clock
**discards its predecessor's pending timestamp** rather than attaching the
previous image's measurement to the newer buttons. P1/P2 held-button state
still updates and releases in the same native input buffer snapshot.
STOP also discards pending observations. Counters and histogram
arrays have constant size over long sessions.

**Input safety:** the optional camera-processing clock is read only while
this probe is enabled and the embedded held-button input path is active.
A driver/clock exception, invalid floating-point result, negative timestamp
or enormous integer silently skips *only that timing sample*. Real two-color
tracking, held-button input delivery and P1/P2 release still run normally
without a new pending sample; the next valid clock automatically resumes
measurements without restarting a camera or emulator. These are software
safety guarantees under synthetic tests, not physical response measurements.

## Sleep/resume and clock discontinuities

A host that sleeps or pauses for more than one hour between processing an
already captured frame and handing off buttons, or before the next native
snapshot, cannot yield a meaningful active-play latency measurement. The
optional 3.3 probe now **rejects that sample** and increments the aggregate
`clock_discontinuities` counter, while the next valid camera frame can be
measured normally. It does not insert a false `>500` ms percentile outlier,
retain raw timestamps, or stop P1/P2 held-button delivery and release.
The one-hour cap is a diagnostic sanity boundary, **not** a latency target
or a promise about real webcam/USB timing. Physical suspend/resume and
controller responsiveness still need owner hardware verification.

## What the three time ranges mean

| Stage | Start | End |
| --- | --- | --- |
| `tracking_to_dispatch` | Start of analysis of an already captured camera frame | The latest held-input snapshot is atomically copied to the native input buffer |
| `dispatch_to_native` | Input buffer handoff | The next armed `before_frame` native input snapshot |
| `tracking_to_native` | Start of that camera frame's analysis | The next native input snapshot |

Results are coarse *percentile buckets*, such as `20-33` milliseconds or
`>500` milliseconds, not exact sensor-response measurements. P50/P95 use
the nearest-rank estimate from a fixed-size histogram. `samples` counts
camera observations actually consumed by native snapshots, not all camera
frames; `superseded` counts observations overwritten before consumption;
`discarded_pending` counts pending observations cleared by Stop or explicit
timing disable. Samples include empty held-button snapshots so button releases
are observable. No old timestamps cross a Stop/ROM boundary.

**Not measured:** sensor exposure, webcam `read()` blocking time, display
latency, rendered response, physical audio, native game reaction, pulse-mode
inputs, or external emulator bridges.

**Classic pulse robustness (separate from this probe):** both native
two-player pulses and the optional external-input bridge now guard their
monotonic cooldown clock. A failed or nonfinite clock skips *new* pulses for
that frame without throwing across camera tracking; a reset/reversed clock
allows fresh pulses rather than stranding the cooldown until the old timer
value is reached. Existing finite-duration pulse release, gamepad and manual
keyboard input remain independent of these optional camera clocks. These cases require independent physical
measurement, not just the software probe. Do not compare bucket bounds as
precise measurements or report them as a verified FPS improvement.

## Post-tracking preview failure isolation

Once a camera frame's P1/P2 controls have been delivered, optional
calibration observations, OpenCV contour/zone annotations, OBS mirroring,
and primary PIL/Tk camera resizing may fail without changing those native
held buttons. A broken contour overlay falls back to the raw frame when
available; failed primary preview rendering revokes its previous Tk image
rather than leaving private camera pixels frozen; failed optional stream
mirroring clears its own cached image when possible. The next camera frame
retries. Errors in real capture or **pre-dispatch tracking** still use the
existing fail-closed Stop/disarm logic in the application camera tick.

These guarantees are covered by synthetic tests; they do not establish
physical USB camera recovery or end-to-end sensor latency.

## Stop and USB unplug shutdown isolation

A Stop or unplug keeps the same fail-closed **native camera input disarm**
policy even when a native capture extension throws during `release()`, a
destroyed Tk camera canvas refuses to delete old pixels, or an optional
calibration/bezel/status widget raises during teardown. Each cleanup stage
continues independently: clear the current camera frame, detach the native
capture handle, revoke the OBS-facing cached camera frame, and retire the
reconnect timer on explicit Stop. A failed optional Stream Mode cleanup
cannot prevent the local camera and native input from stopping.

This behavior has synthetic fault-injection coverage. The real camera
driver's permissions, USB reconnect timing and native-controller release
still require physical-device QA.

## Late camera input after Stop / source changes

3.3 now binds each real camera-to-native P1/P2 update (both continuous
**Held while visible** snapshots and **Pulse (classic)** requests) to the
input generation observed **before** checking the emulator's armed state.
Stop, ROM switching and camera disarm invalidate that generation under the
same native input lock that protects both ports and the bounded pulse queue.
If input publication overlaps a Stop, late input from the earlier generation
is discarded instead of reviving its held buttons or queued presses. Normal
keyboard and controller state remains independently managed. Malformed
classic pulse durations, invalid port numbers and unrecognized button names
are ignored rather than crashing an otherwise healthy tracking frame.

The opt-in **Check my setup → Start input timing** report now exposes two
strictly local counts alongside the three software P50/P95 stages:
`late_camera_updates_dropped` counts stale P1/P2 updates rejected after
disarm, and `clock_discontinuities` counts discarded invalid/suspended
timing intervals. The setup window shows these only when nonzero, even if
there are no valid timing samples yet. Both are aggregate integers; no
tracked colors, frame pixels, button labels, file paths, timestamps or
identifiers enter the report. Starting a fresh timing probe resets its
local dropped-update count. No network upload occurs.

This fixes a software handoff race under deterministic thread tests; it
**does not** claim physical camera hotplug/reconnect or native gamepad timing
has been verified. Owner hardware and long-session checks are still required.

## Manual 3.3 acceptance

Capture separate baselines per host/OS, camera resolution, single vs two
colors, normal view vs Stream Mode, active game console, and control mode.
Document software P50/P95, sample count and any superseded/discarded samples.
Repeat a 30-minute run with disconnect/reconnect and Stop; verify no stuck
buttons, memory growth, game crashes or timestamp leak. For a true
camera-to-screen latency result, use an external high-speed camera or another
independent instrument synchronizing the physical object movement and display;
do not label these software timings as a physical latency result.
