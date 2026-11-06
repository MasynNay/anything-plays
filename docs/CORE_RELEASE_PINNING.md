# v2.0 native core release lock

**Status: exact v2.0.0 core hashes approved for the [published free/noncommercial release](https://github.com/MasynNay/anything-plays/releases/tag/v2.0.0).** The historical candidate-building steps below are retained as an audit trail. See [distribution review](RELEASE_DISTRIBUTION_REVIEW.md) and [RC6 verification](RC6_VERIFICATION.md).

The existing Anything Plays v2.0 app has been functionally tested on Windows,
macOS and Ubuntu. The later mGBA GB/GBC transition and both core packaging paths
also passed automated integration tests. This procedure does not require
repeating the earlier gameplay tests for metadata-only changes.

## Why this control exists

The normal development build downloads the matching mGBA and Snes9x archives
from Libretro's changing `latest` URLs. A version string, URL or Git hash
alone does not prove that a downloaded binary was built from a particular
source tree. A new nightly can replace an older one at the same URL.

**Official release mode never downloads those nightlies.** It requires
`AP_CORE_ARCHIVE_DIR` to point to a local directory containing preserved
ZIPs for the runner's platform, such as:

```text
approved-core-zips/
  mgba_libretro.so.zip
  snes9x_libretro.so.zip
```

Use the `.dll.zip` filenames for Windows or `.dylib.zip` filenames for
macOS. Windows and macOS Intel/Apple Silicon archives must be staged in
separate architecture-specific runner directories, since the macOS filenames
are identical across architectures. A missing ZIP stops the build without
network fallback. The binary extracted from each ZIP must still match the
approved lock's SHA-256, file size, and identity.

`AP_RELEASE_BUILD=1 AP_CORE_ARCHIVE_DIR=/path/to/approved-core-zips`
is the intended release environment, after redistribution approval and
immutable inputs are actually provided.

With `AP_RELEASE_BUILD=1`, `fetch_mgba_core.py` and `verify_bundle.py`
require the approved fingerprints in [the lock](../config/v2.0-core-lock.json).
They compare the actual download's hash, byte count, Libretro version,
reported revision and source repository against the lock. Builds fail closed
if a fingerprint changes, if an architecture is missing, or if
`approved_for_binary_distribution` is not explicitly `true`.

The old automatic rebuild workflow remains **disabled**. The reviewed
one-time publish workflow promoted only exact verified RC6 binaries after
checking the approved lock, complete source and SHA-256 manifests. A Git tag
alone still cannot download changing nightly core builds.

## Core identities observed in passing platform checks

These are *reported* source revisions, independently confirmed to exist in the
respective upstream repositories. They are **not** independently verified
build-to-source correspondence.

| Core | Reported version | Upstream commit |
| --- | --- | --- |
| mGBA | `0.11-212-7a12d6d` | [`7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6`](https://github.com/libretro/mgba/commit/7a12d6d4b9acb14c0ae62c9166b6a2f3d08007f6) |
| Snes9x | `1.63 fae2fea` | [`fae2fea08f74180759ef540ee94259213f503480`](https://github.com/libretro/snes9x/commit/fae2fea08f74180759ef540ee94259213f503480) |

The same reported versions appeared on Windows x64, Linux x64, macOS arm64
and macOS x86_64 in [the passing audited package build](https://github.com/MasynNay/anything-plays/actions/runs/42163068042).

## Captured candidate fingerprints

The candidate lock now includes exact SHA-256 checksums, byte sizes, reported
versions and upstream full source identifiers for **all eight native core
binaries** (mGBA and Snes9x for each of four target architectures).
[Inspect these candidate values](../config/v2.0-core-lock.json). All remain
**unapproved for public distribution**, but the original eight archived ZIPs
and complete mGBA/Snes9x upstream source snapshots **have now been retained**
in the 31-asset [private RC5 draft](RC5_VERIFICATION.md). The release job
checked every original ZIP and extracted binary against the recorded hashes
before building. Retention proves artifact identity; it does **not** independently
reproduce the upstream buildbot's binaries or establish redistribution rights.

## Required release procedure

1. Review the candidate fingerprints already recorded for all four targets
   in [the unapproved core lock](../config/v2.0-core-lock.json):
   `windows-x86_64`, `linux-x86_64`, `macos-arm64`, and
   `macos-x86_64`. These were captured from [passing CI run 42164654048](https://github.com/MasynNay/anything-plays/actions/runs/42164654048), not independently reproduced; ordinary development builds can emit newer candidates without approving them.
2. **Do not ship directly from mutable nightly URLs.** Preserve exact approved
   binary archives in an immutable, access-controlled release-build input
   location. Verify their cryptographic hashes before use.
3. Independently associate each approved binary with its exact upstream
   source (including build options, patches, submodules and third-party
   libraries). Obtain and retain corresponding source, including all
   redistribution-required license/copyright notices.
4. Complete the license review for the noncommercial Snes9x distribution,
   mGBA under MPL 2.0, Python/native dependencies, and project artwork.
   Seek qualified counsel/rights-holder clarification where needed.
5. Populate each `targets` entry in the lock with the exact candidate
   fields and the full, reviewed `source_commit_sha`. Never infer a full
   commit from a short hash without verifying it upstream.
6. After the release owner approves all required evidence, set
   `approved_for_binary_distribution` to `true` in a reviewed PR.
   Re-enable the release workflow in a **separate** reviewed change that
   pins all build inputs. Do not remove the release-mode fingerprint checks.
7. Build the final packages, verify their contents and hashes, document
   unsigned Windows/macOS prompts and notarization limitations, then
   publish the release and checksum manifest.

## Scope and limitations

- A successful lock check proves identity against *approved recorded values*,
  not license compliance, reproducible builds, or ownership of source assets.
- A mutable URL may stop working once its content changes; the correct
  solution is an immutable approved binary archive, **not** weakening the lock.
- The lock contains exact fingerprints from the original four-architecture
  candidates and was approved **only for the unchanged v2.0.0 bytes** in
  [the release decision](RELEASE_DISTRIBUTION_REVIEW.md). A new binary version
  requires a new approval, independently of CI or any Git tag.
- `AP_RELEASE_BUILD=0` was used to assemble privately reviewed RC6
  candidates from immutable pinned inputs. The official published installers
  were promoted *byte for byte* only after an independent promotion check
  against the approved release lock. Never publish an arbitrary development
  build merely because that environment variable is set.
- Original GB/GBC save and video compatibility was tested separately with
  native mGBA using generated synthetic ROMs. Other cartridge mappers require
  their own compatibility evidence if included in release claims.
