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

The Linux workflow now also extracts the **built Debian package** into a
disposable directory and launches its actual frozen App under Xvfb with a
temporary HOME. Its 1.2-second real Tk startup check requires a live root,
initialized app and event loop; it does not use a webcam, ROM or physical
controller. The frozen-startup gate also verifies the exact embedded 3.2
preview identity, 3.2 settings namespace and camera/controller disarmed state.
CI seeds a canary in the existing stable 3.1 preferences folder and checks
that the canary is **byte-for-byte unchanged** after preview startup. It
checks the preview's saved console-profile file rather than incorrectly
assuming a new preferences.json must exist after a read-only launch.
The Windows and macOS artifacts still require equivalent installed
desktop testing and physical-device validation.

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
That earlier failure is resolved in source, but source CI remains pending
until a runner completes tests on the newest commit.

Private preview paths also reject symlink redirection back into stable data
and hardlinked SRAM inputs, so a seemingly distinct directory cannot be used
to import or corrupt a stable game's save during QA. These are source-level
safeguards; a physical device run is still required.

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
