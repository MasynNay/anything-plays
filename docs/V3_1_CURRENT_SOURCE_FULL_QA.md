# Anything Plays 3.1 — Post-RC1 current-source installer QA

**Engineering-only test.** Stable 3.0 and the original public 3.1 RC1 remain unchanged.

## Reason for a new build path

The published 3.1 RC1 four-platform installers were frozen at source revision 26de1e1ad1b701d0735e085158347f8c213ce437, before the recent bezel, camera/game lifecycle, analog hysteresis and reactive controller artwork improvements. Reusing that old pinned assembly without rebuilding the executable would omit those improvements.

## Two native stages, four platforms

The new GitHub Actions workflow builds the current PR head source on Windows x64, Linux x64, macOS Apple Silicon and macOS Intel. Stage one freezes the full Python/Tk/SDL application with only mGBA and emits an exact source SHA and installer SHA-256 receipt. Stage two combines it with exactly eleven original-source native emulator core families from the verified public 3.0.0 native installer. Stable 3.0.0's original checksum manifest must authenticate the native input; the resulting full installer must contain eighteen console profiles.

Both stages use the exact same source SHA, and the second stage verifies a byte-for-byte match between the frozen app installer and the source-stage receipt. A new guarded --expected-source-revision argument is valid only for private PR QA with AP_V31_NEXT_QA=1, AP_V31_RC=1, AP_V31_FULL_TEST_CORES=1, matching AP_V31_QA_CHECKOUT_SHA and git HEAD, with all release-approval variables off. The historical RC1 assembler retains its original SHA pin without these explicit settings.

The workflow uses read-only GitHub permissions and retains temporary QA artifacts and receipts for 30 days. It never uploads to GitHub Releases or publishes a stable build.

## Important installation warning

**These initial refreshed QA installers retain the public RC1 internal application ID and settings namespace.** Do not install them over an existing public RC1 installation. They are disposable runner verification builds, not a separately identified RC2 for general distribution. The final RC2 needs its own independently versioned application, platform installer identities and isolated preferences first.

## Remaining acceptance

Neither these native build jobs nor their technical SDL evidence prove physical webcam or Bluetooth/USB controllers, real retail-game playback, extended saves/audio performance, complete corresponding-source rights, LGPL relinking compliance or stable release approval. All six stable release gates stay false. Installed four-platform frozen-GUI and isolated settings-migration tests must run on exact fresh source assemblies before declaring those particular QA builds usable.
