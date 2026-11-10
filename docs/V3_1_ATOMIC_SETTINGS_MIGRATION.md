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

The planned final hardware-free acceptance uses the above fixture
with the **actual 18-console RC1 Windows, Linux and two Mac packages**.
The test must override HOME (or USERPROFILE on Windows), boot the
frozen app's real Tk UI in a disposable environment, and then verify
that stable files have not changed and RC settings were created.

Do not claim this final installed-product migration result until a
specific GitHub Actions run has completed on all four platforms.
A compiler success or a unit test is a weaker level of evidence.

This migration work is not physical USB/Bluetooth controller,
camera, real-game/save, LGPL, relinking or redistributable source
acceptance. All public stable 3.1 gates remain blocked.
