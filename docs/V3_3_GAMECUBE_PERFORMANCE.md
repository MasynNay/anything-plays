# 3.3 — GameCube native GPU and audio field profile

This guide applies to the experimental **3.3 source branch**, not the
already published 3.2.0 installer. It gathers local, aggregate timing from
the embedded Dolphin Libretro worker; it does not send telemetry, record game
frames or audio, benchmark an external emulator, or verify a real speaker.

## Bounded native GPU negotiation history

For GameCube, the native Libretro core may request a hardware render
context again during a driver failure or reinitialization. Anything Plays
now preserves at most **16** recent allowlisted scalar request records,
with a separate total request count. It prints only the first 16
negotiations to local diagnostic logs. This prevents a broken core from
producing unbounded Python records or repeated log output during a long
session while keeping the latest negotiation outcome available for
development debugging. The hardware negotiation itself is never skipped
or throttled; valid context requests still reach the real GL backend.
A broken or closed local stdout stream is also ignored for this optional
logging: neither an accepted nor a rejected GPU request may raise merely
because its diagnostic print failed during the native Libretro callback.

If the native GL host itself raises while negotiating a hardware context,
the callback now returns a normal rejected result, sets the session Stop
signal, and preserves a fixed safe error category. Native driver messages,
paths and exception types are never copied to the app-facing negotiation
error. An ordinary `False` return (unsupported context) remains a normal
rejection without an invented fatal driver failure. Regression tests cover
three native host exception types, ordinary rejection and existing-error
precedence. This is callback-safety work, not proof of physical GPU
compatibility.

Synthetic tests exercise 10,000 repeated native-pointer requests, a
late rejection and a null callback. They cannot substitute for a real
GameCube GPU/driver endurance run.

## Safe GameCube native startup and teardown errors

The GameCube worker now produces **fixed, path-free error statuses** for
driver, GPU-context, native-core and ROM startup failures. Previously the
general emulator worker included `str(exception)` in the user-facing
status, which on some third-party driver failures can contain private
ROM paths, device IDs or local account folders. GameCube preserves a
fixed actionable OpenGL 3.3 driver-upgrade suggestion, internal GPU
readback/negotiation categories and a generic exception-class fallback.
It never copies arbitrary external exception text. Other console workers
retain their existing error formatting.

This is a privacy and error-recovery boundary: it does not certify
GameCube playback or replace live GPU and speaker tests.

## EGL partial initialization cleanup (Linux)

An EGL display and pbuffer can be created before the OpenGL context or
framebuffer is ready. On a failed GameCube startup, the EGL backend now
attempts cleanup even when `eglInitialize`/`eglCreateContext`/
`eglMakeCurrent` or the FBO setup fails. It destroys a partial pbuffer
separately from an optional context, terminates the display and resets
its native handles. Cleanup is idempotent and continues after individual
native cleanup failures without masking the original startup failure.

Five fake-driver tests cover display-only startup failure, surface without
context, full context startup failure, driver error during teardown, and
a failed framebuffer setup that still releases native GL/EGL objects.
These are isolated resource-lifecycle tests, not proof of real GameCube
hardware compatibility.

## Private 3.3 core fetch resilience for macOS QA

The four-platform private 3.3 installer workflow downloads the mGBA
minimal-core build from Libretro's nightly buildbot before staging the
checksum-verified full native QA package. When a hosted macOS runner
temporarily cannot resolve the buildbot DNS name, only the explicit
**unreleased 3.3 minimal-core QA** lane retries the exact same HTTPS URL
at most two additional times with bounded 2- and 4-second delays.
Missing (HTTP 404/403) or oversized archives still fail immediately.
No mirror, fallback library, network allowance for public release,
hash-check bypass or stable-build change is introduced.

Deterministic regression tests cover successful DNS retry, persistent
failure, non-3.3 and non-buildbot inputs, HTTP errors and archive size,
and the release-only offline-core requirement. This is installer CI
robustness, **not** real device or core-rights certification.

## Native GL pointer callbacks fail safely

The Libretro Dolphin GPU bridge passes two `ctypes.CFUNCTYPE`
callbacks into a native core: `get_proc_address` and
`get_current_framebuffer`. An unexpected EGL/WGL/CGL driver exception
during either callback previously could unwind through `ctypes` and
leave the native core with an undefined function-pointer return value.

Both Linux EGL and the Windows/macOS portable GPU host now use the same
guarded callback methods. The proc callback returns an actual valid
positive native pointer or **NULL**; the framebuffer callback returns a
valid GL framebuffer ID or **zero**. They reject invalid values and
cross-thread access, without copying driver exception messages to
diagnostics. The normal Python GL loader still raises actionable errors
during startup instead of hiding them.

