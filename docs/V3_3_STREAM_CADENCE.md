# 3.3 Stream Mode refresh and publication cadence

This guide applies to the **3.3 development branch**, not the public 3.2.0
installer. Stream Mode is a separate Tk capture-only window intended for
Window Capture in OBS. Diagnostics run locally, without collecting camera
footage, game content, device names, usernames or individual frame traces.

## Reproducible local measurement

1. Open **Stream Mode** with a locally running authorized game or camera
   source. In its **Stream Settings** choose **15 FPS**, **24 FPS**, or
   **30 FPS** under *Output refresh*. These settings affect the OBS-facing
   window only, not GameCube's separate 20/30/60 FPS preview controls, game
   input processing or native emulation speed.
2. In the main application's **Check my setup**, select **Refresh checks**.
   The **Stream Mode capture cadence** section shows your chosen refresh
   target, the achieved **Tk refresh tick cadence**, the number of refreshed
   images, the count of unchanged scene ticks, and the bounded **Stream
   composition P95** time. Composition time is measured from the start to
   the completion of the optional Tk output update, including a cached
   unchanged-image check; it does not measure OBS encoding time.
3. Hold a completely **static scene** for several seconds. The Tk timer can
   refresh near its requested rate without creating extra PIL/Tk images.
   **Changed-image publication FPS may be unavailable** during this period;
   this is healthy caching, not necessarily a slow renderer.
4. Move a tracked object or play a visibly animated scene for 1–2 minutes.
   Refresh checks again. Compare observed refresh tick rate with requested
   rate and inspect the changed-image publication rate, max refresh gap and
   failed tick counter. Compare composition P95/mean/max and the number
   of ticks above the selected 15/24/30 FPS render-time budget. Neither
   measurement proves OBS has encoded a frame.
5. Switch output refresh to a different 15/24/30 FPS option, then repeat.
   Measurements **reset on each rate change** rather than blending unlike
   settings. Closing Stream Mode clears its session-only counters.
6. With a real camera, USB controller and game, repeat under ordinary CPU
   usage, then under heavy image composition. Check frame correctness and
   control release alongside the metrics. Keep hardware/device identifiers
   out of any issue report.

## Stalled camera preview protection

A USB webcam may still report itself open even when it has stopped supplying
frames. The **optional OBS-facing camera picture** is considered stale after
more than 3 seconds without a successful snapshot. At that point, Stream Mode
drops the cached private image and shows **Camera waiting** until a fresh
annotated source frame arrives. Fresh frames resume automatically without
restarting the camera or changing native player input. This is not a claim that
the camera device disconnected, and does not change webcam tracking.

Intentional static reference images do **not** expire; they are not incorrectly
labeled live footage. The safe report includes only the numeric count
`stream_stale_camera_clears` for the current stream session, not a timestamp
history or any captured pixels.

## RGB resize and clock-failure safeguards

In 3.3, a freshly animated game/camera frame that already uses PIL RGB is
resized directly instead of first allocating a second full-sized RGB copy.
If that source already fits its output panel, neither a color conversion nor
a resize runs. Unchanged image fits are cached for only the two active
sources. All original nearest/bilinear scaling decisions and pixel output
remain unchanged. This avoids avoidable work but is **not** a verified FPS
increase until measured on real hardware.

The optional OBS-facing camera frame also rejects invalid monotonic clock
readings without interrupting tracking or native control updates. If the
clock itself fails while a prior webcam image is displayed, the old private
image is revoked until a fresh valid snapshot can be captured.

## Instant settings refresh without discarding fresh webcam pixels

Changing **output FPS** marks the *next optional camera conversion*
as immediately due. Styling-only changes (theme, layout, border color or
width, panel sizing) instead reuse the last successful annotated camera
pixels and recompose the OBS canvas directly. This avoids extra BGR-to-RGB
conversions on every slider step even when the 15/24/30 FPS preview
throttle would otherwise skip the frame.

The previous successful webcam timestamp remains intact while the
current OBS preview is within its privacy window; styling changes cannot
accidentally make a live frame appear untimestamped. After a genuine FPS
change, the next annotated tracking frame publishes immediately at the
selected rate, then normal throttling resumes. The existing three-second
live-camera stale-image revocation still applies if no new image arrives.
No tracking, native input or audio loop is restarted.

