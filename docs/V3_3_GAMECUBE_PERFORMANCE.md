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
   `retro_run` calls/mean/max cost and P95 frame-time **bucket**,
   GPU readback captures/max/share, >5 ms scheduler deadline misses/resyncs,
   and audio delivery counters.
4. Repeat the same segment with the embedded GameCube preview rate set to
   **20, 30 and 60 FPS** (Performance, Balanced, Quality). The separately
   configured **Stream Mode** supports 15, 24 and 30 FPS; those numbers
   control OBS capture composition, not GameCube's GL readback policy.
   Keep the game, camera setup and resolution stable. After switching rates,
   wait for at least two successful preview publications before interpreting
   the new observed capture cadence. Mode changes reset the cadence interval
   counter to avoid blending different requested rates. Note that neither
   capture rate is the number of game frames emulated per second.
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

## Clock integrity and native gameplay

3.3 discards invalid, nonfinite, negative or hours-long timing samples
(above 3,600 seconds) from the optional native-run, scheduler-wait and
deadline-lateness counters. An invalid or oversized reported core-FPS value
is displayed as unavailable rather than crashing the report. The 20/30/60
FPS readback policy also rejects invalid clock values safely. These
safeguards operate on local *measurement data*: they do not skip a native
Dolphin `retro_run` or modify its audio/input loop.

An ignored timing sample is not evidence of successful gameplay. A
suspend/resume or native graphics fault still requires observation on the
user's actual GPU and speakers.

## Interpretation

| Observed field | Meaning | Important limit |
| --- | --- | --- |
| `native_run_calls`, `native_run_mean_ms`, `native_run_max_ms` | Number and elapsed time of completed native `retro_run` calls | Does **not** measure displayed FPS or completed game scenes |
| `native_run_p95_bucket_code` | Nearest-rank P95 `retro_run` duration bucket, using fixed ranges 0–8, 8–16, 16–25, 25–33, 33–50, 50–100, 100–250, 250–500 and >500 ms (codes 0–8). -1 means no valid native frames | This is an interval, not a fabricated precise percentile or physical FPS; only nine aggregate counters are retained, no per-frame timing history |
| `gpu_readback_calls`, `gpu_readback_max_ms`, `gpu_readback_share_of_native_run` | Synchronous UI preview pixel readbacks and their portion of native run cost | Readback time is **included in**, not added to, `retro_run` time |
| `gpu_readback_timing_samples`, `gamecube_preview_clock_failures` | Number of successfully timed GPU readbacks and rejected optional clock observations | A valid clock on every frame or proof that the physical GPU was slow; an otherwise successful captured frame may have no timing sample |
| `scheduler_late_frames`, `scheduler_late_max_ms`, `scheduler_resyncs` | Delays beyond the native frame deadline and scheduler resets | Missing a deadline does not prove a hardware driver fault |
| `audio_output_device_underflow_callbacks` | PortAudio reported output-device underrun callbacks | A nonzero value signals a scheduling symptom, not its root cause |
| `audio_output_underrun_frames`, `audio_queue_dropped_frames` | PCM output frames filled with silence or dropped from the bounded queue | No recorded waveform or audible-speaker confirmation |
| `gamecube_hardware_frames`, `gamecube_preview_readback_skips` | Game frames published to the embedded UI vs deliberately skipped preview readbacks | Does not mean the emulator skipped `retro_run` or game input |
| `gamecube_preview_target_fps`, `gamecube_preview_observed_capture_fps` | Selected 20/30/60 FPS preview cap versus aggregate **successful frame publication cadence** since the most recent preview mode switch | Observed publication frequency is not native Dolphin emulation FPS or physical monitor FPS |
| `gamecube_preview_cadence_intervals`, `gamecube_preview_max_interval_ms` | Number of measured gaps between published preview images and longest such gap | With fewer than two published frames, observed cadence is zero meaning **insufficient samples**, not a 0 FPS performance result |

Readback diagnostics now distinguish **successful GL pixel captures**
(`gpu_readback_calls`) from **valid readback timing samples**
(`gpu_readback_timing_samples`). An optional clock exception does not make
glReadPixels free and must not be labeled as a zero-cost frame. If captures
were published but none could be timed, **Check my setup** displays
**share unavailable** and **maximum unmeasured** rather than a fabricated
0.0% cost. If only a subset was measured, the percentage is explicitly
a *lower bound* and the report says **partial timing**. The counter
`gamecube_preview_clock_failures` counts rejected optional timer readings;
it does not represent a native Dolphin `retro_run` failure. Failed timing
reads are never counted as deliberately throttled readback skips.

A native GL readback that raises an unexpected extension-defined exception
causes a **controlled stop** of the broken GameCube hardware session; it
cannot cross the ctypes callback and leave the core with a permanently
stale display. The application reports only an allowlisted category or
`UnexpectedError`, never the exception message, custom class name, device
serial or private driver path. A failed GPU driver is **not** silently
restarted or substituted with a software framebuffer.

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

## Private full-native 3.3 Linux packaging bridge (unreleased)

The 3.3 owner QA workflow now has a **separate full-native Linux QA
staging step** after the normal mGBA-only install/startup checks. It
downloads the already published `v3.2.0` Linux installer and
`SHA256SUMS.txt` from the GitHub release and refuses to proceed unless
the published package bytes match that immutable manifest. It separately
validates the exact-HEAD 3.3 mGBA-only candidate receipt and its frozen
private `v33_candidate` identity, then copies **only the previously
published native core and original source-notice bytes** into the new
app without modifying the Python runtime notices.

The output is a different, nonpublic
`anything-plays-33-candidate_3.3.0~fullqa1_amd64.deb`. It keeps its
own Linux install identity, launch path, settings namespace and
native-system/save directories, never the public `anything-plays-31`
identity. The verifier requires all 11 original native core families
and 18 console profiles, checks source-byte provenance again after
repacking, and retains a 14-day QA artifact with a separate SHA256 and
`V33_FULL_NATIVE_LINUX_QA_RECEIPT.json` with
`public_release_approved=false`.

This addresses a significant packaging gap: prior 3.3 installer jobs
could only run GB/GBC/GBA through bundled mGBA. **It does not prove real
GameCube gameplay or audio, hardware FPS, other-host native core
compatibility, asset distribution rights, or an approved public 3.3
release.** The macOS and Windows full-native staged upgrades still
require their own verified workflows and physical-owner acceptance.


## Private full-native 3.3 Windows packaging bridge (unreleased)

Windows x64 has a companion to the Linux 11-core staging path. In a
throwaway hosted Windows QA machine it downloads the public `v3.2.0`
`AnythingPlaysSetup-3.2.0.exe` and its original `SHA256SUMS.txt`,
verifies those exact published bytes, and verifies the current 3.3
mGBA-only candidate and its frozen `v33_candidate` identity. It uses
Inno's real isolated install procedure to extract both applications,
copies the unmodified published original 11-core payload and notices
into the **separately installed 3.3** app runtime, and compiles a second
`AnythingPlaysSetup-3.3.0-fullqa1.exe` under the distinct 3.3 QA AppId.

The new Inno installer is then installed again inside the disposable
runner and its frozen identity plus all native core bytes are rechecked.
The result is a separate, 14-day, **UNRELEASED** full-native Windows QA
artifact with its own SHA256 and `V33_FULL_WINDOWS_QA_RECEIPT.json`.
No public `v3.2.0` program, preferences or files are changed. This
is packaging evidence, not physical-controller, GameCube GPU/audio,
macOS compatibility, redistribution clearance or public release approval.

