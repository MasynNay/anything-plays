# 3.2 first-run path — integrated development candidate

**This is an unreleased 3.2 development feature.** The public v3.1.1
installers and update channel have not been changed.

## Run the source-only 3.2 preview (no installer)

Check out the **feature/v3.2-integration** branch, install the regular Python
dependencies documented in the repository, then run:

```bash
python run_v32_preview.py
```

Do not use `python app.py` as the 3.2 preview entrypoint: that old entrypoint
intentionally retains the 3.1 source preview identity for compatibility.

This launcher explicitly selects the **3.2 development preview** identity
and creates only `~/.config/anything-plays-32-preview/`, with no automatic
migration from stable 3.0/3.1/3.1.1 or former release-candidate settings.
It includes no game ROMs or proprietary BIOS. It does not publish releases,
open webcams or scan controllers merely by selecting a settings channel.
A frozen release package cannot switch identity via that environment flag.

No public v3.2 installer exists yet. The preview is unverified with real
camera/gamepad hardware and should not be presented as release quality.

**Console availability:** the test installers know all 18 control profiles
but bundle only mGBA (GB, GBC and GBA). Selecting an unbundled console remains
valid for layout setup; however, launching a game without its verified native
core now displays **Not bundled in this 3.2 preview** and returns to the
library without opening the ROM or emulator. This does *not* mean that the
public stable 3.1.1 installation is damaged. A genuinely missing mGBA core is
identified separately. The main status strip stays short; Check my setup
contains the full next steps.

## Restore and undo without losing newer edits

An all-console backup is a portable **controls-only** archive. Restoring it
modifies only consoles whose portable controls differ; custom local backgrounds,
ROM libraries, controller identities and user data are retained. Undo stores a
snapshot of only those changed consoles. If a player adjusts controls after
restoring the backup, **Undo all restore** identifies the conflicting consoles
and asks before replacing these newer edits. Cancel leaves every saved profile
unchanged. Local-only backgrounds are preserved even when Undo is approved.
An unfinished camera calibration must be canceled or saved before an undo.

## Single-console import and Undo preserve local customizations

The one-console Import controls action now merges approved camera controls into
the current local profile instead of replacing it with a stripped portable
file. Custom zone artwork, ROM directories and other device-local fields
survive both import and Undo. If controls or an imported theme were edited
after the import, Undo asks before replacing those newer choices. Declining
keeps the edits, while confirming restores the earlier portable controls.
Import and Undo both reject unfinished camera calibration.

These guarantees are exercised through pure unit tests and the actual
frozen Tk Import controls and Undo import buttons, without a camera, game,
controller or network connection.

## Backup export does not silently change local controls

**Export controls** writes only the selected console's portable JSON backup.
It does not save or mutate the active on-disk control profile; the private
frozen-installer GUI smoke explicitly checks that restriction. This means an
unsaved editor layout can be safely exported even when local profile storage
is unavailable, and a completed export is never mislabeled as a failure of
another disk write. ROM paths, zone artwork, device identity and saves remain
excluded. To commit the editor layout locally, save or switch the console
normally; exporting the portable file is a separate action.

## Exit protection when profile storage fails

When closing the 3.2 preview, the app first attempts to persist the current
console's control settings and safely cancels unfinished calibration. If the
profile disk is full, read-only, or contains invalid values, an explicit
confirmation asks whether to **Exit without saving**. Declining leaves
the window, control editor, and device lifecycle intact so the user can
correct settings and retry. Approving performs the normal device cleanup and
exits, with the risk of losing unsaved edits explained. Shutdown errors never
include private filesystem paths in the confirmation. A normal successful
close still presents no extra dialog.

## Theme changes can no longer truncate preferences

Changing the theme now updates `preferences.json` through a staged,
fsynced atomic replacement instead of directly truncating and rewriting the
existing file. The theme still updates immediately in the interface. If the
disk write fails, the old on-disk preferences survive intact and the status
explains that the selected theme was not saved. Other preference fields are
preserved. A malformed existing preferences file remains untouched.

