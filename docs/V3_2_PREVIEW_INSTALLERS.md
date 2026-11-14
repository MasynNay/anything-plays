# Anything Plays 3.2 — Unreleased cross-platform preview installers

**Status:** Build automation committed on the `feature/v3.2-integration`
development branch, but no installer is considered verified until the exact
commit's CI job succeeds. This is NOT a public 3.2 release.

## Preview build targets

| Platform | Unreleased QA artifact inside the workflow |
| --- | --- |
| Linux x64 | `anything-plays-32-preview_3.2.0~preview1_amd64.deb` |
| Windows x64 | `AnythingPlaysSetup-3.2.0-preview1.exe` |
| macOS Apple Silicon | `AnythingPlays-3.2.0-preview1-macos-arm64.dmg` |
| macOS Intel | `AnythingPlays-3.2.0-preview1-macos-x64.dmg` |

These are **minimal native-core previews**: the app still knows about all 18
console profiles, but only the mGBA core (GB, GBC, GBA) is bundled. No ROMs,
BIOS/firmware files, commercial game content or additional restricted cores
are added. Do not advertise this QA build as 18-console playable.

## Stable-installation isolation

Every target has a separate installer identity, application name or Linux
package, and the embedded `v32_preview` build marker selects a clean
`anything-plays-32-preview` settings directory. There is no automatic
migration from published stable settings or 3.1 release-candidate profiles.

**Game progress is isolated too.** Unlike published builds, this private
preview never imports or replaces an adjacent `<ROM>.sav` file. Its SRAM
snapshots and native per-core saves use new version-specific user-data folders
on Windows, Linux and macOS; the Libretro firmware/system directory and
per-user core-pack store are version-specific as well. A game already in your
stable library will therefore start with fresh progress in the preview.
Preview save progress can be tested and reopened inside the preview without
touching the stable game's original saves. This is deliberate: test firmware,
save states, core updates and unknown native behavior must not mutate the
working 3.1/3.1.1 installation.

- **Linux:** `anything-plays-32-preview` package, executable, desktop entry,
  icon and `/opt/anything-plays-32-preview` installation.
- **Windows:** distinct `V32PreviewBuild` Inno Setup AppId, folder, program
  shortcuts and `3.2.0-preview1` installer filename.
- **macOS:** `AnythingPlays32Preview.app`, separate
  `com.anythingplays.privatepreview32` bundle identifier and preview DMG.
  This build is ad-hoc signed and **not notarized**.

## Exact-source QA and artifact review

The workflow `.github/workflows/v32-private-preview-installers.yml`
only builds from the integration PR head with exclusive non-release flags.
It stages actual OS-native install packages, invokes existing native bundle
checks, checks the embedded preview marker and native installer metadata, and
generates `V32_PRIVATE_PREVIEW_RECEIPT.json` with source commit and SHA-256. The receipt verifier also inspects the unpacked application to reject any non-mGBA libretro core, extra Dolphin Sys runtime, or provenance manifest claiming more than the single mGBA core.

