# GitHub Actions organization

GitHub requires workflow definitions under this folder. Different files deliberately separate four-platform packaging from individual emulator acceptance and historical releases.

| Workflow | Job |
| --- | --- |
| **ci.yml** | Source tests, GUI smoke, repository hygiene and release-branch package checks |
| **v30-full-bundle.yml** | Four-platform, 11-core offline preview installers and original archive capture |
| **v30-app.yml** | Lightweight application previews |
| **v30-cores.yml** | Native emulator and update verification |
| **v30-ngp.yml** | Dedicated NGP/NGPC audio, video, controls and save tests |
| **v30-pce-pinned-source.yml** | Experimental four-platform PCE core built from exact GPL source and tested with original HuCard PCM/video |
| **v30-pce-offline-integration.yml** | Test all 18 profiles and 11 offline native cores using a verified source-built PCE replacement while retaining original other-core ZIPs |
| **v30-pce-source-delta.yml** | Assemble 11-source review matrix from four verified integrated PCE trial artifacts, retaining unknown old nightly and unapproved rights flags |
| **v30-endurance.yml** | Stability and long-session checks |
| **v30-n64-restart.yml** | N64 repeated-launch checks |
| **v30-virtual-aquarium.yml** | Camera control simulation |
| **v30-lab.yml** | Experimental emulator diagnostics |
| **capture-sources.yml** | Source provenance |
| **candidate-draft.yml**, **release.yml** | Historical, controlled 2.0 release workflows |
| **v30-publish-approved.yml** | Manual only, verified production-only 3.0 release publication (fail closed) |
| **v30-production-candidates.yml** | Manual only, four-target immutable 3.0 installer producer; cannot publish releases |
| **v30-source-snapshots.yml** | Preserve reported upstream source revisions as unapproved Actions evidence |
| **v30-freeze-inputs.yml** | Manually produce an unapproved four-platform 48-archive fingerprint record from saved native inputs |
| **v30-source-review-matrix.yml** | Join all 44 binary identities with ten pinned source archives into a 3.0 review-only artifact, approval flags false |

Every workflow has different evidence boundaries. Passing a preview build does not authorize a stable release. Native redistribution, required sources, signing and real-device QA are tracked in [release readiness](../../docs/V3_DISTRIBUTION_READINESS.md) and the [fail-closed release checker](../../tools/check_v30_release.py).

The 3.0 working branch is **feature/v3.0-unified-test**. Do not publish directly from a mutable nightly download or treat a passing developer test as legal approval.
