# Security policy

## Reporting a vulnerability

Use [GitHub's private vulnerability reporting](https://github.com/MasynNay/anything-plays/security/advisories/new) if enabled. If the feature is unavailable, contact the maintainer privately through an established project contact rather than posting exploit details publicly. Never upload commercial games, proprietary console firmware, private preferences or personal camera footage to a public issue.

## Supported releases

| Release | Status |
| --- | --- |
| **3.0.x** | Current published release line; fixes reviewed through issues and tagged updates |
| **2.0.x** | Previous stable release; historical downloads remain available |
| **1.5.x** | Historical release; migrate to 3.0 when compatible |

The current public version is [Anything Plays 3.0.0](https://github.com/MasynNay/anything-plays/releases/tag/v3.0.0). This community portfolio project does not guarantee commercial support or fixed security-response times.

## Trust boundaries

Anything Plays works with local cameras, user-supplied game files and native emulator libraries. Only install verified releases from the official repository; compare SHA256 checksums with the matching release manifest. Never load arbitrary DLL, SO or DYLIB files from untrusted sources. Keep untrusted ROMs and native code outside the version-controlled source tree.

The official 3.0 release contains 11 original-source-built emulator cores and includes corresponding source archives and original third-party notices. Build-time source downloads are pinned and verified for the released core lineup. No commercial ROMs or proprietary console firmware are distributed. Consult [the source audit](docs/V3_0_EXACT_RUNTIME_LICENSE_SCOPE.md) and [release evidence](docs/V3_0_SOURCE_FIRST_RELEASE_DECISION.md) for precise scope.

We welcome reproducible vulnerability reports, responsibly disclosed through private channels before public technical details are posted.