Six GPU-free regression tests invoke the real `ctypes` callback types
under working, failing and invalid-pointer conditions. This does not
replace a physical GameCube GPU, sound, controller or OBS test.

## Windows/macOS graphics-context teardown after startup errors

Windows WGL and macOS CGL use a portable `glcontext` GPU host.
If context startup or FBO initialization fails, teardown can itself
raise from the native context `__exit__` hook or a GL resource deletion.
The 3.3 candidate now preserves the **original startup failure** even
when teardown raises, attempts to delete every allocated framebuffer,
texture and renderbuffer despite individual native `OSError` or driver
exceptions, and releases/reset its context reference.

Three deterministic mock-host tests cover failure during OpenGL version
lookup with a broken native close hook, FBO startup with failing deletion
of the first allocated GL object, and a context that refuses to enter.
They verify error precedence and lifecycle—not GameCube GPU compatibility.

## Audio-device shutdown and reconnect resilience

The existing PortAudio output stream is shared by GameCube and all
other Libretro cores. If `stream.stop()` raises while the user unplugs
a USB audio device, we now **still call `stream.close()`** to release
its handle. Optional output-device diagnostics cannot crash gameplay
if the frozen launcher closed stderr, and bad PortAudio underflow-status
properties no longer abort the realtime PCM callback. Audio frame
ordering, gain, resampling and device-selection policies are unchanged.

Seven isolated regression tests cover stop/close faults, closed stderr,
no-speaker silent emulation, failed output initialization, malformed
PortAudio callback status and normal underflow telemetry. These tests
cannot substitute for listening to game audio on real speakers.

## Linux EGL advertises only the OpenGL version it actually owns

An EGL context requested with a **minimum** OpenGL 3.3 version can be
created at 3.3, 4.1, 4.5 or another supported driver version. Previously
the Linux GameCube host could claim support for *any* Dolphin request
through 4.5, even when the driver's actual `GL_VERSION` was only 3.3.
The 3.3 candidate now parses the real context version (ignoring normal
driver suffixes) and rejects a Dolphin GL request above that version,
without writing function pointers into the rejected Libretro callback.
The pre-existing maximum request of GL 4.5 is unchanged. Portable
Windows/macOS already performed an equivalent context-version check.

Six GPU-free tests verify GL 3.3, 4.1, 4.5 and 4.6 contexts, accepted
handshakes, rejected native callback pointer state and malformed version
strings. They prevent overstating compatibility but do not certify a
real graphics driver or retail GameCube game.

## Partial OpenGL framebuffer allocation teardown

The shared EGL/WGL/CGL GameCube framebuffer setup previously saved
FBO, color texture and depth/stencil renderbuffer handles only after
`GL_FRAMEBUFFER_COMPLETE`. If a native GL call failed mid-allocation,
the constructor invoked platform-specific teardown, but the host had
recorded **zero** owned objects and could leak live GL resources. The
shared allocator now records each successful native object ID
immediately. A subsequent setup failure or incomplete framebuffer can
release all previously allocated objects in both Linux EGL and the
Windows/macOS portable host, without losing the original failure.

GPU-free fault-injection tests cover interruptions after FBO creation,
texture upload, renderbuffer allocation, incomplete framebuffer status,
normal success, and idempotent teardown on both platform backends.
The tests establish handle ownership and cleanup, not actual Dolphin
graphics compatibility.

## Path-free GameCube save and restore warnings

GameCube's UI-visible `save_warning` previously copied up to 140
characters from an external save or restore exception, including local
ROM filenames, private account folders or native memory-card paths.
The worker now uses fixed, actionable GameCube-only warnings when
battery SRAM, optional recovery data or startup save restoration fails.
Gameplay continues, and the normal atomic save implementation is
unchanged. Other console warning wording remains compatible.

Five no-device regression tests cover periodic SRAM failure, a failed
recovery write after a successful SRAM save, an exception with a broken
`__str__` method, unchanged GBA warnings, and the actual
`CoreSession.run()` startup restore path with a mocked Libretro core.
These do not verify physical storage or GameCube saves in a real game.

## Refuse native GameCube hardware negotiation without a live GPU context

The native callback bridge already returns zero/NULL after GPU teardown.
The Libretro hardware-context *negotiation itself* now also fails closed
when the EGL/WGL/CGL context has been destroyed, or when a portable
context was created but never successfully entered. The former
OpenGL-version string cannot approve an unusable context. A rejected
request receives no framebuffer/proc callback pointers, while a live
compatible context can still negotiate normally.

