# Asset provenance and public release review

Anything Plays includes original branding and image assets. The MIT source
license covers original source code; it should **not** be assumed to grant
rights to third-party artwork or trademarks.

The maintainer confirms that the original betta fish illustration was commissioned
from an artist, that the maintainer purchased full ownership **or** commercial
rights, and that AI was subsequently used to recolor it. This is a direct
maintainer rights attestation; the original contract or license has not been
independently inspected, and the precise scope (copyright assignment versus
commercial-use license, derivative rights, redistribution, sublicensing) is
not yet documented. Do not interpret this statement alone as permission to
relicense the underlying art under the repository's MIT code license.

The public release must have a documented ownership/permission record for
each asset before publication. Git object IDs below identify the current
repository bytes, but are **not** proof of copyright ownership.

| Asset | Current role / observation | Git object ID (short) | Rights status |
| --- | --- | --- | --- |
| `assets/anything_plays.ico` | Windows installer/application icon | `f58833b1` | Maintainer attests purchased ownership or commercial rights; exact icon derivation and terms unverified |
| `assets/anything_plays.png` | Main logo and application image | `c340dafe` | Maintainer's commissioned betta rights attestation recorded; exact derivation/terms unverified |
| `assets/anything_plays_hd.png` | HD-named copy; identical bytes to `anything_plays.png` | `c340dafe` | Same rights as main logo; deduplication optional |
| `assets/anything_plays_small.png` | Linux desktop icon | `a0b572d7` | Maintainer's commissioned betta rights attestation recorded; exact derivation/terms unverified |
| `assets/betta_gb_advance_original.png` | Historical or alternate image; usage in installers needs confirmation | `96e5af04` | Maintainer's commissioned betta rights attestation recorded; exact derivation/terms unverified |

## Approval checklist

- [x] Record maintainer's statement: original betta fish artwork was commissioned, full ownership or commercial rights were purchased, and it was later AI-recolored.
- [ ] Confirm original agreement covers public redistribution and modified derivatives, and establish whether rights are owned or licensed (the maintainer has not distinguished these two legal arrangements).
- [ ] Record who created each unique image, when, and under which terms.
- [ ] Confirm that official free downloads, repository display, and modified
      icon derivatives are permitted. If an asset came from a third-party tool
      or source, retain applicable terms and attribution.
- [ ] Identify any third-party logos, characters, trademarks, game imagery, or
      brand material and whether their inclusion is authorized; replace
      unlicensed components rather than assuming free distribution suffices.
- [ ] Check exactly which assets are frozen into each platform installer.
- [ ] Record final project-owner approval in the binary release review.

This file documents questions still to be resolved. **It does not assert
permission or transfer ownership.** No gameplay assets or interface graphics
are modified by this review.
