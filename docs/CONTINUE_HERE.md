# Anything Plays 3.1 — CONTINUE HERE

Last verified development checkpoint: **November 10, 2026**.
This is a concise, durable handoff for conversations interrupted by
`Error in input stream` and for future release engineers. Do not
repeat full 3.1 assessment or rebuild existing candidate packages
without an actual change requiring a new build.

## Source of truth

- Development branch: `feature/v3.1-controls-usability`.
- Existing draft PR: https://github.com/MasynNay/anything-plays/pull/156
- Latest public stable remains `v3.0.0` (four installers, 18 consoles);
  `v2.0.0` and `v1.5.0` also remain published.
- Actual 3.1 controller runtime source compiled for RC1:
  `26de1e1ad1b701d0735e085158347f8c213ce437`.
- Source-built app QA 4/4: https://github.com/MasynNay/anything-plays/actions/runs/42904937464
- Complete 18-console / 11 native core candidate QA 4/4:
  https://github.com/MasynNay/anything-plays/actions/runs/42905694504
- Actual installed UI / settings migration QA 4/4:
  https://github.com/MasynNay/anything-plays/actions/runs/42906122307
- Source companion and five upstream SDL notice texts:
  https://github.com/MasynNay/anything-plays/actions/runs/42909893531
- Three-minute actual Tk+SDL+synthetic camera endurance:
  https://github.com/MasynNay/anything-plays/actions/runs/42909405091
  PASS: 10,371 changing frames and 0.05 MB post-warmup measured RSS growth.
- Long-retention four-platform installer and source candidate download:
  https://github.com/MasynNay/anything-plays/actions/runs/42911996640
  PASS; seven files preserved as a 472 MB Actions artifact, expiring
  **February 8, 2027**. Source receipts, exact SHA256SUMS and
  audit evidence are included. This is **not a public GitHub Release**.

## Current publishing blocker: GitHub release write permission

- A source/installer validated workflow attempted to create a
  PRIVATE `v3.1.0-rc1` GitHub Release draft in
  https://github.com/MasynNay/anything-plays/actions/runs/42911646991
  and received **HTTP 403: Resource not accessible by integration**
  on the Releases API. The job's permissions section explicitly listed
  `Contents: write`, so simply changing the workflow YAML permission
  declaration is not a proven fix. No `v3.1.0-rc1` draft was created.
- The successful fallback uses a `contents: read` workflow to archive
  exact QA assets with 90-day retention; do not keep retrying the same
  denied release API action until an authorization change is confirmed.
- When GitHub release creation is permitted, create a true *private draft*
  from the verified assets only; do not publish a prerelease or stable
  binary publicly until the release review is complete.

## Remaining real acceptance work, in priority order

1. **Complete SDL/pygame native licensing review:** trace macOS packaged
   signed/thinned native binaries to the exact original builds; verify
   LGPL shared-library replacement/relinking, notices and transitive
   source distribution. Original upstream source candidates are collected,
   but this is not yet a proven complete corresponding-source package.
2. **Final genuine 3.1.0 build identity:** produce and install actual
   version-correct Windows/Linux/Mac packages from 3.1 source; never
   just rename the RC1 `.deb`, `.exe` or `.dmg`. Test isolated upgrade
   from 3.0 with settings/save preservation.
3. **Real-hardware acceptance:** physical SDL gamepad if available,
   camera, actual game loads, saves and audio on final installed binaries.
   Virtual controller/three-minute soak evidence is available but not
   a substitute for real USB/Bluetooth acceptance.
4. **Authorized publication:** use an account/workflow allowed to create
   GitHub Releases. Publish complete corresponding-source materials
   and license notices before or alongside true 3.1.0 installers.
   Verify final public asset SHA256s and update the portfolio site.

## Release safety

`config/v3.1-release-readiness.json` is authoritative; every required
public release gate remains FALSE. This is intentional while rights,
hardware and stable identity are open. Do not modify stable 3.0/2.0
branches, tags, downloads, or existing settings.

Detailed links: [release acceptance](docs/V3_1_RELEASE_ACCEPTANCE.md),
[RC1 owner QA downloads](docs/V3_1_RC_QA_DOWNLOADS.md),
[SDL source review](docs/V3_1_SDL_SOURCE_REVIEW.md),
[source companion](docs/V3_1_SOURCE_COMPANION.md).