### Fail-closed optional resize-cache errors on camera disconnect or Stream close

Stream Mode uses a bounded first-party cache to reuse fitted GAME and CAMERA
PIL pixels. During camera unplug or a Stream Mode close, the preview cache
is optional: a destroyed or customized native cache may fail while clearing
a channel. The webcam disconnect path now **drops the entire cache reference**
if eviction fails, clears its camera snapshot/timestamp and invalidates the
OBS composite. The same error cannot prevent the Stream Output window from
closing or its image references from being revoked. Repeated camera-off
notifications remain idempotent, and active native game input/controls are
not affected.

The Stream Mode local diagnostics report now only accepts the two aggregate
cache counters from the exact built-in `StreamPanelResizeCache`. Arbitrary
cache plugin metrics and exceptions cannot enter the diagnostic clipboard or
`Check my setup` display. If built-in cache reporting fails, the regular
Tk cadence measurements remain available. Regression tests cover camera
disconnect, hidden-only cache errors, safe report generation, and optional
window teardown. Synthetic tests do **not** verify actual webcam hotplug
or OBS encoder output.

## Repeated camera-off signals and shutdown timer safety

Repeated optional Stream Mode camera-off notifications now **leave an
already-empty camera preview unchanged** instead of bumping its image
revision and forcing needless composition of an unchanged game-only scene.
A prior camera image, timestamp, outstanding forced refresh or cached
fitted camera image is still invalidated and cleared immediately. This is
only an OBS-facing optimization; it does not suppress actual camera
reconnect attempts, native held-button release, or game/audio rendering.

Deferred Stream Settings preferences saves are optional UI work: if Tk
is already tearing down and cannot schedule a save callback, the exception
does not escape the settings handler or change the emulator/camera state.
Normal valid settings saves and window-close flush remain unchanged.

## Border-color dialog reuses the existing camera preview

Picking a new border color or resetting it to the theme accent now
changes only the composition of the output canvas. Neither action
forces another BGR-to-RGB webcam conversion or discards the previous
successful frame timestamp. Re-choosing the same color (including
different letter case), resetting an already-default border, canceling
the picker, or closing its parent during selection causes no redundant
output work. The camera, controller and native emulator keep running.

## Redundant controls and destroyed-window recovery

Stream Settings ignores callbacks that do not change a validated setting,
rather than scheduling an unnecessary canvas recomposition or disk write.
If a layout switch races with destruction of the OBS output window,
geometry adjustment is best-effort; the selected layout can still be
stored and the main Tk event loop is not interrupted by its stale window.
Unexpected errors from the separate settings-variable wrapper are also
isolated, without forwarding private error text. This does not alter
emulator input, the live camera reader, or audio.

## Uncaptured Stream Settings status is not an output dependency

The separate Stream Settings status label is **best-effort only**.
A Tk widget destroyed while streaming, or an unexpected error from a
third-party variable wrapper during a status read/write, cannot be counted
as an output failure or blank a healthy capture canvas. No raw exception
messages, device serials or local file paths are forwarded.

## Session-wide compositor fault/recovery metrics

The safe local report now includes `stream_session_faults`,
`stream_session_recoveries` and `stream_recovery_pending`. These are
session-only aggregate counts that **do not reset** when switching the
15/24/30 FPS output cap, unlike intentionally reset per-rate cadence
measurements. A recovery is acknowledged only when a new image is actually
published after a fault; an unchanged tick cannot claim one. Closing and
reopening the output resets all three counters. No frame, clock history,
camera identity or filesystem path is retained.

## Stream compositor failure and privacy recovery

If a PIL image conversion, Tk photo update or native preview wrapper fails,
the **optional OBS-facing canvas is blanked immediately** instead of leaving
the previously captured private webcam/game pixels frozen on screen. A
fixed-category status is shown in the separate uncaptured Stream Settings
window and the compositor retries at most once per second. This recovery
never stops the original webcam tracking or native emulator/input/audio
sessions. After the error clears, the next valid image recreates the one
canvas image item.