## Transaction-safe profile preferences and Undo recovery

Import controls and Undo import now require their preference writes to
succeed; a full disk or permission error is reported and triggers rollback
of the control profile and visible theme rather than claiming the import or
undo succeeded. Normal preference saving retains its existing nonfatal
warning behavior.

Undo all restore now also handles the case where the atomic profile write
succeeds but refreshing the active Tk editor fails. It restores the saved
profiles, returns the previous visible controls, retains the Undo snapshot,
and reports an error. If rollback itself fails, it warns users to inspect
control storage before continuing. The failure paths are covered by unit
tests and an installed frozen Tk import/write-failure smoke.

## Calibration Cancel keeps pre-existing unsaved edits

The camera guide now snapshots both the controls visible in the editor
(including unsaved changes made before opening the guide) and the separately
saved console profile. Cancel restores the pre-guide editor, not stale values
from an earlier disk save. It only writes a rollback to disk if another UI
action auto-saved a change while calibration was open. This prevents a
canceled sample from discarding an unrelated unsaved layout or unexpectedly
committing it to the local profile store.

## Keyboard shortcuts are protected against failed saves

**Game Controls → Keyboard shortcuts** now saves each changed key before
closing the key-capture prompt or updating the visible assignment. If disk
persistence fails, the previous keyboard mapping stays active and the player
can press a new key again to retry. **Reset this console's keys** also keeps
the dialog open and leaves the existing bindings unchanged after a failed
write. These changes affect only the selected console and do not alter
controller mappings or physical input.

## Reversible Reset controls

Approving **Reset controls** now enables a session-only **Undo reset** button
in Safety & Profiles. Undo restores the prior camera-control layout and
detection settings without overwriting newer local zone-art paths, ROM folders
or unrelated settings. New control edits made after resetting trigger an
explicit confirmation before they are replaced. A failed disk write or
interface refresh leaves the Undo snapshot available for retry, and camera
controls remain stopped. Switching to another console does not discard the
snapshot; switch back to the reset console to use Undo. The private frozen
Tk GUI smoke exercises a rejected and approved Undo reset with later edits.
Every unreleased installer must report `v32_reset_undo_verified` after this
real-button exercise, or its acceptance check fails.

## Transactional console-editor switching

Reading controls from the editor now builds a complete candidate profile
before replacing the active one. If a later numeric field is malformed, none
of the earlier fields leak into a partially updated in-memory profile.

The console switch also reads and validates the destination profile before
saving or tearing down the previous game. If a destination read fails or its
Tk controls cannot refresh, the selector returns to the previous console,
the previous editor remains visible, and the game/Stream Mode view is not
switched. No failed destination read can silently trigger emulator teardown. The
four-platform installed-frozen-app smoke also injects a destination read
failure and verifies the native system, prior controls and game identity
remain unchanged in the real Tk interface.

## Profile save and console-switch recovery

Changing consoles now commits the previous console's controls before leaving.
If settings are invalid or the profile disk write fails, the selector returns
to the previous console without discarding the in-progress editor values;
camera gameplay stays disarmed. Reset controls now asks for confirmation before discarding the selected
console's portable camera-control edits. It resets layouts and detection
settings without erasing local zone artwork, ROM directories or other private
settings, even if a newer artwork path is only in the visible editor. A
declined reset does not stop gameplay or write to storage; unfinished
calibration blocks reset. Approved resets write defaults before refreshing
the editor. A failed reset retains the previous editor configuration instead
of making an unsuccessful reset appear permanent.

## Isolated preview zone artwork and safe grid saves

