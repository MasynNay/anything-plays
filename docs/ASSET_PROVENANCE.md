# Asset provenance and public release review

Anything Plays includes original branding and image assets. The MIT source
license covers original source code; it should **not** be assumed to grant
rights to third-party artwork or trademarks.

The maintainer reports that the betta fish artwork was commissioned from an
artist some time ago, and that AI was subsequently used to change its colors.
This is a maintainer-supplied provenance statement, not a verified copyright
assignment, license, or permission to redistribute modified derivatives. The
original commission agreement or artist's permission has not been supplied.

The public release must have a documented ownership/permission record for
each asset before publication. Git object IDs below identify the current
repository bytes, but are **not** proof of copyright ownership.

| Asset | Current role / observation | Git object ID (short) | Rights status |
| --- | --- | --- | --- |
| `assets/anything_plays.ico` | Windows installer/application icon | `f58833b1` | Commissioned betta artwork reported; exact asset derivation and license to confirm |
| `assets/anything_plays.png` | Main logo and application image | `c340dafe` | Creator and use permission to confirm |
| `assets/anything_plays_hd.png` | HD-named copy; identical bytes to `anything_plays.png` | `c340dafe` | Same rights as main logo; deduplication optional |
| `assets/anything_plays_small.png` | Linux desktop icon | `a0b572d7` | Creator and use permission to confirm |
| `assets/betta_gb_advance_original.png` | Historical or alternate image; usage in installers needs confirmation | `96e5af04` | Creator and use permission to confirm |

## Approval checklist

- [x] Record maintainer's statement: original betta fish artwork was commissioned and later AI-recolored; the artist, agreement and per-file derivatives remain unverified.
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