An invalid, missing or exceptional performance clock is also treated as a
failed optional update; it does not fabricate a zero-duration frame or let
the failed timer escape a Tk callback. The bounded failure count can advance
even when no clock sample exists. An invalid camera freshness clock **or a missing/corrupt timestamp for
a cached live camera frame** clears only the optional OBS camera preview.
An open device alone does not authenticate an old frame's age. Static
reference images deliberately bypass webcam timestamp expiry; the actual
camera tracking and native game input are unaffected.

These safeguards prevent **application-retained** stale Stream Mode imagery,
but OBS itself can retain the last captured frame depending on its capture
configuration; physical OBS tests remain mandatory.

## What the metrics mean

| Metric | Meaning | Not proof of |
| --- | --- | --- |
| `stream_target_refresh_fps` | Requested Tk timer refresh option (15, 24, 30) | Physical screen or OBS recording FPS |
| `stream_observed_refresh_fps` | Completed timer callbacks per elapsed tick interval | Every callback producing a changed image |
| `stream_observed_publication_fps` | Changed frames successfully recomposed and published per elapsed *publication* interval | Native emulation frame rate, GPU throughput, webcam exposure rate |
| `stream_refresh_intervals`, `stream_publication_intervals` | Number of intervals behind the respective rates | Reliable FPS estimates with fewer than two observations |
| `stream_published_images`, `stream_unchanged_ticks` | Compositions published versus updates that reused an unchanged scene | Frames dropped by emulator or OBS |
| `stream_max_refresh_gap_ms`, `stream_failed_ticks` | Largest observed Tk callback gap and number of output update exceptions | Precise cause of a stall or physical device fault |
| `stream_render_samples`, `stream_render_mean_ms`, `stream_render_max_ms` | Count and aggregate measured time for optional Tk output updates | Camera tracking latency, native emulator frame cost or OBS encoder work |
| `stream_render_p95_bucket_code` | Nearest-rank P95 render-cost range: codes 0–10 map to 0–5, 5–10, 10–16, 16–25, 25–33, 33–50, 50–67, 67–100, 100–200, 200–500 and >500 ms; -1 means insufficient samples | An exact percentile or physical display frame rate |
| `stream_render_over_budget_ticks` | Number of optional Tk output updates whose measured composition work exceeded the selected output frame interval | A count of frames dropped by OBS or the game |
| `stream_resize_cache_hits`, `stream_resize_cache_misses` | Number of unchanged fitted game/camera panels reused versus rescaled, bounded to two cached sources | A guaranteed FPS increase or persistent disk cache |
| `stream_stale_camera_clears` | Number of stale optional camera pictures removed from a current Stream Mode session | A device-disconnect or tracking-failure count |

The setup UI says *waiting for two timer ticks* or *waiting for two changed
images* when it has too few observations. A static scene can have a healthy
refresh timer and no changed-image cadence. The tracker has fixed-size
counters, a fixed 11-bin composition histogram and two in-memory monotonic
timestamps; it exports only aggregate numeric values, not a frame-time trace. A user must explicitly press **Copy safe report** to copy
setup measurements to their own clipboard.

## Real Tk synthetic Stream Mode endurance gate

The experimental [3.3 Stream Mode CI workflow](../.github/workflows/v33-stream-mode-soak.yml)
runs the **actual desktop Tk window** under a Linux virtual display for
180 seconds using changing synthetic camera and game frames. It requires
successful compositions, continued Stream Mode timer activity, no callback
exceptions, at most one image item per canvas, bounded pending Tk callbacks,
and no more than 96 MiB of resident growth after warm-up. The evidence report
holds only counters, memory usage and diagnostic status, never screenshots.

For a local equivalent on a machine with a display:

```bash
PYTHONPATH=. python tests/soak_gui.py --seconds 180 --enable-stream \
  --max-growth-mb 96 --report stream-soak.json
```

The automated workflow also runs a separate **45-second actual Tk**
transition/fault-recovery check. It drives the **real traced Stream Settings
controls**, not direct internal option writes: 15/24/30 FPS, both layouts,
screen swapping, themes, border thickness and game size are exercised while
synthetic frames continue to be processed. It also injects one deliberate
compositor exception and proves the canvas blanks and resumes without an
unhandled Tk callback. It is separate from the unchanged-image/zero-fault 180-second
baseline. The final stream rate is allowed to be **15, 24 or 30 FPS** in
a rotating-rate stress run; the normal 180-second baseline still requires
exactly **24 FPS**. Neither uses physical hardware.

