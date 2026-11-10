# Anything Plays 3.1 — Atomic settings migration and install acceptance

**Development-only protection.** All QA channels and the public-release gate
remain closed. This change affects the 3.1 development branch; stable public
3.0.0 and the user's established settings remain untouched.

## The failure mode we removed

Older 3.1 preview/RC startup seeded settings by opening the final
`preferences.json` and `system_profiles.json` destinations directly.
An interrupted copy could leave half-written JSON. A concurrent failure
handler could also delete a file another instance had just created.

The new `anything_plays/test_preferences.py` handles startup migration
as a **complete, create-only copy**:

1. Validate the chosen `preview1` or `rc1` identity and keep it in
   a settings namespace separate from 3.0.
2. Read the prior preview or legacy settings **without changing them**,
   skipping unsafe linked source files and linked source directories.
3. Make an isolated, size-bounded temporary copy inside the *candidate*
   settings directory, flush it and sync it to disk.
4. Publish the completed copy by an atomic create-only hard link.
   A pre-existing candidate file wins. A filesystem unable to support
   atomic publication falls back to safe defaults, not a half-written
   preferences file.
5. Remove only the temporary file that **this** process created.
   Never unlink an existing destination on migration failure.
6. Refuse candidate directory and file symlinks, including a symlink
   inserted by another process while publication was attempted.

This protects actual stable data and customized 3.1 user settings even
when multiple instances of the test application start simultaneously.
It does not automatically migrate RC preferences into future stable
3.1: any such upgrade still needs its own reviewed release pathway.

## Tests added

`tests/test_v31_preferences_atomic.py` covers:

- RC and preview channel migration priorities
- Stable settings unchanged after candidate customization
- 32 concurrent starts without missing/partial target files
- Failed hard-link publication, cleanup and source size limits
- Existing candidate files preserved without overwriting
- Malicious symlinked old settings, candidate directories and files
- A competing process introducing a candidate symlink during a copy

`tests/test_v31_installed_settings_migration.py` covers an additional
**disposable HOME fixture**:

- `tools/qa_v31_installed_settings_migration.py seed` creates two
  stable-style test files and their SHA-256 checksums in a fresh,
  empty temporary home only (never the real user's home)
- Running the source migration against this fixture generates a
  distinct RC candidate copy
- `verify` requires the RC theme to have migrated and both original
  stable settings files to retain their exact SHA-256 bytes
- Tampering, missing RC files, aliasing, invalid manifests and
  attempted use of a populated or real HOME fail closed

Run the narrow tests without launching an emulator:

```bash
python -m unittest discover -s tests -p 'test_v31_preferences_atomic.py' -v
python -m unittest discover -s tests -p 'test_v31_installed_settings_migration.py' -v
```

The separate four-platform source CI suite also runs both safety suites.
A passing source test validates the implementation, but **does not**
prove that a frozen installer used this newer copy logic.

## Frozen installed-application acceptance

**VERIFIED 4/4** in [installed-app run 42895538165](https://github.com/MasynNay/anything-plays/actions/runs/42895538165),
using **the actual freshly rebuilt full 18-console RC1 installers**
from [run 42894172881](https://github.com/MasynNay/anything-plays/actions/runs/42894172881). All four native hosts ran the
frozen Tk application in a disposable user profile seeded with
known 3.0-style stable settings (theme: `Plum Dark`). The
workflow then independently verified:

- RC1's separate `anything-plays-31-rc1` settings namespace exists,
  with the migrated preference theme and profiles file;
- The original stable `fish-plays-pokemon-studio` preferences and
  system profiles still match their **exact before-start SHA-256**;
- The actual frozen application initialized its Tk window and ran its
  event loop without startup errors, and all 18 console profiles
  and 11 native core families remained packaged;
- No physical camera, controller, licensed game ROM or user's real
  home directory was required or modified.

Each successful platform job uploaded
`FROZEN_UI_SMOKE.json`, `RC1_INSTALLED_UI_RECEIPT.json`,
`SETTINGS_QA_FIXTURE.json` and
`RC1_INSTALLED_SETTINGS_RECEIPT.json` as independently retained
QA artifacts. These report temporary test-home scenarios, not
every possible installed-user upgrade condition or a public stable
3.1.0 migration approval. The
[four-platform concurrent-copy and adversarial source tests](https://github.com/MasynNay/anything-plays/actions/runs/42893632730)
also **PASSED 4/4**.

This migration work is not physical USB/Bluetooth controller,
camera, real-game/save, LGPL, relinking or redistributable source
acceptance. All public stable 3.1 gates remain blocked.