**All four platforms have passed real installed-frozen-GUI CI gates**
at the verified 3.2 checkpoint `6d8257b6` ([native run
43605185838](https://github.com/MasynNay/anything-plays/actions/runs/43605185838)).
Subsequent code changes must pass their own exact-head rerun:

- **Linux x64:** extract the actual Debian package into a disposable
  directory and launch its frozen App under Xvfb.
- **Windows x64:** silently install the actual Inno Setup EXE into a
  disposable folder, then launch the installed `AnythingPlays.exe` using
  the host's desktop session.
- **macOS Apple Silicon and Intel:** mount the finished, ad-hoc-signed DMG
  read-only, verify the app bundle signature, and launch the actual
  `AnythingPlays32Preview.app` executable from that mounted volume.

Each test opens a real Tk root, constructs the App and runs its event loop for
1.2 seconds. It verifies the exact immutable 3.2 build marker, disarmed inputs,
all 18 **profiles** (not 18 bundled native cores), and a fresh preview profile
saved after clean shutdown. The installed app now also opens and closes five
actual native setup windows: Get started, guided camera calibration, the
controller/keyboard guide, controller button remapping, and setup diagnostics.
The controller remap window must refuse capture when no controller is
connected, and the real App must remain disarmed with no active camera/SDL
device after all dialogs close. The installed-GUI harness now repeats the
five native setup-dialog roundtrips **eight times (40 total)** in the
*same running frozen app*, checking after every round for orphaned Tk
top-level windows and accumulating theme-observer callbacks. This catches
reopen/close resource leaks that a single successful first-run dialog would
miss; it does not simulate a physical webcam or controller.
The common native verifier seeds fake 3.1
preferences **and** console profiles and rejects even one altered byte.
A separate `V32_INSTALLED_GUI_RECEIPT.json` is retained with each installer.
This remains a smoke test without physical camera, USB/Bluetooth controller,
retail ROM, macOS notarization or redistribution approval.

To avoid repeatedly running superseded 3.1 build suites, eleven historic
3.1/3.1.1 workflows now skip expensive jobs for the 3.2 integration PR.
They remain eligible on their original branches. The 3.2 source checks and
dedicated 3.2 four-platform preview workflow remain enabled. GitHub has
already confirmed the legacy jobs' skipped status; that is NOT equivalent
to the new 3.2 jobs passing.

The initial 3.2 source-check runs exposed a strict repository hygiene
allowlist blocker: it rejected the new, reviewed `run_v32_preview.py` entry
point. The allowlist now explicitly permits that single source launcher while
rejecting unrelated root scripts; a regression test locks this down.
That earlier failure was resolved, and source tests passed at the
verified four-platform checkpoint. New source changes continue to require
their own GitHub Actions success before being treated as verified.

Private preview paths also reject symlink redirection back into stable data
and hardlinked SRAM inputs, so a seemingly distinct directory cannot be used
to import or corrupt a stable game's save during QA. This check now extends
**below the private save root** into Neo Geo Pocket cartridge-flash directories,
GameCube memory-card folders, and nested native resume checkpoints. A
symlinked `native-core`, `neo-geo-pocket`, `gamecube`, or `resume` directory
cannot silently route private preview writes to public stable progress. Resume
states also reject hardlinks to other files before reading or writing, and
revalidate parent directories at the actual checkpoint operation rather than
trusting only construction-time checks. Every desktop OS convention is covered
by new synthetic native-save tests in CI. These are source-level safeguards;
a physical device run is still required.

## Camera driver recovery under transient faults

The 3.2 UI scheduler now routes actual native `VideoCapture.read()`
exceptions, success-with-None or empty frame buffers, and errors while
mirroring a valid frame into the **same bounded reconnect loop** used for
ordinary camera hot-unplug. It clears stale previews and camera-held
gameplay input first, retains the selected device, and does **not**
silently arm controls after reconnect. A healthy frame still follows the
normal low-overhead rendering path. The source suite uses injected mock
capture failures and synthetic pixels, not a real camera. USB permissions,
driver-specific failures, and actual hot-unplug remain field-test gates.

## Save recovery and long-session regression scope

The previous Neo Geo Pocket full-state checkpoint writer used one shared
`.apstate.tmp` filename. Concurrent app instances could overwrite or delete
each other's in-flight state. The 3.2 branch now writes to unique temporary
siblings, flushes the complete checkpoint to disk and atomically publishes the
finished bytes. A failed replace must keep the previous state intact, and an
old symlink at the legacy fixed-temp name must remain untouched.

Native source tests and the four-platform package preflight now exercise
two deliberately overlapping checkpoint writers, simulated failed writes,
correctly restored last-complete checkpoints, and 1,500 identical state
snapshots without repeated disk replacements. A separate SRAM test advances
**108,000 simulated 60-FPS frames (30 virtual minutes)**, including 5-second
checkpoint intervals, restarts and a failed checkpoint/retry, while asserting
that a public/stable ROM-adjacent save stays byte-identical. The simulation
runs quickly; **it is not a 30-minute real-world session, game-speed metric,
physical controller test or substitute for the later field soak**.

The artifact workflow intentionally has only read permissions and cannot
create tags, GitHub releases or edit the default branch. GitHub Actions
artifacts may be accessible to people who can download artifacts from the
repository and expire in seven days. Do not treat an Actions artifact as
confidential or as a customer-facing release.


When running the source preview without an installer, use the regular project
setup instructions to install Python dependencies and fetch an appropriate
mGBA core before attempting GB/GBC/GBA gameplay. A missing optional SNES,
N64 or GameCube core in this limited preview is explicitly labeled **not
bundled** rather than incorrectly described as corruption. The same
distinction now appears in the local **Check my setup** troubleshooting
report, not only the main emulator-status strip. If a matching native core
really is installed, diagnostics correctly recognize it instead.

## Missing-core behavior in the limited preview

The console picker still exposes all **18 control profiles** because setup,
mapping and portable profile work should remain usable even when a native
emulator is not included. The test installer currently packages **mGBA only**
for GB, GBC and GBA. In a frozen 3.2 preview, attempting to open a ROM for
an unbundled console now displays **Not bundled in this 3.2 preview**, returns
to the game shelf and does **not** invoke a native emulator. It does not claim
the installation is corrupt or tell the user to reinstall the public 3.1.1
package. An independently verified compatible core already installed by the
user is still recognized normally.

If the mGBA core itself is missing, 3.2 says the **preview mGBA emulator file
is missing**, distinct from the intentionally unbundled consoles. The main
window uses concise status labels; **Check my setup** and the blocked-launch
popup supply detailed guidance. Tests exercise all 18 profiles, stable
missing-core behavior, and matching privacy-safe diagnostics. The four-platform
frozen-app acceptance includes a synthetic unbundled SNES attempt to verify
the real installer never tries to open a ROM or starts a native core. A rejected
launch now uses the normal game teardown path, so a previously running session
cannot leave native gameplay or stale video behind if its core disappears.
The 3.2 Restart action also refuses to revive a prior ROM remembered internally
by a stopped native worker; a new ROM must be explicitly selected. Public
3.1.1 restart fallback behavior is unchanged. No
retail-game file is accessed, and this does not count as 18-console QA.

## Human acceptance still required

On a disposable/test account before considering a public release:

1. Confirm the installed app title says **Anything Plays 3.2 Development
   Preview**, the installer is alongside—not replacing—3.1.1, and the old
   settings, `<ROM>.sav` progress and managed core store are unchanged.
2. Launch the camera wizard using a real USB/internal webcam, sample a
   distinctive target, verify zone feedback, stop/reconnect camera, and verify
   that object controls cannot arm during calibration.
3. Connect a USB or Bluetooth gamepad. Test live input, press-to-remap,
   multiple simultaneous buttons, unplug/replug and focus loss while a game
   is running. Confirm captured inputs cannot reach gameplay.
4. Export, import and undo a control profile, including a rejection for a
   different console. Confirm ROM directories, save files and camera frames
   never leave the machine through exported settings.
5. Check dark/light themes, laptop window size, four setup dialogs, 18-console
   profile switching, Stream Mode, emulator failure recovery, and app exit.
6. Confirm exact release-core and dependency provenance/redistribution terms
   before proposing any final 3.2 release or 18-core installer.

**No production approval, notarization, or physical hardware certification
is inferred from source-only or synthetic CI.**


## Private Linux full-native staging (3.2 research, not release)

The 3.2 integration workflow now adds an independent **Linux x64-only**
candidate using the fresh exact-head 3.2 preview application and 11
original-source native core libraries from the published v3.1.1 release.
The original release DEB is downloaded with its SHA256SUMS and verified
before extraction; every reused native core and its source marker is
verified before and after repackaging. Only native cores and their original
notices are copied, never the old Python application, ROMs, user settings,
save data or emulator configuration. The QA Debian package stays in the
private 3.2 preview package and settings namespace and uses version
`3.2.0~fullqa1`, distinct from the regular mGBA-only preview.

The result is re-extracted and its **actual frozen 3.2 Tk application**
launched under Xvfb. A separate 7-day GitHub Actions artifact retains the
full-core Linux QA DEB, source/hash receipt and installed GUI evidence.
This demonstrates an 18-profile / 11-core **technical inventory**, not
18 verified games, real audio/save/input, hardware compatibility, rights
clearance or production readiness. Windows and both Mac native full-core
assemblies remain separate future tasks. The regular mGBA-only preview
artifacts and public stable 3.1.1 are unchanged.


## Private full-native Windows 3.2 QA staging

The Windows runner now builds a separate private 3.2 Inno Setup candidate using the published v3.1.1 Windows native payload and the exact new 3.2 frozen application. It verifies the public checksum, the 3.2 source receipt, the original 11-core source-build hashes and original notices, then repacks and re-installs the 3.2 application without copying old Python runtime or stable settings. The Windows setup keeps the private 3.2 AppId and creates version `3.2.0-fullqa1`. After installation, an independent frozen Tk GUI smoke verifies that the executable starts with all 18 console profiles and preview settings isolation. The Windows full-native receipt and installer are kept in a separate seven-day Actions artifact, never uploaded as a release. This is technical inventory evidence, not certification for real gameplay, hardware, redistribution or macOS.


## Full-native macOS review candidates (Apple Silicon and Intel)

The 3.2 private workflow now stages both arm64 and x64 full-native QA DMGs.
Each architecture verifies the published 3.1.1 DMG SHA256 and 11 original
source-built core hashes, then copies only native core files and original
license notices into the exact-head 3.2 private preview app. The old
Python, SDL, OpenCV application, game data and user settings are excluded.
The 3.2 bundle ID and private settings namespace remain unchanged. The
full-size candidate is ad-hoc signed (NOT notarized) and packed into a
distinct fullqa1 DMG. The workflow mounts it again, verifies its signature
and original core bytes, starts the actual frozen Tk executable, checks
all 18 console profiles, and confirms dummy stable settings are unchanged.
Separate private 7-day Actions artifacts retain both Mac DMGs and their
native provenance / GUI smoke receipts. They are NOT public releases,
redistribution approval, physical camera/controller testing or evidence
that all 18 console profiles play retail games correctly.


## First original-homebrew native runtime acceptance (Linux)

The full-core Linux runner now performs **actual Libretro execution** using
short original console test programs generated from source at QA time. The
probe opens native libraries from the *re-extracted full-core 3.2 DEB*, not
from an unrelated installed RetroArch copy. It checks real decoded/changing
video frames and core-generated PCM using existing original GB, GBC, GBA,
NES, SNES and Genesis probe programs with individual crash/time limits.
Six profiles (GB, GBC, GBA, NES, source-built Supafaust SNES and
source-built BlastEm Genesis) are now strict acceptance gates after
native frame/PCM evidence passed in 3.2. BlastEm uses the repository's
existing source-generated *non-TMSS* original homebrew variant:
the old Genesis Plus GX fixture performed an unconditional TMSS register
write that could halt BlastEm's non-TMSS console configuration. Only
that optional startup instruction is replaced with five M68000 NOPs;
no commercial game is modified.

Eight additional native profiles are probed as **exploratory**:
Master System, Game Gear and SG-1000 with the same BlastEm build;
Atari 2600 with the source-built GPL2+ Tia replacement; Atari 7800
with ProSystem; PC Engine with exact-source Mednafen PCE Fast; and
WonderSwan mono/color with Mednafen WonderSwan. Each creates original
test ROM bytes at runtime, demands core-generated RGB/PCM using the
existing strict program probes, and records its pass/fail individually.
An exploratory failure does not make the six known-good cases appear
to fail, nor may it be represented as verified gameplay. Neo Geo
Pocket/Color and the heavier N64/GameCube need additional independent
fixtures, runtime systems and platform-specific acceptance.
Individual exploratory failures are explicitly listed in the same report;
they are never relabeled as passing. The runner verifies the 11-core source
manifest, the 3.2 exact Git SHA, and the private build receipt *before*
executing any native module. It uses a disposable home, no network, no
firmware and no commercial or user-supplied games; native crashes are
isolated in subprocesses. Only a sanitized, per-system JSON summary is
retained alongside the full Linux QA installer and other receipts.

This is the start of **software runtime acceptance**, not evidence that
all 18 systems or actual retail games work. Real USB/Bluetooth gamepads,
physical cameras, sound output, sustained saves and four-OS play testing
remain independent acceptance requirements.


## Last four 3.2 native profiles: independently reported software research

The private Linux full-core QA now runs a distinct, nonblocking research
stage for **NGP, NGPC, Nintendo 64, and GameCube** against the exact-head
installed 3.2 emulator core files. These results are recorded separately
in `V32_FOUR_REMAINING_CONSOLES_RESEARCH_QA.json`, alongside the unchanged
14-profile original-homebrew native A/V baseline.

NGP runs an **original source-generated 0x00 monochrome program** with
real K1GE frames, PSG PCM, and native manual/camera-input callbacks.
NGPC downloads only its existing immutable Git-blob-pinned MIT color
homebrew cartridge, checking the true 0x10 color header. N64 downloads
only the pinned Unlicense/public-domain SaveTest ROM and measures actual
native ParaLLEl software frames. GameCube downloads only the previously
pinned zlib-licensed homebrew controller test DOL and attempts real
Dolphin software-rendered, input-driven frames with the cached interpreter.
These THREE third-party binaries are fetched **only in disposable private
CI**, never distributed in the installer; fixed upstream digest checks
precede execution. The original mono NGP test uses no downloads at all.

Each heavy native test runs in a crash/timeout-contained subprocess.
An unavailable fixture, native crash, silence or frozen frame is marked
**NOT VERIFIED**, never passed, while leaving the 14-profile required
original-homebrew gate unchanged. The output is a redacted, per-profile
JSON summary without paths, upstream ROM binaries, usernames, device IDs,
screenshots or raw crash traces. No test grants public release rights or
claims commercial ROM performance, real speakers, webcam/controller
hardware, portable save integrity, or all 18 systems fully compatible.


### Diagnostic refinement after the first four-profile results

At source revision `9ba37c0c`, native original NGP and pinned N64
software-video acceptance passed; NGPC displayed changing color frames and
real PCM but failed its *composite* video/audio/input condition. The
research report now records independent strict video, PCM and native input
Booleans and input callback counts for NGP/NGPC, without releasing ROM
images, local device names or log tails. An A/V-only result is explicitly
**not** a complete input/gameplay pass.

The first GameCube research attempt used the obsolete CPU-only
`CoreSession` probe and reported zero decoded video despite advancing
native steps. The production application actually chooses
**`GameCubeHardwareSession`** with the host's offscreen GPU/FBO path.
The next experiment therefore runs `tools.probe_gamecube_app` against
that *same production backend*, demanding nonblank changing RGB frames,
native input polls and PCM callback frames, while retaining a bounded
time limit, a pinned zlib test DOL and independent nonrelease flags.
It does not claim controller hardware, speakers or general retail game
compatibility even if the accelerated graphics test passes.


### Measured 3.2 native GPU and Neo Geo Pocket Color diagnostic results

The exact-head full-native Linux QA for `d8889e32` again passed the
14 original-homebrew A/V probes. The second independent research run
confirmed NGP genuine mono video/PCM/input and N64 CPU software video.
Production GameCube offscreen GPU rendering now **passes** a real
input-driven, changing-image native probe: 131 native RGB callbacks,
22 distinct RGB frames, 142,912 controller polls and 1,071,041 native
PCM callback frames. However, its headless Mesa run averaged **5.21 FPS**
and the sample DOL emitted **zero nonzero PCM values**. This is successful
rendering evidence, NOT proof of playable speed or sound on real GPUs.

The pinned MIT Neo Geo Pocket Color cartridge produced 603 native
frames at approximately 60 FPS and 281,718 nonzero PCM values. All three
individual A/V/input gates reported true, but its overall native
acceptance Boolean remained false. We preserve that **NOT VERIFIED**
outcome pending independent process-completion and provenance details.
The follow-up diagnostic reports only allowlisted true/false conditions,
bounded native exit codes, offscreen GPU readback timing, and whether a
nonzero PCM sample was observed. It retains **no original error strings,
game assets, usernames, local paths or crashed-process stacks**.


### Neo Geo Pocket Color full native probe result mapping (3.2)

The independent `tools.probe_ngp_mit_homebrew` parent writes its strict
aggregate result as **`passed`**, whereas the N64 homebrew parent writes
`probe_passed`. The first 3.2 extended reporter mistakenly read the N64
key from the NGP Color report, falsely rejecting an otherwise passing
native color homebrew test. This mapping was corrected without changing
the actual NeoPop probe, native checks, exit code, required genuine
0x10 color cartridge header, pinned MIT Git blob identity or A/V/input
criteria. Regression tests now reject fabricated success via an extraneous
`probe_passed` key and require the real parent plus all child gates.
This fix should not be treated as confirmed on an installed 3.2 native
package until the exact-head four-platform QA and Linux research evidence
have both passed. Even after confirmation it is a bounded color homebrew
A/V/input result, not general commercial game or physical hardware QA.


## 18-console homebrew software evidence matrix (still not a release)

In addition to two independent Linux native runtime QA receipts, the
private full-core Linux job now validates and merges them into
`V32_18_PROFILE_SOFTWARE_EVIDENCE_NOT_RELEASE.json`. This uses an exact
3.2 Git SHA and rejects any missing or duplicate profile, wrong native
core family, inconsistent pass count, forged release status, child crash
or timeout presented as success. It records **one original or immutable
hash-pinned homebrew software diagnostic per console profile** across
all 18 console names, and explicitly distinguishes the 14-core A/V
baseline from the four experimental heavy/alternate profiles. The
report contains **no private user game paths, media files or crash logs**.

**18/18 software smoke positives, if achieved, do not mean 18/18 retail
games play well.** The matrix separately records slow headless GameCube
frame rate, silence in its test DOL, untested physical USB/Bluetooth
controllers and cameras, unverified saves and real speakers, missing
cross-platform game execution, macOS notarization and the still-open
native-core redistribution review. `ready_for_public_3_2_release` is
unconditionally **false**; QA can never turn a release on by itself.