A user-requested HTTPS PNG zone-art download in the 3.2 preview now saves
**only** to the private 3.2 preview settings directory. New downloads use
one cache per console (for example, `zone-art-gba.png` and
`zone-art-snes.png`), so selecting artwork on another console cannot
replace the previous console's downloaded image. Older private
`zone-art.png` references remain readable for compatibility. The
unreleased preview's frozen GUI acceptance now verifies both console
downloads through the real URL picker with synthetic PNG responses and
no external network request. It never uses the
older shared `~/.config/anything-plays/zone-art.png` cache. The download
is bounded to 5 MiB, decoded and resized locally, then published through
an atomic PNG file replacement. Unsafe linked preview cache paths are rejected,
and a failed write preserves the prior image. Older, non-3.2 identities retain
their established cache location for compatibility.

**Fit buttons to grid** now commits its candidate geometry before adopting
it in the editor. Storage failures leave the previous zones intact and report
the problem instead of silently implying success. A failed delayed zone-label
size write is also reported without crashing the Tk callback.

## One clear entrance

A **Get started** button appears beside the Anything Plays title. The
optional, non-modal getting-started window provides a four-step path:

1. **Pick a console:** focus the main-window console selector. The software
   includes no ROMs, proprietary BIOS files, or commercial game assets.
2. **Choose how to control it:** optionally run guided camera calibration.
   Users can skip the webcam entirely for keyboard and compatible controller
   input.
3. **Test inputs:** open the controller/keyboard setup guide. The separate
   controller dialog now includes physical **press-to-remap** input capture
   and keeps button mapping visible in a scrollable area.
4. **Check and play:** open local, privacy-safe troubleshooting. An
   **Open a game…** button provides the existing user-ROM loading path.

Merely opening the launchpad never accesses a camera, starts SDL, starts an
emulator, arms camera input, reads or copies game files, or phones home.
All actions are explicit buttons. Each separate guide remains non-modal so a
user can interact with the existing camera, console and input panes.

## Webcam refresh keeps the user's choice

Refreshing the camera list now retains the previously selected webcam when
the exact enumerated device is still present, even if discovery order changes.
When that webcam disappears, the interface selects the first available device
but asks the user to verify it before clicking **Use camera**. Refresh stops
capture and camera-based gameplay input; it never automatically starts a
newly discovered or substituted camera. If a live camera disconnects while
the dropdown points to a different device, retry is canceled rather than
silently opening that new camera. Old retry callbacks also cannot clear
another camera's pending retry token. Selection regression tests and real
source/installed Tk GUI smoke cover discovery without opening a webcam.

## Calibration safety and guidance

The calibration guide monitors the existing camera feed, with at most 90
temporary (center, zone) observations, and retains no video data. Its advice
is based on observed color matches and zone hits, **not** a fabricated
accuracy percentage. It now asks users to collect at least eight frames and
observe the object at least once after sampling before saving.

A new optional **Check stationary jitter** action asks you to hold the sampled
target still for 45 live frames. It reports median and 95th-percentile target
position variation in pixels, plus lost detections. It never records images,
starts a second camera or arms gameplay. Deliberate movement during the hold
also raises the metric, so it is **not** a tracking accuracy score. The small
position-only buffer is cleared on camera changes, resampling and exit.

Closing the application during unfinished calibration cancels it **before**
the normal shutdown profile save. Cancel and switching consoles restore the
exact pre-calibration profile. Saves are never silently approved by closing
a window.

## Live theme parity

All four 3.2 setup windows remain non-modal. Their native scroll canvases
now follow live theme changes made in the main window, including light/dark
switches, rather than leaving white surfaces in a dark interface. The Tk
variable observers detach when each child dialog is destroyed, preventing
stale callbacks during later theme changes or shutdown. This is covered by
headless Tcl lifetime tests and by the integrated Xvfb GUI smoke.

## Controller input safety

When choosing an in-game button and physically pressing a controller
control, the app ignores any button already held before capture started,
rejects ambiguous simultaneous new inputs, requires focus, and suppresses
controller-to-game input during capture **and until release**. Other consoles'
controller mappings are unchanged.

