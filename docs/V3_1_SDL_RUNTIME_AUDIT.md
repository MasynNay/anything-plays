# Anything Plays 3.1: SDL frozen-runtime evidence (unreleased)

This audit makes the pygame-ce/SDL controller dependency in **actual installed
packages** inspectable before licensing, source access, or final release
decisions. The project stays at public stable **3.0.0** until 3.1 acceptance
is complete. A report from this tool is **not a legal compliance certificate**.

## Rebuilt controller UI, full 18-system QA

The four-platform 3.1 Preview 1 build
[run 42853582632](https://github.com/MasynNay/anything-plays/actions/runs/42853582632)
passed and includes the read-only live button tester and immediate button
release on Rescan (application source revision
`d176ff54de90a3cc5e585c6fc6ffd4f68388c104`).

The three full-console assembly jobs now **explicitly pin that exact run and
its commit**, validate each preview installer against its SHA-256 receipt,
verify the public 3.0.0 native payload against the release SHA-256 file, and
reassemble the 11 original-source emulator cores / 18 console profiles as
distinct **Preview 2 test packages**, not stable 3.1.0.

- Linux: `.github/workflows/v31-full-linux-qa.yml`
- Windows: `.github/workflows/v31-full-windows-qa.yml`
- macOS ARM and Intel: `.github/workflows/v31-full-macos-qa.yml`

The jobs retain the installer, full-console verification receipt, and
`SDL_RUNTIME_AUDIT.json` as a temporary Actions artifact. The three original
input workflows remain non-release workflows with read-only GitHub
permissions; the public 3.0 install identity is unchanged.

## What the audit checks

Run `python tools/audit_v31_sdl_runtime.py --target linux-x64
--bundle /path/to/unpacked/app --output /path/to/SDL_RUNTIME_AUDIT.json`
with a **real extracted application directory**, not the build environment.

The tool refuses to create a success record unless:

1. The frozen package's actual
   `licenses/PYTHON_DISTRIBUTIONS.json` lists **exactly one pygame-ce 2.5.8**
   distribution and wheel-provided notice files.
2. Every recorded notice exists in the frozen package, is regular, nonempty,
   unsymlinked and inside the application. Unsafe paths are rejected.
3. At least one native pygame or SDL library/extension is present. All
   matching candidates and wheel notices are hashed with SHA-256 and their
   exact paths and sizes recorded.
4. Each original full-console archive and its provenance receipt has already
   passed its independent build-specific validation.

On a Mac the notice root is inside
`AnythingPlays31Preview.app/Contents/Resources/licenses/`; on Linux
and Windows it is under the unpacked application's `licenses/`.
The Mac audit happens against the **mounted final QA DMG**; the Windows
audit runs on a **freshly installed** Setup, and Linux against the
**re-extracted completed DEB**.

Adversarial tests cover missing notices, mismatched pygame versions,
duplicate metadata, forged paths, symlinked native candidates, and missing
pygame extensions. Tests are source-only and do not require a controller.

## What remains **unverified**

The audit lists candidate shared libraries. It does **not** determine
whether SDL is statically or dynamically linked, trace all recursive
native dependencies, certify LGPL compliance, or independently authenticate
the exact source tree used to build a particular wheel.

Before a stable release:

- Match each **platform's actual packaged pygame-ce wheel and bundled SDL
  binaries** to exact versions/build provenance and original source.
- Confirm individual notices and permissions for included native libraries,
  including any components introduced by PyInstaller collection.
- Review LGPL source access and end-user replacement/relinking conditions
  for the compiled installer layout. Record concrete evidence; do not
  infer approval from the presence of a LICENSE file.
- Test actual USB/Bluetooth controller behavior and complete the
  real-game, save/reload and long-session acceptance checklist.
- Build and inspect **actual version-identity-correct 3.1.0 installers**.
  Renaming Preview 2 files is not acceptable.

The report always sets
`sdl_linkage_reviewed`, `original_sources_verified`,
`lgpl_relinking_reviewed`, and `redistribution_approved` to **false**.
Only separate documented review and source packaging can close these gates.

See [release acceptance](V3_1_RELEASE_ACCEPTANCE.md) and
[draft PR #156](https://github.com/MasynNay/anything-plays/pull/156).
