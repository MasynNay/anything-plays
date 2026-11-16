# 3.3 — GameCube native GPU and audio field profile

This guide applies to the experimental **3.3 source branch**, not the
already published 3.2.0 installer. It gathers local, aggregate timing from
the embedded Dolphin Libretro worker; it does not send telemetry, record game
frames or audio, benchmark an external emulator, or verify a real speaker.

## Reproduce a local session

1. Build/run the 3.3 development app on the target host. Record the OS, CPU,
   GPU, display refresh rate and whether hardware video acceleration is
   available **in your own private notes**. Do not paste private device IDs,
   system paths, game titles, ROM filenames or captured pixels into GitHub.
2. Start a legitimately obtained GameCube game using the embedded player.
   Open **Check my setup** and select **Refresh checks**. A **GameCube
   native A/V (diagnostic)** section appears when the embedded native
   session has provided an aggregate snapshot. No extra tracing mode or
   network service is needed.
3. Play for at least 2 minutes. Refresh the window and inspect native
   `retro_run` calls/mean/max cost, GPU readback captures/max/share,
   >5 ms scheduler deadline misses/resyncs, and audio delivery counters.
4. Repeat the same segment with the preview rate set to 15, 24 and 30 FPS.
   Keep the game, camera setup and resolution stable. Note that preview
   capture rate is **not** the number of game frames emulated per second.
5. Run a 30-minute session with normal controls and audio. Stop the game,
   reopen/refresh **Check my setup** and inspect the last session's counters.
   Start another ROM only after preserving the first session's report:
   intentionally, starting a new ROM clears the previous aggregate.
6. Repeat on every available real OS/GPU combination and include safe
   disconnect/reconnect, Stop/Restart and save checks. Do not generalize a
   headless Mesa synthetic CI result to hardware accelerated gaming.

Click **Copy safe report** only if you choose to retain the aggregate. The
report is generated from fixed allowlisted scalar counters. The emulator
retains no closed Dolphin session, GL context, ROM handle or audio samples
for diagnostics. Do not share external system-information screenshots
alongside it unless you have reviewed them for personal data.

## Interpretation

| Observed field | Meaning | Important limit |
| --- | --- | --- |
| `native_run_calls`, `native_run_mean_ms`, `native_run_max_ms` | Number and elapsed time of completed native `retro_run` calls | Does **not** measure displayed FPS or completed game scenes |
| `gpu_readback_calls`, `gpu_readback_max_ms`, `gpu_readback_share_of_native_run` | Synchronous UI preview pixel readbacks and their portion of native run cost | Readback time is **included in**, not added to, `retro_run` time |
| `scheduler_late_frames`, `scheduler_late_max_ms`, `scheduler_resyncs` | Delays beyond the native frame deadline and scheduler resets | Missing a deadline does not prove a hardware driver fault |
| `audio_output_device_underflow_callbacks` | PortAudio reported output-device underrun callbacks | A nonzero value signals a scheduling symptom, not its root cause |
| `audio_output_underrun_frames`, `audio_queue_dropped_frames` | PCM output frames filled with silence or dropped from the bounded queue | No recorded waveform or audible-speaker confirmation |
| `gamecube_hardware_frames`, `gamecube_preview_readback_skips` | Game frames published to the embedded UI vs deliberately skipped preview readbacks | Does not mean the emulator skipped `retro_run` or game input |

A high readback **share** suggests the synchronous GL pixel copy is an area
to investigate, but no frame-rate increase is proven unless a controlled
before/after physical-device benchmark actually measures one. If native
`retro_run` cost remains high while readback share is low, the bottleneck
may be elsewhere in Dolphin or the host; do not guess which driver is at
fault. Compare audio symptom counters with actual audible playback during
a real session.

The 3.3 software **camera-to-native-input** probe is a separate opt-in
measurement. See [V3_3_INPUT_LATENCY.md](V3_3_INPUT_LATENCY.md). Neither
probe measures physical webcam exposure or LCD response time.

## Release gate

Before publishing 3.3, require exact-head Python tests/native checks,
four-platform builds and SHA-256 checksums, hardware acceptance of GameCube
GPU/audio/input/save flows, and repeatable latency/performance measurements.
A source-only PR or passing synthetic soak does not satisfy those criteria.