When Anything Plays loses keyboard/window focus, controller input is released.
Returning to the app does not replay a button that was pressed or held in
another window: the physical controller must first return to a neutral,
released state. A short status message explains why input is temporarily
paused. The press-to-remap guard remains independent of this focus safety
check. Reconnecting a USB/Bluetooth controller or changing from one pad to
another also suppresses held inputs until the newly connected controller
provides a neutral release sample; first-time enabling the controller
remains responsive without an artificial delay. Manual Rescan follows the
same neutral-release handoff rule. A hotplug during Press to assign cancels
that mapping rather than treating a new device's first button as the old
device's intended control. Synthetic connection, focus and remap tests
run in source CI and in each native preview installer's preflight;
these tests do not certify physical Bluetooth or USB hardware.

## Automated real Tk setup smoke

The integration branch now adds `tests/smoke_v32_gui.py` to the standard
source-check workflow, executed under Xvfb on Python 3.12 and 3.13. Unlike a
pure source-contract test, this starts the real App and Tk root with temporary
preferences, opens the Get started launchpad, calibration wizard, controller
helper and setup troubleshooter, checks that calibration cannot arm object
controls, copies and checks a redacted diagnostic report, and closes each UI.
Device enumeration is suppressed and no physical hardware is used.

The smoke is an **automated GUI lifecycle check only**; it is not evidence
that USB cameras, Bluetooth controllers or commercial game files work.

## Live readiness in Get started

The **Get started** launchpad now displays four concise local status lines:
emulator, camera, controller, and input path. **Refresh status** reads the
same strictly redacted setup snapshot as **Check my setup** without opening
a camera, connecting a controller, launching a core, scanning a ROM or
reaching the network. It updates when the chosen console changes, including
an explicit **Not bundled in this 3.2 preview** label for unavailable
console profiles. The camera and controller are clearly described as
optional. Real source Tk and all four frozen installed-GUI lifecycle
checks exercise this summary and its refresh action.

## Fresh emulator availability checks

**Check my setup → Refresh checks** now performs a read-only core lookup for
the currently selected emulator instead of trusting an old cached core path.
This correctly recognizes a newly installed or removed approved core pack
without restarting the application and avoids treating a previous console's
core as ready for another console. No core is loaded, no ROM is read, and no
device or network connection is opened. Diagnostic reports remain strictly
allowlisted with no native file paths. Unit tests plus source and installed
Tk tests cover stale core references and truthful limited-preview status.

## Game video cleanup on console switching

Switching console profiles now stops the previous game, deactivates manual
controls and explicitly clears the old native video buffer under its lock.
It also invalidates cached Tk game frames, Game-only view, Stream Mode game
snapshots and the game bezel before selecting the next emulator. This avoids
a prior console's image appearing after a new system has been chosen, even
if no new ROM is started. Source Tk and all four native installed-GUI checks
seed synthetic old frames to verify cleanup; no game ROM or native core is
required for these tests.

## Unified game-video cleanup

**Unload game**, changing console profiles, and rejecting a missing preview
core now share one game-display cleanup path. The old native frame is erased
under the emulator lock, the frame revision advances, the primary/Game-only
Tk image caches and the Stream Mode game/output images are cleared, and
the game bezel returns to idle. This happens even if a secondary Tk view was
closed immediately before unload. Camera stream snapshots are preserved.
Source unit tests and real source/frozen Tk tests assert the absence of stale
game pixels; none of these checks load a game ROM.

## Release acceptance remaining

- Full source and four-platform synthetic UI/soak tests on the integrated
  candidate.
- Real webcam, permissions, disconnection and 30-minute camera/input tests.
- Real USB/Bluetooth gamepad connection, release and button-capture checks.
- GUI review of all dialogs at compact window dimensions and 16 themes.
- Correct optional webcam path and separate external emulator messaging.
- Preview artifact/install tests without changing the public stable release.
- Third-party redistribution/source and installer license verification.

Only after those gates should this candidate be proposed for a public v3.2
release. Automated synthetic success alone is insufficient hardware evidence.
