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

## Distinct camera and console identities

The same visual system now has two restrained physical personalities:

- **Camera monitor:** an optical aperture glyph in the header, an
  **OPTICAL SENSOR** lower-rail engraving, and three small sensor-style
  ticks. The center tick carries the theme accent.
- **Game display:** a game-deck header glyph, a **LOCAL PLAY** lower-rail
  engraving, and five slim ventilation-slot marks. The two outer
  marks are accented.

These are *decorative details*, not fake recording indicators,
controller activity signals or selectable buttons. There are no
new camera permissions or status claims. Camera housing uses the
theme's button surface with an inset field-color header; the game
housing reverses these two surfaces to feel like a separate console.
Both remain completely legible across all sixteen themes.

No faceplate art is drawn over camera frames or emulation pixels.
The new lower rail is only a few pixels tall and is laid out once
when the screen widgets are created. A theme change recolors existing
widgets without rebuilding them.

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
