# 3.2 guided camera calibration — development notes

**Source-only prototype.** Do not describe this feature as shipped in the
3.1.1 installers or treat simulated detection metrics as real-device approval.

## What the guide does

The **Guided camera calibration…** button appears beside the primary object
color controls. Its non-modal Tk window guides the user through:

1. Selecting and starting an existing camera in the main window.
2. Sampling the primary target from the *main preview* by clicking the object.
3. Moving the object through zones and reviewing detection observations.
4. Saving the selected console's settings, without arming gameplay input.

The guide uses the existing frame and OpenCV tracking results produced by
`CameraMixin.draw_camera`. It does not open a second device or use a
background camera capture, upload video, or keep original frames. The temporary
buffer contains at most **90 pairs of center coordinates and zone names**.

The live panel reports observed target frames, missed target frames, zone-hit
counts and average pixel movement between consecutive detections. These are
descriptive statistics, **not** accuracy or biological identity scores.
Movement is expected from a fish, hand or toy; higher motion is not necessarily
worse tracking.

**Cancel** restores the original primary target color and initial tolerance
and minimum-area values; **Save & finish** persists the selected console's
settings. Switching consoles cancels the guide before the previous console
profile is saved. The guide never re-arms object controls.

## Verification needed

- Pure metric tests: `python -m unittest tests.test_calibration_metrics -v`.
- Full CI and GUI startup on Windows, Linux and macOS.
- Real webcam permission flow, initial camera discovery, hot-unplug, stop/retry,
  image selection behavior, and preview clicking with a non-modal wizard.
- Verify zero or intermittent detections, multiple tracked objects, disabled
  zones, Shuffle, long observations and app shutdown.
- Exercise Cancel, Save, and console switching without losing prior profiles.
- Verify the wizard works at small desktop window sizes and does not trap
  focus or open extra VideoCapture instances.

This is one 3.2 workstream, not a public v3.2 release.
