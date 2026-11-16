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
   images, and the count of unchanged scene ticks.
3. Hold a completely **static scene** for several seconds. The Tk timer can
   refresh near its requested rate without creating extra PIL/Tk images.
   **Changed-image publication FPS may be unavailable** during this period;
   this is healthy caching, not necessarily a slow renderer.
4. Move a tracked object or play a visibly animated scene for 1–2 minutes.
   Refresh checks again. Compare observed refresh tick rate with requested
   rate and inspect the changed-image publication rate, max refresh gap and
   failed tick counter. Neither measurement proves OBS has encoded a frame.
5. Switch output refresh to a different 15/24/30 FPS option, then repeat.
   Measurements **reset on each rate change** rather than blending unlike
   settings. Closing Stream Mode clears its session-only counters.
6. With a real camera, USB controller and game, repeat under ordinary CPU
   usage, then under heavy image composition. Check frame correctness and
   control release alongside the metrics. Keep hardware/device identifiers
   out of any issue report.

## What the metrics mean

| Metric | Meaning | Not proof of |
| --- | --- | --- |
| `stream_target_refresh_fps` | Requested Tk timer refresh option (15, 24, 30) | Physical screen or OBS recording FPS |
| `stream_observed_refresh_fps` | Completed timer callbacks per elapsed tick interval | Every callback producing a changed image |
| `stream_observed_publication_fps` | Changed frames successfully recomposed and published per elapsed *publication* interval | Native emulation frame rate, GPU throughput, webcam exposure rate |
| `stream_refresh_intervals`, `stream_publication_intervals` | Number of intervals behind the respective rates | Reliable FPS estimates with fewer than two observations |
| `stream_published_images`, `stream_unchanged_ticks` | Compositions published versus updates that reused an unchanged scene | Frames dropped by emulator or OBS |
| `stream_max_refresh_gap_ms`, `stream_failed_ticks` | Largest observed Tk callback gap and number of output update exceptions | Precise cause of a stall or physical device fault |

The setup UI says *waiting for two timer ticks* or *waiting for two changed
images* when it has too few observations. A static scene can have a healthy
refresh timer and no changed-image cadence. The tracker has fixed-size
counters and two in-memory monotonic timestamps; it exports only aggregate
numeric values. A user must explicitly press **Copy safe report** to copy
setup measurements to their own clipboard.

## Before claiming a 3.3 speedup

Compare the same host, window size, theme, camera resolution, game state and
15/24/30 setting against a baseline with controlled load. Capture native
input timing separately and externally verify the OBS recording's actual
frame delivery if that is the goal. Repeat 30-minute runs with resizing,
source disconnect/reconnect and stream close/reopen. Hosted synthetic Tk CI
and timer statistics alone cannot certify physical camera/display latency,
Dolphin GameCube FPS or stable long-term streaming on the user's machine.
