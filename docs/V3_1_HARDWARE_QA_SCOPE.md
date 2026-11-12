# Anything Plays 3.1.0 — Real-device QA disclosure and owner release scope

**This records the exact extent of hardware acceptance; it does not certify tests that were never performed.**

## Tested by real native runners

- The original clean-source 3.1.0 complete 18-console, 11-core installer set from application revision `104b96621ec4cb8dc39fde8c3fe96fc854c406ed` passed [13/13 native build, installed frozen GUI, Stream Mode and configuration-isolation jobs](https://github.com/MasynNay/anything-plays/actions/runs/43140637755) across Linux, Windows, Mac Apple Silicon and Mac Intel.
- The genuine modified C extension in copied original final installations and frozen Tk startup passed on [Linux](https://github.com/MasynNay/anything-plays/actions/runs/43148388829), [Windows](https://github.com/MasynNay/anything-plays/actions/runs/43149732092), and [both Macs](https://github.com/MasynNay/anything-plays/actions/runs/43149191077).
- The project owner previously reported that the **RC2 Linux** installer installed, launched and displayed Stream Mode successfully. This is real end-user evidence for that earlier build, **not a physical-controller or live-camera claim for final 3.1.0**.

## Explicitly not tested or certified

- A real USB/Bluetooth controller pairing, mapping, disconnect/reconnect and gamepad-to-game interaction in the immutable clean 3.1.0 installers.
- A connected live webcam with multiple tracked physical objects across those exact four final installers.
- Licensed retail game ROM compatibility, audio/video timing, save/reload, Dolphin/N64 native gameplay, hardware longevity, or multi-hour session stability on all four physical host types.

Those features passed the applicable automated and synthetic portions of CI where indicated, but **synthetic events must never be reported as tests on a physical device**.

## Release decision and support policy

Physical testing is valuable product QA, **not an independent copyright/license condition**. The maintainer has repeatedly and expressly instructed publication of the actual 3.1.0 full installers despite being told that physical-controller testing was outstanding. This is documented acceptance to release the candidate with the above limitations disclosed, *not* permission to mark the physical tests passed.

If other release gates are satisfied, a free/noncommercial 3.1.0 portfolio release may disclose these gaps as known limitations and provide GitHub Issues for user-reported failures. Release notes must preserve this explicit scope. Any customer incident should be corrected through a separately tested patch release; the current stable 3.0 and 3.1 RC2 packages must remain available for rollback.

**No exception to third-party notices, pygame-ce LGPL source and compatible-library replacement obligations, or any other applicable distribution terms is given by this hardware QA decision.**