GPU-free ctypes tests cover successful negotiation, a subsequent
closed-context request and a not-yet-entered portable host. The Linux
EGL version fixtures now explicitly model an existing graphics context.
This is lifecycle safety, not measured GPU throughput or physical
GameCube compatibility.

## Invalidate native GameCube GL callbacks after graphics teardown

Dolphin's Libretro core receives `ctypes` callbacks that can outlive the
EGL/WGL/CGL context on a native error or delayed callback. The 3.3 native
framebuffer and OpenGL function-pointer callbacks now verify the GPU
context remains alive before handing out **any** framebuffer ID or
attempting a driver function lookup. A closed EGL context, a closed
portable context, or a portable context that never finished entering
returns **zero/NULL**, even if a stale framebuffer ID is still retained
by a third-party object. The direct Python GL loader retains its
existing error handling for real startup diagnostics.

Three additional GPU-free regression cases exercise callbacks after
context invalidation, before the portable context is entered, and after
calling the real `close()` method on both hosts. They verify callback
lifetime, not retail GameCube performance or physical hardware behavior.

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
   GPU readback captures/max/share and session-wide readback P95 bucket /
   slow-copy counts, >5 ms scheduler deadline misses/resyncs, and audio
   delivery counters.
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
for diagnostics. The **Check my setup** report is optional both during
gameplay and after stopping: a failed native driver/audio timing snapshot
returns **unavailable** without ending gameplay, converting a clean Stop into
an error, or masking an actual emulation failure. A new session may collect
fresh metrics; no native report exception text is copied to the interface. Do not share external system-information screenshots
alongside it unless you have reviewed them for personal data.

## Completed native frames versus valid timing samples

The GameCube native loop now separately counts `native_completed_frames`
after each real `retro_run()` returns, without depending on the optional
`perf_counter`. The original `native_run_calls` remains the number of
**validly timed** frames contributing to mean, max and fixed-bin P95.
A failed, missing, reversed or suspended diagnostic clock must not make
the report claim that no native frames executed. When all timing samples
are unavailable, **Check my setup** displays the observed completed-frame
count and explicitly says performance measurements are unavailable. When
some succeed, it shows the timed-frame coverage next to the total.
This is an aggregate count, not an estimate of gameplay FPS, completed
rendered images, audio quality or GPU performance. If native timing
samples are completely unavailable but a full GameCube snapshot exists,
the setup panel still displays separately measured GPU preview cadence,
native deadline status and audio symptoms. It does **not** calculate a
readback share without a measured native-run denominator. Older partial
reports retain their conservative one-line unavailable message.
Neither the original native scheduling nor controller/camera input and
audio paths change.

## Clock integrity and native gameplay

3.3 discards invalid, nonfinite, negative or hours-long timing samples
(above 3,600 seconds) from the optional native-run, scheduler-wait and
deadline-lateness counters. An invalid or oversized reported core-FPS value
is displayed as unavailable rather than crashing the report. The 20/30/60
FPS readback policy also rejects invalid clock values safely. These
safeguards operate on local *measurement data*: they do not skip a native
Dolphin `retro_run` or modify its audio/input loop. The native worker also
uses a failure-isolated optional `perf_counter` read before and after
`retro_run` and scheduler waits. If this diagnostic clock raises, returns an
invalid value or reverses, only that timing sample is omitted. Emulation,
frame scheduling, audio, saves and P1/P2 inputs continue. A report with **zero
valid native timing samples** does *not* prove zero emulated frames; the
setup panel explicitly says the timing data is unavailable.

An ignored timing sample is not evidence of successful gameplay. A
suspend/resume or native graphics fault still requires observation on the
user's actual GPU and speakers.

### Readback completion-based preview pacing

The 20/30/60 FPS **preview-copy** limiter retains the normal start-to-start
cadence for fast GPU readbacks. When the previous blocking `glReadPixels`
consumed at least one preview frame budget, the limiter additionally waits
until a full budget has passed since that image was published to Tk. This
protects Dolphin from repeated back-to-back GPU copies without unnecessarily
halving 30/60 FPS preview targets on fast GPUs. A new copy only happens
when **both** applicable timing conditions are satisfied.
It does **not** change the frequency of game execution, input polling, core
audio, or the OBS-facing Stream Output cap; those remain independent.

The optional GL readback timing probe also rejects invalid or greater-than-
3,600-second duration observations (for example a host suspend), as native
run timing already does. Such frames may still be valid and published, while
the optional readback timing sample is marked missing. A failed/reversed
publication clock falls back to the valid callback-start time **for scheduling
only** and cannot introduce fictitious cadence samples. Synthetic tests cover
fast 30/60 FPS preview cadence, slow readbacks, suspended timing, clock
reversal and healthy recovery. This
is not proof of an actual GPU speedup; compare measured physical sessions.

