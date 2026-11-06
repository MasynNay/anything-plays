# Security policy

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting feature for this repository
if it is available. If private reporting is not enabled, contact the project
maintainer privately before publishing exploit details. Do not post sensitive
reproduction material, private game files, or camera footage in a public issue.

## Supported versions

The last published release line is 1.5.x. Version 2.0 is being prepared and is
not yet a public release. Security support and patch timing are not guaranteed
for historical builds; check the Releases page for the current published
version.

## Trust boundaries

Anything Plays accesses local cameras and runs native emulator libraries.
Only install packages from a verified source, and do not run arbitrary DLL,
SO, or DYLIB files passed off as Libretro cores. Build-time downloads from the
Libretro nightly service are not version-pinned; release maintainers must
review their provenance and third-party license obligations before shipping.