The existing standard desktop soak still runs **without** `--enable-stream`
and remains unchanged. The shorter workflow additionally verifies that the
new source resize cache never holds more than **two fitted panels**, regardless
of game or camera frame count.

A separate [opt-in 30-minute Stream Mode endurance workflow](../.github/workflows/v33-extended-stream-mode-soak.yml)
is now available on the development branch. It uses the same real Tk window
and moving **synthetic** camera/game pixels for 1,800 seconds. During the run,
it also cycles 15/24/30 FPS, both screen layouts, window sizes and screen
swapping, while repeatedly clearing/reacquiring the optional camera preview.
It requires successful recurring transitions, bounded canvas items/Tk jobs,
at most two cached resized sources, zero unhandled Tk callback errors and
at most 96 MiB RSS growth after warm-up. The run deliberately injects **one**
synthetic compositor exception and confirms that the actual capture canvas
becomes blank, the failure counter increases and a fresh frame is published
again after the bounded retry. It does **not** run on every push, open a physical camera or load
a commercial ROM. While 3.3 remains in draft PR #246, explicitly opt in by
adding the `v33-long-soak` PR label (create the label once in the repository
if necessary); the workflow reacts to that `labeled` event, not to routine
source changes. Manual Actions dispatch is also defined for when this workflow
is present on the repository's default branch. No build or release is produced.

Neither synthetic run certifies physical devices, Dolphin GameCube hardware
rendering, actual OBS encoding, or stability of a 30-minute **physical**
stream. Real-device acceptance is still required.

## Linux frozen 3.3 candidate startup QA (still synthetic)

The 3.3 owner-QA installer workflow now *executes the frozen Linux application*
extracted from its actual isolated Debian package under Xvfb. A fresh
disposable HOME contains dummy canaries for the 3.1/stable and 3.2 preview
settings folders. The frozen app must prove its immutable
`v33_candidate` identity and private `anything-plays-33-candidate`
namespace, start a genuine Tk event loop with gameplay and camera controls
disarmed, open and customize the separate Stream Output window using
synthetic camera pixels, and close its windows and frame timers cleanly.
The verifier also confirms the older settings canaries are byte-for-byte
unchanged. Only boolean outcomes are retained in
`V33_FROZEN_GUI_RECEIPT.json`.

This strengthens static installer identity/checksum verification but
**does not** launch any real ROM, Dolphin core, physical camera, controller,
speaker or OBS encoder. Linux runner startup is not evidence that the
installer works in a user's desktop session. Actual Windows/macOS installation
and all four-platform real hardware acceptance remain independent release
gates.

## Windows and macOS frozen 3.3 candidate startup checks

The private candidate installer workflow also performs isolated native-OS
startup checks on **Windows x64** and **both macOS architectures**, when
those hosted runners are available. Windows executes the real private Inno
installer inside a throwaway CI directory and then launches the installed
`AnythingPlays.exe`. macOS verifies the signed candidate app on a
read-only mounted DMG and launches its actual `Contents/MacOS/AnythingPlays`
binary. Both must start real Tk, confirm the immutable
`v33_candidate` identity, keep camera/controller/native-game input
disarmed, render and close a synthetic Stream Output window, and preserve
byte-identical dummy 3.1/3.2 settings canaries. A bounded 120-second launch
timeout prevents an unresponsive window from hanging CI indefinitely.

The same `V33_FROZEN_GUI_RECEIPT.json` verifier runs across Linux,
Windows and macOS, with an independent installer hash and mGBA-only identity
receipt for each host. Raw native crash output, webcam images, ROM paths and
device identifiers are not retained as acceptance artifacts. This is
automated frozen-app **hosted-runner** QA: it does not grant public core
redistribution rights or prove real speakers, cameras, controllers, GameCube
hardware, OBS recording, or owner-installed desktop compatibility. Each
platform's CI job is only considered passed when its own frozen test and
receipt succeed.