## OpenGL state isolation during GameCube preview readbacks

All three embedded Dolphin GPU backends (Linux EGL, Windows WGL,
macOS CGL) share the same bounded readback implementation. It now
preserves and restores the previously active OpenGL pixel-pack
alignment, row length, skipped rows/pixels, pixel pack buffer binding
and per-FBO read buffer, together with the prior read framebuffer binding
after preview `glReadPixels`. It temporarily unbinds Dolphin's PBO
so the destination is treated as a **client memory pointer**, not an
offset into a native buffer object. It also resets inherited row/skip
offsets before using an exactly-sized RGBA buffer, then restores them
on success or error. This avoids a potentially unsafe driver write
or a stale GL state interaction; see
[Khronos glReadPixels](https://wikis.khronos.org/opengl/GLAPI/glReadPixels)
and [glPixelStore](https://wikis.khronos.org/opengl/GLAPI/glPixelStore).
The RGB pixel content and 20/30/60 FPS preview-copy policy are unchanged.
Native no-game synthetic tests cover odd-width transfers, nonzero PBO
and hostile row/skip offsets, and restoration following a driver exception.

This removes a potential GL state interaction; it does **not**
certify actual Dolphin GPU stability or improve measured FPS without
a real-game physical run.

## Interpretation

| Observed field | Meaning | Important limit |
| --- | --- | --- |
| `native_completed_frames`, `native_run_calls`, `native_run_mean_ms`, `native_run_max_ms` | Independently counted returned `retro_run()` frames versus valid timing observations and their costs | Neither count is displayed FPS or completed game scenes; timing coverage may be incomplete |
| `native_run_p95_bucket_code` | Nearest-rank P95 `retro_run` duration bucket, using fixed ranges 0–8, 8–16, 16–25, 25–33, 33–50, 50–100, 100–250, 250–500 and >500 ms (codes 0–8). -1 means no valid native frames | This is an interval, not a fabricated precise percentile or physical FPS; only nine aggregate counters are retained, no per-frame timing history |
| `gpu_readback_calls`, `gpu_readback_max_ms`, `gpu_readback_share_of_native_run` | Synchronous UI preview pixel readbacks and their portion of native run cost | Readback time is **included in**, not added to, `retro_run` time |
| `gpu_readback_timing_samples`, `gamecube_preview_clock_failures` | Number of successfully timed GPU readbacks and rejected optional clock observations | A valid clock on every frame or proof that the physical GPU was slow; an otherwise successful captured frame may have no timing sample |
| `gpu_readback_p95_bucket_code`, `gpu_readback_over_16ms`, `gpu_readback_over_33ms` | Nearest-rank P95 fixed duration bucket (0–2, 2–4, 4–8, 8–16, 16–33, 33–50, 50–100, 100–250, >250 ms, codes 0–8; -1 without data) and slow-copy counts | Only successfully timed GPU captures; not a native game FPS metric. A partial sample or mixed preview target can bias the distribution |
| `scheduler_late_frames`, `scheduler_late_max_ms`, `scheduler_resyncs` | Delays beyond the native frame deadline and scheduler resets | Missing a deadline does not prove a hardware driver fault |
| `audio_output_device_underflow_callbacks` | PortAudio reported output-device underrun callbacks | A nonzero value signals a scheduling symptom, not its root cause |
| `audio_output_underrun_frames`, `audio_queue_dropped_frames` | PCM output frames filled with silence or dropped from the bounded queue | No recorded waveform or audible-speaker confirmation |
| `gamecube_hardware_frames`, `gamecube_preview_readback_skips` | Game frames published to the embedded UI vs deliberately skipped preview readbacks | Does not mean the emulator skipped `retro_run` or game input |
| `gamecube_preview_target_fps`, `gamecube_preview_observed_capture_fps` | Selected 20/30/60 FPS preview cap versus aggregate **successful frame publication cadence** since the most recent preview mode switch | Observed publication frequency is not native Dolphin emulation FPS or physical monitor FPS |
| `gamecube_preview_cadence_intervals`, `gamecube_preview_max_interval_ms` | Number of measured gaps between published preview images and longest such gap | With fewer than two published frames, observed cadence is zero meaning **insufficient samples**, not a 0 FPS performance result |

Readback P95 is computed from nine bounded integer buckets, never a
per-frame history, pixel buffer, ROM name or device identifier. It is a
**range**, not an exact latency value, and covers the whole GameCube session.
Restart the game before comparing 20/30/60 FPS preview modes so each trial
has a fresh histogram. Invalid/suspended clock samples cannot contribute.

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

The hardware readback callback additionally requires that each returned
RGB8 image's width and height **exactly match** Dolphin's requested
Libretro video callback dimensions. The first-party EGL/WGL/CGL hosts
already return pixels in this format; a stale or partial GL buffer from
a torn context must not be treated as the current game image simply
because it has three channels and an 8-bit pixel type. A mismatch
causes a controlled, fixed-category GPU stop without publishing the
incorrect pixels or modifying P1/P2 buttons, saves or audio pacing.
Synthetic tests cover both width and height mismatches. This is not a
claim that every physical OpenGL driver has been tested.

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


## Full-native 3.3 macOS QA staging (unreleased; runner pending)

The macOS Intel and Apple Silicon candidate workflow now includes a
full-native stage mirroring the validated Linux/Windows private repacks.
For each architecture it verifies exact published `v3.2.0` DMG bytes
using the published `SHA256SUMS.txt`, verifies the current 3.3
mGBA-only DMG receipt and frozen private app identity, and copies the
original 11 native cores with their original notices into the separate
`AnythingPlays33Candidate.app`. The source app's Python/Tk/OpenCV
runtime remains from the exact 3.3 candidate build.

Because the app bundle is modified, macOS QA ad-hoc signs the new app,
verifies its signature and native-core bytes, creates an independent
`AnythingPlays-3.3.0-fullqa1-macos-ARCH.dmg`, mounts that final DMG,
and rechecks identity, signature and native-core provenance. The expected
output is a private 14-day artifact with a full DMG SHA256 and
`V33_FULL_MACOS_QA_RECEIPT.json`, explicitly marking notarization,
public approval and real camera/controller/GameCube verification false.

**Both hosted Mac jobs were queued when this was authored.** The code and
pure provenance/identity source tests alone do not prove a DMG was built
or that a real Mac ran it. Do not mark either platform passed until that
exact-head job completes and its full-native artifact exists. The
eventual public 3.3 stable-upgrade installer still requires distinct
release identity, source and license review, and real-host acceptance.


## Full-core frozen-app desktop startup checks

The full-native owner-QA workflow also launches the **repacked** full 11-core
application on each hosted target, independently of the earlier mGBA-only
installer startup. Linux extracts the actual `3.3.0~fullqa1` Debian package
and executes the frozen binary under Xvfb. Windows runs Inno to install the
real `3.3.0-fullqa1` setup into an isolated runner directory before launching
the frozen EXE. Each macOS job, when available, must mount the **repacked
full-native DMG**, recheck its ad-hoc code signature and launch the actual
app executable from the mounted bundle.

Every full-native test seeds dummy 3.1/3.2 settings canaries in a disposable
home, requires the frozen 3.3 QA identity and disarmed inputs, opens and
closes a real Tk Stream Output window with synthetic reference pixels,
and fails if historical settings change. Each full-native artifact must
contain both the original-byte provenance receipt and the independent
`V33_FULL_NATIVE_FROZEN_GUI_RECEIPT.json` that proves its startup path
actually executed. A successful package hash or native-core inventory
**alone** is insufficient for the full-native artifact.

These are hosted CI desktop startup checks, **not real hardware, games,
OBS recording, native audio, player/controller latency, Apple notarization,
or a public 3.3 stable-upgrade validation**. The real 30-minute camera,
GameCube and OBS acceptance requirements remain open.


## ROM-free full-native dynamic-link gate

After the full 11-core package is assembled and its frozen Tk UI opens,
the private QA runner now probes every original-source core from the
**installed full-native package**, not the build-tree or the mGBA-only
installer. Each `*_libretro` library is loaded in its own bounded
subprocess and checked for libretro ABI version 1 plus the public
interface symbols used to connect the emulator to the application.

The probe never calls `retro_init`, loads a ROM, creates a GPU context,
opens audio/camera/SDL input, starts an emulator or emits any private
driver error text. A crashed, stuck or missing native core fails the
private full-native installer job; it cannot crash the main Tk test
runner. The only retained artifact is
`V33_FULL_NATIVE_LINK_RECEIPT.json`, with a list of known core
filenames, pass/fail booleans, and explicit physical GameCube/OBS,
licensing and public release signoffs set to false.

Link success is a necessary *technical* gate, not a claim that all 18
system profiles have playable games, correct audiovisual rendering,
independent redistribution clearance or acceptable controller latency.
GameCube GPU/audio/save and physical OBS/camera testing are still
required for a public v3.3 stable release.

