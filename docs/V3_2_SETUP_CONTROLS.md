# Anything Plays 3.2 — Setup and controls (development)

This is **in-progress source development**, not a public 3.2 release. Public
3.1.1 installers and release notes are unchanged.

## Portable control profiles — first 3.2 workstream

The 3.1 profile buttons previously saved all in-memory settings into raw JSON,
including a local zone-art image path. A file could also be loaded for the
wrong console without confirmation.

3.2 introduces `anything_plays/portable_profiles.py` with a versioned,
allowlisted transfer format, a local preview/confirmation dialog and an
in-session Undo import action. The existing per-console profile store remains
in place, with atomic JSON persistence.

### Use

1. Choose a console and configure its object color, zones and mappings.
2. Select **Export controls** in the Safety & Profiles section.
3. On another compatible computer, choose the **same console**, then
   **Import controls**. Review the listed zone count, mappings, theme and
   file format. Only then confirm.
4. Camera input stops on import and remains disabled until deliberately armed.
   **Undo import** restores your last pre-import control setup and theme
   during the same application session. Switching consoles does not discard
   that snapshot, but you must switch back to undo.

Older, unversioned JSON saved by the previous **Save profile** button remains
importable. Since the old format did not identify its console, review the
selected console carefully before confirming. Unknown legacy-only settings
such as `zone_image` are ignored rather than copied between machines.

### JSON contract

A valid portable JSON file has a `format` of
`anything-plays-control-profile`, integer `version` `1`, the source console
`system`, a `profile` of validated control settings, and optionally a theme
from the application's installed theme list. Import rejects unknown versions,
wrong consoles, malformed zone rectangles, unexpected settings, invalid
button names, nonfinite numbers, duplicate JSON keys and files over 64 KiB.

The format includes selected RGB colors, tracking tolerance and timing,
normalized button zones/mappings and safe overlay style options. It never
serializes ROMs, firmware, save files, local ROM directories, selected camera
devices, frames, credentials, library art, `zone_image` paths/URLs, external
emulator paths, or machine-specific controller identifiers. Theme import
changes only the named local app theme, not game/stream resources.

Export uses an atomic file replacement. Import validates *before* showing
confirmation; cancellation leaves settings untouched. A failed profile-store
write attempts to restore the previous stored profile and visible UI.

### What to test before merging

- Run the portable regression tests:
  `python -m unittest tests.test_portable_profiles -v`
- Run the existing full test suite and source/native CI on the draft PR.
- Test UI export, preview/cancel, imported appearance, Undo and legacy raw
  profile import on a Tk-capable host.
- Confirm missing/locked export paths show errors without losing existing
  profiles. Confirm controller mappings and other consoles remain unchanged.
- Do not equate simulated tests with actual webcam, gamepad or long-session
  hardware acceptance.

## Remaining 3.2 work

- Guided camera selection, color sampling and stability feedback.
- Clearer controller/keyboard onboarding and live remap explanations.
- First-run diagnostics for permission errors and core/device problems.
- End-to-end usability passes with real cameras/controllers and portable
  profile transfer across supported host operating systems.

No 3.2 release is authorized by this development document.
