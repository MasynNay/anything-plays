# Anything Plays 3.1 RC1 — Full 18-console QA downloads

## Persistent four-OS owner QA collection — November 10, 2026

**[Download the complete 3.1 RC1 owner QA collection](https://github.com/MasynNay/anything-plays/actions/runs/42911996640)**
from the GitHub Actions run's **Artifacts** section. This new
**472 MB** artifact contains the exact independently verified Windows
x64, Linux x64, macOS Intel, and macOS Apple Silicon installers;
original pygame/SDL source candidates; five original SDL LICENSE.txt
notices; the SHA256SUMS.txt checksum list; the strict QA receipt; and
explicit draft release notes. Verified in workflow
[42911996640](https://github.com/MasynNay/anything-plays/actions/runs/42911996640).

**Retained through February 8, 2027** rather than November 17, 2026.
The older per-platform seven-day artifacts may expire; prefer this
combined 90-day collection. These packages are still **RC1, not stable
3.1.0**; no physical controller/game ROM guarantees or public
redistribution authorization are claimed. The SHA-256 manifest checks
the installer bytes before use. Opening a GitHub Actions download
may require signing in to GitHub.

### Why this is an Actions download instead of a GitHub release

A complete verified release-draft preparation pipeline ran, but the
GitHub Releases API returned **HTTP 403 Resource not accessible by
integration** when creating an owner-only `v3.1.0-rc1` draft, despite
the job receiving a `Contents: write` token. This is a GitHub publishing
authorization problem, **not a failed installer build**. The workflow
was changed to retain the same bytes for 90 days with read-only
repository permissions, rather than repeatedly requesting the denied
API action. A draft release was **not** created. Do not silently
reinterpret successful QA as legal or hardware approval.

**Latest four-target QA: November 10, 2026.** The current full-console
unreleased artifacts were compiled from the updated controller-recovery app
(`26de1e1ad1b701d0735e085158347f8c213ce437`) on all four OS hosts.
Four full installers and their SHA-256 receipts were verified in
[run 42905694504](https://github.com/MasynNay/anything-plays/actions/runs/42905694504), and **all four actual installed GUI
and stable-settings migration tests passed** in
[run 42906122307](https://github.com/MasynNay/anything-plays/actions/runs/42906122307). The latest signed macOS SDL linkage,
load-order and virtual native joystick checks also passed in
[runs 42906227613](https://github.com/MasynNay/anything-plays/actions/runs/42906227613),
[42906533407](https://github.com/MasynNay/anything-plays/actions/runs/42906533407) and
[42906533323](https://github.com/MasynNay/anything-plays/actions/runs/42906533323). The pygame source/wheel audit
[42906334464](https://github.com/MasynNay/anything-plays/actions/runs/42906334464) passed technical verification,
**not complete LGPL source correspondence or redistribution authorization**.

All four current full RC artifacts are retained through **November 17,
2026, approximately 21:31–21:33 UTC**. These are private/owner
development QA ZIPs, not publicly released stable 3.1.0 installers.
No real USB/Bluetooth gamepad or commercial gameplay was tested in CI.


**Temporary owner QA, not the public 3.1.0 release.** Latest exact native source app revision
`26de1e1ad1b701d0735e085158347f8c213ce437` includes atomic candidate preference migration.
The [four-platform installed migration run 42906122307](https://github.com/MasynNay/anything-plays/actions/runs/42906122307)
**PASSED**: RC settings were created from a disposable 3.0-style
profile and the original files remained byte-identical. The current packages contain the new Copy diagnostics controller action and have passed actual installed GUI startup on all four platforms in run 42906122307. Unlike earlier
Preview 2 installers, these RC1 packages use **fresh platform-native
3.1 application builds**, [verified at source run 42904937464](https://github.com/MasynNay/anything-plays/actions/runs/42904937464),
plus eleven **original-source emulator core binaries** whose exact byte
hashes come from the existing public stable 3.0.0. No ROMs or firmware.

## Where the RC1 full installers are built

The [full RC1 QA Actions run 42905694504](https://github.com/MasynNay/anything-plays/actions/runs/42905694504)
builds the packages separately. For each **green** platform job, open
its Actions run and use the **Artifacts** section to download the
appropriately named ZIP. GitHub sign-in may be required.

| Computer | QA artifact ZIP name | Installer inside |
| --- | --- | --- |
| Linux x64, Debian/Ubuntu | `AnythingPlays-3.1-RC1-FULL-18-linux-x64-UNRELEASED` | `anything-plays-31-rc1_3.1.0~rc1full_amd64.deb` |
| Windows x64 | `AnythingPlays-3.1-RC1-FULL-18-windows-x64-UNRELEASED` | `AnythingPlaysSetup-3.1.0-rc1-full.exe` |
| macOS Apple Silicon | `AnythingPlays-3.1-RC1-FULL-18-macos-arm64-UNRELEASED` | `AnythingPlays-3.1.0-rc1-full-macos-arm64.dmg` |
| macOS Intel | `AnythingPlays-3.1-RC1-FULL-18-macos-x64-UNRELEASED` | `AnythingPlays-3.1.0-rc1-full-macos-x64.dmg` |

**Only download a platform after its job has succeeded and the named
artifact actually appears.** The files are retained for seven days
(approximately through November 17, 2026), not permanent releases.

Each ZIP includes its platform-specific `FULL_*_QA_RECEIPT.json`
with the expected installer SHA-256 and
`SDL_RUNTIME_AUDIT.json` containing the frozen Python/SDL runtime
inventory. Compare the installer hash **before installing**:

- Windows PowerShell: `Get-FileHash -Algorithm SHA256 .\AnythingPlaysSetup-3.1.0-rc1-full.exe`
- macOS: `shasum -a 256 AnythingPlays-3.1.0-rc1-full-macos-*.dmg`
- Linux: `sha256sum 'anything-plays-31-rc1_3.1.0~rc1full_amd64.deb'`

## Quick test plan

1. **Keep stable 3.0 installed.** RC1 uses a separate app ID, desktop
   launcher and settings namespace and must not overwrite the original.
2. Start RC1 and confirm the title **Anything Plays 3.1 · Release
   Candidate 1**. The previous application should remain available
   separately.
3. Open controller configuration on the right. Verify the visual
   diagram, status, per-console mapping dropdowns and **Live Controller
   Test**. Its default disconnected state must be understandable.
   Use **Copy diagnostics** and verify the clipboard confirmation remains visible; no ROM names or camera images are included.
4. Confirm all **18 supported console profiles** appear; inspect
   N64 and GameCube along with the handhelds. The native cores are
   checked by CI but individual game compatibility is not universal.
5. If a USB/Bluetooth controller is available, test each face button,
   D-pad, sticks, triggers, mapping remaps, focus loss, disconnect,
   reconnect and Rescan. Report exact model, OS and outcome. Synthetic
   CI passes do **not** establish physical-device success.
6. With your own game files, test one save/reload and repeated
   game switching, then run the application for a long session to
   check that camera, sound, controller input and memory stay healthy.

For Linux, install from the extracted ZIP directory:

```bash
sudo apt install './anything-plays-31-rc1_3.1.0~rc1full_amd64.deb'
```

On Windows use the candidate Setup executable. On macOS mount the
candidate DMG and launch `AnythingPlays31RC.app`. Mac packages may
be ad-hoc signed but are not notarized; use normal macOS installation
controls rather than disabling system protections.

## What remains before stable 3.1.0

The full RC1 workflow is release **engineering QA**, not the guarded
public publisher. Physical controller compatibility, installed
gameplay/endurance results, complete pygame/SDL corresponding-source
and LGPL relinking review, stable installer identity/migration,
final README/website/release notes and explicit acceptance remain open.
Stable [3.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0)
is unchanged; [draft PR #156](https://github.com/MasynNay/anything-plays/pull/156)
holds the 3.1 work.
