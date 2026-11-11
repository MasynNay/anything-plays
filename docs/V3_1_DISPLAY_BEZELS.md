# Anything Plays 3.1 — Studio display bezels

**Development feature: theme-aware camera and emulator screen housings.**
This UI improvement is not yet in the already published 3.1 RC1 installer.

## What the player sees

The left camera preview is now surrounded by a slim framed housing with
an inset video well, a quiet top rail labeled **CAMERA / TRACKING**, and
an accent trim. The right built-in emulator uses the same visual language
with a distinct **GAME / OUTPUT** label. The effect suggests a small
camera monitor and a dedicated console screen without adding distracting
texture, artificial scan lines, heavy shadows or decorative controls.

Both bezels inherit the six colors of the active theme. Dark, light,
Ocean, Retro and every other saved palette update immediately when
the user switches themes. The existing game Canvas also uses the active
theme's focus accent rather than a fixed blue highlight.

**Material contrast follow-up:** The camera retains the original
button-color housing with a field-color header. The game screen now
reverses those two theme surfaces, resembling a separate console
chassis while retaining the same rail, video inset and focus ring.
Actual `STANDBY` / `CAMERA ON` and `NO GAME` / `SESSION`
indicators are not replaced: both remain driven by the verified
camera/game lifecycle and use the correct new housing color
when inactive. All sixteen themes are covered by tests; no new
images, rendering overlays, preferences or timers are needed.

## Distinct visual identities and real activity cues

The next polishing pass gives each bezel its own identity while retaining
a common design language. The camera receives a restrained lens-like
header instrument; the game screen has three narrow console vent details.
They are rendered with native Tk widgets, not heavy images or game overlays.

The adjacent quiet dot and label are driven by real lifecycle events,
never a looping or simulated recording animation:

- **CAMERA / TRACKING:** `STANDBY` until the camera driver actually
  reports an opened capture, then `CAMERA ON`. Stop, failed open and
  disconnected/retry paths clear the active indicator. The label does
  not imply video is saved, recorded or transmitted.
- **GAME / OUTPUT:** `NO GAME` until a game session has been accepted
  by the embedded or explicitly selected external backend, then
  `SESSION`. Unload, restart preparation or failed launch clears it.
  This is not a promise that a retail ROM has rendered correctly.

State changes update the small header widgets only. The video canvases,
tracking coordinates, focus, emulator frame pacing and capture frame
contents remain entirely outside the chrome. Activity state is neither
stored in preferences nor advanced by a periodic Tk timer. Changing
themes preserves the current state and recolors both instruments,
indicators and housings together.

## Behavior preserved

These are *small native Tk frames around* the original Canvas widgets.
No filters are applied to camera images or emulator frames, no ROM
pixels are clipped by drawn overlays, and input is still bound to the
same Canvas instances. Camera click locations remain relative to the
actual video surface. Game keyboard focus, manual play, normal 18-console
video rendering and the separate Game only view remain unchanged.

The bezels use ordinary pack geometry with both canvases filling their
insets. A slight 3-pixel outer rim and 2-pixel screen inset are kept
small for narrow and high-DPI displays. They add no timers, network
resources, image allocations or additional objects per video frame.

## Verification

The new `tests/test_v31_display_bezels.py` covers color slot matching
across all sixteen themes, widget parent layout, camera and keyboard
binding preservation, theme updates, and Game only isolation.
`tests/smoke_gui.py` now checks that the original canvases are children
of their intended bezels, their focus/click bindings are preserved, and
the chrome updates correctly when changing between dark and light
themes. Existing smoke tests also verify 50 camera draws and 100
emulator redraws reuse a single canvas image.

The stable 3.0 release and public 3.1 RC1 remain unchanged until the
subsequent 3.1 installer/release work. Native SDL licensing, real
controller and camera hardware, complete source correspondence and the
final stable release gates remain separate requirements.
