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
at most two cached resized sources, zero callback errors and at most 96 MiB
RSS growth after warm-up. It does **not** run on every push, open a physical camera or load
a commercial ROM. While 3.3 remains in draft PR #246, explicitly opt in by
adding the `v33-long-soak` PR label (create the label once in the repository
if necessary); the workflow reacts to that `labeled` event, not to routine
source changes. Manual Actions dispatch is also defined for when this workflow
is present on the repository's default branch. No build or release is produced.

Neither synthetic run certifies physical devices, Dolphin GameCube hardware
rendering, actual OBS encoding, or stability of a 30-minute **physical**
stream. Real-device acceptance is still required.

## Before claiming a 3.3 speedup

Compare the same host, window size, theme, camera resolution, game state and
15/24/30 setting against a baseline with controlled load. Capture native
input timing separately and externally verify the OBS recording's actual
frame delivery if that is the goal. Repeat 30-minute runs with resizing,
source disconnect/reconnect and stream close/reopen. Hosted synthetic Tk CI
and timer statistics alone cannot certify physical camera/display latency,
Dolphin GameCube FPS or stable long-term streaming on the user's machine.