### Native core endings cannot retain old game pixels in Stream cache

A game may exit or fail on its own without the user invoking Library Stop.
Stream Output already hides the old game image when `emu.running` becomes
false; 3.3 now also immediately evicts the fitted **GAME** image and
underlying PIL source from its independent resize cache on that transition.
It leaves the cached **CAMERA** image and live camera snapshot untouched,
and keeps successful game frames cached while a native core is running.
A misbehaving optional cache is dropped without breaking OBS capture or
showing raw driver exception text. Synthetic tests cover a core finishing
without an unload, the still-live camera, invalid cache wrappers and
active-game fit reuse. Native GameCube, controller, microphone and physical
OBS recording still require separate owner acceptance.

### Source-generation fence before publishing the OBS composite

Tk Stream Mode deliberately converts native game pixels and resizes the
game/webcam panels outside the emulator's frame lock. A Stop, ROM switch,
camera disconnect, settings edit or Stream window close can arrive while
PIL is still processing the earlier sources. 3.3 now checks the native
frame serial/Stop signal **after conversion**, and checks the game, camera
and output-window generations **after composition but before touching the
OBS-facing Tk PhotoImage**. Superseded frames are discarded rather than
published. A changed camera/game source selectively evicts stale fitted
cache pixels while leaving the unrelated source intact; if an optional
cache fails, its entire reference is dropped. Closing the output during
composition cannot recreate the retired Tk image. Source comparisons
are short and do not hold a native frame lock across PIL or Tk calls.
An extra post-conversion target-window check prevents an in-flight copy
from touching a newly reopened Stream window. If Stop or core exit occurs
during the earlier RGB-to-PIL conversion, the previous OBS PhotoImage is
also revoked **immediately**, not just the attempted new copy. The
camera's independent cached fit is preserved. If only a newer healthy
frame serial arrived, the old photo can stay visible until the next
refresh rather than being unnecessarily blanked. Added regression tests
for prior-photo Stop revocation, normal next-frame continuity, and
window-close/reopen during conversion.

Synthetic adversarial tests exercise Stop during game conversion, Stop or
camera disconnection during PIL composition, a settings change and a
closed window. The fence is not a replacement for owner physical OBS
recording, camera hotplug and 30-minute GameCube QA.

## Collect privacy-safe Stream Mode QA evidence

While **Stream Output** and **Stream Settings** are open, use
**Copy safe diagnostics** in the uncaptured Settings window. Paste the
clipboard JSON into a private QA note or [acceptance issue #247](https://github.com/MasynNay/anything-plays/issues/247)
after reviewing it. The button copies allowlisted finite aggregate counters:
Tk target/observed refresh, changed-image publication, compositor render
cost and fixed-bucket P95, failure/recovery counts, cache hits and
camera-preview privacy clears. It never sends data over the network,
saves a file automatically, or includes camera pixels, device IDs, full
frames, ROM filenames, paths or exception strings. Clipboard integration
is best effort and copying is unavailable when Stream Output is closed.

The JSON intentionally labels its scope as **Tk UI refresh and changed-image
publication**, not OBS encoder FPS, native emulation FPS, real camera sensor
FPS or hardware input latency. Its hardware-verification fields remain
`false` even when the tester has devices connected, because the local
aggregate by itself cannot prove those physical checks. Capture physical
acceptance separately: host/OS, controller and webcam model (only if
comfortable sharing), OBS capture-source settings, OBS dropped-frame
statistics, audio, disconnect/Stop behavior, a real 30-minute elapsed
session and any visible problems. Do not paste private video, ROMs,
camera identifiers, driver dumps or OS home directory paths in GitHub.

## Before claiming a 3.3 speedup

Compare the same host, window size, theme, camera resolution, game state and
15/24/30 setting against a baseline with controlled load. Capture native
input timing separately and externally verify the OBS recording's actual
frame delivery if that is the goal. Repeat 30-minute runs with resizing,
source disconnect/reconnect and stream close/reopen. Hosted synthetic Tk CI
and timer statistics alone cannot certify physical camera/display latency,
Dolphin GameCube FPS or stable long-term streaming on the user's machine.
