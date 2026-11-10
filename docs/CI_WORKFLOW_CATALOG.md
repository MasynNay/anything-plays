# Anything Plays — GitHub Actions

Actions are grouped by purpose. Routine development, platform integration, and publication are separate so a passing exploratory test is not confused with a published release.

| Purpose | Main workflows |
| --- | --- |
| **Code quality** | `ci.yml`: Python regression tests, repository hygiene and package checks |
| **Portfolio site** | `pages.yml`: build and deploy the static site from `site/` |
| **Original emulator source integrity** | `v30-current-tia-source-proof.yml`: cross-check all 44 installed native libraries against 11 pinned upstream Git source trees and 37 Dolphin Gitlink sources |
| **Complete four-platform desktop build** | `v30-retain-four-offline-v3-installers.yml`: source-build, install and test all 18 profiles and save real installer artifacts |
| **Public 3.0 publication** | `v30-publish-source-first-public-3-0.yml`: publish the original source archive first, then verified genuine `3.0.0` installers once the exact successful four-platform run is available |
| **Production approval research** | `v30-production-candidates.yml`, `v30-publish-approved.yml`: stricter historical/manual release-lock route retained for audit |
| **Specialized regression tests** | `v30-n64-restart.yml`, `v30-ngp.yml`, `v30-endurance.yml`, `v30-virtual-aquarium.yml` and other targeted native playback workflows |

The many additional `v30-*` files record historical experiments, isolated core builds, platform diagnostics, and earlier license/source investigations. They are retained for reproducibility, **not** endorsements of whichever core names were in the older experiments. For the selected 3.0 core lineup, use the [current original-source report](../docs/V3_0_EXACT_RUNTIME_LICENSE_SCOPE.md).

## Archived release-candidate workflows

Obsolete **2.0 and 3.0 private release-draft jobs** have been moved to [historical workflows](../docs/history/workflows/) so the Actions menu focuses on useful current engineering. These archived definitions are preserved for provenance and are not active GitHub Actions workflows. The stable 1.5, 2.0 and 3.0 releases are unaffected.

## Historical 3.0 research workflows

The original developer-preview experiments below have been **archived**, not erased. They no longer appear as executable Actions. Their verified runs and exact source definitions remain in [the historical workflow folder](history/workflows/). The present-day CI, platform builds, source audit, release publisher and manual regression workflows remain under `.github/workflows/`.

Archived in this cleanup: `capture-sources.yml`, `v30-corresponding-source-access.yml`, `v30-dolphin-complete-source-bundle.yml`, `v30-dolphin-original-linux-build.yml`, `v30-dolphin-original-macos-source.yml`, `v30-dolphin-original-windows-source.yml`, `v30-dolphin-pinned-source-sys.yml`, `v30-eleven-source-offline-integration.yml`, `v30-eleven-tia-source-offline-integration.yml`, `v30-four-platform-source-evidence-review.yml`, `v30-parallel-n64-original-native.yml`, `v30-pce-source-delta.yml`, `v30-tia-corresponding-source-access.yml`, `v30-source-snapshots.yml`.

## Release safety

- A successful CI run verifies the specific conditions tested, not every commercial game or physical device.
- The current 3.0 application uses eleven original-source-built native emulator libraries, including Tia rather than the old Stella2014 build.
- Public assets must have matching binary hashes, corresponding source code and accurate release notes. The source-first publisher is distinct from private draft creation.
- **Published downloads:** [GitHub Releases](https://github.com/MasynNay/anything-plays/releases/latest). Private draft and workflow artifacts are not public releases.
- Older public version 2.0 installers remain separate and unchanged.

For local development, see [Contributing](../CONTRIBUTING.md), [Architecture](../docs/ARCHITECTURE.md), and [technical documentation](../docs/README.md). Detailed CI reproduction and license provenance belong in those documents, not the repository landing page.
